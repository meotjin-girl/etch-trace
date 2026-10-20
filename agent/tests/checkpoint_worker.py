"""Separate process used to prove PostgreSQL persistence across restarts."""

import json
import sys

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from agent.graph import TaskInput, build_graph
from agent.models import Report
from agent.tests.support import Events, Evidence


def main() -> None:
    dsn, task_id, raw = sys.argv[1:]
    payload = json.loads(raw)
    events = Events()
    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        graph = build_graph(saver, Evidence(), events)
        config: RunnableConfig = {"configurable": {"thread_id": task_id}}
        value: Command | TaskInput = Command(resume=payload["resume"]) if "resume" in payload else {
            "task_id": task_id, "question": payload["question"],
        }
        graph.invoke(value, config)
        snapshot = graph.get_state(config)
        report = snapshot.values.get("report")
        print(json.dumps({
            "waiting": snapshot.interrupts[0].value["kind"] if snapshot.interrupts else None,
            "report": report.model_dump(mode="json") if isinstance(report, Report) else None,
            "events": [event.model_dump(mode="json") for event in events.values],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
