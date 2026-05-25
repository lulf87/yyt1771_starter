"""Live run API routes."""

from __future__ import annotations

from collections.abc import Iterator
import math
import struct
import time
import zlib

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from PIL import Image

from src.application.container import ApplicationContainer
from src.application.preview_render import PreviewBitmap, build_preview_bitmap, enhance_preview_bitmap
from src.application.live_preview_service import compute_preview_interval_ms
from src.core.enums import ObservationAxis, RunStatus
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion, RunDraftRecord, TemperatureSettingsBundle
from src.storage.session_artifacts import SessionArtifactStore
from src.application.runtime_config import RuntimeConfig
from src.webapp.deps import (
    LivePreviewService,
    LiveRunDraftRegistry,
    LiveRunService,
    get_application_container,
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
    TemperatureSettingsRequest,
    TemperatureSettingsResponse,
)
from src.vision.contour_direction import DirectionalContourConfig, DirectionalContourMetricExtractor
from src.vision.metric_two_point_distance import RoiLongestSpanPointDetector, TwoPointDistanceMetricExtractor
from src.workflow.live_run import (
    ROI_LOCAL_WORKING_MAX_HEIGHT,
    ROI_LOCAL_WORKING_MAX_WIDTH,
    summarize_measurement_profile,
    summarize_rate_snapshot,
    summarize_rate_warnings,
)

router = APIRouter(prefix="/api/runs", tags=["runs"])
_PREVIEW_STREAM_BOUNDARY = "frame"


