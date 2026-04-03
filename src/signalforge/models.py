from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["repo", "paper", "article", "note", "market"]
ThesisStatus = Literal["active", "incubating", "watching", "rejected"]
DecisionState = Literal["active", "build", "incubate", "watch", "combine", "reject", "revisit"]
NarrativeMode = Literal["category-defining", "technical", "launch-ready"]


class Source(BaseModel):
    id: str
    type: SourceType
    title: str
    uri: str | None = None
    summary: str | None = None
    strategic_summary: str | None = None
    fingerprint: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    domain_cues: list[str] = Field(default_factory=list)
    capability_hints: list[str] = Field(default_factory=list)
    freshness_score: float = 0.5
    metadata: dict[str, str] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    workspace: str


class InsightMemo(BaseModel):
    id: str
    source_ids: list[str]
    core_summary: str
    reusable_primitives: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    workspace: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OpportunityScores(BaseModel):
    novelty: float
    urgency: float
    founder_fit: float
    buildability: float
    monetization: float
    strategic_leverage: float


class OpportunityEvaluation(BaseModel):
    id: str
    derived_from: list[str]
    title: str
    scores: OpportunityScores
    recommended_motion: Literal["advance", "watch", "combine", "reject"]
    workspace: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Thesis(BaseModel):
    id: str
    name: str
    one_line_thesis: str
    status: ThesisStatus = "active"
    workspace: str
    source_ids: list[str] = Field(default_factory=list)
    opportunity_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DecisionMemo(BaseModel):
    id: str
    thesis_id: str
    decision: Literal["build", "incubate", "watch", "combine", "reject"]
    from_state: DecisionState = "active"
    to_state: DecisionState
    evidence_ids: list[str] = Field(default_factory=list)
    review_after: date | None = None
    workspace: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PublishPack(BaseModel):
    id: str
    workspace: str
    target: str
    source_artifacts: list[str]
    narrative_mode: NarrativeMode = "category-defining"
    remove_private_notes: bool = True
    remove_portfolio_references: bool = True
    replace_source_names_with_descriptors: bool = True
