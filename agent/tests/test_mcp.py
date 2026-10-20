from fastmcp import Client, FastMCP
from pydantic import JsonValue

from agent.evidence import MCPEvidenceProvider
from agent.models import Case, Context
from agent.tests.support import Evidence


def test_adapter_when_fastmcp_returns_arrays_preserves_real_tool_results(monkeypatch):
    # Given: real in-process FastMCP servers, clients, tool schemas, and dispatch.
    business, rag = FastMCP("business"), FastMCP("rag")
    evidence = Evidence()
    seen = []

    @business.tool
    def search_cases(context: dict[str, JsonValue]) -> list[Case]:
        parsed = Context.model_validate(context)
        seen.append(("search_cases", parsed))
        return evidence.search_cases(parsed)

    @business.tool
    def analyze_metrics(cases: list[dict[str, JsonValue]],
                        metrics: dict[str, float]) -> list[dict[str, JsonValue]]:
        parsed = [Case.model_validate(case) for case in cases]
        seen.append(("analyze_metrics", len(parsed)))
        return [metric.model_dump(mode="json") for metric in
                evidence.analyze_metrics(parsed, Context(metrics=metrics))]

    @rag.tool
    def search_documents(document_ids: list[str]) -> list[dict[str, JsonValue]]:
        seen.append(("search_documents", document_ids))
        return [
            {**doc.model_dump(mode="json"), "is_demo": True, "source": "frontend_demo"}
            for doc in evidence.search_documents(document_ids)
        ]

    servers = {"http://business/mcp": business, "http://rag/mcp": rag}
    monkeypatch.setattr("agent.evidence.Client", lambda url: Client(servers[url]))
    adapter = MCPEvidenceProvider("http://business", "http://rag/mcp")
    context = Context(equipment="ETCH-07", metrics={"endpoint_sec": 94})
    # When
    cases = adapter.search_cases(context)
    metrics = adapter.analyze_metrics(cases, context)
    documents = adapter.search_documents(["DOC#1"])
    # Then
    assert cases == evidence.cases
    assert metrics[0].value == 94
    assert metrics[0].model_dump()["caseIds"] == [case.id for case in cases]
    assert documents[0].id == "DOC#1"
    assert seen == [
        ("search_cases", context), ("analyze_metrics", 5), ("search_documents", ["DOC#1"]),
    ]
