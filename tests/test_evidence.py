from __future__ import annotations

import json
import math
import os
import sys
import threading
import unittest
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar, override
from unittest.mock import patch

import anyio
import psycopg
from fastmcp import Client
from fastmcp.exceptions import ToolError
from psycopg.rows import class_row
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
# These are script directories, not a local package named "mcp": that name
# belongs to FastMCP's protocol SDK dependency.
sys.path.insert(0, str(ROOT / "mcp"))
sys.path.insert(0, str(ROOT / "db"))

import business
import rag
from evidence import (
    Case,
    Context,
    MetricAnalysis,
    ScoredCase,
    analyze_metrics,
    search_cases,
    similarity,
)
from seed import seed


def demo_cases() -> list[Case]:
    return TypeAdapter(list[Case]).validate_json(
        (ROOT / "db/cases.json").read_bytes()
    )


@contextmanager
def backend(
    cases: list[Case], expected_key: str = "test-secret"
) -> Generator[tuple[str, list[tuple[str, str | None]]]]:
    """Serve the actual internal HTTP contract, including its key check."""
    requests: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            key = self.headers.get("X-Internal-Key")
            requests.append((self.path, key))
            if key != expected_key:
                self.send_error(403)
                return
            if self.path != "/internal/cases":
                self.send_error(404)
                return
            body = json.dumps(cases).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            _ = self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: str | int) -> None:
            return

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", requests
        finally:
            server.shutdown()
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError("Test backend did not shut down")


