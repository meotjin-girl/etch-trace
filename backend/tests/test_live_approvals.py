"""Real database approval races, identity attribution, and snapshot retention."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from conftest import KEY, headers
from fastapi.testclient import TestClient
from investigations_models import Approval, ApprovalInput, InvestigationSummary
from live_support import API, candidate, create, detail, put
from psycopg import sql
from pydantic import TypeAdapter


def test_approval_uses_verified_reviewer_not_headers(client: TestClient) -> None:
    # Given a published candidate and a reviewer with spoofed display headers.
    thread_id, body = create(client)
    chosen = body.candidates[1]
    review = ApprovalInput(candidate_id=chosen.id, expected_revision=1, comment="Checked RF")
    # When an authenticated collaborator approves.
    response = client.post(
        f"{API}/{thread_id}/approval",
        headers={**headers("actual"), "X-User-Name": "spoof", "X-User-Role": "admin"},
        json=review.model_dump(mode="json"),
    )
    # Then the exact selected candidate is attributed only to the signed account.
    assert response.status_code == 200
    approval = Approval.model_validate(response.json())
    assert approval.candidate == chosen
    assert (approval.approved_by_id, approval.approved_by) == ("account:actual", "actual")
    assert approval.revision == 1 and approval.comment == review.comment
    assert detail(client, thread_id).approval == approval
    listing = TypeAdapter(list[InvestigationSummary]).validate_python(
        client.get(API, headers=headers()).json()
    )
    assert listing[0].approved_at == approval.approved_at


@pytest.mark.parametrize("field", ["approved_by", "approved_by_id", "approved_at"])
def test_reviewer_body_spoof_is_rejected(client: TestClient, field: str) -> None:
    # Given a valid approval request with an untrusted identity or timestamp field.
    thread_id, body = create(client)
    review = ApprovalInput(candidate_id=body.candidates[0].id, expected_revision=1)
    # When the browser attempts to supply server-owned approval metadata.
    response = client.post(
        f"{API}/{thread_id}/approval",
        headers=headers(),
        json={**review.model_dump(mode="json"), field: "spoof"},
    )
    # Then the request is rejected without an approval.
    assert response.status_code == 422
    assert detail(client, thread_id).approval is None


@pytest.mark.parametrize(
    "identity", [{}, KEY, {"X-User-Name": "reviewer"}, {"Authorization": "Bearer invalid", **KEY}]
)
def test_approval_requires_valid_access_token(client: TestClient, identity: dict[str, str]) -> None:
    # Given a reviewable candidate but no valid user session.
    thread_id, body = create(client)
    review = ApprovalInput(candidate_id=body.candidates[0].id, expected_revision=1)
    # When approval is requested.
    response = client.post(
        f"{API}/{thread_id}/approval", headers=identity, json=review.model_dump(mode="json")
    )
    # Then internal and spoofed identities cannot approve.
    assert response.status_code == 401
    assert detail(client, thread_id).approval is None


def test_stale_review_cannot_approve_edited_candidates(client: TestClient) -> None:
    # Given a candidate list changed since the reviewer loaded it.
    thread_id, body = create(client)
    edited = body.candidates[0].model_copy(update={"cause": "Changed hypothesis"})
    assert (
        put(
            client, thread_id, body.model_copy(update={"base_revision": 1, "candidates": (edited,)})
        ).status_code
        == 200
    )
    # When the stale reviewer selects an ID that still exists.
    response = client.post(
        f"{API}/{thread_id}/approval",
        headers=headers(),
        json=ApprovalInput(candidate_id=edited.id, expected_revision=1).model_dump(mode="json"),
    )
    # Then identity matching alone cannot approve unseen content.
    assert response.status_code == 409
    assert detail(client, thread_id).approval is None


def test_unknown_candidate_cannot_be_approved(client: TestClient) -> None:
    # Given a current revision.
    thread_id, _ = create(client)
    # When a candidate from outside that revision is selected.
    response = client.post(
        f"{API}/{thread_id}/approval",
        headers=headers(),
        json=ApprovalInput(candidate_id=uuid4(), expected_revision=1).model_dump(mode="json"),
    )
    # Then no snapshot is recorded.
    assert response.status_code == 422
    assert detail(client, thread_id).approval is None


def test_synchronized_approvals_record_exactly_one_snapshot(client: TestClient) -> None:
    # Given two reviewers selecting different candidates from the same revision.
    thread_id, body = create(client)
    barrier = Barrier(2)

    def approve(index: int) -> tuple[int, str]:
        review = ApprovalInput(
            candidate_id=body.candidates[index].id, expected_revision=1, comment=f"Review {index}"
        )
        _ = barrier.wait(timeout=5)
        response = client.post(
            f"{API}/{thread_id}/approval",
            headers=headers(f"reviewer-{index}"),
            json=review.model_dump(mode="json"),
        )
        return response.status_code, response.text

    # When both HTTP requests compete on the persisted row.
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(approve, [0, 1]))
    # Then the winner alone owns the immutable snapshot.
    assert sorted(status for status, _ in responses) == [200, 409]
    winner = Approval.model_validate_json(next(text for status, text in responses if status == 200))
    assert detail(client, thread_id).approval == winner
    assert winner.approved_by_id in {"account:reviewer-0", "account:reviewer-1"}


@pytest.mark.parametrize("removed", [True, False])
def test_snapshot_survives_candidate_changes_after_approval(
    client: TestClient, removed: bool
) -> None:
    # Given an approved candidate.
    thread_id, body = create(client)
    chosen = body.candidates[0]
    approved = client.post(
        f"{API}/{thread_id}/approval",
        headers=headers("reviewer"),
        json=ApprovalInput(candidate_id=chosen.id, expected_revision=1).model_dump(mode="json"),
    )
    assert approved.status_code == 200
    snapshot = Approval.model_validate(approved.json())
    replacement = (
        candidate()
        if removed
        else chosen.model_copy(update={"cause": "Changed cause", "action": "Changed action"})
    )
    # When a follow-up edits or removes the selected candidate.
    assert (
        put(
            client,
            thread_id,
            body.model_copy(update={"base_revision": 1, "candidates": (replacement,)}),
        ).status_code
        == 200
    )
    # Then the thread continues, but the original reviewed content stays immutable.
    current = detail(client, thread_id)
    assert current.revision == 2 and current.candidates == (replacement,)
    assert current.approval == snapshot
    assert snapshot.candidate == chosen


def test_second_approval_is_rejected_after_followup(client: TestClient) -> None:
    # Given an approved thread with a newer live revision.
    thread_id, body = create(client)
    chosen = body.candidates[0]
    review = ApprovalInput(candidate_id=chosen.id, expected_revision=1)
    first = client.post(
        f"{API}/{thread_id}/approval", headers=headers(), json=review.model_dump(mode="json")
    )
    assert first.status_code == 200
    assert put(client, thread_id, body.model_copy(update={"base_revision": 1})).status_code == 200
    # When another collaborator approves the current revision.
    response = client.post(
        f"{API}/{thread_id}/approval",
        headers=headers("another"),
        json=ApprovalInput(candidate_id=chosen.id, expected_revision=2).model_dump(mode="json"),
    )
    # Then one approval remains authoritative even though conversation continues.
    assert response.status_code == 409
    assert detail(client, thread_id).approval == Approval.model_validate(first.json())


@pytest.mark.parametrize("column", ["alert", "approval"])
def test_database_guards_immutable_evidence(
    client: TestClient, database_url: str, column: str
) -> None:
    # Given approved evidence protected independently of the write route.
    thread_id, body = create(client)
    assert (
        client.post(
            f"{API}/{thread_id}/approval",
            headers=headers(),
            json=ApprovalInput(candidate_id=body.candidates[0].id, expected_revision=1).model_dump(
                mode="json"
            ),
        ).status_code
        == 200
    )
    # When a direct database update tries to replace that evidence.
    with psycopg.connect(database_url) as conn, pytest.raises(psycopg.errors.CheckViolation):
        _ = conn.execute(
            sql.SQL("UPDATE v1_live_investigations SET {}='{{}}'::jsonb WHERE id=%s").format(
                sql.Identifier(column)
            ),
            (thread_id,),
        )
    # Then the database constraint, not caller cooperation, blocks the change.
