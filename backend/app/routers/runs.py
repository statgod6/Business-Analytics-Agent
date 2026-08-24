"""Run management routes: create, list, get, gate decisions, and WebSocket
event streaming.

All routes require a valid JWT (except WebSocket, which validates the token
from the query string).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status, File
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user, get_token_from_ws
from backend.app.database import Run, User, get_db
from backend.app.engine import engine
from backend.app.schemas import GateDecisionIn, GateDecisionOut, RunCreate, RunListOut, RunOut
from backend.app.config import settings
from backend.app.websocket_manager import ws_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    body: RunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new BA Agent analysis run."""
    run = Run(
        user_id=current_user.id,
        user_request=body.user_request,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Fire off the background run
    await engine.start(
        run_id=str(run.id),
        user_request=body.user_request,
        settings=settings,
    )

    return run


@router.get("", response_model=RunListOut)
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List this user's runs, most recent first."""
    total_q = select(func.count()).select_from(Run).where(Run.user_id == current_user.id)
    total = (await db.execute(total_q)).scalar() or 0

    q = (
        select(Run)
        .where(Run.user_id == current_user.id)
        .order_by(Run.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    runs = (await db.execute(q)).scalars().all()
    return RunListOut(runs=runs, total=total)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a single run."""
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/gates/{gate_id}/decision", response_model=GateDecisionOut)
async def gate_decision(
    run_id: str,
    gate_id: int,
    body: GateDecisionIn,
    current_user: User = Depends(get_current_user),
):
    """Submit a human decision for an open gate.

    Body must match the GateDecisionIn schema (action, feedback,
    target_stage, edit_payload).
    """
    payload = body.model_dump(exclude_none=True)
    payload["gate_id"] = gate_id  # for the graph to use
    ok = await engine.submit_decision(run_id, payload)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail="Run not active or gate already decided",
        )
    return GateDecisionOut()


ALLOWED_UPLOAD_EXTENSIONS = frozenset({".csv", ".xlsx", ".xls", ".json", ".pdf"})

UPLOAD_DIR = "uploads"


@router.post("/{run_id}/files")
async def upload_file(
    run_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a data file for a run (Stage 2 ingestion)."""
    # Verify run exists and belongs to user
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
        )

    # Save file
    run_dir = os.path.join(UPLOAD_DIR, str(run_id))
    os.makedirs(run_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    dest = os.path.join(run_dir, safe_name)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    # Store metadata in run.files
    meta = {
        "original_name": file.filename,
        "stored_name": safe_name,
        "path": dest,
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    current_files = list(run.files or [])
    current_files.append(meta)
    stmt = (
        update(Run)
        .where(Run.id == run_id)
        .values(files=current_files)
    )
    await db.execute(stmt)
    await db.commit()

    return {"files": current_files}


@router.websocket("/{run_id}/ws")
async def run_events_ws(ws: WebSocket, run_id: str):
    """WebSocket endpoint for live run events.

    Authenticate via query parameter ``?token=<JWT>``. Receives JSON events
    (stage_signed, gate_open, gate_closed, run_complete, run_error).
    """
    try:
        user_id = await get_token_from_ws(ws.query_params)
    except HTTPException:
        await ws.close(code=4001)
        return

    await ws_manager.connect(run_id, ws)
    try:
        # Keep the connection alive until the client disconnects
        while True:
            msg = await ws.receive_text()
            # Ping/pong or cancel signals could go here
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(run_id, ws)