class InvestigationTest(unittest.TestCase):
    def test_history_reads_forward_identity_and_internal_key(self):
        from urllib.parse import parse_qs, urlsplit
        from uuid import uuid4
        seen = []
        tid = str(uuid4())

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                target = urlsplit(self.path)
                seen.append((target.path, parse_qs(target.query), self.headers["X-Internal-Key"]))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"id":"saved"}' if target.path.endswith(tid) else b'[]')

            def log_message(self, *args):
                pass

        async def read():
            async with Client(business.mcp) as client:
                args = {"user_name": "작업자 / A", "user_role": "worker"}
                listing = await client.call_tool("list_investigations", args)
                detail = await client.call_tool("get_investigation", {**args, "task_id": tid})
                self.assertEqual(listing.structured_content, {"result": []})
                self.assertEqual(detail.structured_content, {"id": "saved"})

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                with patch.dict(os.environ, {
                    "BACKEND_URL": f"http://127.0.0.1:{server.server_port}",
                    "INTERNAL_API_KEY": "test-secret",
                }):
                    anyio.run(read)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual([row[0] for row in seen], [
            "/internal/investigations", f"/internal/investigations/{tid}",
        ])
        for _, query, key in seen:
            self.assertEqual(query, {"user_name": ["작업자 / A"], "user_role": ["worker"]})
            self.assertEqual(key, "test-secret")

    def test_save_forwards_ids_payload_and_propagates_backend_rejection(self):
        from uuid import uuid4
        seen = []
        status = [200]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path, self.headers, json.loads(
                    self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(status[0])
                self.end_headers()
                self.wfile.write(b'{"accepted":true,"duplicate":false}')

            def log_message(self, *args):
                pass

        async def call():
            async with Client(business.mcp) as client:
                return await client.call_tool("save_investigation", args)

        tid, cid = str(uuid4()), str(uuid4())
        args = {"task_id": tid, "command_id": cid, "event_id": "done-1",
                "payload": {"report": {"summary": "승인 보고서", "demo": True}}}
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                with patch.dict(os.environ, {
                    "BACKEND_URL": f"http://127.0.0.1:{server.server_port}",
                    "INTERNAL_API_KEY": "test-secret",
                }):
                    result = anyio.run(call)
                    self.assertEqual(result.structured_content, {"accepted": True, "duplicate": False})
                    status[0] = 409
                    with self.assertRaises(ToolError):
                        anyio.run(call)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        path, headers, body = seen[0]
        self.assertEqual(path, f"/internal/tasks/{tid}/investigation")
        self.assertEqual(headers["X-Command-ID"], cid)
        self.assertEqual(headers["X-Internal-Key"], "test-secret")
        self.assertEqual(body, {"type": "DONE", "event_id": "done-1", "payload": args["payload"]})


class EvidenceTest(unittest.TestCase):
    def test_seed_ids_units_demo_labels_and_document_linkage(self) -> None:
        # Given
        cases = demo_cases()
        documents = TypeAdapter(list[rag.Document]).validate_json(
            (ROOT / "db/documents.json").read_bytes()
        )
        # When
        case_ids = {case["id"] for case in cases}
        linked_ids = {doc_id for case in cases for doc_id in case["docs"]}
        # Then
        self.assertEqual(
            case_ids,
            {"ETCH-2025-014", "ETCH-2025-031", "ETCH-2025-044",
             "ETCH-2025-052", "ETCH-2026-006"},
        )
        self.assertEqual(len(cases), 5)
        self.assertEqual(len(documents), 5)
        self.assertEqual(linked_ids, {document["id"] for document in documents})
        for case in cases:
            self.assertTrue(case.get("is_demo"))
            self.assertEqual(case.get("source"), "frontend_demo")
            self.assertEqual(
                case.get("metric_units"),
                {"endpoint_sec": "sec", "etch_rate_nm_min": "nm/min",
                 "rf_reflected_w": "W", "pressure_mtorr": "mTorr"},
            )
        for document in documents:
            self.assertTrue(document.get("is_demo"))
            self.assertEqual(document.get("source"), "frontend_demo")
            self.assertTrue(document["title"])
            self.assertTrue(document["text"])

    def test_similarity_uses_frontend_weights_and_token_cap(self) -> None:
        # Given
        case = demo_cases()[0]
        context: Context = {
            "equipment": "ETCH-07", "chamber": "CH-B", "recipe": "OX-120",
            "symptom": "ETCH rate 저하 · endpoint 지연",
            "metrics": {"endpoint_sec": 118, "pressure_mtorr": 50},
        }
        # When
        score = similarity(case, context)
        # Then
        self.assertAlmostEqual(score, 1.0)

    def test_search_threshold_ranking_and_frontend_shape(self) -> None:
        # Given
        cases = demo_cases()
        context: Context = {
            "equipment": "ETCH-07", "chamber": "CH-B", "recipe": "OX-120",
            "symptom": "endpoint 지연", "metrics": {"endpoint_sec": 118},
        }
        # When
        results = search_cases(cases, context)
        # Then
        self.assertEqual(
            [case["id"] for case in results],
            ["ETCH-2025-014", "ETCH-2025-031", "ETCH-2026-006",
             "ETCH-2025-052", "ETCH-2025-044"],
        )
        for actual, expected in zip(
            [case["score"] for case in results], [0.9, 0.9, 0.8, 0.7, 0.5]
        ):
            self.assertAlmostEqual(actual, expected)
        self.assertNotIn("score", cases[0])
        self.assertEqual(results[0]["metrics"], cases[0]["metrics"])
        self.assertEqual(results[0]["docs"], cases[0]["docs"])

    def test_search_includes_threshold_and_limits_stable_ties(self) -> None:
        # Given
        cases: list[Case] = [{**demo_cases()[0], "id": str(index)} for index in range(8)]
        # When
        results = search_cases(cases, {"recipe": "OX-120"})
        # Then
        self.assertEqual([case["id"] for case in results], ["0", "1", "2", "3", "4"])
        self.assertEqual([case["score"] for case in results], [0.25] * 5)

    def test_search_omits_cases_below_threshold(self) -> None:
        # Given
        cases = demo_cases()
        # When
        results = search_cases(cases, {"chamber": "CH-B"})
        # Then
        self.assertEqual(results, [])

    def test_metrics_use_population_statistics_and_source_ids(self) -> None:
        # Given
        cases = demo_cases()
        # When
        result = analyze_metrics(cases, {"endpoint_sec": 118})[0]
        # Then
        self.assertEqual(result["key"], "endpoint_sec")
        self.assertEqual(result["value"], 118)
        self.assertAlmostEqual(result["mean"], 92.4)
        self.assertAlmostEqual(result["std"], math.sqrt(5.84))
        self.assertAlmostEqual(result["deltaPct"], 25.6 / 92.4 * 100)
        z = result["z"]
        assert z is not None
        self.assertAlmostEqual(z, 25.6 / math.sqrt(5.84))
        self.assertEqual(result["severity"], "비정상")
        self.assertEqual(result["unit"], "sec")
        self.assertEqual(
            result["supporting_case_ids"], [case["id"] for case in cases]
        )

    def test_metrics_link_only_finite_present_observations(self) -> None:
        # Given
        template = demo_cases()[0]
        cases: list[Case] = [
            {**template, "id": "valid", "metrics": {"endpoint_sec": 10}},
            {**template, "id": "missing", "metrics": {}},
            {**template, "id": "nan", "metrics": {"endpoint_sec": math.nan}},
            {**template, "id": "infinite", "metrics": {"endpoint_sec": math.inf}},
        ]
        # When
        result = analyze_metrics(cases, {"endpoint_sec": 11, "unknown": 1})
        # Then
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["supporting_case_ids"], ["valid"])
        self.assertEqual(result[0]["mean"], 10)
        self.assertEqual(result[0]["std"], 0)
        self.assertIsNone(result[0]["z"])
        self.assertEqual(result[0]["severity"], "주의")

    def test_zero_mean_and_zero_variance_match_frontend(self) -> None:
        # Given
        case: Case = {**demo_cases()[0], "metrics": {"endpoint_sec": 0}}
        # When
        result = analyze_metrics([case], {"endpoint_sec": 100})[0]
        # Then
        self.assertEqual(result["deltaPct"], 0)
        self.assertIsNone(result["z"])
        self.assertEqual(result["severity"], "정상")

    def test_metrics_severity_boundaries_without_variance(self) -> None:
        # Given
        case: Case = {**demo_cases()[0], "metrics": {"endpoint_sec": 100}}
        # When
        results = [
            analyze_metrics([case], {"endpoint_sec": value})[0]["severity"]
            for value in [109, 110, 120, 90, 80]
        ]
        # Then
        self.assertEqual(results, ["정상", "주의", "비정상", "주의", "비정상"])

    def test_metrics_severity_can_be_driven_by_z_score(self) -> None:
        # Given
        template = demo_cases()[0]
        cases: list[Case] = [
            {**template, "metrics": {"endpoint_sec": 99}},
            {**template, "metrics": {"endpoint_sec": 101}},
        ]
        # When
        results = [
            analyze_metrics(cases, {"endpoint_sec": value})[0]["severity"]
            for value in [100, 101, 102]
        ]
        # Then
        self.assertEqual(results, ["정상", "주의", "비정상"])

    def test_empty_observations_return_no_metrics(self) -> None:
        # Given
        cases: list[Case] = []
        # When
        results = analyze_metrics(cases, {"endpoint_sec": 118})
        # Then
        self.assertEqual(results, [])


