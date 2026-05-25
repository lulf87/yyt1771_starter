from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "ui-shell.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def _js_function_body(source: str, function_name: str) -> str:
    marker = f"function {function_name}("
    start = source.index(marker)
    paren_depth = 0
    brace_start = -1
    for index in range(source.index("(", start), len(source)):
        char = source[index]
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "{" and paren_depth == 0:
            brace_start = index
            break
    if brace_start < 0:
        raise AssertionError(f"Function {function_name} body not found")
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start + 1 : index]
    raise AssertionError(f"Function {function_name} body not found")


def test_static_app_js_preserves_rotated_roi_angle_in_metric_box() -> None:
    app_js = (PROJECT_ROOT / "src/webapp/static/app.js").read_text(encoding="utf-8")

    metric_box_body = _js_function_body(app_js, "metricBoxForDirectionalRoi")
    analysis_roi_body = _js_function_body(app_js, "getCurrentAnalysisRoi")
    payload_body = _js_function_body(app_js, "buildLiveDefinitionBasePayload")

    assert "angle_deg: Number(Number(box.angle_deg || 0).toFixed(1))" in metric_box_body
    assert "return boundingRectForMetricBox(getCurrentRoiBox());" in analysis_roi_body
    assert "analysis_roi: boundingRectForMetricBox(roiBox)" in payload_body


def test_static_app_js_resizes_rotated_roi_in_roi_local_axes() -> None:
    app_js = (PROJECT_ROOT / "src/webapp/static/app.js").read_text(encoding="utf-8")

    pointer_move_body = _js_function_body(app_js, "handleLivePreviewPointerMove")

    assert "function resizeMetricBoxFromFixedCorner" in app_js
    assert "resizeMetricBoxFromFixedCorner(" in pointer_move_body
    assert "Math.abs(point.x - drag.fixedCorner.x)" not in pointer_move_body
    assert "Math.abs(point.y - drag.fixedCorner.y)" not in pointer_move_body


def test_static_app_js_defaults_formal_ab_selection_to_max_chord() -> None:
    app_js = (PROJECT_ROOT / "src/webapp/static/app.js").read_text(encoding="utf-8")

    body = _js_function_body(app_js, "currentDirectionProjectionMode")
    auto_detect_body = _js_function_body(app_js, "autoDetectLiveDefinition")

    assert 'resolvedDirectionProjectionMode: "max_chord"' in app_js
    assert 'liveRunState.resolvedDirectionProjectionMode = "auto";' not in app_js
    assert ': "max_chord";' in body
    assert 'payload.direction_projection_mode' in auto_detect_body
    assert ': "max_chord";' in auto_detect_body


def test_static_app_js_rotates_roi_without_resizing() -> None:
    app_js = (PROJECT_ROOT / "src/webapp/static/app.js").read_text(encoding="utf-8")

    pointer_move_body = _js_function_body(app_js, "handleLivePreviewPointerMove")
    pointer_up_body = _js_function_body(app_js, "handleLivePreviewPointerUp")
    commit_body = _js_function_body(app_js, "commitAnalysisRoiSelection")
    rotate_branch = pointer_move_body[pointer_move_body.index('drag.tool === "rotate-roi"') :]
    rotate_branch = rotate_branch[: rotate_branch.index("updateLiveDefinitionAfterLocalEdit")]

    assert "rotateMetricBoxAroundCenter" in rotate_branch
    assert "ensureMetricBoxWithinAnalysisRoi();" not in rotate_branch
    assert "updateLiveDefinitionAfterLocalEdit({ constrain: false });" in pointer_move_body
    assert 'completedTool === "rotate-roi"' in pointer_up_body
    assert "constrain: false" in pointer_up_body
    assert "function metricBoxWithinPreviewFrame" in app_js
    assert "metricBoxWithinPreviewFrame(getCurrentMetricBox())" in commit_body
    assert "ROI 超出画面" in commit_body


