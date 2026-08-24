"""Shared fixtures for the test suite.

The canonical valid artifact dicts live in the backend
(backend/app/agents/stub_fixtures.py) so the StubRunner is self-contained;
this module re-exports them and adds context builders that assemble the
prior signed artifacts each contract's hard rules consult.
"""
from __future__ import annotations

from backend.app.agents.stub_fixtures import (  # noqa: F401  (re-exported)
    STUB_OUTPUTS,
    USER_REQUEST,
    VALID_INTERPRETATION,
    VALID_MANIFEST,
    VALID_PD,
    VALID_PREPARED,
    VALID_RECOMMENDATION,
    VALID_REPORT,
)
from backend.app.contracts.analysis_report import AnalysisReport
from backend.app.contracts.collection_manifest import CollectionManifest
from backend.app.contracts.interpretation import Interpretation
from backend.app.contracts.prepared_dataset import PreparedDataset
from backend.app.contracts.problem_definition import ProblemDefinition


def pd_context() -> dict:
    return {
        "problem_definition": ProblemDefinition.model_validate(VALID_PD),
        "user_request": USER_REQUEST,
    }


def prepared_context() -> dict:
    ctx = pd_context()
    ctx["collection_manifest"] = CollectionManifest.model_validate(VALID_MANIFEST)
    return ctx


def analysis_context() -> dict:
    ctx = prepared_context()
    ctx["prepared_dataset"] = PreparedDataset.model_validate(VALID_PREPARED)
    ctx["analysis_report"] = AnalysisReport.model_validate(VALID_REPORT)
    ctx["interpretation"] = Interpretation.model_validate(VALID_INTERPRETATION)
    return ctx


def full_context() -> dict:
    return analysis_context()
