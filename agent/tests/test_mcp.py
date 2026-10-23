from fastmcp import Client, FastMCP
from pydantic import JsonValue

from agent.evidence import MCPEvidenceProvider
from agent.models import Case, Context, PhysicsInputs
from agent.tests.support import Evidence


def test_adapter_when_fastmcp_returns_arrays_preserves_real_tool_results(monkeypatch):
    # Given: real in-process FastMCP servers, clients, tool schemas, and dispatch.
    business, rag, physics = FastMCP("business"), FastMCP("rag"), FastMCP("physics")
    evidence = Evidence()
    seen = []

    @business.tool
    def search_cases(context: dict[str, JsonValue]) -> list[Case]:
        parsed = Context.model_validate(context)
        seen.append(("search_cases", parsed))
        return evidence.search_cases(parsed)

    @business.tool
    def analyze_metrics(
        cases: list[dict[str, JsonValue]], metrics: dict[str, float]
    ) -> list[dict[str, JsonValue]]:
        parsed = [Case.model_validate(case) for case in cases]
        seen.append(("analyze_metrics", len(parsed)))
        return [
            metric.model_dump(mode="json")
            for metric in evidence.analyze_metrics(parsed, Context(metrics=metrics))
        ]

    @rag.tool
    def search_documents(document_ids: list[str]) -> list[dict[str, JsonValue]]:
        seen.append(("search_documents", document_ids))
        return [
            {**doc.model_dump(mode="json"), "is_demo": True, "source": "frontend_demo"}
            for doc in evidence.search_documents(document_ids)
        ]

    @physics.tool
    def evaluate_etch_physics(inputs: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
        parsed = Context(physics=PhysicsInputs.model_validate(inputs))
        seen.append(("evaluate_etch_physics", parsed.physics))
        return [item.model_dump(mode="json") for item in evidence.evaluate_etch_physics(parsed)]

    servers = {
        "http://business/mcp": business,
        "http://rag/mcp": rag,
        "http://physics/mcp": physics,
    }
    monkeypatch.setattr("agent.evidence.Client", lambda url: Client(servers[url]))
    adapter = MCPEvidenceProvider("http://business", "http://rag/mcp", "http://physics")
    context = Context(
        equipment="ETCH-07",
        metrics={"endpoint_sec": 94},
        physics=PhysicsInputs(etch_rate_nm_min=500, etch_time_sec=120),
    )
    # When
    cases = adapter.search_cases(context)
    metrics = adapter.analyze_metrics(cases, context)
    documents = adapter.search_documents(["DOC#1"])
    physics_results = adapter.evaluate_etch_physics(context)
    # Then
    assert cases == evidence.cases
    assert metrics[0].value == 94
    assert metrics[0].model_dump()["caseIds"] == [case.id for case in cases]
    assert documents[0].id == "DOC#1"
    assert physics_results[0].result is not None
    assert physics_results[0].result.value == 1000
    assert seen == [
        ("search_cases", Context(equipment="ETCH-07", metrics={"endpoint_sec": 94})),
        ("analyze_metrics", 5),
        ("search_documents", ["DOC#1"]),
        ("evaluate_etch_physics", context.physics),
    ]
