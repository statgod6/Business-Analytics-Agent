"""Smoke tests: registry integrity, model routing, and the full
traceability chain (stage by stage, contracts signed in order)."""
from __future__ import annotations

import pytest

from backend.app.config import settings
from backend.app.contracts import STAGE_CONTRACTS, STAGE_ORDER, contract_for_stage
from backend.app.hitl import GateMode

from tests.fixtures import (
    VALID_INTERPRETATION,
    VALID_MANIFEST,
    VALID_PD,
    VALID_PREPARED,
    VALID_RECOMMENDATION,
    VALID_REPORT,
    USER_REQUEST,
)


def test_registry_has_six_ordered_contracts():
    assert STAGE_ORDER == [1, 2, 3, 4, 5, 6]
    assert len(STAGE_CONTRACTS) == 6


def test_gate_modes_match_policy():
    assert STAGE_CONTRACTS[1].gate_mode is GateMode.BLOCK
    assert STAGE_CONTRACTS[6].gate_mode is GateMode.BLOCK
    for stage in (2, 3, 4, 5):
        assert STAGE_CONTRACTS[stage].gate_mode is GateMode.REVIEW_ABLE


def test_unknown_stage_raises():
    with pytest.raises(KeyError):
        contract_for_stage(7)


def test_model_router_tiers():
    assert settings.model_for_stage(1) == settings.model_strong
    assert settings.model_for_stage(4) == settings.model_strong
    assert settings.model_for_stage(5) == settings.model_strong
    assert settings.model_for_stage(6) == settings.model_strong
    assert settings.model_for_stage(2) == settings.model_efficient
    assert settings.model_for_stage(3) == settings.model_efficient


def test_full_traceability_chain_signs():
    """The whole chain validates in order — the integration guarantee."""
    context: dict = {"user_request": USER_REQUEST}
    for stage, data in (
        (1, VALID_PD),
        (2, VALID_MANIFEST),
        (3, VALID_PREPARED),
        (4, VALID_REPORT),
        (5, VALID_INTERPRETATION),
        (6, VALID_RECOMMENDATION),
    ):
        result = STAGE_CONTRACTS[stage].validate(data, context)
        assert result.valid, f"stage {stage} failed: {result.summary()}"
        context[STAGE_CONTRACTS[stage].name] = result.artifact


def test_chain_blocks_forward_without_prior_contract():
    """No-Debt-Forward: Stage 4 cannot sign without Stage 3's contract."""
    context = {"user_request": USER_REQUEST}
    result = STAGE_CONTRACTS[1].validate(VALID_PD, context)
    assert result.valid
    context["problem_definition"] = result.artifact
    # Stage 2 signs, but Stage 3's artifact is missing:
    result = STAGE_CONTRACTS[4].validate(VALID_REPORT, context)
    assert not result.valid
    assert any(v.rule == "missing_input" for v in result.violations)
