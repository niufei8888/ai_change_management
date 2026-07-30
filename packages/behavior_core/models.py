"""Tables shared by the chatbot and (in step 2) the console.

These live here rather than in apps/console because the chatbot has to write
Conversation rows and read Version rows on every request. If they lived in the
console package the serving path would depend on the control plane, which is
backwards.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Version(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    label: str
    config_hash: str
    config: dict[str, Any] = Field(sa_column=Column(JSON))
    status: str = "draft"  # draft | active | archived
    parent_id: str | None = None
    note: str = ""
    created_at: datetime = Field(default_factory=_now)


class Experiment(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    tag: str
    candidate_version_id: str
    baseline_version_id: str
    rollout_pct: int = 0
    status: str = "draft"  # draft | running | stopped
    created_at: datetime = Field(default_factory=_now)


class Conversation(SQLModel, table=True):
    """One question in, one answer out, plus everything step 2 needs to judge it.

    The behavior columns (version_id, config_hash, experiment_tag, arm) are what
    turn a pile of chat logs into something you can slice by experiment.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(index=True)
    question: str = Field(sa_column=Column(Text))
    answer: str = Field(default="", sa_column=Column(Text))
    error: str | None = None

    version_id: str
    config_hash: str
    model_version: str
    experiment_tag: str | None = Field(default=None, index=True)
    arm: str

    trajectory: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    terminated_by: str
    loop_count: int = 0
    llm_call_count: int = 0
    retrieved_articles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    citations: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))

    latency_ms: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    created_at: datetime = Field(default_factory=_now)
