import unittest
from pathlib import Path
from unittest.mock import patch

from langgraph.types import Command

from etch_investigator import build_chat_graph, build_graph
from etch_investigator.cli import main


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


class WorkflowTest(unittest.TestCase):
    def test_natural_language_question_returns_answer_without_record(self):
        graph = build_chat_graph()
        config = _config("chat-answer")
        result = graph.invoke(
            {
                "question": (
                    "ETCH-07 CH-B의 OX-120 공정에서 endpoint가 118초로 지연되고 "
                    "RF reflected power가 29W로 상승했어. 관련 사례와 점검 항목을 알려줘."
                ),
                "request": {},
            },
            config,
        )
        payload = result["__interrupt__"][0].value
        self.assertEqual(payload["type"], "record_offer")
        self.assertIn("ETCH-2025-031", payload["answer"])
        self.assertIn("SPEC-RF-03#2.4", payload["answer"])
        self.assertEqual(result["request"]["metrics"]["endpoint_sec"], 118.0)

        result = graph.invoke(Command(resume={"create_report": False}), config)
        self.assertEqual(result["status"], "answered")
        self.assertFalse(result["wants_report"])

    def test_question_clarification_then_report_flow(self):
        graph = build_chat_graph()
        config = _config("chat-report")
        result = graph.invoke({"question": "비슷한 이상 사례를 찾아줘", "request": {}}, config)
        self.assertEqual(
            result["__interrupt__"][0].value["type"], "question_clarification"
        )
        result = graph.invoke(
            Command(resume="ETCH-07 CH-B에서 endpoint가 118초로 지연됐어"), config
        )
        self.assertEqual(result["__interrupt__"][0].value["type"], "record_offer")
        result = graph.invoke(Command(resume={"create_report": True}), config)
        payload = result["__interrupt__"][0].value
        self.assertEqual(payload["type"], "record_clarification")
        self.assertEqual(
            {item["field"] for item in payload["missing_fields"]},
            {"event_time", "recipe"},
        )
        result = graph.invoke(
            Command(
                resume={
                    "event_time": "2026-10-19T09:35:00+09:00",
                    "recipe": "OX-120",
                }
            ),
            config,
        )
        self.assertEqual(result["__interrupt__"][0].value["type"], "approval_required")

    def test_output_flag_without_path_uses_default(self):
        with patch(
            "sys.argv",
            ["etch-investigate", "examples/request_complete.json", "--output"],
        ), patch("etch_investigator.cli.build_graph") as graph_builder:
            graph_builder.return_value.invoke.return_value = {
                "report": "# test\n",
                "status": "approved",
            }
            with patch.object(Path, "write_text") as write_text:
                main()
            write_text.assert_called_once_with("# test\n", encoding="utf-8")

    def test_missing_information_interrupt_then_approval(self):
        graph = build_graph()
        config = _config("missing-flow")
        result = graph.invoke(
            {"request": {"equipment_id": "ETCH-07", "symptom": "etch rate 저하"}},
            config,
        )
        payload = result["__interrupt__"][0].value
        self.assertEqual(payload["type"], "clarification_required")
        self.assertEqual(
            {item["field"] for item in payload["missing_fields"]},
            {"chamber_id", "event_time", "recipe", "metrics"},
        )

        result = graph.invoke(
            Command(
                resume={
                    "chamber_id": "CH-B",
                    "event_time": "2026-10-19T09:35:00+09:00",
                    "recipe": "OX-120",
                    "metrics": {"etch_rate_nm_min": 430, "endpoint_sec": 118},
                }
            ),
            config,
        )
        self.assertEqual(result["__interrupt__"][0].value["type"], "approval_required")
        self.assertIn("ETCH-2025-014", result["report"])

    def test_complete_request_produces_evidence_backed_report_and_approval(self):
        graph = build_graph()
        config = _config("complete-flow")
        request = {
            "equipment_id": "ETCH-07",
            "chamber_id": "CH-B",
            "event_time": "2026-10-19T09:35:00+09:00",
            "recipe": "OX-120",
            "product": "P-A17",
            "symptom": "etch rate 저하 endpoint 지연 RF reflected power 상승",
            "metrics": {"etch_rate_nm_min": 430, "endpoint_sec": 118, "rf_reflected_w": 29},
        }
        result = graph.invoke({"request": request}, config)
        self.assertEqual(result["__interrupt__"][0].value["type"], "approval_required")
        self.assertTrue(any(item["severity"] == "abnormal" for item in result["analyses"]))
        self.assertIn("SOP-ETCH-12", result["report"])

        result = graph.invoke(
            Command(resume={"approved": True, "reviewer": "홍길동", "comment": "근거 확인"}),
            config,
        )
        self.assertEqual(result["status"], "approved")
        self.assertIn("승인자: 홍길동", result["report"])
        self.assertIn("- [x] 조사 책임자 검토 및 승인", result["report"])


if __name__ == "__main__":
    unittest.main()

