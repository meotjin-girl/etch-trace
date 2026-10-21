"""Exercise the public MCP HTTP gateway against an internal HTTP backend."""

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, quote, urlsplit
from uuid import uuid4

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import business


class HistoryHttpTest(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.status = 200
        self.payload = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                test.seen.append((self.path, self.headers.get("X-Internal-Key")))
                self.send_response(test.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(test.payload).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        env = patch.dict(os.environ, {
            "BACKEND_URL": f"http://127.0.0.1:{server.server_port}",
            "INTERNAL_API_KEY": "test-secret",
        })
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(business.mcp.http_app())
        self.addCleanup(self.client.close)
        self.headers = {"X-User-Name": quote("작업자 %20 / A"), "X-User-Role": "worker"}

    def test_list_forwards_identity_and_server_key(self):
        response = self.client.get("/api/ai/investigations?user_role=admin", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        path, key = self.seen[0]
        self.assertEqual(urlsplit(path).path, "/internal/investigations")
        self.assertEqual(parse_qs(urlsplit(path).query), {
            "user_name": [self.headers["X-User-Name"]], "user_role": ["worker"],
        })
        self.assertEqual(key, "test-secret")

    def test_detail_returns_snapshot(self):
        tid = str(uuid4())
        self.payload = {"id": tid, "report": {"summary": "승인"}}
        response = self.client.get(f"/api/ai/investigations/{tid}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.payload)
        self.assertEqual(urlsplit(self.seen[0][0]).path, f"/internal/investigations/{tid}")

    def test_invalid_identity_never_calls_backend(self):
        for headers in ({}, {**self.headers, "X-User-Role": "unknown"},
                        {**self.headers, "X-User-Name": "%20"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get("/api/ai/investigations", headers=headers).status_code, 401)
        self.assertEqual(self.seen, [])

    def test_invalid_id_never_calls_backend(self):
        response = self.client.get("/api/ai/investigations/not-a-uuid", headers=self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.seen, [])

    def test_access_failures_preserve_status(self):
        for status in (401, 403, 404, 422):
            with self.subTest(status=status):
                self.status = status
                response = self.client.get(f"/api/ai/investigations/{uuid4()}", headers=self.headers)
                self.assertEqual(response.status_code, status)

    def test_upstream_failure_is_not_empty_history(self):
        self.status = 500
        response = self.client.get("/api/ai/investigations", headers=self.headers)
        self.assertEqual(response.status_code, 502)
        with patch.object(business, "_read_investigations", side_effect=OSError("unavailable")):
            response = self.client.get("/api/ai/investigations", headers=self.headers)
        self.assertEqual(response.status_code, 502)

    def test_malformed_response_and_non_get(self):
        self.payload = {"unexpected": "object"}
        self.assertEqual(self.client.get("/api/ai/investigations", headers=self.headers).status_code, 502)
        self.assertEqual(self.client.post("/api/ai/investigations", headers=self.headers).status_code, 405)
