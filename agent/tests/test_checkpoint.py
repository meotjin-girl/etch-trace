import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo


def test_restart_when_postgres_preserves_clarification_review_and_feedback():
    # Given: checkpoint-only schema isolated from application/business tables.
    base_dsn = os.getenv("AGENT_TEST_DATABASE_URL")
    if not base_dsn:
        pytest.skip("Set AGENT_TEST_DATABASE_URL for the real PostgreSQL restart test")
    schema = f"agent_test_{uuid4().hex}"
    task = str(uuid4())
    with psycopg.connect(base_dsn, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    dsn = make_conninfo(base_dsn, options=f"-c search_path={schema}")
    root = Path(__file__).resolve().parents[2]

    def run(payload):
        result = subprocess.run(
            [sys.executable, "-m", "agent.tests.checkpoint_worker", dsn, task, json.dumps(payload)],
            cwd=root, check=True, capture_output=True, text=True, timeout=30,
            env={key: value for key, value in os.environ.items()
                 if key not in {"OPENAI_API_KEY", "OPENAI_MODEL"}},
        )
        return json.loads(result.stdout)

    try:
        first = run({"question": "endpoint 지연 94초"})
        assert first["waiting"] == "clarification"
        second = run({"resume": {"text": "ETCH-07"}})
        assert second["waiting"] == "review"
        # When: a third independent process resumes review with a revision.
        revised = run({"resume": {"action": "revise", "comment": "RF 확인 요청", "by": "engineer"}})
        # Then: feedback and original evidence survive; the revised callback is new.
        assert revised["waiting"] == "review"
        assert revised["report"]["feedback"] == ["RF 확인 요청"]
        assert revised["report"]["scored"] == second["report"]["scored"]
        assert revised["report"]["metrics"] == second["report"]["metrics"]
        assert revised["events"][-1]["event_id"] != second["events"][-1]["event_id"]
        approved = run({"resume": {"action": "approve", "comment": "", "by": "engineer"}})
        assert approved["waiting"] is None
        assert approved["events"][-1]["type"] == "DONE"
        assert approved["events"][-1]["payload"]["report"]["feedback"] == ["RF 확인 요청"]
    finally:
        with psycopg.connect(base_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
