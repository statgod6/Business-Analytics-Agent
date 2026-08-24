"""Stage Contract machinery: artifact schemas + hard rules + validation.

A Stage Contract is the definition of done for one stage:
  - ``requires``: prior signed artifacts that must exist in context
  - ``artifact_schema``: pydantic model of the expected output
  - ``hard_rules``: callables returning violation messages; any hit
    bounces the artifact back into the stage (No-Debt-Forward)
  - ``gate_mode``: the HITL policy after this stage
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Type

from pydantic import BaseModel, ValidationError

from backend.app.hitl import GateMode

# (artifact, context) -> list of violation detail strings
HardRule = Callable[[BaseModel, dict[str, Any]], list[str]]


@dataclass(frozen=True)
class ContractViolation:
    rule: str
    detail: str


@dataclass
class ContractResult:
    valid: bool
    artifact: BaseModel | None = None
    violations: list[ContractViolation] = field(default_factory=list)

    def summary(self) -> str:
        if self.valid:
            return f"contract signed ({type(self.artifact).__name__})"
        details = "; ".join(f"{v.rule}: {v.detail}" for v in self.violations[:5])
        return f"contract FAILED ({len(self.violations)} violation(s)): {details}"


class StageContract:
    def __init__(
        self,
        stage: int,
        name: str,
        gate_mode: GateMode,
        artifact_schema: Type[BaseModel],
        hard_rules: list[HardRule] | None = None,
        requires: list[str] | None = None,
    ) -> None:
        self.stage = stage
        self.name = name
        self.gate_mode = gate_mode
        self.artifact_schema = artifact_schema
        self.hard_rules = hard_rules or []
        self.requires = requires or []

    def validate(
        self,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ContractResult:
        """Validate candidate output against schema + hard rules.

        ``context`` holds prior signed artifacts (by state field name,
        e.g. {"problem_definition": ProblemDefinition(...)}), which the
        cross-stage traceability rules consult.
        """
        context = context or {}

        missing = [name for name in self.requires if not context.get(name)]
        if missing:
            return ContractResult(
                valid=False,
                violations=[
                    ContractViolation(
                        "missing_input",
                        f"required prior artifact(s) not signed: {', '.join(missing)}",
                    )
                ],
            )

        try:
            artifact = self.artifact_schema.model_validate(data)
        except ValidationError as exc:
            violations = [
                ContractViolation("schema", f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}")
                for e in exc.errors()
            ]
            return ContractResult(valid=False, violations=violations)

        violations: list[ContractViolation] = []
        for rule in self.hard_rules:
            for detail in rule(artifact, context):
                violations.append(ContractViolation(rule.__name__, detail))

        return ContractResult(
            valid=not violations,
            artifact=artifact if not violations else None,
            violations=violations,
        )
