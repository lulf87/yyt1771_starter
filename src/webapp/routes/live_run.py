"""Live run API routes."""

from __future__ import annotations

from collections.abc import Iterator
import struct
import zlib

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from PIL import Image

from src.core.enums import RunStatus
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion, RunDraftRecord
from src.storage.session_artifacts import SessionArtifactStore
from src.application.runtime_config import RuntimeConfig
from src.webapp.deps import (
    LivePreviewService,
    LiveRunDraftRegistry,
    LiveRunService,
    get_live_preview_service,
    get_live_run_registry,
    get_live_run_service,
    get_runtime_config,
    get_session_artifact_store,
)
from src.webapp.schemas import (
    AutoDetectDefinitionRequest,
    AutoDetectDefinitionResponse,
    EditorStateResponse,
    MeasurementDefinitionRequest,
    MeasurementDefinitionResponse,
    MeasurementProfileResponse,
    MetricBoxResponse,
    PixelPointResponse,
    PreviewStateResponse,
    RectRegionResponse,
    RunCreateRequest,
    RunDetailResponse,
    RunRatesResponse,
    RunResultResponse,
    RunStartRequest,
    RunStartResponse,
    RunSummaryResponse,
    RunTelemetryPointResponse,
    RunTelemetryResponse,
)
from src.vision.metric_two_point_distance import (
    TwoPointDistanceMetricExtractor,
    downsample_grayscale_image,
    normalize_frame_image,
)
from src.workflow.live_run import summarize_measurement_profile, summarize_rate_snapshot, summarize_rate_warnings

router = APIRouter(prefix="/api/runs", tags=["runs"])
_PREVIEW_STREAM_BOUNDARY = "frame"
_PREVIEW_STREAM_MAX_WIDTH = 384
_PREVIEW_STREAM_MAX_HEIGHT = 256


@router.post("", response_model=RunSummaryResponse)
def create_run_draft(
    payload: RunCreateRequest,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
) -> RunSummaryResponse:
    requested_profile = payload.profile or runtime_config.profile
    if requested_profile != runtime_config.profile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Run profile must match the loaded runtime profile: {runtime_config.profile}",
        )

    record = registry.create(profile=requested_profile, preset=payload.preset)
    return _build_run_summary(record)


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run_draft(
    run_id: str,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunDetailResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    return _build_run_detail(
        record,
        runtime_config=runtime_config,
        preview_service=preview_service,
        live_run_service=live_run_service,
    )


@router.put("/{run_id}/definition", response_model=RunDetailResponse)
def save_measurement_definition(
    run_id: str,
    payload: MeasurementDefinitionRequest,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunDetailResponse:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(
            x=payload.analysis_roi.x,
            y=payload.analysis_roi.y,
            width=payload.analysis_roi.width,
            height=payload.analysis_roi.height,
        ),
        metric_box=MetricBox(
            center_x=payload.metric_box.center_x,
            center_y=payload.metric_box.center_y,
            width=payload.metric_box.width,
            height=payload.metric_box.height,
            angle_deg=payload.metric_box.angle_deg,
        ),
        point_a_px=PixelPoint(x=payload.point_a_px.x, y=payload.point_a_px.y),
        point_b_px=PixelPoint(x=payload.point_b_px.x, y=payload.point_b_px.y),
        foreground_polarity=payload.foreground_polarity,
        threshold_mode=payload.threshold_mode,
        ignore_internal_texture=payload.ignore_internal_texture,
        min_target_area_px=payload.min_target_area_px,
    )
    try:
        record = registry.save_definition(run_id, definition)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_run_detail(
        record,
        runtime_config=runtime_config,
        preview_service=preview_service,
        live_run_service=live_run_service,
    )


@router.post("/{run_id}/preview/frame")
def fetch_preview_frame(
    run_id: str,
    cached: bool = False,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    ) -> Response:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    try:
        frame = preview_service.fetch_frame(runtime_config, run_id=run_id, prefer_cached=cached)
        image = _preview_frame_image(frame.image)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview frame fetch failed: {exc}",
        ) from exc

    registry.mark_preview_frozen(run_id)
    return Response(
        content=_encode_grayscale_png(image),
        media_type="image/png",
        headers={
            "X-Frame-Width": str(len(image[0])),
            "X-Frame-Height": str(len(image)),
            "X-Frame-Id": str(frame.frame_id or 0),
        },
    )


