from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agent.main import create_app
from agent.models import Context, PhysicsInputs
from agent.react_agent import build_react_graph, prepare_request
from agent.tests.support import Evidence
from agent.tools import TOOL_NAMES, build_tools


def _client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app()
    saver = InMemorySaver()
    evidence = Evidence()
    app.state.graph = build_react_graph(saver, evidence)
    app.state.internal_key = "test-key"
    return TestClient(app, headers={"X-Command-ID": str(uuid4())}), evidence


def test_internal_key_when_missing_or_wrong_is_rejected(monkeypatch):
    client, _ = _client(monkeypatch)
    url = f"/internal/tasks/{uuid4()}/run"
    payload = {"role": "user", "content": "압력이 설정값보다 높습니다."}
    assert client.post(url, json=payload).status_code == 403
    assert client.post(url, headers={"X-Internal-Key": "wrong"}, json=payload).status_code == 403


def test_initial_alert_and_user_followups_share_one_conversation_id(monkeypatch):
    client, _ = _client(monkeypatch)
    task_id = str(uuid4())
    url = f"/internal/tasks/{task_id}/run"
    headers = {
        "X-Internal-Key": "test-key",
        "X-Requester-Name": "collaborator",
        "X-Requester-Role": "user",
    }

    initial = client.post(
        url,
        headers=headers,
        json={
            "role": "system",
            "content": "[경보] ETCH-07 / CH-B / Lot LOT-1 / Wafer W01 / OX-120\n"
            "- 15:15:11 FDC WATCH rf_sensor z=4.1 (OCAP-RF)",
        },
    )
    assert initial.status_code == 200
    assert initial.json()["status"] == "completed"
    assert "OPENAI_API_KEY" in initial.json()["response"]

    followup = client.post(
        url,
        headers={"X-Internal-Key": "test-key"},
        json={"role": "user", "content": "원인 후보가 이상해. 다시 찾아줘"},
    )
    assert followup.status_code == 200
    assert followup.json()["response"]

    app = cast(Any, client.app)
    snapshot = app.state.graph.get_state({"configurable": {"thread_id": task_id}})
    assert snapshot.values["context"]["equipment"] == "ETCH-07"
    assert len(snapshot.values["messages"]) == 4
    assert isinstance(snapshot.values["messages"][0], HumanMessage)
    assert isinstance(snapshot.values["messages"][1], AIMessage)


def test_legacy_backend_resume_becomes_user_turn_in_same_thread(monkeypatch):
    client, _ = _client(monkeypatch)
    task_id = str(uuid4())
    url = f"/internal/tasks/{task_id}/run"
    headers = {"X-Internal-Key": "test-key"}
    client.post(url, headers=headers, json={"question": "처음 조사해줘"})
    resumed = client.post(url, headers=headers, json={"resume": {"text": "압력이 높다는 뜻이야"}})
    assert resumed.status_code == 200
    app = cast(Any, client.app)
    snapshot = app.state.graph.get_state({"configurable": {"thread_id": task_id}})
    assert len(snapshot.values["messages"]) == 4
    assert snapshot.values["messages"][2].content == "압력이 높다는 뜻이야"


def test_tools_are_visible_and_ordered_for_the_react_agent():
    tools = build_tools(Evidence())
    assert tuple(tool.name for tool in tools) == TOOL_NAMES
    assert TOOL_NAMES == (
        "search_cases",
        "analyze_metrics",
        "search_documents",
        "search_sop",
        "evaluate_etch_physics",
        "list_investigations",
        "record_selection",
    )
    physics = next(tool for tool in tools if tool.name == "evaluate_etch_physics")
    assert "D=R*t" in physics.description


def test_react_graph_loops_from_toolnode_back_to_model(monkeypatch):
    evidence = Evidence()
    calls = []

    def fake_llm(model, system_prompt, messages, tools):
        calls.append((system_prompt, messages, tools))
        if len(calls) == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "evaluate_etch_physics",
                                        "arguments": (
                                            '{"inputs":{"etch_rate_nm_min":500,'
                                            '"etch_time_sec":120}}'
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"content": "예상 식각 깊이는 1,000 nm입니다."}}]}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr("agent.react_agent._call_llm", fake_llm)
    graph = build_react_graph(InMemorySaver(), evidence)
    task_id = str(uuid4())
    result = graph.invoke(
        prepare_request("user", "식각 속도 500 nm/min, 식각 시간 120초일 때 깊이를 계산해줘"),
        {"configurable": {"thread_id": task_id}, "recursion_limit": 20},
    )
    assert len(calls) == 2
    assert "evaluate_etch_physics" in str(calls[0][2])
    assert isinstance(calls[1][1][-1], ToolMessage)
    assert "1000" in str(calls[1][1][-1].content)
    assert result["messages"][-1].content == "예상 식각 깊이는 1,000 nm입니다."
    physics_result = evidence.evaluate_etch_physics(
        Context(physics=PhysicsInputs(etch_rate_nm_min=500, etch_time_sec=120))
    )[0].result
    assert physics_result is not None
    assert physics_result.value == 1000
