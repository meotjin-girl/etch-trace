"""Non-blocking HTTP command dispatch; checkpoints remain agent-owned."""

import json
from contextlib import closing
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from uuid import UUID

import anyio
from v1_commands import dispatch_failed, start
from v1_models import Requester, Settings
from v1_store import Row, Store


def send(settings: Settings, tid: UUID, command_id: UUID, body: Row, actor: Requester) -> None:
    url = urlsplit(settings.agent_url)
    transport = HTTPSConnection if url.scheme == "https" else HTTPConnection
    with closing(transport(url.netloc, timeout=30)) as connection:
        connection.request(
            "POST",
            f"{url.path.rstrip('/')}/internal/tasks/{tid}/run",
            body=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": settings.internal_api_key,
                "X-Command-ID": str(command_id),
                "X-Requester-Name": quote(actor.name, safe=""),
                "X-Requester-Role": actor.role,
            },
        )
        with connection.getresponse() as response:
            if not 200 <= response.status < 300:
                raise HTTPError(
                    settings.agent_url,
                    response.status,
                    response.reason,
                    response.headers,
                    None,
                )
            _ = response.read()


async def dispatch(
    store: Store,
    settings: Settings,
    tid: UUID,
    body: Row,
    command_id: UUID | None = None,
) -> None:
    if command_id is None:
        command_id = await anyio.to_thread.run_sync(start, store, tid)
    if command_id is None:
        return
    try:
        actor = await anyio.to_thread.run_sync(store.task_actor, tid)
        await anyio.to_thread.run_sync(send, settings, tid, command_id, body, actor)
    except (OSError, HTTPException) as exc:
        await anyio.to_thread.run_sync(
            dispatch_failed,
            store,
            tid,
            command_id,
            f"Agent HTTP dispatch failed: {exc}",
        )
