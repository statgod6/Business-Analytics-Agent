"""Stage 5 contract: Interpretation.

The translator: statistics become business meaning. Pure reasoning — no
tools in this stage. Every Stage 4 finding must be interpreted or
explicitly flagged; every causal claim is labeled by evidence strength.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode


class BusinessMeaning(BaseModel):
    finding_ref: str
    so_what: str  # the business consequence
    magnitude_of_impact: str = ""  # estimated, with basis
    affected: list[str] = Field(default_factory=list)


class CausalHypothesis(BaseModel):
    hypothesis: str
    status: Literal["evidence_supported", "plausible", "speculative"]
    supporting_evidence_refs: list[str] = Field(default_factory=list)
    rival_explanations: list[str] = Field(default_factory=list)
    testability: str = ""


class Risk(BaseModel):
    risk: str
    likelihood: Literal["low", "medium", "high"]
    impact: Literal["low", "medium", "high"]
    mitigation_hint: str = ""


class Interpretation(BaseModel):
    business_meaning: list[BusinessMeaning]
    causal_hypotheses: list[CausalHypothesis] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)
    what_would_change_conclusions: list[str] = Field(default_factory=list)


def _rule_no_orphan_findings(artifact: Interpretation, context: dict[str, Any]) -> list[str]:
    """Every Stage 4 finding is interpreted or explicitly flagged."""
    report = context.get("analysis_report")
    if report is None:
        return []
    interpreted = {bm.finding_ref for bm in artifact.business_meaning}
    flagged = " ".join(artifact.what_would_change_conclusions)
    orphans = [
        f.finding_id
        for f in report.findings
        if f.finding_id not in interpreted and f.finding_id not in flagged
    ]
    return [
        f"finding {fid!r} is neither interpreted nor flagged in "
        "what_would_change_conclusions"
        for fid in orphans
    ]


def _rule_supported_claims_have_evidence(artifact: Interpretation, context: dict[str, Any]) -> list[str]:
    return [
        f"hypothesis {h.hypothesis[:40]!r} claims evidence_supported but cites "
        "no supporting evidence"
        for h in artifact.causal_hypotheses
        if h.status == "evidence_supported" and not h.supporting_evidence_refs
    ]


CONTRACT = StageContract(
    stage=5,
    name="interpretation",
    gate_mode=GateMode.REVIEW_ABLE,
    artifact_schema=Interpretation,
    hard_rules=[
        _rule_no_orphan_findings,
        _rule_supported_claims_have_evidence,
    ],
    requires=["analysis_report"],
)
