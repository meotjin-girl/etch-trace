"""Field action records and choice cancel: action only after approval, once, by the signed account."""

from uuid import UUID

import pytest
from conftest import headers
from fastapi.testclient import TestClient
from investigations_models import ActionRecord, ApprovalInput, InvestigationSummary
from live_support import API, create, detail
from pydantic import TypeAdapter

ACTION = {"content": "Compared previous runs and checked throttle valve", "result": "Valve response normal"}


def approve(client: TestClient) -> UUID:
    thread_id, body = create(client)
    review = ApprovalInput(candidate_id=body.candidates[0].id, expected_revision=1)
    response = client.post(
        f"{API}/{thread_id}/approval", headers=headers(), json=review.model_dump(mode="json")
    )
    assert response.status_code == 200, response.text
    return thread_id


def test_action_requires_an_approved_candidate(client: TestClient) -> None:
    # Given an investigation nobody has approved yet.
    thread_id, _ = create(client)
    # When a field action is recorded.
    response = client.post(f"{API}/{thread_id}/action", headers=headers(), json=ACTION)
    # Then it is refused and nothing is stored.
    assert response.status_code == 409
    assert detail(client, thread_id).action is None


def test_action_is_recorded_once_and_listed(client: TestClient) -> None:
    # Given an approved investigation.
    thread_id = approve(client)
    # When the engineer records the action, with a spoofed display header.
    response = client.post(
        f"{API}/{thread_id}/action", headers={**headers("field"), "X-User-Name": "spoof"}, json=ACTION
    )
    # Then the record belongs to the signed account and appears in detail and listing.
    assert response.status_code == 200, response.text
    record = ActionRecord.model_validate(response.json())
    assert (record.content, record.result) == (ACTION["content"], ACTION["result"])
    assert (record.recorded_by_id, record.recorded_by) == ("account:field", "field")
    stored = detail(client, thread_id)
    assert stored.action == record
    listing = TypeAdapter(list[InvestigationSummary]).validate_python(
        client.get(API, headers=headers()).json()
    )
    assert listing[0].action_recorded_at == record.recorded_at
    # And a second record is refused without overwriting the first.
    again = client.post(f"{API}/{thread_id}/action", headers=headers(), json={**ACTION, "result": "x"})
    assert again.status_code == 409
    assert detail(client, thread_id).action == record


@pytest.mark.parametrize(
    "body",
    [
        {"content": "  ", "result": "ok"},
        {"content": "did it", "result": ""},
        {"content": "did it"},
        {**ACTION, "recorded_by": "spoof"},
    ],
)
def test_action_input_is_validated(client: TestClient, body: dict[str, str]) -> None:
    # Given an approved investigation and an invalid or spoofed body.
    thread_id = approve(client)
    # When it is submitted.
    response = client.post(f"{API}/{thread_id}/action", headers=headers(), json=body)
    # Then it is rejected and nothing is stored.
    assert response.status_code == 422
    assert detail(client, thread_id).action is None


def test_action_requires_a_valid_access_token(client: TestClient) -> None:
    thread_id = approve(client)
    response = client.post(f"{API}/{thread_id}/action", json=ACTION)
    assert response.status_code == 401


def test_choice_can_be_cleared_and_rechosen_before_the_action(client: TestClient) -> None:
    # Given an investigation approved with its first candidate.
    thread_id = approve(client)
    # When the choice is cleared.
    response = client.delete(f"{API}/{thread_id}/approval", headers=headers())
    # Then nothing is approved and another candidate can be chosen.
    assert response.status_code == 204, response.text
    stored = detail(client, thread_id)
    assert stored.approval is None
    review = ApprovalInput(candidate_id=stored.candidates[1].id, expected_revision=stored.revision)
    again = client.post(
        f"{API}/{thread_id}/approval", headers=headers(), json=review.model_dump(mode="json")
    )
    assert again.status_code == 200, again.text
    assert detail(client, thread_id).approval.candidate.id == stored.candidates[1].id  # type: ignore[union-attr]


def test_choice_cannot_be_cleared_without_approval_or_after_the_action(client: TestClient) -> None:
    unapproved, _ = create(client)
    assert client.delete(f"{API}/{unapproved}/approval", headers=headers()).status_code == 409
    thread_id = approve(client)
    assert client.post(f"{API}/{thread_id}/action", headers=headers(), json=ACTION).status_code == 200
    approval = detail(client, thread_id).approval
    assert client.delete(f"{API}/{thread_id}/approval", headers=headers()).status_code == 409
    assert detail(client, thread_id).approval == approval
    assert client.delete(f"{API}/{thread_id}/approval").status_code == 401