@router.get("/{run_id}/preview/stream")
def stream_preview_frames(
    run_id: str,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
) -> StreamingResponse:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    try:
        active_stream, first_frame = preview_service.start_stream(runtime_config, run_id=run_id)
    except RuntimeError as exc:
        status_code = status.HTTP_409_CONFLICT if "already active" in str(exc) else status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=status_code, detail=f"Preview stream start failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview stream start failed: {exc}",
        ) from exc

    registry.mark_preview_streaming(run_id)
    return StreamingResponse(
        _iter_preview_stream_payload(
            preview_service=preview_service,
            run_id=run_id,
            active_stream=active_stream,
            first_frame=first_frame,
            frame_interval_ms=_preview_stream_interval_ms(runtime_config),
        ),
        media_type=f"multipart/x-mixed-replace; boundary={_PREVIEW_STREAM_BOUNDARY}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.post("/{run_id}/preview/stream/stop", response_model=RunDetailResponse)
def stop_preview_stream(
    run_id: str,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunDetailResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    stopped = preview_service.stop_stream(run_id=run_id)
    if stopped:
        if not preview_service.wait_for_stream_stop(run_id=run_id, timeout_ms=3_000):
            preview_service.force_stop_stream(run_id=run_id)
            preview_service.wait_for_stream_stop(run_id=run_id, timeout_ms=250)
    if preview_service.get_preview_state(run_id=run_id).frozen_frame_available:
        record = registry.mark_preview_frozen(run_id)
    return _build_run_detail(
        record,
        runtime_config=runtime_config,
        preview_service=preview_service,
        live_run_service=live_run_service,
    )


@router.post("/{run_id}/definition/auto", response_model=AutoDetectDefinitionResponse)
def auto_detect_measurement_definition(
    run_id: str,
    payload: AutoDetectDefinitionRequest,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
) -> AutoDetectDefinitionResponse:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")

    try:
        frame = preview_service.fetch_frame(runtime_config, run_id=run_id, prefer_cached=True)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview frame fetch failed: {exc}",
        ) from exc

    registry.mark_preview_frozen(run_id)
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(
            x=payload.analysis_roi.x,
            y=payload.analysis_roi.y,
            width=payload.analysis_roi.width,
            height=payload.analysis_roi.height,
        ),
        metric_box=MetricBox(
            center_x=payload.metric_box.center_x,
            center_y=payload.metric_box.center_y,
            width=payload.metric_box.width,
            height=payload.metric_box.height,
            angle_deg=payload.metric_box.angle_deg,
        ),
        foreground_polarity=payload.foreground_polarity,
        threshold_mode=payload.threshold_mode,
        threshold_margin=runtime_config.live.vision.edge_threshold,
        ignore_internal_texture=payload.ignore_internal_texture,
        min_target_area_px=payload.min_target_area_px,
        quality_threshold=runtime_config.live.vision.quality_threshold,
    )
    metric = extractor.extract(frame)
    if metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Auto detection failed: {metric.meta.get('reason', 'unknown_error')}",
        )

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(
            x=payload.analysis_roi.x,
            y=payload.analysis_roi.y,
            width=payload.analysis_roi.width,
            height=payload.analysis_roi.height,
        ),
        metric_box=MetricBox(
            center_x=payload.metric_box.center_x,
            center_y=payload.metric_box.center_y,
            width=payload.metric_box.width,
            height=payload.metric_box.height,
            angle_deg=payload.metric_box.angle_deg,
        ),
        point_a_px=PixelPoint(x=metric.point_a_px[0], y=metric.point_a_px[1]),
        point_b_px=PixelPoint(x=metric.point_b_px[0], y=metric.point_b_px[1]),
        foreground_polarity=payload.foreground_polarity,
        threshold_mode=payload.threshold_mode,
        ignore_internal_texture=payload.ignore_internal_texture,
        min_target_area_px=payload.min_target_area_px,
    )
    detail = ""
    if metric.quality < runtime_config.live.vision.quality_threshold:
        detail = "Auto detection succeeded with low confidence. Please verify or adjust points manually."
    return AutoDetectDefinitionResponse(
        definition=_build_measurement_definition(definition),
        quality=metric.quality,
        metric_raw=metric.metric_raw,
        detail=detail,
    )


@router.post("/{run_id}/start", response_model=RunStartResponse)
def start_live_run(
    run_id: str,
    payload: RunStartRequest,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunStartResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    if record.definition is None or record.status.value != "run_ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run must be in run_ready before start: {run_id}",
        )

    try:
        live_run_service.start_run(
            record=record,
            runtime_config=runtime_config,
            target_temperature_celsius=payload.target_temperature_celsius,
            registry=registry,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Live run failed: {exc}",
        ) from exc
    return RunStartResponse(
        run_id=record.run_id,
        session_id=record.run_id,
        status=RunStatus.RUNNING.value,
        point_count=None,
        af95=None,
    )


