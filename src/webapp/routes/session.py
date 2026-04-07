"""Session API routes."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.application.runtime_config import RuntimeConfig
from src.curve.afas_postprocessing_analysis import analyze_preprocessed_afas_channel
from src.curve.afas_dataset_import import (
    build_imported_session_detail,
    build_imported_session_result,
    normalize_imported_afas_dataset,
)
from src.curve.afas_postprocessing_export import (
    build_afas_analysis_png_bytes,
    build_afas_excel_report_bytes,
)
from src.curve.afas_preprocessing import preprocess_afas_channel
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SessionSummary, SqliteSessionRepo
from src.webapp.deps import (
    get_adjustment_service,
    get_runtime_config,
    get_session_artifact_store,
    get_session_repo,
    get_session_runner,
)
from src.webapp.schemas import (
    AdjustmentDraftRequest,
    AdjustmentStateResponse,
    AfasWorkspaceAnalysisRequest,
    AfasWorkspaceAnalysisResponse,
    AfasOverviewItemResponse,
    AfasOverviewSeriesResponse,
    ReplayDetailResponse,
    SessionHistoryResponse,
    SessionSummaryResponse,
)
from src.workflow.adjustments import AdjustmentService
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


@router.post("/import-afas-dataset", response_model=SessionSummaryResponse)
def import_afas_dataset(
    payload: dict[str, Any],
    repo: SqliteSessionRepo = Depends(get_session_repo),
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> SessionSummaryResponse:
    requested_session_id = str(payload.get("session_id") or f"import-{uuid.uuid4().hex[:12]}")
    if repo.get_summary(requested_session_id) is not None or artifact_store.session_exists(requested_session_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session already exists: {requested_session_id}",
        )

    try:
        dataset = normalize_imported_afas_dataset(payload, session_id=requested_session_id)
        detail = build_imported_session_detail(dataset)
        preprocessing = preprocess_afas_channel(dataset, channel_name=str(dataset["active_channel"]))
        analysis = analyze_preprocessed_afas_channel(preprocessing)
        resolved = {
            "active_channel": str(dataset["active_channel"]),
            "available_channels": [str(name) for name in dict(dataset["channel_map"]).keys()],
            "overview": [
                _build_afas_overview_item(
                    dataset,
                    channel_name=str(channel_name),
                    preprocessing_overrides=None,
                    analysis_overrides=None,
                )
                for channel_name in dict(dataset["channel_map"]).keys()
            ],
            "preprocessing": preprocessing,
            "analysis": analysis,
        }
        result = build_imported_session_result(
            dataset,
            analysis=analysis,
            point_count=int(detail["point_count"]),
        )
    except (KeyError, ValueError) as exc:
        _raise_afas_validation_error(exc)

    artifact_store.save_imported_afas_bundle(
        requested_session_id,
        detail=detail,
        afas_dataset=dataset,
        result=result,
        afas_analysis=_build_afas_analysis_response_payload(requested_session_id, resolved),
    )
    summary = SessionSummary(
        session_id=requested_session_id,
        state="completed",
        point_count=int(detail["point_count"]),
        af95=detail["af95"],
        created_at_ms=int(time.time() * 1000),
    )
    repo.save_summary(summary)
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


@router.get("/{session_id}/adjustment", response_model=AdjustmentStateResponse)
def get_session_adjustment(
    session_id: str,
    service: AdjustmentService = Depends(get_adjustment_service),
) -> AdjustmentStateResponse:
    try:
        state_payload = service.get_adjustment_state(session_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return AdjustmentStateResponse(**state_payload)


@router.post("/{session_id}/afas/analysis", response_model=AfasWorkspaceAnalysisResponse)
def analyze_session_afas(
    session_id: str,
    payload: AfasWorkspaceAnalysisRequest,
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> AfasWorkspaceAnalysisResponse:
    try:
        resolved = _resolve_afas_analysis_payload(session_id, payload, artifact_store)
    except (KeyError, ValueError) as exc:
        _raise_afas_validation_error(exc)

    response = AfasWorkspaceAnalysisResponse(
        session_id=session_id,
        active_channel=resolved["active_channel"],
        available_channels=resolved["available_channels"],
        overview=resolved["overview"],
        preprocessing=resolved["preprocessing"],
        analysis=resolved["analysis"],
    )
    artifact_store.save_afas_analysis(session_id, response.model_dump())
    return response


@router.post("/{session_id}/afas/export.png")
def export_session_afas_png(
    session_id: str,
    payload: AfasWorkspaceAnalysisRequest,
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> Response:
    try:
        resolved = _resolve_afas_analysis_payload(session_id, payload, artifact_store)
        png_bytes = build_afas_analysis_png_bytes(
            resolved["preprocessing"],
            resolved["analysis"],
            channel_name=resolved["active_channel"],
        )
    except (KeyError, ValueError) as exc:
        _raise_afas_validation_error(exc)

    artifact_store.save_afas_analysis(session_id, _build_afas_analysis_response_payload(session_id, resolved))
    artifact_store.save_afas_plot(session_id, png_bytes)
    filename = f"{session_id}-{resolved['active_channel']}-afas-analysis.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{session_id}/afas/report.xlsx")
def export_session_afas_report(
    session_id: str,
    payload: AfasWorkspaceAnalysisRequest,
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> Response:
    try:
        resolved = _resolve_afas_analysis_payload(session_id, payload, artifact_store)
        workbook_bytes = build_afas_excel_report_bytes(
            resolved["preprocessing"],
            resolved["analysis"],
            session_id=session_id,
            channel_name=resolved["active_channel"],
        )
    except (KeyError, ValueError) as exc:
        _raise_afas_validation_error(exc)

    artifact_store.save_afas_analysis(session_id, _build_afas_analysis_response_payload(session_id, resolved))
    artifact_store.save_afas_report(session_id, workbook_bytes)
    filename = f"{session_id}-{resolved['active_channel']}-afas-report.xlsx"
    return Response(
        content=workbook_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{session_id}/adjustment/draft", response_model=AdjustmentStateResponse)
def save_session_adjustment_draft(
    session_id: str,
    payload: AdjustmentDraftRequest,
    service: AdjustmentService = Depends(get_adjustment_service),
) -> AdjustmentStateResponse:
    try:
        state_payload = service.save_draft(
            session_id=session_id,
            overrides=payload.overrides,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AdjustmentStateResponse(**state_payload)


@router.post("/{session_id}/adjustment/apply", response_model=AdjustmentStateResponse)
def apply_session_adjustment(
    session_id: str,
    service: AdjustmentService = Depends(get_adjustment_service),
) -> AdjustmentStateResponse:
    try:
        state_payload = service.apply_draft(session_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AdjustmentStateResponse(**state_payload)


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


def _build_afas_overview_item(
    dataset: dict[str, Any],
    *,
    channel_name: str,
    preprocessing_overrides: dict[str, Any] | None,
    analysis_overrides: dict[str, Any] | None,
) -> AfasOverviewItemResponse:
    preprocessing = preprocess_afas_channel(
        dataset,
        channel_name=channel_name,
        parameter_overrides=preprocessing_overrides,
    )
    analysis = analyze_preprocessed_afas_channel(
        preprocessing,
        parameter_overrides=analysis_overrides,
    )
    smoothed = dict(preprocessing.get("smoothed", {}))
    result = dict(analysis.get("result", {}))
    return AfasOverviewItemResponse(
        channel_name=channel_name,
        point_count=len(smoothed.get("temperature_celsius", [])),
        outlier_count=int(preprocessing.get("outlier_repair", {}).get("outlier_count", 0)),
        result_status=str(analysis.get("result_status", "unavailable")),
        as_value=result.get("As"),
        af_tan=result.get("Af_tan"),
        max_slope_temp=result.get("max_slope_temp"),
        series=AfasOverviewSeriesResponse(
            temperature_celsius=[float(value) for value in smoothed.get("temperature_celsius", [])],
            values=[float(value) for value in smoothed.get("values", [])],
        ),
    )


def _resolve_afas_analysis_payload(
    session_id: str,
    payload: AfasWorkspaceAnalysisRequest,
    artifact_store: SessionArtifactStore,
) -> dict[str, Any]:
    dataset = artifact_store.get_afas_dataset(session_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AFAS dataset not found: {session_id}",
        )

    available_channels = [str(name) for name in dict(dataset.get("channel_map", {})).keys()]
    if not available_channels:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AFAS dataset does not contain any channels: {session_id}",
        )

    selected_channel = str(payload.channel_name or dataset.get("active_channel") or available_channels[0])
    if selected_channel not in available_channels:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown AFAS channel: {selected_channel}",
        )

    request_overrides = payload.model_dump(exclude_none=True)
    request_overrides.pop("channel_name", None)
    preprocessing_overrides = {
        key: request_overrides[key]
        for key in (
            "group_by_temperature",
            "outlier_window",
            "outlier_threshold",
            "outlier_max_iterations",
            "savgol_window_length",
            "savgol_polyorder",
        )
        if key in request_overrides
    }
    analysis_overrides = {
        key: request_overrides[key]
        for key in ("low_range_celsius", "high_range_celsius", "tangent_offset")
        if key in request_overrides
    }

    selected_preprocessing = preprocess_afas_channel(
        dataset,
        channel_name=selected_channel,
        parameter_overrides=preprocessing_overrides or None,
    )
    selected_analysis = analyze_preprocessed_afas_channel(
        selected_preprocessing,
        parameter_overrides=analysis_overrides or None,
    )
    overview = [
        _build_afas_overview_item(
            dataset,
            channel_name=channel_name,
            preprocessing_overrides=preprocessing_overrides or None,
            analysis_overrides=analysis_overrides or None,
        )
        for channel_name in available_channels
    ]
    return {
        "active_channel": selected_channel,
        "available_channels": available_channels,
        "overview": overview,
        "preprocessing": selected_preprocessing,
        "analysis": selected_analysis,
    }


def _raise_afas_validation_error(exc: KeyError | ValueError) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Malformed AFAS dataset is missing {exc!s}",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    ) from exc


def _build_afas_analysis_response_payload(session_id: str, resolved: dict[str, Any]) -> dict[str, Any]:
    return AfasWorkspaceAnalysisResponse(
        session_id=session_id,
        active_channel=resolved["active_channel"],
        available_channels=resolved["available_channels"],
        overview=resolved["overview"],
        preprocessing=resolved["preprocessing"],
        analysis=resolved["analysis"],
    ).model_dump()
