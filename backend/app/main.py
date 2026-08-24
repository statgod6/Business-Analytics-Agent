"""FastAPI application entry point.

Mounts routers under /auth and /api/runs, configures CORS for the
Vite dev server (http://localhost:5173), and initialises the database
tables during the lifespan event.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db
from backend.app.routers import auth, runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Initialising database …")
    await init_db()
    logger.info("Database ready.")
    yield
    # Shutdown: run engine cleans up, connections close on GC


app = FastAPI(
    title="BA Agent API",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and any docker-network service
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",  # alternative dev port
        "http://127.0.0.1:5173",
        "http://localhost",  # Docker nginx
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(runs.router)


@app.get("/health")
async def health():
    return {"status": "ok", "stage": "3", "version": "0.3.0"}