@router.post("/{run_id}/stop", response_model=RunDetailResponse)
def stop_live_run(
    run_id: str,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    live_run_service: LiveRunService = Depends(get_live_run_service),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
) -> RunDetailResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    if record.status not in {RunStatus.RUNNING, RunStatus.INVALIDATED, RunStatus.STOPPING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not currently running: {run_id}",
        )
    if not live_run_service.request_stop(run_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not currently running: {run_id}",
        )
    updated_record = registry.update_status(run_id, status=RunStatus.STOPPING)
    return _build_run_detail(
        updated_record,
        runtime_config=runtime_config,
        preview_service=preview_service,
        live_run_service=live_run_service,
    )


@router.get("/{run_id}/telemetry", response_model=RunTelemetryResponse)
def get_live_run_telemetry(
    run_id: str,
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunTelemetryResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")

    snapshot = live_run_service.get_snapshot(run_id)
    curve = list(snapshot.telemetry) if snapshot is not None and snapshot.telemetry else artifact_store.get_telemetry(run_id)
    if curve is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run telemetry not available: {run_id}",
        )
    latest = curve[-1] if curve else None
    return RunTelemetryResponse(
        run_id=run_id,
        status=record.status.value,
        latest=None if latest is None else RunTelemetryPointResponse(**latest),
        curve=[RunTelemetryPointResponse(**item) for item in curve],
    )


@router.get("/{run_id}/result", response_model=RunResultResponse)
def get_live_run_result(
    run_id: str,
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
    live_run_service: LiveRunService = Depends(get_live_run_service),
) -> RunResultResponse:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    snapshot = live_run_service.get_snapshot(run_id)
    if snapshot is not None and snapshot.execution is not None:
        return RunResultResponse(**snapshot.execution.result)
    payload = artifact_store.get_result(run_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run result not available: {run_id}",
        )
    return RunResultResponse(**payload)


def _build_run_summary(record: RunDraftRecord) -> RunSummaryResponse:
    return RunSummaryResponse(
        run_id=record.run_id,
        status=record.status.value,
        profile=record.profile,
        preset=record.preset,
    )


def _build_run_detail(
    record: RunDraftRecord,
    *,
    runtime_config: RuntimeConfig | None = None,
    preview_service: LivePreviewService | None = None,
    live_run_service: LiveRunService | None = None,
) -> RunDetailResponse:
    definition = record.definition
    definition_complete = bool(definition and definition.is_complete())
    preview_state = (
        preview_service.get_preview_state(run_id=record.run_id)
        if preview_service is not None
        else None
    )
    snapshot = live_run_service.get_snapshot(record.run_id) if live_run_service is not None else None
    rate_snapshot = (
        summarize_rate_snapshot(
            telemetry=list(snapshot.telemetry),
            preview_display_fps=None if preview_state is None else preview_state.preview_display_fps,
        )
        if snapshot is not None and snapshot.telemetry
        else summarize_rate_snapshot(
            preview_display_fps=None if preview_state is None else preview_state.preview_display_fps,
        )
    )
    measurement_profile = (
        summarize_measurement_profile(runtime_config.live.camera)
        if runtime_config is not None
        else None
    )
    editor_state = "empty"
    if definition_complete:
        editor_state = "locked"
    elif record.status == RunStatus.DEFINITION_EDITING or (
        preview_state is not None and preview_state.frozen_frame_available
    ):
        editor_state = "editing"
    warnings = summarize_rate_warnings(
        rate_snapshot,
        target_measurement_hz=None if runtime_config is None else runtime_config.live.run.measurement_target_hz,
        is_terminal=record.status in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.INVALIDATED,
            RunStatus.ABORTED,
        },
    )
    return RunDetailResponse(
        run_id=record.run_id,
        status=record.status.value,
        profile=record.profile,
        preset=record.preset,
        definition=None if definition is None else _build_measurement_definition(definition),
        created_at_ms=record.created_at_ms,
        updated_at_ms=record.updated_at_ms,
        definition_complete=definition_complete,
        capture_mode=record.capture_mode.value,
        rates=RunRatesResponse(
            camera_resulting_fps=rate_snapshot.camera_resulting_fps,
            preview_display_fps=rate_snapshot.preview_display_fps,
            measurement_sample_hz=rate_snapshot.measurement_sample_hz,
            artifact_capture_hz=rate_snapshot.artifact_capture_hz,
            dropped_frame_count=rate_snapshot.dropped_frame_count,
        ),
        measurement_profile=MeasurementProfileResponse(
            acquisition_roi=None
            if measurement_profile is None or measurement_profile.acquisition_roi is None
            else RectRegionResponse(
                x=measurement_profile.acquisition_roi.x,
                y=measurement_profile.acquisition_roi.y,
                width=measurement_profile.acquisition_roi.width,
                height=measurement_profile.acquisition_roi.height,
            ),
            decimation=None if measurement_profile is None else measurement_profile.decimation,
            binning=None if measurement_profile is None else measurement_profile.binning,
            exposure_us=None if measurement_profile is None else measurement_profile.exposure_us,
        ),
        preview=PreviewStateResponse(
            stream_active=False if preview_state is None else preview_state.stream_active,
            frozen_frame_available=False if preview_state is None else preview_state.frozen_frame_available,
            last_frame_id=None if preview_state is None else preview_state.last_frame_id,
        ),
        editor=EditorStateResponse(state=editor_state),
        warnings=warnings,
    )


