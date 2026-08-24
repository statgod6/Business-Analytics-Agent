"""The LangGraph harness: 6-stage linear chain, contract validation,
in-stage fix loops, and harness-owned HITL gates.

Methodology is gravity: stages are graph nodes and cannot be skipped.
Contracts are law: a stage only exits through a signed artifact, looping
internally (with corrective feedback) until it signs or escalates.
Gates are harness-owned: BLOCK gates interrupt for the human; REVIEW-ABLE
gates auto-pass with the artifact logged.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.agents.runner import DeepAgentRunner, MissionRunner
from backend.app.config import settings
from backend.app.contracts import STAGE_CONTRACTS, contract_for_stage
from backend.app.hitl import GateMode, GateSpec
from backend.app.state import BAState

# stage -> state field holding its signed artifact
ARTIFACT_FIELD: dict[int, str] = {c.stage: c.name for c in STAGE_CONTRACTS.values()}


class StageEscalationError(RuntimeError):
    """A stage failed to sign its contract after the maximum attempts.

    M2: propagates to the caller. M3: routed to a human gate with the
    structured error report instead.
    """

    def __init__(self, stage: int, violations: list[str]) -> None:
        self.stage = stage
        self.violations = violations
        super().__init__(f"stage {stage} failed to sign its contract: {'; '.join(violations[:3])}")


def build_context(state: BAState) -> dict[str, Any]:
    """Prior signed artifacts + user request, as the contracts' context."""
    context: dict[str, Any] = {"user_request": state.get("user_request", "")}
    context.update({name: state.get(name) for name in ARTIFACT_FIELD.values() if state.get(name)})
    return context


def make_stage_node(stage: int, runner: MissionRunner, max_attempts: int) -> Callable[[BAState], dict[str, Any]]:
    """Run the mission, validate against the Stage Contract, loop in-stage
    on failure (No-Debt-Forward), escalate when exhausted."""
    contract = contract_for_stage(stage)

    def stage_node(state: BAState) -> dict[str, Any]:
        statuses = dict(state.get("stage_statuses") or {})
        statuses[str(stage)] = "running"
        fix_feedback: list[str] = []
        attempts = 0
        while True:
            attempts += 1
            raw = runner.run(stage, state, fix_feedback)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                fix_feedback = [f"output was not valid JSON: {exc}"]
            else:
                result = contract.validate(data, build_context(state))
                if result.valid:
                    statuses[str(stage)] = "signed"
                    return {
                        "current_stage": stage,
                        "stage_statuses": statuses,
                        contract.name: result.artifact,
                        "decision_log": [
                            {"event": "stage_signed", "stage": stage, "attempts": attempts}
                        ],
                    }
                fix_feedback = [f"{v.rule}: {v.detail}" for v in result.violations]
            if attempts >= max_attempts:
                statuses[str(stage)] = "failed"
                raise StageEscalationError(stage, fix_feedback)

    return stage_node


def make_gate_node(gate: GateSpec) -> Callable[[BAState], dict[str, Any]]:
    """The door between missions. BLOCK gates interrupt for the human;
    REVIEW-ABLE gates auto-pass with the artifact logged."""
    field = ARTIFACT_FIELD[gate.stage]
    contract = contract_for_stage(gate.stage)

    def gate_node(state: BAState) -> dict[str, Any]:
        decision = {"action": "approve"}
        if gate.mode is GateMode.BLOCK:
            artifact = state.get(field)
            payload = interrupt(
                {
                    "type": "gate_open",
                    "gate_id": gate.gate_id,
                    "stage": gate.stage,
                    "artifact": artifact.model_dump() if artifact else None,
                    "question": f"Approve the Stage {gate.stage} artifact ({contract.name})?",
                }
            )
            action = payload.get("action", "approve")
            decision = {
                "action": action,
                "feedback": payload.get("feedback", ""),
                "target_stage": payload.get("target_stage"),
            }
            if action == "edit":
                edits = payload.get("edit_payload") or {}
                current = artifact.model_dump() if artifact else {}
                current.update(edits)
                res = contract.validate(current, build_context(state))
                if res.valid:
                    return {
                        "last_gate_decision": decision,
                        field: res.artifact,
                        "feedback": [
                            {
                                "gate": gate.gate_id,
                                "stage": gate.stage,
                                "action": "edit",
                                "text": payload.get("feedback", ""),
                            }
                        ],
                    }
                decision = {
                    "action": "regenerate",
                    "feedback": "Your edits failed validation: " + res.summary(),
                }
        updates: dict[str, Any] = {"last_gate_decision": decision}
        if gate.mode is GateMode.BLOCK:
            updates["feedback"] = [
                {
                    "gate": gate.gate_id,
                    "stage": gate.stage,
                    "action": decision["action"],
                    "text": decision.get("feedback", ""),
                }
            ]
        return updates

    return gate_node


def make_after_gate_route(stage: int) -> Callable[[BAState], str]:
    """Route after a gate: approve -> next (or END); regenerate -> same stage;
    send_back -> target stage (loop-back edge)."""

    def route(state: BAState) -> str:
        decision = state.get("last_gate_decision") or {}
        action = decision.get("action")
        if action == "regenerate":
            return f"stage_{stage}"
        if action == "send_back":
            target = decision.get("target_stage")
            return f"stage_{target}" if target in ARTIFACT_FIELD else f"stage_{stage}"
        return END if stage == 6 else f"stage_{stage + 1}"

    return route


def build_graph(
    runner: MissionRunner | None = None,
    gate_modes: dict[int, GateMode] | None = None,
):
    """Assemble and compile the harness. Injected runner/gate modes keep
    tests deterministic; production defaults use Deep Agents + .env."""
    runner = runner or DeepAgentRunner()
    modes = gate_modes or settings.gate_modes()

    graph = StateGraph(BAState)
    for stage in ARTIFACT_FIELD:
        graph.add_node(
            f"stage_{stage}",
            make_stage_node(stage, runner, max_attempts=settings.stage_retries + 1),
        )
        graph.add_node(
            f"gate_{stage}",
            make_gate_node(GateSpec(gate_id=stage, stage=stage, mode=modes[stage])),
        )

    graph.add_edge(START, "stage_1")
    paths = {f"stage_{s}": f"stage_{s}" for s in ARTIFACT_FIELD}
    paths[END] = END
    for stage in ARTIFACT_FIELD:
        graph.add_edge(f"stage_{stage}", f"gate_{stage}")
        graph.add_conditional_edges(f"gate_{stage}", make_after_gate_route(stage), paths)

    return graph.compile(checkpointer=MemorySaver())
