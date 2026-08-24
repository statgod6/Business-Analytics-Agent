"""Stage 3 contract: PreparedDataset (with the Data Contract).

Cleaning happens in E2B and must be auditable. Every field needs a business
semantic meaning, and poor quality metrics must be acknowledged as
limitations — a dirty dataset claiming no limitations fails.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.app.contracts.base import StageContract
from backend.app.hitl import GateMode


class FieldContract(BaseModel):
    name: str
    semantic_meaning: str  # the BUSINESS meaning, not the column name
    data_type: str
    allowed_values_or_range: str = ""
    nullability: bool = False
    quality_flags: list[str] = Field(default_factory=list)
    transformations_applied: list[str] = Field(default_factory=list)
    source_ref: str = ""


class DataContract(BaseModel):
    version: str = "1.0"
    fields: list[FieldContract]


class DatasetInfo(BaseModel):
    location: str
    row_count: int
    column_count: int
    primary_key: str | None = None
    granularity: str = ""
    time_range: dict[str, Any] | None = None


class QualityMetrics(BaseModel):
    missingness_percent: float = 0.0
    duplicate_rate: float = 0.0
    validation_errors: list[str] = Field(default_factory=list)


class Limitation(BaseModel):
    limitation: str
    impact_on_analysis: str


class PreparedDataset(BaseModel):
    dataset: DatasetInfo
    data_contract: DataContract
    quality_metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    cleaning_log: list[str] = Field(default_factory=list)
    limitations: list[Limitation] = Field(default_factory=list)


def _rule_named_fields(artifact: PreparedDataset, context: dict[str, Any]) -> list[str]:
    return [
        f"field {f.name!r} has no semantic meaning — no unnamed columns"
        for f in artifact.data_contract.fields
        if not f.semantic_meaning.strip()
    ]


def _rule_quality_acknowledged(artifact: PreparedDataset, context: dict[str, Any]) -> list[str]:
    """Poor quality requires matching limitations — no silent dirt."""
    q = artifact.quality_metrics
    dirty = (
        q.missingness_percent > 5.0
        or q.duplicate_rate > 5.0
        or bool(q.validation_errors)
    )
    if dirty and not artifact.limitations:
        return [
            "quality metrics indicate issues (missingness "
            f"{q.missingness_percent:.1f}%, duplicates {q.duplicate_rate:.1f}%, "
            f"{len(q.validation_errors)} validation error(s)) but no limitations "
            "are declared"
        ]
    return []


def _rule_cleaning_logged(artifact: PreparedDataset, context: dict[str, Any]) -> list[str]:
    """Any transformation must be recorded in the cleaning log."""
    transformed = any(f.transformations_applied for f in artifact.data_contract.fields)
    if transformed and not artifact.cleaning_log:
        return ["fields declare transformations but the cleaning log is empty"]
    return []


CONTRACT = StageContract(
    stage=3,
    name="prepared_dataset",
    gate_mode=GateMode.REVIEW_ABLE,
    artifact_schema=PreparedDataset,
    hard_rules=[
        _rule_named_fields,
        _rule_quality_acknowledged,
        _rule_cleaning_logged,
    ],
    requires=["problem_definition", "collection_manifest"],
)
