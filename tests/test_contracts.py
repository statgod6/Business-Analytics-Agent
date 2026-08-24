"""Contract tests: every hard rule, per stage, valid + invalid fixtures."""
from __future__ import annotations

import copy

from backend.app.contracts import STAGE_CONTRACTS

from tests.fixtures import (
    VALID_INTERPRETATION,
    VALID_MANIFEST,
    VALID_PD,
    VALID_PREPARED,
    VALID_RECOMMENDATION,
    VALID_REPORT,
    USER_REQUEST,
    analysis_context,
    pd_context,
    prepared_context,
)


def validate_stage(stage: int, data: dict, context: dict | None = None):
    return STAGE_CONTRACTS[stage].validate(data, context or {})


# ── Stage 1: ProblemDefinition ─────────────────────────────

def test_stage1_valid():
    result = validate_stage(1, VALID_PD, pd_context())
    assert result.valid, result.summary()


def test_stage1_verbatim_copy_fails():
    data = dict(VALID_PD)
    data["problem_statement"] = USER_REQUEST  # no interpretation
    result = validate_stage(1, data, pd_context())
    assert not result.valid
    assert any("identical to the user request" in v.detail for v in result.violations)


def test_stage1_missing_horizon_fails():
    data = dict(VALID_PD)
    data["success_criteria"] = ["Grow revenue significantly"]  # no target, no horizon
    result = validate_stage(1, data, pd_context())
    assert not result.valid
    assert any("numeric target" in v.detail for v in result.violations)
    assert any("time horizon" in v.detail for v in result.violations)


def test_stage1_key_question_not_a_question_fails():
    data = dict(VALID_PD)
    data["key_questions"] = ["Category breakdown"]
    result = validate_stage(1, data, pd_context())
    assert not result.valid
    assert any("not phrased as a question" in v.detail for v in result.violations)


# ── Stage 2: CollectionManifest ────────────────────────────

def test_stage2_valid():
    result = validate_stage(2, VALID_MANIFEST, pd_context())
    assert result.valid, result.summary()


def test_stage2_requires_problem_definition():
    result = validate_stage(2, VALID_MANIFEST, {})
    assert not result.valid
    assert any(v.rule == "missing_input" for v in result.violations)


def test_stage2_uncovered_question_fails():
    data = copy.deepcopy(VALID_MANIFEST)
    data["coverage"] = data["coverage"][:1]  # drops the regions question
    result = validate_stage(2, data, pd_context())
    assert not result.valid
    assert any("not covered" in v.detail for v in result.violations)


def test_stage2_unresolved_missing_data_fails():
    data = copy.deepcopy(VALID_MANIFEST)
    data["missing_data"] = [
        {"what": "Customer segment", "why": "Not exported", "impact": "No segmentation", "resolved_in_stage": False}
    ]
    result = validate_stage(2, data, pd_context())
    assert not result.valid
    assert any("unresolved in-stage" in v.detail for v in result.violations)


def test_stage2_failed_source_must_be_accounted():
    data = copy.deepcopy(VALID_MANIFEST)
    data["sources"][0]["ingestion"]["status"] = "failed"
    result = validate_stage(2, data, pd_context())
    assert not result.valid
    assert any("failed ingestion" in v.detail for v in result.violations)


# ── Stage 3: PreparedDataset ───────────────────────────────

def test_stage3_valid():
    result = validate_stage(3, VALID_PREPARED, prepared_context())
    assert result.valid, result.summary()


def test_stage3_unnamed_field_fails():
    data = copy.deepcopy(VALID_PREPARED)
    data["data_contract"]["fields"][0]["semantic_meaning"] = ""
    result = validate_stage(3, data, prepared_context())
    assert not result.valid
    assert any("no semantic meaning" in v.detail for v in result.violations)


def test_stage3_dirty_without_limitations_fails():
    data = copy.deepcopy(VALID_PREPARED)
    data["quality_metrics"]["missingness_percent"] = 42.0
    result = validate_stage(3, data, prepared_context())
    assert not result.valid
    assert any("no limitations" in v.detail for v in result.violations)


