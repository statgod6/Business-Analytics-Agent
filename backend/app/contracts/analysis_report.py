"""Stage 4 contract: AnalysisReport.

The intellect of the pipeline: every finding MUST carry evidence that
references a real computed output (E2B artifact) — no evidence, no finding.
Every Stage 1 key question must be answered or explicitly left open.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode


class KeyNumber(BaseModel):
    metric: str
    value: float
    unit: str = ""


class StatisticalTest(BaseModel):
    test: str
    statistic: float | None = None
    p_value: float | None = None
    significant: bool | None = None


class Evidence(BaseModel):
    computed_output_ref: str  # MUST reference a real E2B/sandbox artifact
    key_numbers: KeyNumber | None = None
    statistical_test: StatisticalTest | None = None


class Finding(BaseModel):
    finding_id: str
    statement: str
    evidence: Evidence
    answers_question: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"
    caveats: list[str] = Field(default_factory=list)


class MethodologyStep(BaseModel):
    step: str
    method: str
    justification: str = ""


class ArtifactRef(BaseModel):
    name: str
    type: Literal["chart", "table", "script"]
    location: str


class AnalysisReport(BaseModel):
    methodology: list[MethodologyStep] = Field(default_factory=list)
    findings: list[Finding]
    open_questions: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)


def _rule_evidence_required(artifact: AnalysisReport, context: dict[str, Any]) -> list[str]:
    return [
        f"finding {f.finding_id!r} has no computed output reference — "
        "no evidence, no finding"
        for f in artifact.findings
        if not f.evidence.computed_output_ref.strip()
    ]


def _rule_key_questions_answered(artifact: AnalysisReport, context: dict[str, Any]) -> list[str]:
    """Every Stage 1 key question is answered by a finding or explicitly open."""
    problem = context.get("problem_definition")
    if problem is None:
        return []
    answered = {f.answers_question for f in artifact.findings}
    open_set = set(artifact.open_questions)
    return [
        f"key question neither answered nor declared open: {q!r}"
        for q in problem.key_questions
        if q not in answered and q not in open_set
    ]


def _rule_significance_evidence(artifact: AnalysisReport, context: dict[str, Any]) -> list[str]:
    """A significance claim without a p-value is not a claim."""
    violations = []
    for f in artifact.findings:
        t = f.evidence.statistical_test
        if t is not None and t.significant is not None and t.p_value is None:
            violations.append(
                f"finding {f.finding_id!r} claims significance (significant="
                f"{t.significant}) without a p-value"
            )
    return violations


CONTRACT = StageContract(
    stage=4,
    name="analysis_report",
    gate_mode=GateMode.REVIEW_ABLE,
    artifact_schema=AnalysisReport,
    hard_rules=[
        _rule_evidence_required,
        _rule_key_questions_answered,
        _rule_significance_evidence,
    ],
    requires=["problem_definition", "prepared_dataset"],
)
