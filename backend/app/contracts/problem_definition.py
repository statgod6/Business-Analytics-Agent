"""Stage 1 contract: ProblemDefinition (the anchor).

The agent must show interpretation of the raw request, define measurable
success criteria, and pose data-answerable key questions. G1 is BLOCK:
the human approves or edits this artifact before any work begins.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode

_HORIZON = re.compile(
    r"\b(daily|weekly|monthly|quarterly|yearly|by\s+\w+|q[1-4]|fy\d{4}|"
    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
    r"(business\s+|calendar\s+)?"
    r"(day|week|month|quarter|year)s?\b)",
    re.IGNORECASE,
)


class Stakeholder(BaseModel):
    role: str
    interest: str


class Scope(BaseModel):
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)


class ProblemDefinition(BaseModel):
    problem_statement: str
    objectives: list[str]
    success_criteria: list[str]
    scope: Scope = Field(default_factory=Scope)
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    key_questions: list[str]


def _rule_success_criteria_shape(artifact: ProblemDefinition, context: dict[str, Any]) -> list[str]:
    """Each success criterion must carry a numeric target and a time horizon."""
    violations = []
    if not artifact.success_criteria:
        return ["at least one success criterion is required"]
    for i, sc in enumerate(artifact.success_criteria):
        if not re.search(r"\d", sc):
            violations.append(f"success_criteria[{i}] has no numeric target: {sc!r}")
        if not _HORIZON.search(sc):
            violations.append(f"success_criteria[{i}] has no time horizon: {sc!r}")
    return violations


def _rule_interpretation_visible(artifact: ProblemDefinition, context: dict[str, Any]) -> list[str]:
    """The problem statement must interpret the request, not copy it verbatim."""
    request = context.get("user_request")
    if not request:
        return []
    req_tokens = set(re.findall(r"\w+", request.lower()))
    st_tokens = set(re.findall(r"\w+", artifact.problem_statement.lower()))
    if not req_tokens or not st_tokens:
        return []
    overlap = len(req_tokens & st_tokens) / len(st_tokens)
    if overlap > 0.9:
        return [
            f"problem_statement is {overlap:.0%} identical to the user request — "
            "interpretation is required, not restatement"
        ]
    return []


def _rule_key_questions(artifact: ProblemDefinition, context: dict[str, Any]) -> list[str]:
    violations = []
    if not artifact.key_questions:
        return ["at least one key question is required"]
    for i, q in enumerate(artifact.key_questions):
        if not q.strip().endswith("?"):
            violations.append(f"key_questions[{i}] is not phrased as a question: {q!r}")
    return violations


CONTRACT = StageContract(
    stage=1,
    name="problem_definition",
    gate_mode=GateMode.BLOCK,
    artifact_schema=ProblemDefinition,
    hard_rules=[
        _rule_success_criteria_shape,
        _rule_interpretation_visible,
        _rule_key_questions,
    ],
)