def test_ui_shell_route_returns_html_with_expected_hooks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "实时预览" in response.text
    assert "ROI 框选" in response.text
    assert "查看ROI参数" in response.text
    assert "更多工具与诊断" in response.text
    assert "保存数据" in response.text
    assert "进入分析" in response.text
    assert "新测试" in response.text
    assert "<title" in response.text
    assert "实时测试</title>" in response.text
    assert 'data-language-toggle="zh"' in response.text
    assert 'data-language-toggle="en"' in response.text
    assert 'id="fixture-video-switch"' in response.text
    assert 'id="fixture-video-select"' in response.text
    assert 'data-testid="fixture-video-select"' in response.text
    assert '/static/app.css?v=' in response.text
    assert '/static/app.js?v=' in response.text
    assert 'id="health-status"' in response.text
    assert 'id="profile-name"' in response.text
    assert 'id="home-completion-dock"' in response.text
    assert 'id="home-result-session-id"' in response.text
    assert 'id="home-result-session-state"' in response.text
    assert 'id="save-session-data-btn"' in response.text
    assert 'id="new-live-test-btn"' in response.text
    assert 'id="session-workspace-link" class="workspace-link button-secondary workspace-link--hidden"' in response.text
    assert 'id="live-run-id"' in response.text
    assert 'id="live-run-status"' in response.text
    assert 'id="live-run-preset-select"' in response.text
    assert 'id="live-preview-rate"' in response.text
    assert 'id="live-measurement-rate"' in response.text
    assert 'id="stop-live-preview-stream-btn"' in response.text
    assert ">冻结画面<" in response.text
    assert 'id="live-preview-img"' in response.text
    assert 'id="live-preview-stage"' in response.text
    assert 'id="live-process-panel"' in response.text
    assert 'id="live-process-chart"' in response.text
    assert 'id="live-process-status-card"' in response.text
    assert 'id="live-process-point-count"' in response.text
    assert 'id="live-process-outlier-count"' in response.text
    assert 'id="live-process-as-value"' in response.text
    assert 'id="live-process-af-tan-value"' in response.text
    assert 'id="live-point-prompt"' in response.text
    assert 'id="live-point-prompt-title"' in response.text
    assert 'id="live-point-prompt-body"' in response.text
    assert 'id="live-preview-overlay"' in response.text
    assert 'id="live-current-temperature"' in response.text
    assert 'id="temp-serial-port-select"' in response.text
    assert 'id="refresh-temp-serial-ports-btn"' in response.text
    assert 'id="apply-temp-serial-port-btn"' in response.text
    assert 'id="temp-serial-port-status"' in response.text
    assert 'id="live-target-temperature"' in response.text
    assert 'id="live-completion-mode"' in response.text
    assert 'value="manual_stop_only"' in response.text
    assert 'id="live-output-power-percent"' in response.text
    assert 'id="confirm-target-temperature-btn"' in response.text
    assert 'id="stop-live-run-btn"' in response.text
    assert 'id="draw-analysis-roi-btn"' in response.text
    assert 'id="start-live-preview-stream-btn"' in response.text
    assert 'id="recompute-definition-btn"' in response.text
    assert 'id="live-point-a-summary"' in response.text
    assert 'id="live-point-b-summary"' in response.text
    assert 'id="live-analysis-roi-x"' in response.text
    assert 'id="live-analysis-roi-y"' in response.text
    assert 'id="live-analysis-roi-width"' in response.text
    assert 'id="live-analysis-roi-height"' in response.text
    assert 'id="live-analysis-roi-angle"' in response.text
    assert 'id="live-point-a-x"' in response.text
    assert 'id="live-point-b-y"' in response.text
    assert 'id="live-sensitivity"' in response.text
    assert 'id="live-ignore-internal-texture"' in response.text
    ignore_texture_control = response.text[
        response.text.index('id="live-ignore-internal-texture"') :
        response.text.index('id="live-ignore-internal-texture"') + 180
    ]
    assert "checked" not in ignore_texture_control
    assert "正在连接实时预览" in response.text
    assert 'id="app-title"' not in response.text
    assert 'data-testid="home-journey"' not in response.text
    assert 'id="home-current-task-title"' not in response.text
    assert 'id="home-current-task-copy"' not in response.text
    assert 'id="home-current-task-step"' not in response.text
    assert "YYT1771" not in response.text
    assert "启动与控制驾驶舱" not in response.text
    assert 'id="create-live-run-btn"' not in response.text
    assert 'id="fetch-live-preview-btn"' not in response.text
    assert 'id="pick-point-a-btn"' not in response.text
    assert 'id="pick-point-b-btn"' not in response.text
    assert 'id="draw-observation-window-btn"' not in response.text
    assert 'id="rotate-observation-window-btn"' not in response.text
    assert 'id="auto-detect-definition-btn"' not in response.text
    assert 'id="save-live-definition-btn"' not in response.text
    assert 'id="precheck-status"' in response.text
    assert 'id="precheck-items"' in response.text
    assert 'id="refresh-precheck-btn"' in response.text
    assert 'id="probe-camera-btn"' in response.text
    assert 'id="probe-mode-select"' in response.text
    assert 'id="probe-allowed-models-input"' in response.text
    assert 'id="probe-serial-number-input"' in response.text
    assert 'id="probe-ip-input"' in response.text
    assert 'id="probe-local-override-hint"' in response.text
    assert "camera_sdk_runtime" in response.text
    assert 'id="camera-probe-result"' in response.text
    assert 'id="run-mock-btn"' in response.text
    assert 'id="run-replay-btn"' in response.text
    assert 'id="import-afas-dataset-file"' in response.text
    assert 'id="import-afas-dataset-btn"' in response.text
    assert 'id="import-afas-dataset-hint"' in response.text
    assert 'id="session-workspace-link"' in response.text
    assert 'id="session-result"' in response.text
    assert 'id="recent-sessions"' in response.text
    assert 'id="detail-af95"' in response.text
    assert 'id="detail-point-count"' in response.text
    assert 'id="detail-curve"' in response.text
    assert 'id="detail-curve-layers"' in response.text
    assert 'id="detail-key-frames"' in response.text


