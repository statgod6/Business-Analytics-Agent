"""Per-stage mission definitions: personas and mission prompt builder.

The same agent engine runs six scoped missions. The Stage Contract
enforces structure; the mission prompt sets the persona and injects the
agent's perception (prior artifacts, human feedback, fix feedback).
"""
from __future__ import annotations

import json
from typing import Any

from backend.app.contracts import contract_for_stage

STAGE_MISSIONS: dict[int, dict[str, str]] = {
    1: {
        "name": "problem_definition",
        "persona": (
            "You are a senior business analyst clarifying a mandate. Turn a raw "
            "business request into a precise problem definition: scope, objectives, "
            "measurable success criteria, and data-answerable key questions. You do "
            "NOT collect or analyze data yet. Show interpretation — never restate "
            "the request verbatim."
        ),
    },
    2: {
        "name": "collection_manifest",
        "persona": (
            "You are a data hunter. Locate and acquire the data needed to answer "
            "the key questions, INGEST it (convert raw files to structured data), "
            "and report provenance, ingestion status, schema, coverage, and missing "
            "data. Every gap must be resolved in this stage: re-fetch, find an "
            "alternative source, or derive it. You may search the web and read "
            "local files."
        ),
    },
    3: {
        "name": "prepared_dataset",
        "persona": (
            "You are a meticulous data engineer. Clean, validate, and transform the "
            "collected data into an analysis-ready dataset, and issue a Data "
            "Contract giving every field a business semantic meaning. Record every "
            "transformation in the cleaning log and declare limitations honestly."
        ),
    },
    4: {
        "name": "analysis_report",
        "persona": (
            "You are a rigorous statistician. Answer the key questions with real "
            "computed results — write and run code in the sandbox for every "
            "analysis. Every finding MUST reference the computed output that "
            "supports it. No evidence, no finding."
        ),
    },
    5: {
        "name": "interpretation",
        "persona": (
            "You are a business translator. Convert analytical findings into "
            "business meaning: so-what, causal hypotheses labeled by evidence "
            "strength, risks, and implications. You have NO tools — reason only "
            "from the evidence in hand. Never claim external benchmarks."
        ),
    },
    6: {
        "name": "recommendation",
        "persona": (
            "You are a decision advisor. Synthesize everything into actionable, "
            "prioritized recommendations. Every recommendation must cite a Stage 1 "
            "success criterion, and its rationale must trace through real findings "
            "and hypotheses. Address every success criterion or explicitly defer it."
        ),
    },
}


def _serialize(value: Any) -> str:
    if value is None:
        return "(none yet)"
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return json.dumps(value, indent=2, default=str)


def build_mission_prompt(stage: int, state: dict, fix_feedback: list[str]) -> str:
    """Compose the mission prompt from the agent's perception of the world."""
    mission = STAGE_MISSIONS[stage]
    contract = contract_for_stage(stage)

    context_parts = [f"USER REQUEST:\n{state.get('user_request', '')}"]
    for prior in range(1, stage):
        c = contract_for_stage(prior)
        context_parts.append(f"ARTIFACT FROM STAGE {prior} ({c.name}):\n{_serialize(state.get(c.name))}")
    human_feedback = state.get("feedback") or []
    if human_feedback:
        context_parts.append(f"RECENT HUMAN FEEDBACK:\n{_serialize(human_feedback[-3:])}")
    if fix_feedback:
        context_parts.append(
            "YOUR PREVIOUS OUTPUT WAS REJECTED. Fix these violations:\n- "
            + "\n- ".join(fix_feedback)
        )

    schema = contract.artifact_schema.model_json_schema()
    return (
        f"{mission['persona']}\n\n"
        f"CONTEXT:\n" + "\n\n".join(context_parts)
        + f"\n\nTASK: Produce the {contract.name} artifact for stage {stage}.\n"
        "Respond with ONLY valid JSON matching this schema:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "Do not wrap it in markdown fences. Do not add commentary."
    )
