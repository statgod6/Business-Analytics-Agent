"""Stage 2 contract: CollectionManifest.

Data is acquired AND ingested here (format conversion at acquisition, so
parse failures surface while the source is still reachable). Every Stage 1
key question must be covered, and every missing-data entry must be resolved
in-stage — no gaps travel forward.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode


class FieldSchema(BaseModel):
    field: str
    inferred_type: str


class IngestionReport(BaseModel):
    format: Literal["csv", "excel", "pdf", "json", "word", "sql"]
    status: Literal["success", "partial", "failed"]
    records_extracted: int = 0
    parse_errors: list[str] = Field(default_factory=list)
    schema_extracted: list[FieldSchema] = Field(default_factory=list)


class Source(BaseModel):
    source_id: str
    source_type: Literal["web", "file", "database", "api"]
    location: str
    acquired_at: str
    provenance_notes: str
    ingestion: IngestionReport


class Coverage(BaseModel):
    key_question_ref: str
    covered_by: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class MissingData(BaseModel):
    what: str
    why: str
    impact: str
    resolved_in_stage: bool = False


class CollectionManifest(BaseModel):
    sources: list[Source]
    coverage: list[Coverage]
    missing_data: list[MissingData] = Field(default_factory=list)
    access_issues: list[str] = Field(default_factory=list)
    overall_status: Literal["complete"] = "complete"


def _rule_full_coverage(artifact: CollectionManifest, context: dict[str, Any]) -> list[str]:
    """Every Stage 1 key question must appear in coverage."""
    problem = context.get("problem_definition")
    if problem is None:
        return []  # requires[] already guards this; defensive no-op
    covered = {c.key_question_ref for c in artifact.coverage}
    return [
        f"key question not covered by any source: {q!r}"
        for q in problem.key_questions
        if q not in covered
    ]


def _rule_missing_data_resolved(artifact: CollectionManifest, context: dict[str, Any]) -> list[str]:
    """No-Debt-Forward: every gap must be resolved in this stage."""
    return [
        f"missing data unresolved in-stage: {m.what!r} (impact: {m.impact})"
        for m in artifact.missing_data
        if not m.resolved_in_stage
    ]


def _rule_failed_sources_accounted(artifact: CollectionManifest, context: dict[str, Any]) -> list[str]:
    """A failed ingestion may not silently disappear — it must be re-fetched
    or declared in missing_data (which then must be resolved)."""
    accounted = " ".join(f"{m.what} {m.why}" for m in artifact.missing_data).lower()
    violations = []
    for src in artifact.sources:
        if src.ingestion.status == "failed" and src.source_id.lower() not in accounted:
            violations.append(
                f"source {src.source_id!r} failed ingestion but is not accounted "
                "for in missing_data"
            )
    return violations


CONTRACT = StageContract(
    stage=2,
    name="collection_manifest",
    gate_mode=GateMode.REVIEW_ABLE,
    artifact_schema=CollectionManifest,
    hard_rules=[
        _rule_full_coverage,
        _rule_missing_data_resolved,
        _rule_failed_sources_accounted,
    ],
    requires=["problem_definition"],
)