def test_stage3_unlogged_transformations_fail():
    data = copy.deepcopy(VALID_PREPARED)
    data["data_contract"]["fields"][0]["transformations_applied"] = ["standardized region names"]
    data["cleaning_log"] = []
    result = validate_stage(3, data, prepared_context())
    assert not result.valid
    assert any("cleaning log is empty" in v.detail for v in result.violations)


# ── Stage 4: AnalysisReport ────────────────────────────────

def test_stage4_valid():
    result = validate_stage(4, VALID_REPORT, analysis_context())
    assert result.valid, result.summary()


def test_stage4_no_evidence_fails():
    data = copy.deepcopy(VALID_REPORT)
    data["findings"][0]["evidence"]["computed_output_ref"] = ""
    result = validate_stage(4, data, analysis_context())
    assert not result.valid
    assert any("no evidence, no finding" in v.detail for v in result.violations)


def test_stage4_unanswered_question_fails():
    data = copy.deepcopy(VALID_REPORT)
    data["findings"][0]["answers_question"] = ""
    data["open_questions"] = []
    result = validate_stage(4, data, analysis_context())
    assert not result.valid
    assert any("neither answered nor declared open" in v.detail for v in result.violations)


def test_stage4_significance_without_pvalue_fails():
    data = copy.deepcopy(VALID_REPORT)
    data["findings"][0]["evidence"]["statistical_test"]["p_value"] = None
    result = validate_stage(4, data, analysis_context())
    assert not result.valid
    assert any("without a p-value" in v.detail for v in result.violations)


# ── Stage 5: Interpretation ────────────────────────────────

def test_stage5_valid():
    result = validate_stage(5, VALID_INTERPRETATION, analysis_context())
    assert result.valid, result.summary()


def test_stage5_orphan_finding_fails():
    data = copy.deepcopy(VALID_INTERPRETATION)
    data["business_meaning"][0]["finding_ref"] = "F99"  # no such finding
    result = validate_stage(5, data, analysis_context())
    assert not result.valid
    assert any("neither interpreted nor flagged" in v.detail for v in result.violations)


def test_stage5_supported_claim_without_evidence_fails():
    data = copy.deepcopy(VALID_INTERPRETATION)
    data["causal_hypotheses"][0]["status"] = "evidence_supported"
    data["causal_hypotheses"][0]["supporting_evidence_refs"] = []
    result = validate_stage(5, data, analysis_context())
    assert not result.valid
    assert any("cites no supporting evidence" in v.detail for v in result.violations)


# ── Stage 6: Recommendation ────────────────────────────────

def test_stage6_valid():
    result = validate_stage(6, VALID_RECOMMENDATION, analysis_context())
    assert result.valid, result.summary()


def test_stage6_unanchored_recommendation_fails():
    data = copy.deepcopy(VALID_RECOMMENDATION)
    data["recommendations"][0]["success_criteria_ref"] = ""
    result = validate_stage(6, data, analysis_context())
    assert not result.valid
    assert any("cites no valid success criterion" in v.detail for v in result.violations)


def test_stage6_unaddressed_criterion_fails():
    data = copy.deepcopy(VALID_RECOMMENDATION)
    data["recommendations"][0]["success_criteria_ref"] = "SC1"
    data["deferred_criteria"] = []  # SC2 now unaddressed
    result = validate_stage(6, data, analysis_context())
    assert not result.valid
    assert any("not addressed and not deferred" in v.detail for v in result.violations)


def test_stage6_uncited_rationale_fails():
    data = copy.deepcopy(VALID_RECOMMENDATION)
    data["recommendations"][0]["rationale"] = "Because it is the right thing to do."
    result = validate_stage(6, data, analysis_context())
    assert not result.valid
    assert any("uncited rationale" in v.detail for v in result.violations)
