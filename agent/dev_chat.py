"""Run a plain-text conversation against the local Agent HTTP endpoint."""

from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def send_turn(base_url: str, task_id: str, role: str, content: str) -> str:
    """Send one message to the same checkpoint thread and return only its prose."""
    internal_key = os.getenv("INTERNAL_API_KEY")
    if not internal_key:
        raise RuntimeError("INTERNAL_API_KEY 환경변수가 필요합니다.")
    request = Request(
        f"{base_url.rstrip('/')}/internal/tasks/{task_id}/run",
        data=json.dumps({"role": role, "content": content}, ensure_ascii=False).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Internal-Key": internal_key,
            "X-Command-ID": str(uuid4()),
            "X-Requester-Name": os.getenv("TRACE_REQUESTER_NAME", "local-test"),
            "X-Requester-Role": os.getenv("TRACE_REQUESTER_ROLE", "user"),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agent HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Agent 연결 실패: {error.reason}") from error
    return str(payload.get("response", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="TRACE Agent 텍스트 대화 시험")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--role", choices=("user", "system"), default="user")
    parser.add_argument("--task-id", default=str(uuid4()))
    args = parser.parse_args()

    print(f"대화 ID: {args.task_id}")
    print("입력 후 Enter를 누르세요. 종료하려면 /exit 를 입력하세요.")
    role = args.role
    while True:
        try:
            content = input("\n나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if content == "/exit":
            break
        if not content:
            continue
        try:
            print("\nAgent> " + send_turn(args.base_url, args.task_id, role, content))
        except RuntimeError as error:
            print(f"\n오류> {error}")
        role = "user"


if __name__ == "__main__":
    main()
