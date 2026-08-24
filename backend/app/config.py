"""Application settings loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.hitl import DEFAULT_GATE_MODES, GateMode, gate_specs


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API keys ────────────────────────────────────────────
    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    e2b_api_key: str = ""

    # ── Database ────────────────────────────────────────────
    database_url: str = "postgresql://ba:ba@localhost:5432/ba_agent"

    # ── Auth ────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-prod"
    jwt_expire_minutes: int = 1440

    # ── Brain (OpenRouter model routing) ────────────────────
    model_strong: str = "anthropic/claude-sonnet-4"  # Stages 1, 4, 5, 6
    model_efficient: str = "openai/gpt-4o-mini"  # Stages 2, 3

    # ── HITL gate modes (G1, G6 are always BLOCK) ───────────
    gate_mode_s2: GateMode = GateMode.REVIEW_ABLE
    gate_mode_s3: GateMode = GateMode.REVIEW_ABLE
    gate_mode_s4: GateMode = GateMode.REVIEW_ABLE
    gate_mode_s5: GateMode = GateMode.REVIEW_ABLE

    # ── Harness ─────────────────────────────────────────────
    stage_recursion_limit: int = 120
    stage_retries: int = 2
    stage_timeout_seconds: int = 1800

    def model_for_stage(self, stage: int) -> str:
        """OpenRouter model id for a stage (strong vs efficient tier)."""
        return self.model_strong if stage in (1, 4, 5, 6) else self.model_efficient

    def gate_modes(self) -> dict[int, GateMode]:
        modes = dict(DEFAULT_GATE_MODES)
        modes[2] = self.gate_mode_s2
        modes[3] = self.gate_mode_s3
        modes[4] = self.gate_mode_s4
        modes[5] = self.gate_mode_s5
        return modes

    def gate_specs(self) -> list:
        from backend.app.hitl import gate_specs as _gate_specs

        return _gate_specs(self.gate_modes())


settings = Settings()