def _build_measurement_definition(definition: MeasurementDefinition) -> MeasurementDefinitionResponse:
    return MeasurementDefinitionResponse(
        analysis_roi=RectRegionResponse(
            x=definition.analysis_roi.x,
            y=definition.analysis_roi.y,
            width=definition.analysis_roi.width,
            height=definition.analysis_roi.height,
        ),
        metric_box=MetricBoxResponse(
            center_x=definition.metric_box.center_x,
            center_y=definition.metric_box.center_y,
            width=definition.metric_box.width,
            height=definition.metric_box.height,
            angle_deg=definition.metric_box.angle_deg,
        ),
        point_a_px=PixelPointResponse(x=definition.point_a_px.x, y=definition.point_a_px.y),
        point_b_px=PixelPointResponse(x=definition.point_b_px.x, y=definition.point_b_px.y),
        foreground_polarity=definition.foreground_polarity,
        threshold_mode=definition.threshold_mode,
        ignore_internal_texture=definition.ignore_internal_texture,
        min_target_area_px=definition.min_target_area_px,
    )


def _encode_grayscale_png(image: list[list[int]]) -> bytes:
    width = len(image[0]) if image else 1
    height = len(image) if image else 1
    raw = bytearray()
    for row in image:
        raw.append(0)
        raw.extend(max(0, min(255, int(value))) for value in row)

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    idat = _chunk(b"IDAT", zlib.compress(bytes(raw)))
    iend = _chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def _encode_grayscale_jpeg(image: list[list[int]], *, quality: int = 70) -> bytes:
    width = len(image[0]) if image else 1
    height = len(image) if image else 1
    flat = bytearray()
    for row in image:
        flat.extend(max(0, min(255, int(value))) for value in row)
    jpeg_image = Image.frombytes("L", (width, height), bytes(flat))
    from io import BytesIO

    buffer = BytesIO()
    jpeg_image.save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()


def _preview_frame_image(
    image: object,
    *,
    max_width: int = 640,
    max_height: int = 480,
) -> list[list[int]]:
    native_downsample = getattr(image, "downsample_rows", None)
    if callable(native_downsample):
        preview_rows = native_downsample(max_width=max_width, max_height=max_height)
        if preview_rows:
            return preview_rows
    return downsample_grayscale_image(
        normalize_frame_image(image),
        max_width=max_width,
        max_height=max_height,
    )


def _iter_preview_stream_payload(
    *,
    preview_service: LivePreviewService,
    run_id: str,
    active_stream: object,
    first_frame: object,
    frame_interval_ms: int,
) -> Iterator[bytes]:
    for frame in preview_service.stream_frames(
        active_stream,
        first_frame=first_frame,
        frame_interval_ms=frame_interval_ms,
    ):
        preview_service.cache_frame(run_id=run_id, frame=frame)
        image = _preview_frame_image(
            frame.image,
            max_width=_PREVIEW_STREAM_MAX_WIDTH,
            max_height=_PREVIEW_STREAM_MAX_HEIGHT,
        )
        payload = _encode_grayscale_jpeg(image)
        yield _encode_preview_stream_part(
            payload=payload,
            width=len(image[0]) if image else 1,
            height=len(image),
            frame_id=int(frame.frame_id or 0),
            content_type="image/jpeg",
        )


def _preview_stream_interval_ms(runtime_config: RuntimeConfig) -> int:
    preview_target_fps = float(runtime_config.live.run.preview_target_fps or 0.0)
    if preview_target_fps > 0:
        return max(50, int(round(1000.0 / preview_target_fps)))
    return max(50, int(runtime_config.live.run.preview_poll_ms))


def _encode_preview_stream_part(
    *,
    payload: bytes,
    width: int,
    height: int,
    frame_id: int,
    content_type: str = "image/jpeg",
) -> bytes:
    headers = [
        f"--{_PREVIEW_STREAM_BOUNDARY}".encode("ascii"),
        f"Content-Type: {content_type}".encode("ascii"),
        f"Content-Length: {len(payload)}".encode("ascii"),
        f"X-Frame-Width: {width}".encode("ascii"),
        f"X-Frame-Height: {height}".encode("ascii"),
        f"X-Frame-Id: {frame_id}".encode("ascii"),
        b"",
    ]
    return b"\r\n".join(headers) + b"\r\n" + payload + b"\r\n"
