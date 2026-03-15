"""Workspace models — guides, role stories, explanation summaries."""

from __future__ import annotations

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import ExplanationAudience, OperatorRole


class RoleStory(AppModel):
    story_id: str
    persona_name: str
    title: str
    platform_role: OperatorRole
    goal: str
    workflow_steps: list[str] = Field(default_factory=list)
    success_signal: str
    recommended_view: str


class WorkspaceGuide(AppModel):
    primary_workflow_title: str
    primary_workflow_summary: str
    role_stories: list[RoleStory] = Field(default_factory=list)
    scoring_guarantees: list[str] = Field(default_factory=list)
    llm_positioning_note: str


class ExplanationProviderSummary(AppModel):
    requested_provider: str
    active_provider: str
    source_of_truth: str
    notes: list[str] = Field(default_factory=list)


class AnalysisExplanation(AppModel):
    dataset_id: str
    dataset_name: str
    audience: ExplanationAudience
    headline: str
    narrative: str
    deterministic_evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    watchouts: list[str] = Field(default_factory=list)
    provider_summary: ExplanationProviderSummary
