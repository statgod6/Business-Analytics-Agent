"""Run engine: async orchestrator that connects the LangGraph harness to
the WebSocket event stream and gate-decision API.

Flow per run:
  1. Start graph.ainvoke() in background; stream events via WebSocket.
  2. When a BLOCK gate interrupts: emit `gate_open` event; wait on an
     asyncio.Event for the human's decision.
  3. Decision arrived via POST → Command(resume=...) → graph resumes.
  4. Repeat until graph completes (or errors), then update the Run row.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.runner import DeepAgentRunner, StubRunner
from backend.app.agents.stub_fixtures import USER_REQUEST
from backend.app.config import Settings
from backend.app.database import Run
from backend.app.graph import StageEscalationError, build_graph
from backend.app.hitl import GateMode
from backend.app.websocket_manager import ws_manager  # app singleton

logger = logging.getLogger(__name__)

ARTIFACT_FIELDS = [
    "problem_definition",
    "collection_manifest",
    "prepared_dataset",
    "analysis_report",
    "interpretation",
    "recommendation",
]


@dataclass
class RunContext:
    """Per-run coordination state held in memory while a run is active."""

    run_id: str
    decision_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision_payload: dict | None = None
    current_gate: dict | None = None  # last gate_open payload for context
    cancelled: bool = False

    def set_decision(self, payload: dict) -> None:
        self.decision_payload = payload
        self.decision_event.set()

    def clear_decision(self) -> None:
        self.decision_payload = None
        self.decision_event.clear()


class RunEngine:
    """Orchestrates one graph execution per run, bridging interrupts
    to the async WebSocket/API layer."""

    def __init__(self) -> None:
        self._runs: dict[str, RunContext] = {}

    # ── Public API ────────────────────────────────────────────

    async def start(
        self,
        run_id: str,
        user_request: str,
        settings: Settings,
    ) -> None:
        """Begin a graph run in the background."""
        ctx = RunContext(run_id=run_id)
        self._runs[run_id] = ctx
        asyncio.create_task(self._execute(run_id, user_request, settings))

    async def submit_decision(self, run_id: str, payload: dict) -> bool:
        """Feed a gate decision back to a waiting graph."""
        ctx = self._runs.get(run_id)
        if not ctx or ctx.decision_event.is_set():
            return False
        ctx.set_decision(payload)
        return True

    def get_context(self, run_id: str) -> RunContext | None:
        return self._runs.get(run_id)

    def cleanup(self, run_id: str) -> None:
        ctx = self._runs.pop(run_id, None)
        if ctx:
            ctx.cancelled = True
            ctx.set_decision({"action": "approve"})  # unblock if stuck

    # ── Internal ──────────────────────────────────────────────

    async def _execute(
        self,
        run_id: str,
        user_request: str,
        settings: Settings,
    ) -> None:
        """Background coroutine: build graph, run it, handle interrupts."""
        ctx = self._runs.get(run_id)
        if not ctx:
            return

        from backend.app.database import async_session as _session_factory

        async with _session_factory() as db:
            await self._update_run(db, run_id, status="running")
            await self._emit(run_id, {"type": "run_started", "run_id": run_id})

            try:
                has_real_keys = bool(settings.openrouter_api_key)
                runner = DeepAgentRunner() if has_real_keys else StubRunner()
                graph = build_graph(runner=runner)

                config = {"configurable": {"thread_id": f"run-{run_id}"}}
                state = {"user_request": user_request}

                await self._run_graph_loop(run_id, ctx, graph, state, config, db)

                await self._emit(run_id, {"type": "run_complete", "run_id": run_id})
                await self._update_run(
                    db, run_id, status="completed", result=state
                )

            except StageEscalationError as exc:
                logger.warning("Run %s escalated at stage %s", run_id, exc.stage)
                await self._emit(run_id, {
                    "type": "run_error",
                    "stage": exc.stage,
                    "detail": str(exc),
                })
                await self._update_run(
                    db,
                    run_id,
                    status="failed",
                    error=str(exc),
                )
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Run %s crashed", run_id)
                await self._emit(run_id, {"type": "run_error", "detail": "Internal error"})
                await self._update_run(db, run_id, status="failed", error="Internal error")
            finally:
                self._runs.pop(run_id, None)

    async def _run_graph_loop(
        self,
        run_id: str,
        ctx: RunContext,
        graph,
        state: dict,
        config: dict,
        db: AsyncSession | None = None,
    ) -> dict:
        """Loop: invoke graph → handle interrupts → resume."""
        result = await graph.ainvoke(state, config)
        while "__interrupt__" in result:
            interrupt_value = result["__interrupt__"][0].value
            gate_id = interrupt_value["gate_id"]
            stage = interrupt_value.get("stage", gate_id)
            artifact = interrupt_value.get("artifact")
            question = interrupt_value.get("question", f"Gate {gate_id} open")

            ctx.current_gate = {
                "gate_id": gate_id,
                "stage": stage,
                "artifact": artifact,
            }

            # Emit stage events from result state
            signed_artifacts = {
                f: result.get(f)
                for f in ARTIFACT_FIELDS
                if result.get(f) is not None
            }
            for fname, val in signed_artifacts.items():
                await self._emit(run_id, {
                    "type": "stage_signed",
                    "stage": ARTIFACT_FIELDS.index(fname) + 1,
                    "artifact_name": fname,
                })

            await self._emit(run_id, {
                "type": "gate_open",
                "gate_id": gate_id,
                "stage": stage,
                "artifact": artifact,
                "question": question,
            })

            await self._update_run(db, run_id=run_id, current_stage=stage)

            # Wait for human decision
            await ctx.decision_event.wait()
            decision = ctx.decision_payload or {"action": "approve"}
            ctx.clear_decision()

            await self._emit(run_id, {
                "type": "gate_closed",
                "gate_id": gate_id,
                "decision": decision.get("action"),
            })

            result = await graph.ainvoke(Command(resume=decision), config)

        # Final signed artifacts from the completed run
        for fname in ARTIFACT_FIELDS:
            val = result.get(fname)
            if val is not None:
                await self._emit(run_id, {
                    "type": "stage_signed",
                    "stage": ARTIFACT_FIELDS.index(fname) + 1,
                    "artifact_name": fname,
                })

        return result

    async def _emit(self, run_id: str, event: dict) -> None:
        try:
            await ws_manager.broadcast(run_id, event)
        except Exception:
            logger.exception("Broadcast failed for run %s", run_id)

    async def _update_run(
        self,
        db: AsyncSession | None,
        run_id: str,
        **kwargs,
    ) -> None:
        if db is None:
            return
        try:
            result = await db.execute(select(Run).where(Run.id == run_id))
            run = result.scalar_one_or_none()
            if run:
                for key, val in kwargs.items():
                    setattr(run, key, val)
                await db.commit()
        except Exception:
            logger.exception("Failed to update run %s", run_id)


# Singleton — shared with runs router
engine = RunEngine()