class BusinessMCPTest(unittest.TestCase):
    def test_mcp_dispatch_reads_authenticated_backend_and_links_analysis(self) -> None:
        # Given
        cases = demo_cases()
        context: Context = {"equipment": "ETCH-07", "metrics": {"endpoint_sec": 118}}

        async def scenario() -> None:
            async with Client(business.mcp) as client:
                # When
                found = await client.call_tool("search_cases", {"context": context})
                assert found.structured_content is not None
                scored = TypeAdapter(list[ScoredCase]).validate_python(
                    found.structured_content["result"]
                )
                analyzed = await client.call_tool(
                    "analyze_metrics",
                    {"cases": scored, "metrics": {"endpoint_sec": 118}},
                )
                assert analyzed.structured_content is not None
                metrics = TypeAdapter(list[MetricAnalysis]).validate_python(
                    analyzed.structured_content["result"]
                )
                # Then
                self.assertEqual(scored, search_cases(cases, context))
                self.assertEqual(metrics, analyze_metrics(scored, context["metrics"]))
                self.assertTrue(scored[0].get("is_demo"))

        with backend(cases) as (url, requests), patch.dict(
            os.environ, {"BACKEND_URL": url, "INTERNAL_API_KEY": "test-secret"}
        ):
            anyio.run(scenario)
        self.assertEqual(requests, [("/internal/cases", "test-secret")])

    def test_backend_auth_failure_is_a_tool_error(self) -> None:
        # Given
        async def scenario() -> None:
            async with Client(business.mcp) as client:
                # When / Then
                with self.assertRaises(ToolError):
                    _ = await client.call_tool("search_cases", {"context": {}})

        with backend(demo_cases()) as (url, requests), patch.dict(
            os.environ, {"BACKEND_URL": url, "INTERNAL_API_KEY": "wrong-key"}
        ):
            anyio.run(scenario)
        self.assertEqual(requests, [("/internal/cases", "wrong-key")])

    def test_empty_document_request_needs_no_database(self) -> None:
        # Given
        async def scenario() -> None:
            async with Client(rag.mcp) as client:
                # When
                result = await client.call_tool("search_documents", {"document_ids": []})
                # Then
                self.assertEqual(result.structured_content, {"result": []})

        with patch.dict(os.environ, {}, clear=True):
            anyio.run(scenario)


