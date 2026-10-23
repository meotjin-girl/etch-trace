"""MCP-only business evidence access; no business database connection."""

from dataclasses import dataclass
from typing import Protocol

import anyio
from fastmcp import Client
from pydantic import BaseModel, JsonValue

from .models import (
    Case,
    Context,
    Document,
    EducationalSimulationResult,
    Metric,
    PhysicsResult,
    QuantitativeResult,
    Requester,
    SensorAnalysis,
)


class ToolEnvelope[T](BaseModel):
    result: list[T]


class EvidenceProvider(Protocol):
    def search_cases(self, context: Context) -> list[Case]: ...

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]: ...

    def search_documents(self, document_ids: list[str]) -> list[Document]: ...

    def evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]: ...

    def analyze_etch_quantitatively(self, context: Context) -> list[QuantitativeResult]: ...

    def analyze_sensor_run(self, context: Context) -> SensorAnalysis: ...

    def simulate_etch_education(
        self, context: Context, sensor: SensorAnalysis | None,
    ) -> EducationalSimulationResult | None: ...


class HistoryEvidenceReader(Protocol):
    def list_investigations(self, requester: Requester) -> list[dict[str, JsonValue]]: ...


class SopRagSearcher(Protocol):
    def search_sop(self, query: str) -> list[Document]: ...


def mcp_url(base: str) -> str:
    """Accept either a service base URL or its explicit MCP endpoint."""
    base = base.rstrip("/")
    return base if base.endswith("/mcp") else f"{base}/mcp"


@dataclass(frozen=True, slots=True)
class MCPEvidenceProvider:
    business_url: str
    rag_url: str
    physics_url: str = ""
    sensor_url: str = ""

    async def _search_cases(self, context: Context) -> list[Case]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "search_cases", {"context": {
                    key: value for key, value in context.model_dump(exclude_none=True).items()
                    if key != "physics"
                }},
            )
        return ToolEnvelope[Case].model_validate(result.structured_content).result

    async def _analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool(
                "analyze_metrics",
                {
                    "cases": [case.model_dump() for case in cases],
                    "metrics": context.metrics,
                },
            )
        return ToolEnvelope[Metric].model_validate(result.structured_content).result

    async def _search_documents(self, document_ids: list[str]) -> list[Document]:
        async with Client(mcp_url(self.rag_url)) as client:
            result = await client.call_tool(
                "search_documents", {"document_ids": document_ids},
            )
        return ToolEnvelope[Document].model_validate(result.structured_content).result

    async def _search_sop(self, query: str) -> list[Document]:
        async with Client(mcp_url(self.rag_url)) as client:
            result = await client.call_tool("search_sop", {"query": query})
        return ToolEnvelope[Document].model_validate(result.structured_content).result

    async def _list_investigations(
        self, requester: Requester,
    ) -> list[dict[str, JsonValue]]:
        async with Client(mcp_url(self.business_url)) as client:
            result = await client.call_tool("list_investigations", {
                "user_name": requester.name, "user_role": requester.role,
            })
        return ToolEnvelope[dict[str, JsonValue]].model_validate(
            result.structured_content,
        ).result

    async def _evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]:
        async with Client(mcp_url(self.physics_url)) as client:
            result = await client.call_tool(
                "evaluate_etch_physics", {"inputs": context.physics.model_dump(
                    include={
                        "etch_rate_nm_min", "etch_time_sec", "pre_thickness_nm",
                        "post_thickness_nm", "target_etch_rate_nm_min",
                        "mask_etch_rate_nm_min", "sources",
                    },
                )},
            )
        return ToolEnvelope[PhysicsResult].model_validate(result.structured_content).result

    async def _analyze_etch_quantitatively(
        self, context: Context,
    ) -> list[QuantitativeResult]:
        async with Client(mcp_url(self.physics_url)) as client:
            result = await client.call_tool("analyze_etch_quantitatively", {"inputs": {
                "measured_etch_depth_nm": context.physics.measured_etch_depth_nm,
                "target_etch_depth_nm": context.physics.target_etch_depth_nm,
                "depth_control_limit": (
                    context.physics.depth_control_limit.model_dump()
                    if context.physics.depth_control_limit else None
                ),
                "rate_intervals": [item.model_dump() for item in context.physics.rate_intervals],
            }})
        return ToolEnvelope[QuantitativeResult].model_validate(
            result.structured_content,
        ).result

    async def _analyze_sensor_run(self, context: Context) -> SensorAnalysis:
        if not self.sensor_url:
            return SensorAnalysis(
                problem="센서 시계열에서 이상 시작·지속·동반 신호와 관련 OCAP 근거 확인",
                status="INSUFFICIENT_DATA", missing_fields=["SENSOR_MCP_URL"],
            )
        async with Client(mcp_url(self.sensor_url)) as client:
            result = await client.call_tool("analyze_current_etch_run", {
                "equipment": context.equipment,
                "chamber": context.chamber,
                "recipe": context.recipe,
            })
        return SensorAnalysis.model_validate(result.structured_content)

    async def _simulate_etch_education(
        self, context: Context, sensor: SensorAnalysis | None,
    ) -> EducationalSimulationResult | None:
        if not context.physics.simulation_requested:
            return None
        async with Client(mcp_url(self.physics_url)) as client:
            result = await client.call_tool("simulate_educational_etch", {"inputs": {
                "base_etch_rate_nm_min": context.physics.etch_rate_nm_min,
                "feature_width_nm": context.physics.feature_width_nm,
                "arde_coefficient": context.physics.arde_coefficient,
                "arde_coefficient_source": context.physics.sources.get(
                    "arde_coefficient",
                    "TRACE educational assumption v1; not literature-derived or calibrated",
                ),
                "process_points": [
                    item.model_dump() for item in (sensor.process_series if sensor else [])
                ],
                "source_run_id": sensor.target_run_id if sensor else None,
            }})
        return EducationalSimulationResult.model_validate(result.structured_content)

    def search_cases(self, context: Context) -> list[Case]:
        return anyio.run(self._search_cases, context)

    def analyze_metrics(self, cases: list[Case], context: Context) -> list[Metric]:
        return anyio.run(self._analyze_metrics, cases, context)

    def search_documents(self, document_ids: list[str]) -> list[Document]:
        return anyio.run(self._search_documents, document_ids)

    def search_sop(self, query: str) -> list[Document]:
        return anyio.run(self._search_sop, query)

    def evaluate_etch_physics(self, context: Context) -> list[PhysicsResult]:
        return anyio.run(self._evaluate_etch_physics, context)

    def analyze_etch_quantitatively(self, context: Context) -> list[QuantitativeResult]:
        return anyio.run(self._analyze_etch_quantitatively, context)

    def analyze_sensor_run(self, context: Context) -> SensorAnalysis:
        return anyio.run(self._analyze_sensor_run, context)

    def simulate_etch_education(
        self, context: Context, sensor: SensorAnalysis | None,
    ) -> EducationalSimulationResult | None:
        return anyio.run(self._simulate_etch_education, context, sensor)

    def list_investigations(
        self, requester: Requester,
    ) -> list[dict[str, JsonValue]]:
        return anyio.run(self._list_investigations, requester)
