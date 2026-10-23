"""Real PostgreSQL and HTTP tests for live writes and revision conflicts."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from conftest import KEY, headers
from fastapi.testclient import TestClient
from investigations_models import InvestigationSummary
from live_support import API, INTERNAL, candidate, create, detail, payload, put
from pydantic import JsonValue, TypeAdapter


def test_update_replaces_candidates_on_same_thread(client: TestClient) -> None:
    # Given an initial live record independent of legacy tasks.
    thread_id, body = create(client)
    original = detail(client, thread_id)
    replacement = candidate()
    updated = body.model_copy(
        update={"base_revision": 1, "summary": "New evidence", "candidates": (replacement,)}
    )
    # When that thread publishes a revised candidate list.
    response = put(client, thread_id, updated)
    # Then identity and alert remain stable while the live view and list advance.
    assert response.json() == {"id": str(thread_id), "thread_id": str(thread_id), "revision": 2}
    result = detail(client, thread_id)
    assert result.id == result.thread_id == thread_id
    assert result.alert == original.alert == body.alert
    assert result.candidates == (replacement,)
    assert result.summary == "New evidence"
    assert result.created_at == original.created_at
    assert result.updated_at >= original.updated_at
    rows = TypeAdapter(list[InvestigationSummary]).validate_python(
        client.get(API, headers=headers("other")).json()
    )
    assert len(rows) == 1
    assert (rows[0].id, rows[0].revision, rows[0].candidate_count) == (thread_id, 2, 1)
    assert (rows[0].tool_id, rows[0].chamber_id, rows[0].lot_id) == ("ETCH-02", "CH-A", "LOT-1")
    assert rows[0].approved_at is None and rows[0].demo is True
    assert client.get("/api/ai/tasks", headers=headers()).json() == []
    internal = client.get(f"{INTERNAL}/{thread_id}", headers=KEY)
    assert internal.json() == result.model_dump(mode="json")


@pytest.mark.parametrize("revision", [0, 2])
def test_stale_write_keeps_current_record(client: TestClient, revision: int) -> None:
    # Given revision one.
    thread_id, body = create(client)
    before = detail(client, thread_id)
    # When a replay or future revision attempts to replace it.
    response = put(
        client, thread_id, body.model_copy(update={"base_revision": revision, "summary": "Stale"})
    )
    # Then the complete persisted record remains unchanged.
    assert response.status_code == 409
    assert detail(client, thread_id) == before


def test_first_write_requires_zero_revision(client: TestClient) -> None:
    # Given a thread not yet persisted.
    thread_id = uuid4()
    # When it claims a previous revision.
    response = put(client, thread_id, payload().model_copy(update={"base_revision": 1}))
    # Then no live record is created.
    assert response.status_code == 409
    assert client.get(f"{INTERNAL}/{thread_id}", headers=KEY).status_code == 404


def test_changed_alert_is_rejected(client: TestClient) -> None:
    # Given immutable original evidence.
    thread_id, body = create(client)
    changed = body.alert.model_copy(update={"source_text": "Replacement evidence"})
    # When an otherwise current update attempts to rewrite it.
    response = put(
        client, thread_id, body.model_copy(update={"base_revision": 1, "alert": changed})
    )
    # Then source text and revision are preserved.
    assert response.status_code == 422
    saved = detail(client, thread_id)
    assert saved.alert == body.alert and saved.revision == 1


@pytest.mark.parametrize(
    "invalid",
    [
        {"candidates": []},
        {"base_revision": -1},
        {"base_revision": True},
        {"base_revision": "0"},
        {"demo": False},
        {"approved_by": "spoof"},
        {"approval": None},
    ],
)
def test_invalid_live_payload_is_rejected(
    client: TestClient, invalid: dict[str, JsonValue]
) -> None:
    # Given an otherwise valid first publication.
    body: dict[str, JsonValue] = payload().model_dump(mode="json")
    body.update(invalid)
    # When an invalid field crosses the HTTP boundary.
    response = client.put(f"{INTERNAL}/{uuid4()}", headers=KEY, json=body)
    # Then it is rejected before persistence.
    assert response.status_code == 422
    assert client.get(API, headers=headers()).json() == []


@pytest.mark.parametrize(
    "field", ["id", "cause", "action", "rationale", "checks", "case_ids", "doc_ids", "unknowns"]
)
def test_candidate_fields_are_required(client: TestClient, field: str) -> None:
    # Given one candidate missing a contract field.
    draft: dict[str, JsonValue] = candidate().model_dump(mode="json")
    _ = draft.pop(field)
    body = {**payload().model_dump(mode="json"), "candidates": [draft]}
    # When that draft is published.
    response = client.put(f"{INTERNAL}/{uuid4()}", headers=KEY, json=body)
    # Then partial candidate structures are not accepted.
    assert response.status_code == 422


@pytest.mark.parametrize("invalid", [{"id": "invalid"}, {"extra": "value"}, {"checks": [1]}])
def test_candidate_types_and_extra_fields_are_rejected(
    client: TestClient, invalid: dict[str, JsonValue]
) -> None:
    # Given a malformed candidate within a valid publication.
    draft = {**candidate().model_dump(mode="json"), **invalid}
    body = {**payload().model_dump(mode="json"), "candidates": [draft]}
    # When the candidate crosses the boundary.
    response = client.put(f"{INTERNAL}/{uuid4()}", headers=KEY, json=body)
    # Then exact candidate structure is enforced.
    assert response.status_code == 422


def test_duplicate_candidate_ids_are_rejected(client: TestClient) -> None:
    # Given two positions referring to the same candidate.
    draft = candidate().model_dump(mode="json")
    body = {**payload().model_dump(mode="json"), "candidates": [draft, draft]}
    # When that list is published.
    response = client.put(f"{INTERNAL}/{uuid4()}", headers=KEY, json=body)
    # Then identity cannot depend on list position.
    assert response.status_code == 422


@pytest.mark.parametrize("initial", [True, False])
def test_competing_publications_claim_one_revision(client: TestClient, initial: bool) -> None:
    # Given two writers with the same revision, including the absent-row case.
    thread_id, body = (uuid4(), payload()) if initial else create(client)
    revision = 0 if initial else 1
    barrier = Barrier(2)

    def publish(summary: str) -> int:
        _ = barrier.wait(timeout=5)
        return put(
            client,
            thread_id,
            body.model_copy(update={"base_revision": revision, "summary": summary}),
        ).status_code

    # When they concurrently publish different contents.
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(publish, ["First", "Second"]))
    # Then exactly one transaction advances the thread.
    assert sorted(statuses) == [200, 409]
    assert detail(client, thread_id).revision == revision + 1


@pytest.mark.parametrize("path", [API, f"{API}/{uuid4()}"])
def test_public_reads_require_signed_identity(client: TestClient, path: str) -> None:
    # Given only spoofable identity headers.
    # When reading a public surface.
    response = client.get(path, headers={"X-User-Name": "reviewer", **KEY})
    # Then an internal key cannot replace a public access token.
    assert response.status_code == 401


@pytest.mark.parametrize("method", ["get", "put"])
def test_internal_surfaces_require_internal_key(client: TestClient, method: str) -> None:
    # Given only a valid browser session.
    # When accessing the live persistence API.
    response = client.request(
        method, f"{INTERNAL}/{uuid4()}", headers=headers(), json=payload().model_dump(mode="json")
    )
    # Then browser identity cannot write or read the internal surface.
    assert response.status_code == 401
