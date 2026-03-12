"""Session API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.webapp.config import RuntimeConfig
from src.webapp.deps import (
    get_runtime_config,
    get_session_artifact_store,
    get_session_repo,
    get_session_runner,
)
from src.webapp.schemas import ReplayDetailResponse, SessionHistoryResponse, SessionSummaryResponse
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


@router.post("/run-replay", response_model=SessionSummaryResponse)
def run_replay_session(
    runner: WorkflowSessionRunner = Depends(get_session_runner),
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
) -> SessionSummaryResponse:
    dataset_path = runtime_config.replay.get("dataset_path")
    if not dataset_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Replay dataset path is not configured for the current profile",
        )

    try:
        summary = runner.run_replay(
            session_id=f"replay-{uuid.uuid4().hex[:12]}",
            dataset_path=str(dataset_path),
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return SessionSummaryResponse(
        session_id=summary.session_id,
        state=summary.state,
        point_count=summary.point_count,
        af95=summary.af95,
    )


@router.get("/{session_id}/detail", response_model=ReplayDetailResponse)
def get_session_detail(
    session_id: str,
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> ReplayDetailResponse:
    detail = artifact_store.get_detail(session_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session detail not found: {session_id}",
        )
    return ReplayDetailResponse(**detail)


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
