"""Tiered human-in-the-loop (HITL) policy for the 6-stage methodology.

G1 (after Stage 1) and G6 (after Stage 6) are mandatory BLOCK gates.
G2-G5 are REVIEW-ABLE by default and configurable via environment
variables (GATE_MODE_S2..S5) or programmatic overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class GateMode(str, Enum):
    """Policy for a gate between two stages."""

    BLOCK = "BLOCK"  # always interrupt for human review
    REVIEW_ABLE = "REVIEW_ABLE"  # auto-progress, artifact logged


class GateDecision(str, Enum):
    """Human decisions submitted at a gate."""

    APPROVE = "approve"
    EDIT = "edit"
    REGENERATE = "regenerate"
    SEND_BACK = "send_back"


class GateStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"  # interrupt raised, waiting on the human
    AWAITING_DECISION = "awaiting_decision"
    RESUMED = "resumed"
    LOOPED_BACK = "looped_back"


# Gate N sits AFTER stage N (1:1 pairing, never drifts).
GATE_FOR_STAGE = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

# G1 and G6 are always BLOCK; the rest default to REVIEW_ABLE.
DEFAULT_GATE_MODES: dict[int, GateMode] = {
    1: GateMode.BLOCK,
    2: GateMode.REVIEW_ABLE,
    3: GateMode.REVIEW_ABLE,
    4: GateMode.REVIEW_ABLE,
    5: GateMode.REVIEW_ABLE,
    6: GateMode.BLOCK,
}

# Env var name -> stage for the configurable gates.
_GATE_ENV_OVERRIDES: dict[str, int] = {
    "GATE_MODE_S2": 2,
    "GATE_MODE_S3": 3,
    "GATE_MODE_S4": 4,
    "GATE_MODE_S5": 5,
}


@dataclass(frozen=True)
class GateSpec:
    """Static description of a gate: which stage it follows and its policy."""

    gate_id: int
    stage: int
    mode: GateMode


@dataclass
class GateState:
    """Runtime state of one gate, owned by the harness (never the agent)."""

    gate_id: int
    status: GateStatus = GateStatus.CLOSED
    decision: GateDecision | None = None
    feedback: str | None = None
    edit_payload: dict | None = None
    target_stage: int | None = None  # for SEND_BACK

    def open_gate(self) -> None:
        self.status = GateStatus.OPEN

    def record_decision(
        self,
        decision: GateDecision,
        feedback: str | None = None,
        edit_payload: dict | None = None,
        target_stage: int | None = None,
    ) -> None:
        self.decision = decision
        self.feedback = feedback
        self.edit_payload = edit_payload
        self.target_stage = target_stage
        if decision is GateDecision.SEND_BACK:
            self.status = GateStatus.LOOPED_BACK
        else:
            self.status = GateStatus.RESUMED


def resolve_gate_modes(
    overrides: Mapping[str, str] | None = None,
) -> dict[int, GateMode]:
    """Effective GateMode per stage, applying env-style overrides.

    Override keys follow the same convention as the environment
    (e.g. ``GATE_MODE_S3=BLOCK``). G1 and G6 are non-configurable.
    """
    modes = dict(DEFAULT_GATE_MODES)
    for key, stage in _GATE_ENV_OVERRIDES.items():
        value = (overrides or {}).get(key)
        if value is None:
            continue
        try:
            modes[stage] = GateMode(value.upper())
        except ValueError:
            raise ValueError(f"invalid GateMode {value!r} for {key}") from None
    return modes


def gate_specs(modes: Mapping[int, GateMode]) -> list[GateSpec]:
    return [
        GateSpec(gate_id=GATE_FOR_STAGE[stage], stage=stage, mode=modes[stage])
        for stage in sorted(GATE_FOR_STAGE)
    ]
