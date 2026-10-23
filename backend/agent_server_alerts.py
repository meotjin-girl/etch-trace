"""Submit closed alert bundles directly to Agent Server, without legacy tasks."""

import logging
from typing import Final
from uuid import UUID

import anyio
import httpx2
from pydantic import ValidationError
from v1_alerts import POLL_S, AlertBundle, AlertPoller, Prometheus, render
from v1_models import Output, Settings

log: Final = logging.getLogger(__name__)


class ThreadCreated(Output):
    thread_id: UUID


async def submit(settings: Settings, bundle: AlertBundle) -> UUID:
    """Create a thread and start exactly one run; failed requests are not retried."""
    async with httpx2.AsyncClient(
        base_url=settings.agent_server_url.rstrip("/") + "/",
        headers={"X-Internal-Key": settings.internal_api_key},
        timeout=httpx2.Timeout(connect=5, read=30, write=10, pool=10),
        limits=httpx2.Limits(max_connections=10, max_keepalive_connections=5),
    ) as client:
        response = await client.post("threads", json={})
        _ = response.raise_for_status()
        thread = ThreadCreated.model_validate_json(response.content)
        response = await client.post(
            f"threads/{thread.thread_id}/runs",
            json={
                "assistant_id": "trace",
                "input": {"request": {"role": "system", "content": render(bundle)}},
                "multitask_strategy": "reject",
            },
        )
        _ = response.raise_for_status()
    return thread.thread_id


async def watch(settings: Settings) -> None:
    """Reuse the poller's in-memory lifecycle, without a new dedup or retry store."""
    poller = AlertPoller(Prometheus(settings.prometheus_url), known=lambda _key: False)
    while True:
        try:
            bundles = await anyio.to_thread.run_sync(poller.poll)
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            log.error("alert poll failed", extra={"error_type": type(exc).__name__})
        else:
            for bundle in bundles:
                try:
                    thread_id = await submit(settings, bundle)
                except (httpx2.HTTPError, ValidationError) as exc:
                    log.error(
                        "agent server alert submit failed",
                        extra={"alert_key": bundle.key, "error_type": type(exc).__name__},
                    )
                else:
                    log.info(
                        "agent server alert submitted",
                        extra={"alert_key": bundle.key, "thread_id": str(thread_id)},
                    )
        await anyio.sleep(POLL_S)
