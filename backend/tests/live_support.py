"""Typed fixtures shared by real live-investigation HTTP tests."""

from uuid import UUID, uuid4

from conftest import KEY, headers
from fastapi.testclient import TestClient
from httpx2 import Response
from investigations_models import Alert, Candidate, Investigation, LiveInput

API = "/api/investigations"
INTERNAL = "/internal/investigations/live"


def candidate() -> Candidate:
    return Candidate(
        id=uuid4(),
        cause="RF match drift",
        action="Inspect the matching network",
        rationale="Reflected power rose while gas remained stable",
        checks=("Inspect RF match",),
        case_ids=("CASE-1",),
        doc_ids=("OCAP-ETCH-RF",),
        unknowns=("Maintenance history unavailable",),
    )


def payload() -> LiveInput:
    return LiveInput(
        base_revision=0,
        alert=Alert(
            tool_id="ETCH-02",
            chamber_id="CH-A",
            lot_id="LOT-1",
            wafer_id="W01",
            recipe_id="RCP-1",
            source_text="[sensor] 2026-10-23T01:00:00Z RF (W): 5 39.42",
        ),
        summary="Investigate reflected power",
        candidates=(candidate(), candidate()),
        demo=True,
    )


def put(client: TestClient, thread_id: UUID, body: LiveInput) -> Response:
    return client.put(f"{INTERNAL}/{thread_id}", headers=KEY, json=body.model_dump(mode="json"))


def create(client: TestClient) -> tuple[UUID, LiveInput]:
    thread_id, body = uuid4(), payload()
    response = put(client, thread_id, body)
    assert response.status_code == 200, response.text
    return thread_id, body


def detail(client: TestClient, thread_id: UUID) -> Investigation:
    response = client.get(f"{API}/{thread_id}", headers=headers("collaborator"))
    assert response.status_code == 200, response.text
    return Investigation.model_validate(response.json())
