"""Session API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.storage.sqlite_repo import SqliteSessionRepo
from src.webapp.deps import get_session_repo, get_session_runner
from src.webapp.schemas import SessionHistoryResponse, SessionSummaryResponse
from src.workflow.session import WorkflowSessionRunner, build_mock_sync_points

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("", response_model=SessionHistoryResponse)
def list_session_summaries(
    limit: int = Query(default=10, ge=1),
    repo: SqliteSessionRepo = Depends(get_session_repo),
) -> SessionHistoryResponse:
    items = [
        SessionSummaryResponse(
            session_id=summary.session_id,
            state=summary.state,
            point_count=summary.point_count,
            af95=summary.af95,
        )
        for summary in repo.list_summaries(limit=limit)
    ]
    return SessionHistoryResponse(items=items)


@router.post("/run-mock", response_model=SessionSummaryResponse)
def run_mock_session(runner: WorkflowSessionRunner = Depends(get_session_runner)) -> SessionSummaryResponse:
    session_id = f"mock-{uuid.uuid4().hex[:12]}"
    summary = runner.run_offline(session_id=session_id, sync_points=build_mock_sync_points())
    return SessionSummaryResponse(
        session_id=summary.session_id,
        state=summary.state,
        point_count=summary.point_count,
        af95=summary.af95,
    )


@router.get("/{session_id}", response_model=SessionSummaryResponse)
def get_session_summary(
    session_id: str,
    repo: SqliteSessionRepo = Depends(get_session_repo),
) -> SessionSummaryResponse:
    summary = repo.get_summary(session_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return SessionSummaryResponse(
        session_id=summary.session_id,
        state=summary.state,
        point_count=summary.point_count,
        af95=summary.af95,
    )
