"""Async SQLAlchemy engine, session factory, and ORM models.

Uses the asyncpg driver for PostgreSQL. Migrations are managed by
SQLAlchemy's ``create_all`` in the FastAPI lifespan (safe for the single-
developer/single-instance M3-M4 phase; M5 adds Alembic).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.app.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Engine & session ──────────────────────────────────────────

# Convert sync URL to async (postgresql:// -> postgresql+asyncpg://)
_ASYNC_DB_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

engine = create_async_engine(_ASYNC_DB_URL, echo=False, pool_size=5, max_overflow=2)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI dependency: yields one async session per request."""
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables. Called during FastAPI lifespan startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Base ──────────────────────────────────────────────────────


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ── Mixins ────────────────────────────────────────────────────


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


# ── User ──────────────────────────────────────────────────────


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    runs: Mapped[list[Run]] = relationship("Run", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# ── Run (analysis engagement) ─────────────────────────────────


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending | running | completed | failed
    current_stage: Mapped[int | None] = mapped_column(nullable=True)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    files: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run {self.id} [{self.status}]>"