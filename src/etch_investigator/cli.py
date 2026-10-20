from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from .chat_graph import build_chat_graph
from .graph import build_graph


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_for_interrupt(payload: dict) -> dict:
    if payload["type"] in {"clarification_required", "record_clarification"}:
        print(payload["message"])
        answer = {}
        for item in payload["missing_fields"]:
            raw = input(f"- {item['question']} ").strip()
            if item["field"] == "metrics":
                answer[item["field"]] = json.loads(raw)
            else:
                answer[item["field"]] = raw
        return answer
    if payload["type"] == "question_clarification":
        return input(f"\nAgent: {payload['message']}\n나: ").strip()
    if payload["type"] == "record_offer":
        print("\n" + payload["answer"])
        create = input(f"\nAgent: {payload['message']} [y/N] ").strip().lower() == "y"
        return {"create_report": create}
    print(payload["report"])
    approved = input("\n승인하시겠습니까? [y/N] ").strip().lower() == "y"
    reviewer = input("검토자: ").strip()
    comment = input("의견(선택): ").strip()
    return {"approved": approved, "reviewer": reviewer, "comment": comment}


def main() -> None:
    parser = argparse.ArgumentParser(description="식각 장비 이상 조사 LangGraph Agent")
    parser.add_argument(
        "request",
        type=Path,
        nargs="?",
        help="자동화용 조사 요청 JSON(생략하면 대화형 질문 모드)",
    )
    parser.add_argument("-q", "--question", help="대화형 조사 질문")
    parser.add_argument(
        "--output",
        type=Path,
        nargs="?",
        const=Path("investigation_report.md"),
        default=Path("investigation_report.md"),
        help="결과 Markdown 경로(파일명 생략 시 investigation_report.md)",
    )
    args = parser.parse_args()

    config = {"configurable": {"thread_id": str(uuid4())}}
    if args.request:
        graph = build_graph()
        result = graph.invoke({"request": _read_json(args.request)}, config)
    else:
        graph = build_chat_graph()
        question = args.question or input(
            "조사할 이상을 질문해 주세요.\n"
            "예: ETCH-07 CH-B의 endpoint가 118초로 지연됐어. 관련 사례와 점검 항목을 알려줘.\n\n"
            "나: "
        ).strip()
        if not question:
            parser.error("질문을 입력해 주세요.")
        result = graph.invoke({"question": question, "request": {}}, config)
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        result = graph.invoke(Command(resume=_prompt_for_interrupt(payload)), config)
    if result.get("report") and result.get("status") == "approved":
        args.output.write_text(result["report"], encoding="utf-8")
        print(f"\n상태: {result['status']} / 저장: {args.output.resolve()}")
    elif result.get("answer"):
        print("\n조사를 종료했습니다. 승인용 기록은 생성하지 않았습니다.")


if __name__ == "__main__":
    main()

