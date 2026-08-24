"""Gate policy tests: defaults, overrides, and the gate state machine."""
from __future__ import annotations

import pytest

from backend.app.hitl import (
    DEFAULT_GATE_MODES,
    GateDecision,
    GateMode,
    GateState,
    GateStatus,
    gate_specs,
    resolve_gate_modes,
)


def test_default_modes_are_tiered():
    assert DEFAULT_GATE_MODES[1] is GateMode.BLOCK
    assert DEFAULT_GATE_MODES[6] is GateMode.BLOCK
    for stage in (2, 3, 4, 5):
        assert DEFAULT_GATE_MODES[stage] is GateMode.REVIEW_ABLE


def test_override_flips_reviewable_gate():
    modes = resolve_gate_modes({"GATE_MODE_S3": "BLOCK"})
    assert modes[3] is GateMode.BLOCK
    assert modes[2] is GateMode.REVIEW_ABLE  # untouched
    assert modes[1] is GateMode.BLOCK  # non-configurable


def test_invalid_override_raises():
    with pytest.raises(ValueError):
        resolve_gate_modes({"GATE_MODE_S4": "MAYBE"})


def test_gate_specs_are_six_ordered():
    specs = gate_specs(DEFAULT_GATE_MODES)
    assert [s.stage for s in specs] == [1, 2, 3, 4, 5, 6]
    assert [s.gate_id for s in specs] == [1, 2, 3, 4, 5, 6]


def test_gate_state_approve_resumes():
    gate = GateState(gate_id=1)
    gate.open_gate()
    assert gate.status is GateStatus.OPEN
    gate.record_decision(GateDecision.APPROVE, feedback="looks good")
    assert gate.status is GateStatus.RESUMED
    assert gate.feedback == "looks good"
    assert gate.decision is GateDecision.APPROVE


def test_gate_state_send_back_loops():
    gate = GateState(gate_id=6)
    gate.open_gate()
    gate.record_decision(GateDecision.SEND_BACK, feedback="seasonality missing", target_stage=5)
    assert gate.status is GateStatus.LOOPED_BACK
    assert gate.target_stage == 5


def test_gate_state_edit_carries_payload():
    gate = GateState(gate_id=1)
    gate.open_gate()
    gate.record_decision(GateDecision.EDIT, edit_payload={"problem_statement": "edited"})
    assert gate.status is GateStatus.RESUMED
    assert gate.edit_payload == {"problem_statement": "edited"}
