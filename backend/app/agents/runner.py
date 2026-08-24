"""Mission runners.

``MissionRunner`` is the interface between the harness and the engine.
``DeepAgentRunner`` uses the real Deep Agents loop (planner + executor)
with OpenRouter-routed models and stage-scoped tools; ``StubRunner``
returns deterministic fixtures so graph tests and offline demos run
without API keys.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from backend.app.agents.missions import STAGE_MISSIONS, build_mission_prompt
from backend.app.agents.stub_fixtures import STUB_OUTPUTS
from backend.app.agents.tools import build_stage_tools
from backend.app.config import Settings, settings


class MissionRunner(Protocol):
    """Anything that produces a stage's candidate artifact (raw JSON text)."""

    def run(self, stage: int, state: dict, fix_feedback: list[str]) -> str: ...


class StubRunner:
    """Deterministic mission runner for tests and offline demos."""

    def __init__(self, always_bad: bool = False, fail_once: bool = False) -> None:
        self.always_bad = always_bad
        self.fail_once = fail_once
        self.calls: dict[int, int] = {}

    def run(self, stage: int, state: dict, fix_feedback: list[str]) -> str:
        self.calls[stage] = self.calls.get(stage, 0) + 1
        if self.always_bad:
            return "{definitely not valid json"
        if self.fail_once and stage == 1 and not fix_feedback:
            # schema-invalid output (problem_statement must be a string)
            return json.dumps({"problem_statement": 123, "key_questions": []})
        return json.dumps(STUB_OUTPUTS[stage], default=str)


PURE_STAGE_EXCLUDED_TOOLS = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute", "task"}
)
"""Built-in deep-agents tools stripped from pure stages (1, 5, 6)."""


def _pure_stage_middleware() -> list[Any]:
    """Tool-exclusion middleware for pure stages.

    ``create_deep_agent`` always mounts filesystem tools via required
    ``FilesystemMiddleware``; the library's own exclusion middleware (used by
    harness profiles to strip them) must be placed in the user middleware
    stack, which lands after the core stack. Fail fast if the private module
    moves in a future deepagents release — silent purity loss is worse.
    """
    try:
        from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
    except ImportError as exc:  # pragma: no cover - version drift guard
        raise RuntimeError(
            "deepagents version moved: _ToolExclusionMiddleware unavailable; "
            "pure-stage tool exclusion cannot be enforced"
        ) from exc
    return [_ToolExclusionMiddleware(excluded=PURE_STAGE_EXCLUDED_TOOLS)]


def _extract_output(result: Any) -> str:
    """Pull the final answer text out of a deep-agents run result."""
    messages = result.get("messages") or [] if isinstance(result, dict) else []
    if not messages:
        return str(result)
    content = messages[-1].content
    if isinstance(content, str):
        return content
    parts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(parts)


class DeepAgentRunner:
    """Real engine: one cached Deep Agent per stage (perceive-plan-decide-act)."""

    def __init__(self, s: Settings | None = None) -> None:
        self.settings = s or settings
        self._agents: dict[int, Any] = {}

    def _agent(self, stage: int):
        if stage not in self._agents:
            from deepagents import create_deep_agent
            from langchain_openai import ChatOpenAI

            if not self.settings.openrouter_api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY not set — add it to .env or use --stub for offline runs"
                )
            model = ChatOpenAI(
                model=self.settings.model_for_stage(stage),
                api_key=self.settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.2,
            )
            kwargs: dict[str, Any] = {}
            if stage in (1, 5, 6):
                kwargs["middleware"] = _pure_stage_middleware()
            self._agents[stage] = create_deep_agent(
                model=model,
                tools=build_stage_tools(stage),
                system_prompt=STAGE_MISSIONS[stage]["persona"],
                name=f"stage_{stage}_{STAGE_MISSIONS[stage]['name']}",
                **kwargs,
            )
        return self._agents[stage]

    def run(self, stage: int, state: dict, fix_feedback: list[str]) -> str:
        prompt = build_mission_prompt(stage, state, fix_feedback)
        result = self._agent(stage).invoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
        return _extract_output(result)
