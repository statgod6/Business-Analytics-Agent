"""Stage Contract registry: the six contracts, ordered by stage."""
from __future__ import annotations

from backend.app.contracts.analysis_report import CONTRACT as ANALYSIS_REPORT
from backend.app.contracts.base import StageContract
from backend.app.contracts.collection_manifest import CONTRACT as COLLECTION_MANIFEST
from backend.app.contracts.interpretation import CONTRACT as INTERPRETATION
from backend.app.contracts.prepared_dataset import CONTRACT as PREPARED_DATASET
from backend.app.contracts.problem_definition import CONTRACT as PROBLEM_DEFINITION
from backend.app.contracts.recommendation import CONTRACT as RECOMMENDATION

STAGE_CONTRACTS: dict[int, StageContract] = {
    1: PROBLEM_DEFINITION,
    2: COLLECTION_MANIFEST,
    3: PREPARED_DATASET,
    4: ANALYSIS_REPORT,
    5: INTERPRETATION,
    6: RECOMMENDATION,
}

STAGE_ORDER = sorted(STAGE_CONTRACTS)


def contract_for_stage(stage: int) -> StageContract:
    try:
        return STAGE_CONTRACTS[stage]
    except KeyError:
        raise KeyError(f"no Stage Contract for stage {stage}") from None


__all__ = [
    "STAGE_CONTRACTS",
    "STAGE_ORDER",
    "contract_for_stage",
    "StageContract",
]
