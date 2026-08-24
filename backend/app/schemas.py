"""Pydantic schemas for the BA Agent API."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Runs ──────────────────────────────────────────────────────


class RunCreate(BaseModel):
    user_request: str = Field(min_length=1, max_length=10000)


class RunOut(BaseModel):
    id: UUID
    status: str
    current_stage: int | None
    user_request: str
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class RunListOut(BaseModel):
    runs: list[RunOut]
    total: int


# ── Gate decisions ────────────────────────────────────────────


class GateDecisionIn(BaseModel):
    action: str = Field(
        pattern=r"^(approve|regenerate|send_back|edit)$",
        description="approve | regenerate | send_back | edit",
    )
    feedback: str = Field(default="", max_length=2000)
    target_stage: int | None = Field(default=None, ge=1, le=6)
    edit_payload: dict | None = None


class GateDecisionOut(BaseModel):
    status: str = "accepted"


# ── WebSocket events ─────────────────────────────────────────
# Not Pydantic models per se — wire format for WS messages.
# See websocket_manager.py for the event dicts.