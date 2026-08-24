"""Harness tests: graph topology, in-stage fix loops, gate interrupts,
loop-back routing, and escalation."""
from __future__ import annotations

import uuid

import pytest
from langgraph.types import Command

from backend.app.agents.missions import build_mission_prompt
from backend.app.agents.runner import StubRunner
from backend.app.agents.stub_fixtures import USER_REQUEST
from backend.app.config import settings
from backend.app.graph import StageEscalationError, build_graph
from backend.app.hitl import GateMode

GATES_ALL_REVIEW = {s: GateMode.REVIEW_ABLE for s in range(1, 7)}

ARTIFACT_NAMES = (
    "problem_definition",
    "collection_manifest",
    "prepared_dataset",
    "analysis_report",
    "interpretation",
    "recommendation",
)


def _config() -> dict:
    return {"configurable": {"thread_id": f"test-{uuid.uuid4().hex[:8]}"}}


def _interrupt_value(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__") or []
    return interrupts[0].value if interrupts else None


def _resume(graph, result, config, payload: dict):
    return graph.invoke(Command(resume=payload), config)


def test_full_chain_all_reviewable_signs_all_six():
    """No skipping: every stage must run and sign before the next exists."""
    runner = StubRunner()
    graph = build_graph(runner=runner, gate_modes=GATES_ALL_REVIEW)

    final = graph.invoke({"user_request": USER_REQUEST}, _config())

    assert set(final["stage_statuses"].values()) == {"signed"}
    assert len(final["stage_statuses"]) == 6
    for name in ARTIFACT_NAMES:
        assert final[name] is not None, f"{name} missing"
    assert final["current_stage"] == 6
    signed = [e for e in final["decision_log"] if e["event"] == "stage_signed"]
    assert [e["stage"] for e in signed] == [1, 2, 3, 4, 5, 6]


def test_default_gates_interrupt_only_at_one_and_six():
    """Default policy: G1 and G6 BLOCK, G2-G5 REVIEW-ABLE (auto-pass)."""
    runner = StubRunner()
    graph = build_graph(runner=runner)

    seen: list[int] = []
    config = _config()
    result = graph.invoke({"user_request": USER_REQUEST}, config)
    while "__interrupt__" in result:
        value = _interrupt_value(result)
        seen.append(value["gate_id"])
        result = _resume(graph, result, config, {"action": "approve"})

    assert seen == [1, 6]


def test_stage1_interrupt_payload_carries_artifact():
    """The BLOCK gate hands the human the signed artifact to review."""
    graph = build_graph(runner=StubRunner())
    config = _config()

    result = graph.invoke({"user_request": USER_REQUEST}, config)
    value = _interrupt_value(result)

    assert value["type"] == "gate_open"
    assert value["gate_id"] == 1
    assert value["stage"] == 1
    assert "question" in value
    assert value["artifact"]["problem_statement"]


def test_in_stage_fix_loop_signs_on_second_attempt():
    """No-Debt-Forward: a rejected output loops INSIDE the stage until valid."""
    runner = StubRunner(fail_once=True)
    graph = build_graph(runner=runner, gate_modes=GATES_ALL_REVIEW)

    final = graph.invoke({"user_request": USER_REQUEST}, _config())

    assert runner.calls[1] == 2
    assert final["problem_definition"] is not None


def test_escalation_after_max_attempts():
    """A stage that never signs escalates with its violations attached."""
    runner = StubRunner(always_bad=True)
    graph = build_graph(runner=runner, gate_modes=GATES_ALL_REVIEW)

    with pytest.raises(StageEscalationError) as exc:
        graph.invoke({"user_request": USER_REQUEST}, _config())

    assert exc.value.stage == 1
    assert runner.calls[1] == settings.stage_retries + 1
    assert exc.value.violations  # the corrective feedback trail


def test_regenerate_at_gate_reruns_same_stage():
    """A human 'regenerate' sends the mission back into the same stage."""
    runner = StubRunner()
    graph = build_graph(runner=runner)
    config = _config()

    result = graph.invoke({"user_request": USER_REQUEST}, config)
    assert _interrupt_value(result)["gate_id"] == 1

    result = _resume(graph, result, config, {"action": "regenerate", "feedback": "rethink"})
    assert _interrupt_value(result)["gate_id"] == 1  # same gate re-opens
    assert runner.calls[1] == 2

    result = _resume(graph, result, config, {"action": "approve"})
    assert result["problem_definition"] is not None


def test_edit_at_gate_updates_artifact():
    """A human 'edit' merges the payload and re-validates the contract."""
    graph = build_graph(runner=StubRunner())
    config = _config()

    result = graph.invoke({"user_request": USER_REQUEST}, config)
    result = _resume(
        graph,
        result,
        config,
        {
            "action": "edit",
            "feedback": "add a budget constraint",
            "edit_payload": {"constraints": ["No new hires before Q4", "Budget frozen"]},
        },
    )
    # Stage 2..5 auto-pass; next interrupt is gate 6 — approve to finish.
    assert _interrupt_value(result)["gate_id"] == 6
    result = _resume(graph, result, config, {"action": "approve"})

    assert result["problem_definition"].constraints == [
        "No new hires before Q4",
        "Budget frozen",
    ]


def test_edit_failing_validation_falls_back_to_regenerate():
    """An edit that breaks the contract can never slip through the gate."""
    graph = build_graph(runner=StubRunner())
    config = _config()

    result = graph.invoke({"user_request": USER_REQUEST}, config)
    # problem_statement verbatim-copied from the user request is rejected
    # by the Stage 1 hard rules, so the gate must fall back to regenerate.
    result = _resume(
        graph,
        result,
        config,
        {"action": "edit", "edit_payload": {"problem_statement": USER_REQUEST}},
    )

    assert _interrupt_value(result)["gate_id"] == 1
    result = _resume(graph, result, config, {"action": "approve"})
    assert result["problem_definition"] is not None


def test_send_back_loops_to_target_stage():
    """G6 SEND_BACK routes to the target stage, which reruns before G6 re-opens."""
    runner = StubRunner()
    graph = build_graph(runner=runner)
    config = _config()

    result = graph.invoke({"user_request": USER_REQUEST}, config)
    result = _resume(graph, result, config, {"action": "approve"})
    value = _interrupt_value(result)
    assert value["gate_id"] == 6

    result = _resume(
        graph,
        result,
        config,
        {"action": "send_back", "target_stage": 5, "feedback": "seasonality missing"},
    )
    value = _interrupt_value(result)
    assert value["gate_id"] == 6  # gate 6 re-opens after the loop
    assert runner.calls[5] == 2  # stage 5 ran again

    result = _resume(graph, result, config, {"action": "approve"})
    assert result["recommendation"] is not None
    assert len(result["feedback"]) == 3  # G1 + G6(send_back) + G6(approve)


def test_mission_prompt_carries_perception():
    """The mission prompt feeds the agent its environment: prior artifacts,
    human feedback, fix feedback, and the contract schema."""
    from backend.app.contracts import contract_for_stage

    state = {"user_request": USER_REQUEST, "feedback": [{"gate": 1, "text": "tighter scope"}]}
    prompt = build_mission_prompt(2, state, [])

    assert "USER REQUEST" in prompt
    assert "ARTIFACT FROM STAGE 1" in prompt  # prior signed artifact
    assert "tighter scope" in prompt  # human feedback
    assert "collection_manifest" in prompt  # the contract schema
    assert '"coverage"' in prompt  # a manifest schema field

    fix = build_mission_prompt(2, state, ["coverage: question not covered"])
    assert "YOUR PREVIOUS OUTPUT WAS REJECTED" in fix
    assert "coverage: question not covered" in fix

    first = build_mission_prompt(1, state, [])
    assert "ARTIFACT FROM STAGE" not in first  # stage 1 has no prior artifacts
    assert contract_for_stage(1).name in first