@router.post("", response_model=RunSummaryResponse)
def create_run_draft(
    payload: RunCreateRequest,
    container: ApplicationContainer = Depends(get_application_container),
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
) -> RunSummaryResponse:
    requested_profile = payload.profile or runtime_config.profile
    if requested_profile != runtime_config.profile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Run profile must match the loaded runtime profile: {runtime_config.profile}",
        )

    container.reset_temp_controller()
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
    draft = registry.get(run_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
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
        sensitivity=payload.sensitivity,
        direction_angle_deg=payload.direction_angle_deg,
        direction_projection_mode=_resolve_direction_projection_mode(payload, draft.preset),
        observation_axis=ObservationAxis(payload.observation_axis),
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
    tracking: bool = False,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    ) -> Response:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")
    try:
        if tracking:
            frame = preview_service.get_tracking_frame(run_id=run_id)
            if frame is None:
                raise RuntimeError("tracking frame not available")
        else:
            frame = preview_service.fetch_frame(runtime_config, run_id=run_id, prefer_cached=cached)
        bitmap = build_preview_bitmap(
            frame.image,
            max_width=runtime_config.live.run.preview_display_max_width,
            max_height=runtime_config.live.run.preview_display_max_height,
        )
        if not _preview_frame_is_already_enhanced(frame):
            bitmap = enhance_preview_bitmap(bitmap)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview frame fetch failed: {exc}",
        ) from exc

    if not tracking:
        registry.mark_preview_frozen(run_id)
    frame_width, frame_height = _frame_image_dimensions(frame)
    source_width, source_height = _frame_source_dimensions(frame, fallback=(frame_width, frame_height))
    if source_width < 1 or source_height < 1:
        source_width, source_height = bitmap.width, bitmap.height
    return Response(
        content=_encode_grayscale_png_bitmap(bitmap),
        media_type="image/png",
        headers={
            "X-Frame-Width": str(bitmap.width),
            "X-Frame-Height": str(bitmap.height),
            "X-Frame-Source-Width": str(source_width),
            "X-Frame-Source-Height": str(source_height),
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
            runtime_config=runtime_config,
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


@router.put("/{run_id}/temperature-settings", response_model=RunDetailResponse)
def confirm_temperature_settings(
    run_id: str,
    payload: TemperatureSettingsRequest,
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    registry: LiveRunDraftRegistry = Depends(get_live_run_registry),
    preview_service: LivePreviewService = Depends(get_live_preview_service),
    live_run_service: LiveRunService = Depends(get_live_run_service),
    container: ApplicationContainer = Depends(get_application_container),
) -> RunDetailResponse:
    if registry.get(run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")

    try:
        result = container.with_temp_controller(
            lambda controller: _write_and_confirm_temperature_settings(
                controller=controller,
                target_temperature_celsius=payload.target_temperature_celsius,
                output_power_percent=payload.output_power_percent,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Temperature settings update unavailable: {exc}") from exc

    record = registry.save_temperature_settings(
        run_id,
        TemperatureSettingsBundle(
            target_temperature_celsius=float(payload.target_temperature_celsius),
            control_mode=str(payload.control_mode),
            output_power_percent=float(payload.output_power_percent),
            completion_mode=str(payload.completion_mode or runtime_config.live.temp.control.completion_mode),
            confirmed_target_temperature_celsius=float(result["confirmed_target_temperature_celsius"]),
            confirmed_output_power_percent=float(result["confirmed_output_power_percent"]),
            confirmed_at_ms=int(result["confirmed_at_ms"]),
            source=str(result["source"]),
        ),
    )
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
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run not found: {run_id}")

    try:
        frame = preview_service.fetch_frame(runtime_config, run_id=run_id, prefer_cached=True)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Preview frame fetch failed: {exc}",
        ) from exc

    registry.mark_preview_frozen(run_id)
    metric, threshold_mode_used, foreground_polarity_used = _best_auto_detect_metric(
        frame=frame,
        payload=payload,
        runtime_config=runtime_config,
        preset=record.preset,
    )
    if metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Auto detection failed: {metric.meta.get('reason', 'unknown_error')}",
        )
    detail_parts: list[str] = []
    if threshold_mode_used != payload.threshold_mode and foreground_polarity_used != payload.foreground_polarity:
        detail_parts.append(
            f"Auto detection selected {foreground_polarity_used} polarity and {threshold_mode_used} thresholding because that combination produced a higher-confidence ROI-local A/B result."
        )
    elif threshold_mode_used != payload.threshold_mode:
        detail_parts.append(
            f"Auto detection selected {threshold_mode_used} thresholding because it produced a higher-confidence ROI-local A/B result."
        )
    elif foreground_polarity_used != payload.foreground_polarity:
        detail_parts.append(
            f"Auto detection selected {foreground_polarity_used} polarity because it produced a higher-confidence ROI-local A/B result."
        )
    if metric.quality < runtime_config.live.vision.quality_threshold:
        detail_parts.append(
            "Auto detection succeeded with low confidence. Please verify the ROI-local result and recompute if needed."
        )
    detail = " ".join(detail_parts)
    return AutoDetectDefinitionResponse(
        point_a_px=PixelPointResponse(x=metric.point_a_px[0], y=metric.point_a_px[1]),
        point_b_px=PixelPointResponse(x=metric.point_b_px[0], y=metric.point_b_px[1]),
        source_point_a_px=_metric_meta_point_response(metric, "source_point_a_px"),
        source_point_b_px=_metric_meta_point_response(metric, "source_point_b_px"),
        axis_point_a_px=_metric_meta_point_response(metric, "axis_point_a_px"),
        axis_point_b_px=_metric_meta_point_response(metric, "axis_point_b_px"),
        quality=metric.quality,
        metric_raw=metric.metric_raw,
        threshold_mode_used=threshold_mode_used,
        foreground_polarity_used=foreground_polarity_used,
        direction_angle_deg=_metric_direction_angle_deg(metric),
        direction_projection_mode=_metric_projection_mode(metric),
        selection_mode=_metric_selection_mode(metric),
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
    if record.temperature_settings is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run must have confirmed temperature settings before start: {run_id}",
        )
    if abs(float(payload.target_temperature_celsius) - float(record.temperature_settings.target_temperature_celsius)) >= 0.05:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run target temperature must match confirmed temperature settings before start: {run_id}",
        )

    try:
        live_run_service.start_run(
            record=record,
            runtime_config=runtime_config,
            target_temperature_celsius=record.temperature_settings.target_temperature_celsius,
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


def _best_auto_detect_metric(
    *,
    frame,
    payload: AutoDetectDefinitionRequest,
    runtime_config: RuntimeConfig,
    preset: str = "balloon",
):
    analysis_roi = RectRegion(
        x=payload.analysis_roi.x,
        y=payload.analysis_roi.y,
        width=payload.analysis_roi.width,
        height=payload.analysis_roi.height,
    )
    if payload.direction_angle_deg is not None:
        return _best_directional_contour_metric(
            frame=frame,
            analysis_roi=analysis_roi,
            payload=payload,
            runtime_config=runtime_config,
            preset=preset,
        )

    metric_box = None if payload.metric_box is None else MetricBox(
        center_x=payload.metric_box.center_x,
        center_y=payload.metric_box.center_y,
        width=payload.metric_box.width,
        height=payload.metric_box.height,
        angle_deg=payload.metric_box.angle_deg,
    )
    observation_axis = ObservationAxis(payload.observation_axis)
    selection_strategy = "roi_local_horizontal_boundary" if payload.metric_box is not None else "axis_aligned_span"
    threshold_modes = _candidate_threshold_modes(payload.threshold_mode)
    best_metric = None
    best_threshold_mode = payload.threshold_mode
    best_foreground_polarity = payload.foreground_polarity

    def _extract_candidate(foreground_polarity: str, threshold_mode: str):
        if metric_box is not None and observation_axis == ObservationAxis.SHORT_AXIS:
            detector = TwoPointDistanceMetricExtractor(
                analysis_roi=analysis_roi,
                metric_box=metric_box,
                measurement_axis_deg=float(metric_box.angle_deg) + 90.0,
                foreground_polarity=foreground_polarity,
                threshold_mode=threshold_mode,
                threshold_margin=runtime_config.live.vision.edge_threshold,
                ignore_internal_texture=payload.ignore_internal_texture,
                min_target_area_px=payload.min_target_area_px,
                quality_threshold=runtime_config.live.vision.quality_threshold,
                sensitivity=payload.sensitivity,
                selection_strategy="auto_extremes",
            )
        else:
            detector = RoiLongestSpanPointDetector(
                analysis_roi=analysis_roi,
                roi_box=metric_box,
                foreground_polarity=foreground_polarity,
                threshold_mode=threshold_mode,
                threshold_margin=runtime_config.live.vision.edge_threshold,
                ignore_internal_texture=payload.ignore_internal_texture,
                min_target_area_px=payload.min_target_area_px,
                quality_threshold=runtime_config.live.vision.quality_threshold,
                sensitivity=payload.sensitivity,
                selection_strategy=selection_strategy,
                working_max_width=ROI_LOCAL_WORKING_MAX_WIDTH,
                working_max_height=ROI_LOCAL_WORKING_MAX_HEIGHT,
            )
        return detector.extract(frame)

    requested_polarity_best = None
    requested_polarity_threshold = payload.threshold_mode
    for threshold_mode in threshold_modes:
        candidate_metric = _extract_candidate(payload.foreground_polarity, threshold_mode)
        if best_metric is None or _auto_detect_metric_rank(candidate_metric, analysis_roi, metric_box=metric_box) > _auto_detect_metric_rank(best_metric, analysis_roi, metric_box=metric_box):
            best_metric = candidate_metric
            best_threshold_mode = threshold_mode
            best_foreground_polarity = payload.foreground_polarity
        if requested_polarity_best is None or _auto_detect_metric_rank(candidate_metric, analysis_roi, metric_box=metric_box) > _auto_detect_metric_rank(
            requested_polarity_best,
            analysis_roi,
            metric_box=metric_box,
        ):
            requested_polarity_best = candidate_metric
            requested_polarity_threshold = threshold_mode

    if _auto_detect_metric_is_acceptably_specific(
        requested_polarity_best,
        analysis_roi,
        metric_box=metric_box,
        quality_threshold=runtime_config.live.vision.quality_threshold,
    ):
        return requested_polarity_best, requested_polarity_threshold, payload.foreground_polarity

    for foreground_polarity in _candidate_foreground_polarities(payload.foreground_polarity):
        if foreground_polarity == payload.foreground_polarity:
            continue
        for threshold_mode in threshold_modes:
            candidate_metric = _extract_candidate(foreground_polarity, threshold_mode)
            if best_metric is None or _auto_detect_metric_rank(candidate_metric, analysis_roi, metric_box=metric_box) > _auto_detect_metric_rank(best_metric, analysis_roi, metric_box=metric_box):
                best_metric = candidate_metric
                best_threshold_mode = threshold_mode
                best_foreground_polarity = foreground_polarity
    return best_metric, best_threshold_mode, best_foreground_polarity


def _best_directional_contour_metric(
    *,
    frame,
    analysis_roi: RectRegion,
    payload: AutoDetectDefinitionRequest,
    runtime_config: RuntimeConfig,
    preset: str = "balloon",
):
    requested_threshold_mode = str(payload.threshold_mode)
    threshold_modes = _candidate_threshold_modes(requested_threshold_mode)
    best_metric = None
    best_threshold_mode = requested_threshold_mode
    best_foreground_polarity = payload.foreground_polarity
    requested_metric = None
    requested_foreground_polarity = payload.foreground_polarity
    metric_box = None if payload.metric_box is None else MetricBox(
        center_x=payload.metric_box.center_x,
        center_y=payload.metric_box.center_y,
        width=payload.metric_box.width,
        height=payload.metric_box.height,
        angle_deg=payload.metric_box.angle_deg,
    )
    for foreground_polarity in _candidate_foreground_polarities(payload.foreground_polarity):
        candidate_metric = _extract_directional_auto_detect_metric(
            frame=frame,
            analysis_roi=analysis_roi,
            payload=payload,
            runtime_config=runtime_config,
            preset=preset,
            foreground_polarity=foreground_polarity,
            threshold_mode=requested_threshold_mode,
        )
        if requested_metric is None or _directional_auto_detect_metric_rank(
            candidate_metric,
            analysis_roi,
            metric_box=metric_box,
        ) > _directional_auto_detect_metric_rank(
            requested_metric,
            analysis_roi,
            metric_box=metric_box,
        ):
            requested_metric = candidate_metric
            requested_foreground_polarity = foreground_polarity
    if requested_metric is not None and _directional_metric_is_acceptably_specific(
        requested_metric,
        analysis_roi,
        metric_box=metric_box,
        quality_threshold=runtime_config.live.vision.quality_threshold,
    ):
        return requested_metric, requested_threshold_mode, requested_foreground_polarity
    best_metric = requested_metric
    best_foreground_polarity = requested_foreground_polarity
    for foreground_polarity in _candidate_foreground_polarities(payload.foreground_polarity):
        for threshold_mode in threshold_modes:
            if threshold_mode == requested_threshold_mode:
                continue
            candidate_metric = _extract_directional_auto_detect_metric(
                frame=frame,
                analysis_roi=analysis_roi,
                payload=payload,
                runtime_config=runtime_config,
                preset=preset,
                foreground_polarity=foreground_polarity,
                threshold_mode=threshold_mode,
            )
            if best_metric is None or _directional_auto_detect_metric_rank(
                candidate_metric,
                analysis_roi,
                metric_box=metric_box,
            ) > _directional_auto_detect_metric_rank(
                best_metric,
                analysis_roi,
                metric_box=metric_box,
            ):
                best_metric = candidate_metric
                best_threshold_mode = threshold_mode
                best_foreground_polarity = foreground_polarity
    return best_metric, best_threshold_mode, best_foreground_polarity


def _extract_directional_auto_detect_metric(
    *,
    frame,
    analysis_roi: RectRegion,
    payload: AutoDetectDefinitionRequest,
    runtime_config: RuntimeConfig,
    preset: str,
    foreground_polarity: str,
    threshold_mode: str,
):
    metric_box = None if payload.metric_box is None else MetricBox(
        center_x=payload.metric_box.center_x,
        center_y=payload.metric_box.center_y,
        width=payload.metric_box.width,
        height=payload.metric_box.height,
        angle_deg=payload.metric_box.angle_deg,
    )
    detector = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=analysis_roi,
            direction_angle_deg=float(payload.direction_angle_deg),
            metric_box=metric_box,
            foreground_polarity=foreground_polarity,
            threshold_mode=threshold_mode,
            threshold_value=runtime_config.live.vision.edge_threshold,
            ignore_internal_texture=payload.ignore_internal_texture,
            min_target_area_px=payload.min_target_area_px,
            sensitivity=payload.sensitivity,
            component_bridge_kernel=_directional_component_bridge_kernel_for_sensitivity(
                payload.sensitivity,
                direction_angle_deg=payload.direction_angle_deg,
            ),
            projection_mode=_resolve_direction_projection_mode(payload, preset),
        )
    )
    return detector.extract(frame)


def _candidate_threshold_modes(requested_threshold_mode: str) -> list[str]:
    ordered = [requested_threshold_mode, "otsu", "adaptive", "binary"]
    candidates: list[str] = []
    for threshold_mode in ordered:
        if threshold_mode not in candidates:
            candidates.append(threshold_mode)
    return candidates


def _candidate_foreground_polarities(requested_foreground_polarity: str) -> list[str]:
    alternate = "light_on_dark" if requested_foreground_polarity == "dark_on_light" else "dark_on_light"
    return [requested_foreground_polarity, alternate]


def _directional_component_bridge_kernel_for_sensitivity(
    sensitivity: float,
    direction_angle_deg: float | None = None,
) -> int:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    angle = None if direction_angle_deg is None else abs(float(direction_angle_deg) % 180.0)
    near_vertical = angle is not None and abs(angle - 90.0) <= 15.0
    if near_vertical:
        if normalized <= 0.5:
            size = 7.0 + (normalized / 0.5) * 34.0
        else:
            size = 41.0 + ((normalized - 0.5) / 0.5) * 22.0
    elif normalized <= 0.5:
        size = 3.0 + (normalized / 0.5) * 8.0
    else:
        size = 11.0 + ((normalized - 0.5) / 0.5) * 28.0
    kernel = max(1, int(round(size)))
    if kernel % 2 == 0:
        kernel += 1
    return kernel


def _auto_detect_metric_rank(
    metric,
    analysis_roi: RectRegion,
    *,
    metric_box: MetricBox | None = None,
) -> tuple[float, int, int, int, float, int]:
    point_score = 1 if metric.metric_raw is not None and metric.point_a_px is not None and metric.point_b_px is not None else 0
    component_area = int(getattr(metric, "meta", {}).get("component_area") or 0)
    roi_area = max(int(analysis_roi.width) * int(analysis_roi.height), 1)
    endpoint_border_touch_count = _auto_detect_endpoint_edge_touch_count(metric, analysis_roi, metric_box=metric_box)
    target_component_score = 0 if component_area >= int(roi_area * 0.85) or endpoint_border_touch_count >= 2 else 1
    endpoint_interior_score = 2 - endpoint_border_touch_count
    quality = float(metric.quality or 0.0)
    span = float(metric.metric_raw or 0.0)
    span_reference = _auto_detect_span_reference(analysis_roi, metric_box=metric_box)
    span_ratio = min(1.0, span / max(span_reference, 1.0))
    # A single ROI/metric edge touch can be a legitimate physical boundary when
    # the operator drew the ROI close to the sample. Bucket the horizontal span
    # before the edge penalty so a clearly fuller envelope can win, while still
    # preferring interior endpoints when candidates cover the same object span.
    span_bucket = int(math.floor(span_ratio / 0.15))
    return (point_score, target_component_score, span_bucket, endpoint_interior_score, quality, int(round(span)))


def _directional_auto_detect_metric_rank(
    metric,
    analysis_roi: RectRegion,
    *,
    metric_box: MetricBox | None = None,
) -> tuple[float, int, int, float, int]:
    point_score = 1 if metric.metric_raw is not None and metric.point_a_px is not None and metric.point_b_px is not None else 0
    component_area = int(getattr(metric, "meta", {}).get("component_area") or 0)
    roi_area = max(int(analysis_roi.width) * int(analysis_roi.height), 1)
    target_component_score = 0 if component_area >= int(roi_area * 0.85) else 1
    endpoint_interior_score = 2 - _auto_detect_endpoint_edge_touch_count(metric, analysis_roi, metric_box=metric_box)
    quality = float(metric.quality or 0.0)
    span = float(metric.metric_raw or 0.0)
    return (point_score, target_component_score, endpoint_interior_score, quality, int(round(span)))


def _auto_detect_metric_is_acceptably_specific(
    metric,
    analysis_roi: RectRegion,
    *,
    metric_box: MetricBox | None = None,
    quality_threshold: float,
) -> bool:
    if metric is None or metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        return False
    component_area = int(getattr(metric, "meta", {}).get("component_area") or 0)
    roi_area = max(int(analysis_roi.width) * int(analysis_roi.height), 1)
    if component_area >= int(roi_area * 0.85):
        return False
    if _auto_detect_endpoint_edge_touch_count(metric, analysis_roi, metric_box=metric_box) >= 2:
        return False
    return float(metric.quality or 0.0) >= float(quality_threshold)


def _auto_detect_span_reference(analysis_roi: RectRegion, *, metric_box: MetricBox | None) -> float:
    if metric_box is not None:
        return float(max(metric_box.width, 1))
    return float(max(analysis_roi.width, analysis_roi.height, 1))


def _auto_detect_endpoint_edge_touch_count(
    metric,
    analysis_roi: RectRegion,
    *,
    metric_box: MetricBox | None,
) -> int:
    analysis_touch_count = _directional_endpoint_border_touch_count(metric, analysis_roi)
    if metric_box is None:
        return analysis_touch_count
    return max(analysis_touch_count, _metric_box_endpoint_edge_touch_count(metric, metric_box))


def _metric_box_endpoint_edge_touch_count(metric, metric_box: MetricBox) -> int:
    points = [metric.point_a_px, metric.point_b_px]
    if any(point is None for point in points):
        return 2
    margin = max(2.0, float(min(metric_box.width, metric_box.height)) * 0.025)
    half_width = float(metric_box.width) / 2.0
    half_height = float(metric_box.height) / 2.0
    angle_rad = math.radians(float(metric_box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    touches = 0
    for point in points:
        try:
            x = float(point[0])
            y = float(point[1])
        except (TypeError, ValueError, IndexError):
            touches += 1
            continue
        translated_x = x - float(metric_box.center_x)
        translated_y = y - float(metric_box.center_y)
        local_x = translated_x * cos_theta + translated_y * sin_theta
        local_y = -translated_x * sin_theta + translated_y * cos_theta
        if (
            local_x <= -half_width + margin
            or local_x >= half_width - margin
            or local_y <= -half_height + margin
            or local_y >= half_height - margin
        ):
            touches += 1
    return min(2, touches)


def _directional_endpoint_border_touch_count(metric, analysis_roi: RectRegion) -> int:
    points = [metric.point_a_px, metric.point_b_px]
    if any(point is None for point in points):
        return 2
    margin = max(1, int(round(float(min(int(analysis_roi.width), int(analysis_roi.height))) * 0.015)))
    left = int(analysis_roi.x) + margin
    right = int(analysis_roi.x + analysis_roi.width) - 1 - margin
    top = int(analysis_roi.y) + margin
    bottom = int(analysis_roi.y + analysis_roi.height) - 1 - margin
    touches = 0
    for point in points:
        try:
            x = int(point[0])
            y = int(point[1])
        except (TypeError, ValueError, IndexError):
            touches += 1
            continue
        if x <= left or x >= right or y <= top or y >= bottom:
            touches += 1
    return min(2, touches)


def _directional_metric_is_acceptably_specific(
    metric,
    analysis_roi: RectRegion,
    *,
    metric_box: MetricBox | None = None,
    quality_threshold: float,
) -> bool:
    if metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        return False
    component_area = int(getattr(metric, "meta", {}).get("component_area") or 0)
    roi_area = max(int(analysis_roi.width) * int(analysis_roi.height), 1)
    if component_area >= int(roi_area * 0.85):
        return False
    if _auto_detect_endpoint_edge_touch_count(metric, analysis_roi, metric_box=metric_box) >= 2:
        return False
    return float(metric.quality or 0.0) >= float(quality_threshold)


def _metric_direction_angle_deg(metric) -> float | None:
    value = getattr(metric, "meta", {}).get("direction_angle_deg")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_projection_mode(metric) -> str:
    value = getattr(metric, "meta", {}).get("projection_point_mode")
    if value in {"max_chord", "mask_projection"}:
        return str(value)
    return "auto"


def _resolve_direction_projection_mode(payload, preset: str) -> str:
    explicit_fields = getattr(payload, "model_fields_set", set())
    if "direction_projection_mode" in explicit_fields:
        return str(payload.direction_projection_mode)
    return _default_direction_projection_mode_for_preset(preset)


def _default_direction_projection_mode_for_preset(preset: str) -> str:
    return "auto"


def _metric_selection_mode(metric) -> str | None:
    value = getattr(metric, "meta", {}).get("selection_mode")
    return None if value is None else str(value)


def _metric_meta_point_response(metric, key: str) -> PixelPointResponse | None:
    value = getattr(metric, "meta", {}).get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        return PixelPointResponse(x=int(value[0]), y=int(value[1]))
    except (TypeError, ValueError):
        return None


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


def _frame_image_dimensions(frame) -> tuple[int, int]:
    image = frame.image
    if hasattr(image, "shape"):
        shape = getattr(image, "shape")
        if len(shape) >= 2:
            return int(shape[1]), int(shape[0])
    if isinstance(image, (list, tuple)):
        height = len(image)
        if height == 0:
            return (0, 0)
        first_row = image[0]
        if isinstance(first_row, (list, tuple)):
            return (len(first_row), height)
        return (height, 1)
    return (0, 0)


def _frame_source_dimensions(frame, *, fallback: tuple[int, int]) -> tuple[int, int]:
    meta = getattr(frame, "meta", None)
    if isinstance(meta, dict):
        try:
            source_width = int(meta.get("tracking_preview_source_width", 0) or 0)
            source_height = int(meta.get("tracking_preview_source_height", 0) or 0)
        except (TypeError, ValueError):
            source_width = 0
            source_height = 0
        if source_width > 0 and source_height > 0:
            return source_width, source_height
    return fallback


def _preview_frame_is_already_enhanced(frame) -> bool:
    meta = getattr(frame, "meta", None)
    return isinstance(meta, dict) and bool(meta.get("tracking_preview_already_enhanced"))


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
    execution_detail = snapshot.execution.detail if snapshot is not None and snapshot.execution is not None else None
    if execution_detail is not None:
        rate_payload = dict(execution_detail.get("rates", {}) or {})
        measurement_profile_payload = dict(execution_detail.get("measurement_profile", {}) or {})
        warnings = list(execution_detail.get("warnings", []) or [])
    else:
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
        rate_payload = {
            "camera_resulting_fps": rate_snapshot.camera_resulting_fps,
            "preview_display_fps": rate_snapshot.preview_display_fps,
            "measurement_sample_hz": rate_snapshot.measurement_sample_hz,
            "artifact_capture_hz": rate_snapshot.artifact_capture_hz,
            "dropped_frame_count": rate_snapshot.dropped_frame_count,
        }
        measurement_profile_payload = {
            "acquisition_roi": None
            if measurement_profile is None or measurement_profile.acquisition_roi is None
            else {
                "x": measurement_profile.acquisition_roi.x,
                "y": measurement_profile.acquisition_roi.y,
                "width": measurement_profile.acquisition_roi.width,
                "height": measurement_profile.acquisition_roi.height,
            },
            "decimation": None if measurement_profile is None else measurement_profile.decimation,
            "binning": None if measurement_profile is None else measurement_profile.binning,
            "exposure_us": None if measurement_profile is None else measurement_profile.exposure_us,
        }
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
    editor_state = "empty"
    if definition_complete:
        editor_state = "locked"
    elif record.status == RunStatus.DEFINITION_EDITING or (
        preview_state is not None and preview_state.frozen_frame_available
    ):
        editor_state = "editing"
    return RunDetailResponse(
        run_id=record.run_id,
        status=record.status.value,
        profile=record.profile,
        preset=record.preset,
        definition=None if definition is None else _build_measurement_definition(definition),
        temperature_settings=None
        if record.temperature_settings is None
        else _build_temperature_settings(record.temperature_settings),
        temperature_settings_confirmed=record.temperature_settings is not None,
        created_at_ms=record.created_at_ms,
        updated_at_ms=record.updated_at_ms,
        definition_complete=definition_complete,
        capture_mode=record.capture_mode.value,
        rates=RunRatesResponse(
            camera_resulting_fps=rate_payload.get("camera_resulting_fps"),
            preview_display_fps=rate_payload.get("preview_display_fps"),
            measurement_sample_hz=rate_payload.get("measurement_sample_hz"),
            artifact_capture_hz=rate_payload.get("artifact_capture_hz"),
            dropped_frame_count=int(rate_payload.get("dropped_frame_count", 0) or 0),
        ),
        measurement_profile=MeasurementProfileResponse(
            acquisition_roi=None
            if measurement_profile_payload.get("acquisition_roi") is None
            else RectRegionResponse(
                x=int(measurement_profile_payload["acquisition_roi"]["x"]),
                y=int(measurement_profile_payload["acquisition_roi"]["y"]),
                width=int(measurement_profile_payload["acquisition_roi"]["width"]),
                height=int(measurement_profile_payload["acquisition_roi"]["height"]),
            ),
            decimation=measurement_profile_payload.get("decimation"),
            binning=measurement_profile_payload.get("binning"),
            exposure_us=measurement_profile_payload.get("exposure_us"),
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
        observation_axis=definition.observation_axis.value,
        foreground_polarity=definition.foreground_polarity,
        threshold_mode=definition.threshold_mode,
        ignore_internal_texture=definition.ignore_internal_texture,
        min_target_area_px=definition.min_target_area_px,
        sensitivity=definition.sensitivity,
        direction_angle_deg=definition.direction_angle_deg,
        direction_projection_mode=definition.direction_projection_mode,
    )


def _build_temperature_settings(settings: TemperatureSettingsBundle) -> TemperatureSettingsResponse:
    confirmed_target = (
        float(settings.confirmed_target_temperature_celsius)
        if settings.confirmed_target_temperature_celsius is not None
        else float(settings.target_temperature_celsius)
    )
    return TemperatureSettingsResponse(
        target_temperature_celsius=float(settings.target_temperature_celsius),
        control_mode=str(settings.control_mode),
        output_power_percent=float(settings.output_power_percent),
        completion_mode=str(settings.completion_mode),
        confirmed_target_temperature_celsius=confirmed_target,
        confirmed_output_power_percent=(
            float(settings.confirmed_output_power_percent)
            if settings.confirmed_output_power_percent is not None
            else None
        ),
        confirmed_at_ms=int(settings.confirmed_at_ms),
        source=str(settings.source),
    )


def _write_and_confirm_temperature_settings(
    *,
    controller: object,
    target_temperature_celsius: float,
    output_power_percent: float,
) -> dict[str, object]:
    controller.set_target_temperature(target_temperature_celsius)
    controller.set_output_power_percent(output_power_percent)
    return {
        "confirmed_target_temperature_celsius": float(controller.read_target_temperature()),
        "confirmed_output_power_percent": float(controller.read_output_power_percent()),
        "confirmed_at_ms": int(time.time() * 1000),
        "source": type(controller).__name__,
    }


def _encode_grayscale_jpeg_bitmap(bitmap: PreviewBitmap, *, quality: int = 55) -> bytes:
    jpeg_image = Image.frombytes("L", (bitmap.width, bitmap.height), bitmap.pixels)
    from io import BytesIO

    buffer = BytesIO()
    jpeg_image.save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()


def _encode_grayscale_png_bitmap(bitmap: PreviewBitmap) -> bytes:
    width = bitmap.width
    height = bitmap.height
    raw = bytearray(height * (width + 1))
    write_index = 0
    pixel_index = 0
    for _ in range(height):
        raw[write_index] = 0
        write_index += 1
        row_end = pixel_index + width
        raw[write_index : write_index + width] = bitmap.pixels[pixel_index:row_end]
        write_index += width
        pixel_index = row_end

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


def _iter_preview_stream_payload(
    *,
    runtime_config: RuntimeConfig,
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
        bitmap = build_preview_bitmap(
            frame.image,
            max_width=runtime_config.live.run.preview_display_max_width,
            max_height=runtime_config.live.run.preview_display_max_height,
        )
        bitmap = enhance_preview_bitmap(bitmap)
        payload = _encode_grayscale_jpeg_bitmap(bitmap)
        yield _encode_preview_stream_part(
            payload=payload,
            content_type="image/jpeg",
        )


def _preview_stream_interval_ms(runtime_config: RuntimeConfig) -> int:
    preview_target_fps = float(runtime_config.live.run.preview_target_fps or 0.0)
    return compute_preview_interval_ms(
        target_fps=preview_target_fps,
        fallback_ms=runtime_config.live.run.preview_poll_ms,
    )


def _encode_preview_stream_part(
    *,
    payload: bytes,
    content_type: str = "image/jpeg",
) -> bytes:
    headers = [
        f"--{_PREVIEW_STREAM_BOUNDARY}".encode("ascii"),
        f"Content-Type: {content_type}".encode("ascii"),
        f"Content-Length: {len(payload)}".encode("ascii"),
        b"",
    ]
    return b"\r\n".join(headers) + b"\r\n" + payload + b"\r\n"
