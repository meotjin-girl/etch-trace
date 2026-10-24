"""Authenticated live investigation reads, writes, and candidate approval."""

from typing import Annotated
from uuid import UUID

from api_dependencies import Dependencies
from fastapi import APIRouter, Depends
from investigations_models import (
    Approval,
    ApprovalInput,
    Investigation,
    InvestigationSummary,
    LiveInput,
    LiveResult,
)
from v1_models import Actor


def router(dependencies: Dependencies) -> APIRouter:
    api = APIRouter()

    @api.get("/api/investigations", dependencies=[Depends(dependencies.actor)])
    def listing() -> list[InvestigationSummary]:
        return dependencies.current().investigations.listing()

    @api.get("/api/investigations/{thread_id}", dependencies=[Depends(dependencies.actor)])
    def detail(thread_id: UUID) -> Investigation:
        return dependencies.current().investigations.detail(thread_id)

    @api.post("/api/investigations/{thread_id}/approval")
    def approve(
        thread_id: UUID,
        body: ApprovalInput,
        actor: Annotated[Actor, Depends(dependencies.actor)],
    ) -> Approval:
        return dependencies.current().investigations.approve(thread_id, body, actor)

    @api.get(
        "/internal/investigations/live/{thread_id}",
        dependencies=[Depends(dependencies.internal)],
    )
    def internal_detail(thread_id: UUID) -> Investigation:
        return dependencies.current().investigations.detail(thread_id)

    @api.put(
        "/internal/investigations/live/{thread_id}",
        dependencies=[Depends(dependencies.internal)],
    )
    def upsert(thread_id: UUID, body: LiveInput) -> LiveResult:
        return dependencies.current().investigations.upsert(thread_id, body)

    return api