def test_static_app_js_is_served(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "/api/system/profile" in response.text
    assert "/api/system/precheck" in response.text
    assert "/api/system/camera/probe" in response.text
    assert "/api/system/real-offline-alignment/live-probe" in response.text
    assert "/api/system/temp/current" in response.text
    assert "/api/system/temp/serial-ports" in response.text
    assert "/api/system/temp/serial-port" in response.text
    assert "/api/debug/fixture-videos" in response.text
    assert "fixture-video-select" in response.text
    assert "loadFixtureVideoSwitch" in response.text
    assert "switchFixtureVideo" in response.text
    assert "resolvedDirectionProjectionMode" in response.text
    assert "payload.direction_projection_mode" in response.text
    assert "buildRealOfflineLiveProbeRequest" in response.text
    assert "real_offline_alignment_definition_attached" in response.text
    assert 'buildLiveDefinitionPayload({ coordinateSpace: "source" })' in response.text
    assert 'body: JSON.stringify(alignmentDefinition)' in response.text
    assert "/api/runs" in response.text
    assert "/preview/frame" in response.text
    assert "/preview/stream" in response.text
    assert "/definition/auto" in response.text
    assert "/temperature-settings" in response.text
    assert "/start" in response.text
    assert "/stop" in response.text
    assert "/telemetry" in response.text
    assert "/result" in response.text
    assert "ensureLiveSetupBootstrapped" in response.text
    assert "live-run-preset-select" in response.text
    assert "live-preview-rate" in response.text
    assert "live-measurement-rate" in response.text
    assert "live-current-temperature" in response.text
    assert "live-target-temperature" in response.text
    assert "live-completion-mode" in response.text
    assert "completion_mode" in response.text
    assert "live-output-power-percent" in response.text
    assert "confirm-target-temperature-btn" in response.text
    assert "startCurrentTemperaturePolling" in response.text
    assert "confirmTargetTemperature" in response.text
    assert "refreshTempSerialPorts" in response.text
    assert "applyTempSerialPort" in response.text
    assert "Confirming bundled temperature settings on the controller" in response.text
    assert "confirmedTemperatureSettings" in response.text
    assert "isTemperatureSettingsConfirmed" in response.text
    assert "clearTemperatureSettingsConfirmation" in response.text
    assert "saveSessionData" in response.text
    assert "save-session-data-btn" in response.text
    assert "new-live-test-btn" in response.text
    assert "startNewLiveTest" in response.text
    assert "handleNewLiveTestClick" in response.text
    assert "confirm_new_test" in response.text
    assert "new-live-test-confirming" in response.text
    assert "clearHomeResultDisplays" in response.text
    assert "fetchSessionSummaryPayload" in response.text
    assert "buildTerminalRunDetailFromSessionSummary" in response.text
    assert "restoreTerminalLiveRunHomeState" in response.text
    assert "只有点击“新测试”才会清空并开始下一次测试" in response.text
    assert "persistLiveDefinition" in response.text
    assert "hasUnsavedDefinition" not in response.text
    assert "!roiReady || isRunActive || isTerminal" not in response.text
    assert 'const LANGUAGE_STORAGE_KEY = "yyt1771-ui-language"' in response.text
    assert "data-language-toggle" in response.text
    assert "applyStaticTranslations" in response.text
    assert "setLocale" in response.text
    assert "startLiveTrackingLoop" in response.text
    assert "const LIVE_TRACKING_POLL_MS = 50" in response.text
    assert "renderLiveProcessTelemetry" in response.text
    assert "live-process-chart-line" in response.text
    assert "live-process-chart-smooth-line" in response.text
    assert "smoothLiveProcessDisplaySamples" in response.text
    assert "buildLiveProcessSmoothPath" in response.text
    assert "moving_weighted_average" in response.text
    assert '["running", "stopping", "invalidated"].includes(statusValue)' not in response.text
    assert "live-process-status-card" in response.text
    assert ".slice(-600)" not in response.text
    assert "renderChartAxes" in response.text
    assert "温度 (°C)" in response.text
    assert "形变 / Space1 (px)" in response.text
    assert 'const xLabel = currentLocale === "en" ? "Temperature (°C)" : "温度 (°C)";' in response.text
    assert "liveProcessChartEmptyNode.style.display" in response.text
    assert "intOrDefault" not in response.text
    assert "refreshTrackingPreviewFrame" in response.text
    assert 'queryParams.set("tracking", "1")' in response.text
    assert "stop-live-run-btn" in response.text
    assert "live-preview-img" in response.text
    assert "live-point-prompt" in response.text
    assert "renderLiveToolPrompt" in response.text
    assert "Recomputing Locked Points" in response.text
    assert "Capturing a new frame to recalculate ROI-local A/B" in response.text
    assert "cached: false" in response.text
    assert "Point recompute failed. Adjust ROI or sensitivity and try again." in response.text
    assert "Failed to recompute ROI-local A/B:" in response.text
    assert "setupRecomputeInFlight" in response.text
    assert "updatePointSummaries" in response.text
    assert "live-preview-overlay" in response.text
    assert "draw-analysis-roi-btn" in response.text
    assert "stop-live-preview-stream-btn" in response.text
    assert "start-live-preview-stream-btn" in response.text
    assert "async function stopLivePreviewStream({ clearImage = false, silent = false } = {})" in response.text
    assert 'livePreviewImageNode.removeAttribute("src")' in response.text
    assert "scheduleRoiPointRecompute" in response.text
    assert "roiChanged || force || !hasValidPointInputs()" in response.text
    assert "Auto-detecting locked points along the contour direction" in response.text
    assert "Auto-detecting locked points from the ROI-local horizontal axis" not in response.text
    assert "direction_angle_deg: Number(roiBox.angle_deg || 0)" in response.text
    assert "direction_angle_deg: null" not in response.text
    assert "direction_angle_deg: definition.direction_angle_deg == null ? null : Number(definition.direction_angle_deg)" in response.text
    assert "direction_angle_deg: Number(definition.direction_angle_deg ?? normalizedMetricBox?.angle_deg ?? 0)" not in response.text
    assert "direction_angle_deg" in response.text
    assert "directionProjectionOverlayFromTelemetry" in response.text
    assert "source_point_a_preview_px" not in response.text
    assert "axisAlignedRectForRoiBox" in response.text
    assert "convertDirectionAngleForCoordinateSpace" in response.text
    assert "Save Definition when the ROI and A/B look correct." not in response.text
    assert "Definition saved. Live run is ready for the Phase 3 start flow." not in response.text
    assert 'const LIVE_SETUP_RUN_STORAGE_KEY = "yyt1771-live-setup-run-id"' in response.text

    assert "probe-mode-select" in response.text
    assert "create-live-run-btn" not in response.text
    assert "fetch-live-preview-btn" not in response.text
    assert "draw-observation-window-btn" not in response.text
    assert "rotate-observation-window-btn" not in response.text
    assert "auto-detect-definition-btn" not in response.text
    assert "/api/session" in response.text
    assert "/api/session/run-mock" in response.text
    assert "/api/session/run-replay" in response.text
    assert "/api/session/import-afas-dataset" in response.text
    assert "/api/session/${sessionId}/detail" in response.text
    assert "/workspace/" in response.text
    assert 'workspace-keyframe-card' in response.text
    assert "import-afas-dataset-file" in response.text
    assert "importAfasDataset" in response.text


def test_fixture_video_debug_endpoint_can_be_absent_without_console_404(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/debug/fixture-videos")

    assert response.status_code == 200
    assert response.json() == {
        "current": None,
        "current_label": None,
        "videos": [],
    }


def test_fixture_video_debug_endpoint_reports_offline_capture_fixture(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    runtime_config = client.app.state.runtime_config
    first_dir = tmp_path / "first-capture"
    second_dir = tmp_path / "second-capture"
    first_dir.mkdir()
    second_dir.mkdir()
    runtime_config.adapters["camera"] = "offline_capture"
    runtime_config.camera["offline_capture"] = {
        "capture_dir": str(first_dir),
        "fixtures": [
            {"key": "first", "label": "第一段素材", "capture_dir": str(first_dir)},
            {"key": "second", "label": "第二段素材", "capture_dir": str(second_dir)},
        ],
    }

    response = client.get("/api/debug/fixture-videos")

    assert response.status_code == 200
    assert response.json()["current"] == "first"
    assert response.json()["current_label"] == "第一段素材"
    assert response.json()["videos"] == [
        {"key": "first", "label": "第一段素材"},
        {"key": "second", "label": "第二段素材"},
    ]

    switch_response = client.post("/api/debug/fixture-videos/current", json={"key": "second"})

    assert switch_response.status_code == 200
    assert switch_response.json()["current"] == "second"
    assert runtime_config.camera["offline_capture"]["capture_dir"] == str(second_dir)


def test_favicon_route_returns_no_content(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/favicon.ico")

    assert response.status_code == 204
    assert response.text == ""
