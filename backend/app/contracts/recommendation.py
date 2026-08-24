"""Stage 6 contract: Recommendation (the deliverable).

Every recommendation must be anchored to a Stage 1 success criterion and
its rationale must trace through real findings/hypotheses. Uncited advice
fails. G6 is BLOCK: the human approves or sends it back.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode


class ExpectedImpact(BaseModel):
    metric: str
    estimate: str  # quantified or bounded
    basis: list[str] = Field(default_factory=list)


class Effort(BaseModel):
    level: Literal["low", "medium", "high"]
    estimate: str = ""


class RecommendationItem(BaseModel):
    recommendation_id: str
    action: str  # specific verb + object
    rationale: str  # trace: success_criterion <- finding <- hypothesis
    expected_impact: ExpectedImpact
    effort: Effort
    cost_estimate: str | None = None
    risks: list[str] = Field(default_factory=list)
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    depends_on: list[str] = Field(default_factory=list)
    success_criteria_ref: str = ""


class Alternative(BaseModel):
    alternative: str
    rejected_because: str = ""


class DeferredCriterion(BaseModel):
    criterion_ref: str
    reason: str


class Recommendation(BaseModel):
    recommendations: list[RecommendationItem]
    alternatives_considered: list[Alternative] = Field(default_factory=list)
    deferred_criteria: list[DeferredCriterion] = Field(default_factory=list)
    final_summary: str
    next_steps: list[str] = Field(default_factory=list)
    overall_confidence: Literal["high", "medium", "low"] = "medium"


def _criteria_matches(ref: str, criteria: list[str]) -> bool:
    if ref in criteria:
        return True
    m = re.fullmatch(r"SC(\d+)", ref)
    return bool(m and 1 <= int(m.group(1)) <= len(criteria))


def _rule_anchored_recommendations(artifact: Recommendation, context: dict[str, Any]) -> list[str]:
    """Every recommendation cites a valid Stage 1 success criterion."""
    problem = context.get("problem_definition")
    if problem is None:
        return []
    criteria = problem.success_criteria
    return [
        f"recommendation {r.recommendation_id!r} cites no valid success "
        f"criterion (ref {r.success_criteria_ref!r})"
        for r in artifact.recommendations
        if not r.success_criteria_ref or not _criteria_matches(r.success_criteria_ref, criteria)
    ]


def _rule_criteria_addressed(artifact: Recommendation, context: dict[str, Any]) -> list[str]:
    """Every success criterion is addressed or explicitly deferred."""
    problem = context.get("problem_definition")
    if problem is None:
        return []
    addressed = {
        r.success_criteria_ref
        for r in artifact.recommendations
        if _criteria_matches(r.success_criteria_ref, problem.success_criteria)
    }
    deferred = {d.criterion_ref for d in artifact.deferred_criteria}
    violations = []
    for i, sc in enumerate(problem.success_criteria):
        sc_ref = f"SC{i + 1}"
        if sc not in addressed and sc_ref not in addressed and sc not in deferred and sc_ref not in deferred:
            violations.append(
                f"success criterion not addressed and not deferred: {sc!r} (or {sc_ref})"
            )
    return violations


def _rule_rationale_traces(artifact: Recommendation, context: dict[str, Any]) -> list[str]:
    """Rationale must reference real findings/hypotheses from prior stages."""
    report = context.get("analysis_report")
    interp = context.get("interpretation")
    if report is None:
        return []
    finding_ids = [f.finding_id for f in report.findings]
    hypothesis_texts = [h.hypothesis[:32] for h in (interp.causal_hypotheses if interp else [])]
    violations = []
    for r in artifact.recommendations:
        cited = any(fid in r.rationale for fid in finding_ids) or any(
            h in r.rationale for h in hypothesis_texts
        )
        if not cited:
            violations.append(
                f"recommendation {r.recommendation_id!r} rationale cites no "
                "finding or hypothesis — uncited rationale fails"
            )
    return violations


CONTRACT = StageContract(
    stage=6,
    name="recommendation",
    gate_mode=GateMode.BLOCK,
    artifact_schema=Recommendation,
    hard_rules=[
        _rule_anchored_recommendations,
        _rule_criteria_addressed,
        _rule_rationale_traces,
    ],
    requires=["problem_definition", "analysis_report", "interpretation"],
)