@unittest.skipUnless(
    os.getenv("EVIDENCE_TEST_DATABASE_URL"), "Requires an isolated PostgreSQL database"
)
class PostgreSQLEvidenceTest(unittest.TestCase):
    database_url: ClassVar[str]

    @classmethod
    @override
    def setUpClass(cls) -> None:
        cls.database_url = os.environ["EVIDENCE_TEST_DATABASE_URL"]
        seed(cls.database_url, ROOT / "db/schema.sql")

    def test_seed_is_idempotent_and_preserves_json_values(self) -> None:
        # Given
        with psycopg.Connection[rag.DocumentRow].connect(
            self.database_url, row_factory=class_row(rag.DocumentRow)
        ) as connection:
            before = connection.execute(
                "SELECT id, data::text FROM etch_cases ORDER BY id"
            ).fetchall()
        # When
        seed(self.database_url, ROOT / "db/schema.sql")
        # Then
        with psycopg.Connection[rag.DocumentRow].connect(
            self.database_url, row_factory=class_row(rag.DocumentRow)
        ) as connection:
            after = connection.execute(
                "SELECT id, data::text FROM etch_cases ORDER BY id"
            ).fetchall()
            document_count = len(connection.execute(
                "SELECT id, data::text FROM etch_documents"
            ).fetchall())
        self.assertEqual(before, after)
        self.assertEqual(
            [TypeAdapter(Case).validate_json(row.data) for row in after], demo_cases()
        )
        self.assertEqual(document_count, 5)

    def test_rag_mcp_resolves_exact_ids_and_preserves_source_links(self) -> None:
        # Given
        ids = ["WI-PM-07#3.1", "missing", "SOP-ETCH-12#4.2", "WI-PM-07#3.1"]

        async def scenario() -> None:
            async with Client(rag.mcp) as client:
                # When
                result = await client.call_tool("search_documents", {"document_ids": ids})
                assert result.structured_content is not None
                documents = TypeAdapter(list[rag.Document]).validate_python(
                    result.structured_content["result"]
                )
                # Then
                self.assertEqual(
                    [document["id"] for document in documents],
                    ["WI-PM-07#3.1", "SOP-ETCH-12#4.2"],
                )
                for document in documents:
                    self.assertTrue(document["title"])
                    self.assertTrue(document["text"])
                    self.assertTrue(document.get("is_demo"))
                    self.assertEqual(document.get("source"), "frontend_demo")

        with patch.dict(os.environ, {"DATABASE_URL": self.database_url}):
            anyio.run(scenario)


if __name__ == "__main__":
    _ = unittest.main()
