"""API tests: auth flow (register, login, me) and run lifecycle.

Uses FastAPI's TestClient wrapped for async (httpx.AsyncClient +
ASGITransport).  Each test runs in its own database transaction that
is rolled back on teardown — complete isolation, no shared state.
Requires a running PostgreSQL instance (see docker-compose.yml).
"""
from __future__ import annotations

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
async def token(client: AsyncClient) -> str:
    r = await client.post(
        "/auth/register",
        json={"email": "t@ba.dev", "password": "secret123"},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


@pytest.fixture
def authed_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth ──────────────────────────────────────────────────────


class TestAuth:
    async def test_health(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_register_creates_user_and_returns_token(self, client: AsyncClient):
        r = await client.post(
            "/auth/register",
            json={"email": "a@b.com", "password": "pass1234"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post("/auth/register", json={"email": "dup@b.com", "password": "pass1234"})
        r = await client.post("/auth/register", json={"email": "dup@b.com", "password": "other123"})
        assert r.status_code == 409

    async def test_login_returns_token(self, client: AsyncClient):
        await client.post("/auth/register", json={"email": "log@b.com", "password": "pass1234"})
        r = await client.post("/auth/token", data={"username": "log@b.com", "password": "pass1234"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_bad_password(self, client: AsyncClient):
        await client.post("/auth/register", json={"email": "bad@b.com", "password": "pass1234"})
        r = await client.post("/auth/token", data={"username": "bad@b.com", "password": "wrong"})
        assert r.status_code == 401

    async def test_me_returns_user(self, client: AsyncClient, authed_headers: dict):
        r = await client.get("/auth/me", headers=authed_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "t@ba.dev"

    async def test_me_requires_auth(self, client: AsyncClient):
        r = await client.get("/auth/me")
        assert r.status_code == 401


# ── Runs ──────────────────────────────────────────────────────


class TestRuns:
    async def test_create_run(self, client: AsyncClient, authed_headers: dict):
        r = await client.post(
            "/api/runs",
            json={"user_request": "Why did Q2 sales drop?"},
            headers=authed_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "pending"
        assert "id" in body
        assert body["user_request"] == "Why did Q2 sales drop?"

    async def test_create_run_requires_auth(self, client: AsyncClient):
        r = await client.post("/api/runs", json={"user_request": "test"})
        assert r.status_code == 401

    async def test_list_runs(self, client: AsyncClient, authed_headers: dict):
        await client.post("/api/runs", json={"user_request": "run one"}, headers=authed_headers)
        r = await client.get("/api/runs", headers=authed_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    async def test_list_runs_other_user_isolated(self, client: AsyncClient):
        r1 = await client.post("/auth/register", json={"email": "a@b.com", "password": "pass1234"})
        tok_a = r1.json()["access_token"]
        await client.post("/api/runs", json={"user_request": "user a"}, headers={"Authorization": f"Bearer {tok_a}"})

        r2 = await client.post("/auth/register", json={"email": "b@b.com", "password": "pass1234"})
        tok_b = r2.json()["access_token"]
        r = await client.get("/api/runs", headers={"Authorization": f"Bearer {tok_b}"})
        assert r.json()["total"] == 0

    async def test_get_run(self, client: AsyncClient, authed_headers: dict):
        created = await client.post("/api/runs", json={"user_request": "test"}, headers=authed_headers)
        run_id = created.json()["id"]
        r = await client.get(f"/api/runs/{run_id}", headers=authed_headers)
        assert r.status_code == 200
        assert r.json()["user_request"] == "test"

    async def test_get_run_not_found(self, client: AsyncClient, authed_headers: dict):
        r = await client.get("/api/runs/00000000-0000-0000-0000-000000000000", headers=authed_headers)
        assert r.status_code == 404

    async def test_gate_decision_no_active_run(self, client: AsyncClient, authed_headers: dict):
        r = await client.post(
            "/api/runs/no-such-run/gates/1/decision",
            json={"action": "approve"},
            headers=authed_headers,
        )
        assert r.status_code == 409

    async def test_cors_headers_present(self, client: AsyncClient):
        r = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"