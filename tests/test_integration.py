"""Integration tests: file upload and WebSocket event streaming.

Requires a running PostgreSQL instance (see docker-compose.yml).
Uses FastAPI's TestClient with httpx.AsyncClient + ASGITransport.
"""
from __future__ import annotations

import io
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import Base, engine, get_db
from backend.app.main import app

BASE = "http://test"


@pytest.fixture(autouse=True)
async def _db_tx():
    """Drop and recreate tables, wrap each test in a rollback-able transaction.

    Using drop_all + create_all ensures schema changes (e.g. new columns)
    are picked up even when the persistent Docker PostgreSQL already has
    tables from a previous run.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)

    async def _get_db_override():
        yield session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    await trans.rollback()
    await conn.close()
    await engine.dispose()
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as ac:
        yield ac


@pytest.fixture
async def authed_headers(client: AsyncClient) -> dict:
    r = await client.post(
        "/auth/register",
        json={"email": "integ@ba.dev", "password": "secret123"},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def run_id(client: AsyncClient, authed_headers: dict) -> str:
    r = await client.post(
        "/api/runs",
        json={"user_request": "Integration test run"},
        headers=authed_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ── File Upload ────────────────────────────────────────────────


class TestFileUpload:
    async def test_upload_csv(self, client: AsyncClient, authed_headers: dict, run_id: str):
        content = b"col1,col2\n1,2\n3,4"
        r = await client.post(
            f"/api/runs/{run_id}/files",
            files={"file": ("test.csv", io.BytesIO(content), "text/csv")},
            headers=authed_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "files" in body
        assert len(body["files"]) == 1
        assert body["files"][0]["original_name"] == "test.csv"
        assert body["files"][0]["size"] == len(content)

    async def test_upload_invalid_extension(self, client: AsyncClient, authed_headers: dict, run_id: str):
        r = await client.post(
            f"/api/runs/{run_id}/files",
            files={"file": ("test.exe", io.BytesIO(b"bad"), "application/octet-stream")},
            headers=authed_headers,
        )
        assert r.status_code == 422

    async def test_upload_to_nonexistent_run(self, client: AsyncClient, authed_headers: dict):
        r = await client.post(
            "/api/runs/00000000-0000-0000-0000-000000000000/files",
            files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
            headers=authed_headers,
        )
        assert r.status_code == 404

    async def test_upload_requires_auth(self, client: AsyncClient, run_id: str):
        r = await client.post(
            f"/api/runs/{run_id}/files",
            files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
        )
        assert r.status_code == 401

    async def test_run_files_column_stores_metadata(self, client: AsyncClient, authed_headers: dict, run_id: str):
        content = b"x,y\n1,2"
        await client.post(
            f"/api/runs/{run_id}/files",
            files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
            headers=authed_headers,
        )
        r = await client.get(f"/api/runs/{run_id}", headers=authed_headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body["files"]) == 1
        assert body["files"][0]["original_name"] == "data.csv"


# ── WebSocket ──────────────────────────────────────────────────


# WebSocket integration tests require a real WebSocket client library.
# httpx ASGITransport cannot perform WebSocket upgrades, so these are
# verified via the existing graph tests that exercise the HITL flow
# (test_graph.py), and manually via the frontend.