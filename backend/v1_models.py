"""Boundary models for the v1 backend and agent protocol."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Role = Literal["worker", "engineer", "admin"]
Status = Literal[
    "QUEUED", "RUNNING", "WAITING_INPUT", "WAITING_APPROVAL",
    "DONE", "INCOMPLETE", "FAILED",
]


class Input(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class TaskInput(Input):
    question: str = Field(min_length=1, max_length=10000)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


class MessageInput(Input):
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class ApprovalInput(Input):
    action: Literal["approve", "revise"]
    comment: str = Field(default="", max_length=10000)
    event_time: datetime | None = None
    lot_id: str | None = Field(default=None, max_length=200)


class Document(Input):
    id: str
    title: str
    text: str


class Report(Input):
    context: dict[str, JsonValue] = Field(default_factory=dict)
    scored: list[dict[str, JsonValue]] = Field(default_factory=list)
    metrics: list[dict[str, JsonValue]] = Field(default_factory=list)
    causeCases: list[dict[str, JsonValue]] = Field(default_factory=list)
    docIds: list[str] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    summary: str = ""
    unknowns: list[str] = Field(default_factory=list)
    feedback: list[JsonValue] = Field(default_factory=list)
    demo: Literal[True] = True


class Callback(Input):
    type: str = Field(min_length=1, max_length=100)
    payload: dict[str, JsonValue] = Field(default_factory=dict)
    event_id: str = Field(min_length=1, max_length=200)


class Output(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


class CaseData(Output):
    data: dict[str, JsonValue]


class Event(Output):
    task_id: UUID
    seq: int
    event_id: str | None
    type: str
    payload: dict[str, JsonValue]
    created_at: datetime


class Message(Output):
    id: int
    task_id: UUID
    role: str
    text: str
    user_name: str
    user_role: str
    created_at: datetime


class Review(Output):
    id: int
    task_id: UUID
    action: Literal["approve", "revise"]
    comment: str
    user_name: str
    user_role: Role
    report: Report | None
    event_time: datetime | None
    lot_id: str | None
    created_at: datetime


class Investigation(Output):
    id: int
    task_id: UUID
    review_id: int
    report: Report
    approved_by: str
    approved_role: Role
    event_time: datetime | None
    lot_id: str | None
    approved_at: datetime
    created_at: datetime


class InvestigationRecord(Output):
    """Approved report and existing storage metadata, without conversation history."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    id: UUID
    user_name: str
    user_role: Role
    question: str
    status: Literal["DONE"] = "DONE"
    report: Report
    approved_by: str
    approved_role: Role
    event_time: datetime | None
    lot_id: str | None
    approved_at: datetime
    created_at: datetime
    updated_at: datetime


class Task(Output):
    id: UUID
    user_name: str
    user_role: Role
    question: str
    command_id: UUID
    status: Status
    report: Report | None
    created_at: datetime
    updated_at: datetime


class Detail(Task):
    messages: list[Message]
    events: list[Event]
    reviews: list[Review]
    investigation: Investigation | None


@dataclass(frozen=True, slots=True)
class Actor:
    name: str
    role: Role


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    agent_url: str
    internal_api_key: str
