"""Shared state for the BA Agent graph.

Organized by stage artifacts (never by analyst): future specialist fan-out
changes node internals only, never the harness or this state shape.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from backend.app.contracts.analysis_report import AnalysisReport
from backend.app.contracts.collection_manifest import CollectionManifest
from backend.app.contracts.interpretation import Interpretation
from backend.app.contracts.prepared_dataset import PreparedDataset
from backend.app.contracts.problem_definition import ProblemDefinition
from backend.app.contracts.recommendation import Recommendation


class BAState(TypedDict, total=False):
    """The single shared state object the whole graph reads and writes."""

    # ── Control ─────────────────────────────────────────────
    user_request: str
    current_stage: int
    stage_statuses: dict[str, str]  # stage -> pending|running|signed|failed
    error: str | None
    retries: int

    # ── User & loop ─────────────────────────────────────────
    feedback: Annotated[list[dict[str, Any]], operator.add]  # human feedback per gate
    decision_log: Annotated[list[dict[str, Any]], operator.add]  # agent reasoning trail
    last_gate_decision: dict[str, Any] | None  # set by gate nodes; consumed by routing

    # ── Signed artifacts (the contracts) ────────────────────
    problem_definition: ProblemDefinition | None
    collection_manifest: CollectionManifest | None
    prepared_dataset: PreparedDataset | None
    analysis_report: AnalysisReport | None
    interpretation: Interpretation | None
    recommendation: Recommendation | None
