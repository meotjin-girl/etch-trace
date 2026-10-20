import atexit
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv(Path(__file__).parent.parent / ".env")
DSN = os.getenv("DATABASE_URL", "postgresql://trace:trace@localhost:5432/trace")
pool = ConnectionPool(DSN, kwargs={"autocommit": True, "row_factory": dict_row}, open=True)
atexit.register(pool.close)


def q(sql, params=None):
    with pool.connection() as c:
        cur = c.execute(sql, params)
        return cur.fetchall() if cur.description else []


def init():
    q((Path(__file__).parent / "schema.sql").read_text())


def emit(task_id, type_, payload=None):
    # 진행 이벤트 = task_events 한 행. SSE는 이 테이블을 읽어 중계 (향후 Kafka 토픽 메시지와 1:1)
    q("""INSERT INTO task_events (task_id, seq, type, payload)
         SELECT %s, coalesce(max(seq), 0) + 1, %s, %s FROM task_events WHERE task_id = %s""",
      (task_id, type_, json.dumps(payload or {}, ensure_ascii=False, default=str), task_id))


def set_status(task_id, status, **cols):
    sets = ", ".join(f"{k} = %s" for k in cols)
    vals = [json.dumps(v, ensure_ascii=False) if k == "report" else v for k, v in cols.items()]
    q(f"UPDATE tasks SET status = %s, updated_at = now(){', ' + sets if sets else ''} WHERE id = %s",
      (status, *vals, task_id))
