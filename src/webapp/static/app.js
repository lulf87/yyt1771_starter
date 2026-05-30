const healthStatusNode = document.getElementById("health-status");
const profileNameNode = document.getElementById("profile-name");
const profileModeNode = document.getElementById("profile-mode");
const sessionResultNode = document.getElementById("session-result");
const recentSessionsNode = document.getElementById("recent-sessions");
const runMockButton = document.getElementById("run-mock-btn");
const runReplayButton = document.getElementById("run-replay-btn");
const importAfasDatasetFileInput = document.getElementById("import-afas-dataset-file");
const importAfasDatasetButton = document.getElementById("import-afas-dataset-btn");
const saveSessionDataButton = document.getElementById("save-session-data-btn");
const newLiveTestButton = document.getElementById("new-live-test-btn");
const probeCameraButton = document.getElementById("probe-camera-btn");
const probeModeSelect = document.getElementById("probe-mode-select");
const probeAllowedModelsInput = document.getElementById("probe-allowed-models-input");
const probeSerialNumberInput = document.getElementById("probe-serial-number-input");
const probeIpInput = document.getElementById("probe-ip-input");
const probeModeHintNode = document.getElementById("probe-mode-hint");
const liveRunPresetSelect = document.getElementById("live-run-preset-select");
const liveRunIdNode = document.getElementById("live-run-id");
const liveRunStatusNode = document.getElementById("live-run-status");
const liveRunPresetNode = document.getElementById("live-run-preset");
const liveSourceFrameSizeNode = document.getElementById("live-source-frame-size");
const liveDisplayFrameSizeNode = document.getElementById("live-display-frame-size");
const livePreviewRateNode = document.getElementById("live-preview-rate");
const liveMeasurementRateNode = document.getElementById("live-measurement-rate");
const stopLivePreviewStreamButton = document.getElementById("stop-live-preview-stream-btn");
const startLivePreviewStreamButton = document.getElementById("start-live-preview-stream-btn");
const saveLiveDefinitionButton = document.getElementById("save-live-definition-btn");
const startLiveRunButton = document.getElementById("start-live-run-btn");
const stopLiveRunButton = document.getElementById("stop-live-run-btn");
const drawAnalysisRoiButton = document.getElementById("draw-analysis-roi-btn");
const recomputeDefinitionButton = document.getElementById("recompute-definition-btn");
const livePreviewStageNode = document.getElementById("live-preview-stage");
const livePointPromptNode = document.getElementById("live-point-prompt");
const livePointPromptTitleNode = document.getElementById("live-point-prompt-title");
const livePointPromptBodyNode = document.getElementById("live-point-prompt-body");
const livePreviewImageNode = document.getElementById("live-preview-img");
const livePreviewOverlayNode = document.getElementById("live-preview-overlay");
const livePreviewEmptyNode = document.getElementById("live-preview-empty");
const liveProcessPanelNode = document.getElementById("live-process-panel");
const liveProcessStatusPillNode = document.getElementById("live-process-status-pill");
const liveProcessChartLayersNode = document.getElementById("live-process-chart-layers");
const liveProcessChartEmptyNode = document.getElementById("live-process-chart-empty");
const liveProcessStatusCardNode = document.getElementById("live-process-status-card");
const liveProcessChannelStatusNode = document.getElementById("live-process-channel-status");
const liveProcessPointCountNode = document.getElementById("live-process-point-count");
const liveProcessOutlierCountNode = document.getElementById("live-process-outlier-count");
const liveProcessAsValueNode = document.getElementById("live-process-as-value");
const liveProcessAfTanValueNode = document.getElementById("live-process-af-tan-value");
const livePointPickerStatusNode = document.getElementById("live-point-picker-status");
const liveRunMessageNode = document.getElementById("live-run-message");
const homeCurrentTaskTitleNode = document.getElementById("home-current-task-title");
const homeCurrentTaskCopyNode = document.getElementById("home-current-task-copy");
const homeCurrentTaskStepNode = document.getElementById("home-current-task-step");
const homeAbStateNode = document.getElementById("home-ab-state");
const livePointASummaryInput = document.getElementById("live-point-a-summary");
const livePointBSummaryInput = document.getElementById("live-point-b-summary");
const homeCompletionDockNode = document.getElementById("home-completion-dock");
const homeCompactResultSessionIdNode = document.getElementById("home-result-session-id");
const homeCompactResultStateNode = document.getElementById("home-result-session-state");
const homeCompactResultSummaryNode = document.getElementById("home-result-summary");
const homeJourneyStepNodes = Array.from(document.querySelectorAll("[data-home-step-index]"));
const liveAnalysisRoiXInput = document.getElementById("live-analysis-roi-x");
const liveAnalysisRoiYInput = document.getElementById("live-analysis-roi-y");
const liveAnalysisRoiWidthInput = document.getElementById("live-analysis-roi-width");
const liveAnalysisRoiHeightInput = document.getElementById("live-analysis-roi-height");
const liveAnalysisRoiAngleInput = document.getElementById("live-analysis-roi-angle");
const livePointAXInput = document.getElementById("live-point-a-x");
const livePointAYInput = document.getElementById("live-point-a-y");
const livePointBXInput = document.getElementById("live-point-b-x");
const livePointBYInput = document.getElementById("live-point-b-y");
const liveForegroundPolaritySelect = document.getElementById("live-foreground-polarity");
const liveThresholdModeSelect = document.getElementById("live-threshold-mode");
const liveDirectionProjectionModeSelect = document.getElementById("live-direction-projection-mode");
const liveTargetGeometryModeSelect = document.getElementById("live-target-geometry-mode");
const liveSideGuardRatioInput = document.getElementById("live-side-guard-ratio");
const liveEnvelopeMinSupportInput = document.getElementById("live-envelope-min-support");
const liveEnvelopeQuantileInput = document.getElementById("live-envelope-quantile");
const liveIgnoreInternalTextureInput = document.getElementById("live-ignore-internal-texture");
const liveMinTargetAreaInput = document.getElementById("live-min-target-area");
const liveSensitivityInput = document.getElementById("live-sensitivity");
const liveCurrentTemperatureInput = document.getElementById("live-current-temperature");
const tempSerialPortSelect = document.getElementById("temp-serial-port-select");
const refreshTempSerialPortsButton = document.getElementById("refresh-temp-serial-ports-btn");
const applyTempSerialPortButton = document.getElementById("apply-temp-serial-port-btn");
const tempSerialPortStatusNode = document.getElementById("temp-serial-port-status");
const liveTargetTemperatureInput = document.getElementById("live-target-temperature");
const liveControlModeSelect = document.getElementById("live-control-mode");
const liveCompletionModeSelect = document.getElementById("live-completion-mode");
const liveOutputPowerInput = document.getElementById("live-output-power-percent");
const confirmTargetTemperatureButton = document.getElementById("confirm-target-temperature-btn");
const liveConfirmedTargetTemperatureInput = document.getElementById("live-confirmed-target-temperature");
const fixtureVideoSwitchNode = document.getElementById("fixture-video-switch");
const fixtureVideoSelectNode = document.getElementById("fixture-video-select");
const refreshPrecheckButton = document.getElementById("refresh-precheck-btn");
const precheckStatusNode = document.getElementById("precheck-status");
const precheckItemsNode = document.getElementById("precheck-items");
const cameraProbeResultNode = document.getElementById("camera-probe-result");
const detailAf95Node = document.getElementById("detail-af95");
const detailPointCountNode = document.getElementById("detail-point-count");
const detailCurveLayersNode = document.getElementById("detail-curve-layers");
const detailCurveNode = document.getElementById("detail-curve-line");
const detailKeyFramesNode = document.getElementById("detail-key-frames");
const sessionWorkspaceLinkNode = document.getElementById("session-workspace-link");
const workspaceShellNode = document.getElementById("workspace-shell");
const workspaceSessionIdNode = document.getElementById("workspace-session-id");
const workspaceSessionStateNode = document.getElementById("workspace-session-state");
const workspaceSideStateNode = document.getElementById("workspace-side-state");
const workspaceAf95Node = document.getElementById("workspace-af95");
const workspacePointCountNode = document.getElementById("workspace-point-count");
const workspaceSourceNode = document.getElementById("workspace-source");
const workspaceDetailPointCountNode = document.getElementById("workspace-detail-point-count");
const workspaceKeyframeCountNode = document.getElementById("workspace-keyframe-count");
const workspaceCurveLayersNode = document.getElementById("workspace-curve-layers");
const workspaceCurveNode = document.getElementById("workspace-curve-line");
const workspaceCurvePointsNode = document.getElementById("workspace-curve-points");
const workspaceCurveEmptyNode = document.getElementById("workspace-curve-empty");
const workspaceAf95LineNode = document.getElementById("workspace-af95-line");
const workspaceAfasRunButton = document.getElementById("workspace-afas-run-btn");
const workspaceAfasExportPngButton = document.getElementById("workspace-afas-export-png-btn");
const workspaceAfasExportXlsxButton = document.getElementById("workspace-afas-export-xlsx-btn");
const workspaceAfasChannelNode = document.getElementById("workspace-afas-channel");
const workspaceAfasSavgolWindowNode = document.getElementById("workspace-afas-savgol-window");
const workspaceAfasSavgolPolyorderNode = document.getElementById("workspace-afas-savgol-polyorder");
const workspaceAfasLowStartNode = document.getElementById("workspace-afas-low-start");
const workspaceAfasLowEndNode = document.getElementById("workspace-afas-low-end");
const workspaceAfasHighStartNode = document.getElementById("workspace-afas-high-start");
const workspaceAfasHighEndNode = document.getElementById("workspace-afas-high-end");
const workspaceAfasTangentOffsetNode = document.getElementById("workspace-afas-tangent-offset");
const workspaceAfasStatusNode = document.getElementById("workspace-afas-status");
const workspaceAfasSurfaceNode = document.getElementById("workspace-afas-surface");
const workspaceAfasEmptyStateNode = document.getElementById("workspace-afas-empty-state");
const workspaceAfasChannelNoteNode = document.getElementById("workspace-afas-channel-note");
const workspaceAfasOverviewChartNode = document.getElementById("workspace-afas-overview-chart");
const workspaceAfasOverviewSeriesNode = document.getElementById("workspace-afas-overview-series");
const workspaceAfasOverviewSummaryNode = document.getElementById("workspace-afas-overview-summary");
const workspaceAfasAnalysisChartNode = document.getElementById("workspace-afas-analysis-chart");
const workspaceAfasAnalysisLayersNode = document.getElementById("workspace-afas-analysis-layers");
const workspaceAfasAnalysisEmptyNode = document.getElementById("workspace-afas-analysis-empty");
const workspaceAfasResultStatusNode = document.getElementById("workspace-afas-result-status");
const workspaceAfasResultAsNode = document.getElementById("workspace-afas-result-as");
const workspaceAfasResultAfTanNode = document.getElementById("workspace-afas-result-af-tan");
const workspaceAfasResultDeltaNode = document.getElementById("workspace-afas-result-delta");
const workspaceAfasResultMaxSlopeNode = document.getElementById("workspace-afas-result-max-slope");
const workspaceAfasParameterSummaryNode = document.getElementById("workspace-afas-parameter-summary");
const workspaceAfasResultHintNode = document.getElementById("workspace-afas-result-hint");
const workspaceAfasOutlierCountNode = document.getElementById("workspace-afas-outlier-count");
const workspaceAfasSmoothedCountNode = document.getElementById("workspace-afas-smoothed-count");
const workspaceAfasWarningListNode = document.getElementById("workspace-afas-warning-list");
const workspaceKeyframesNode = document.getElementById("workspace-keyframes");
const workspaceCurrentStageNode = document.getElementById("workspace-current-stage");
const workspaceStageDescriptionNode = document.getElementById("workspace-stage-description");
const workspaceDetailStatusNode = document.getElementById("workspace-detail-status");
const workspaceRefreshButton = document.getElementById("workspace-refresh-btn");
const workspaceImportAfasDatasetFileInput = document.getElementById("workspace-import-afas-dataset-file");
const workspaceImportAfasDatasetButton = document.getElementById("workspace-import-afas-dataset-btn");
const workspaceImportAfasDatasetHintNode = document.getElementById("workspace-import-afas-dataset-hint");
const workspaceActivePointNode = document.getElementById("workspace-active-point");
const workspaceActiveLabelNode = document.getElementById("workspace-active-label");
const workspaceActiveTimestampNode = document.getElementById("workspace-active-timestamp");
const workspaceActiveCelsiusNode = document.getElementById("workspace-active-celsius");
const workspaceActiveMetricRawNode = document.getElementById("workspace-active-metric-raw");
const workspaceActiveMetricNormNode = document.getElementById("workspace-active-metric-norm");
const workspaceActiveFeaturePointNode = document.getElementById("workspace-active-feature-point");
const workspaceActiveQualityNode = document.getElementById("workspace-active-quality");
const workspaceAdjustmentSourceNode = document.getElementById("workspace-adjustment-source");
const workspaceAdjustmentPointCountNode = document.getElementById("workspace-adjustment-point-count");
const workspaceAdjustmentKeyframeCountNode = document.getElementById("workspace-adjustment-keyframe-count");
const workspaceAdjustmentAf95Node = document.getElementById("workspace-adjustment-af95");
const workspaceAdjustmentStageNode = document.getElementById("workspace-adjustment-stage");
const workspaceAdjustmentDetailStatusNode = document.getElementById("workspace-adjustment-detail-status");
const workspaceAdjustmentActiveSummaryNode = document.getElementById("workspace-adjustment-active-summary");
const workspaceAdjustmentBasisCopyNode = document.getElementById("workspace-adjustment-basis-copy");
const workspaceAdjustmentRoiNode = document.getElementById("workspace-adjustment-roi");
const workspaceAdjustmentFeaturePointNode = document.getElementById("workspace-adjustment-feature-point");
const workspaceAdjustmentBaselineNode = document.getElementById("workspace-adjustment-baseline");
const workspaceAdjustmentQualityNode = document.getElementById("workspace-adjustment-quality");
const workspaceAdjustmentThresholdNode = document.getElementById("workspace-adjustment-threshold");
const workspaceAdjustmentComponentAreaNode = document.getElementById("workspace-adjustment-component-area");
const workspaceAdjustmentMetricNormNode = document.getElementById("workspace-adjustment-metric-norm");
const workspaceAdjustmentContextStageNode = document.getElementById("workspace-adjustment-context-stage");
const adjustmentAutoAf95Node = document.getElementById("adjustment-auto-af95");
const adjustmentAutoSourceNode = document.getElementById("adjustment-auto-source");
const adjustmentAutoPointCountNode = document.getElementById("adjustment-auto-point-count");
const adjustmentLatestAf95Node = document.getElementById("adjustment-latest-af95");
const adjustmentLatestSourceNode = document.getElementById("adjustment-latest-source");
const adjustmentLatestVersionNode = document.getElementById("adjustment-latest-version");
const adjustmentLatestNoteNode = document.getElementById("adjustment-latest-note");
const adjustmentDraftAf95Node = document.getElementById("adjustment-draft-af95");
const adjustmentDraftReasonNode = document.getElementById("adjustment-draft-reason");
const adjustmentSaveDraftButton = document.getElementById("adjustment-save-draft-btn");
const adjustmentApplyButton = document.getElementById("adjustment-apply-btn");
const adjustmentDraftStatusNode = document.getElementById("adjustment-draft-status");
const adjustmentHasDraftNode = document.getElementById("adjustment-has-draft");
const adjustmentAppliedCountNode = document.getElementById("adjustment-applied-count");
const adjustmentIsManualNode = document.getElementById("adjustment-is-manual");
const adjustmentDraftUpdatedNode = document.getElementById("adjustment-draft-updated");
const adjustmentVersionHistoryNode = document.getElementById("adjustment-version-history");
const workspaceStepNodes = Array.from(document.querySelectorAll("[data-testid='workspace-step']"));
const languageToggleButtons = Array.from(document.querySelectorAll("[data-language-toggle]"));

const WORKSPACE_STEPS = ["设备就绪", "预览冻结", "ROI 定义", "A/B 确认", "温控设置确认", "开始测试", "打开分析", "AFAS 出点 / 导出"];
const WORKSPACE_STEP_LABELS_EN = [
  "Device Ready",
  "Freeze Preview",
  "Define ROI",
  "Confirm A/B",
  "Confirm Temperature Settings",
  "Start Run",
  "Open Analysis",
  "AFAS Answer / Export",
];
const TARGET_TEMPERATURE_MIN_C = -50;
const TARGET_TEMPERATURE_MAX_C = 50;
const LIVE_TRACKING_POLL_MS = 200;
const LIVE_PREVIEW_STATUS_POLL_MS = 1000;
const NEW_LIVE_TEST_CONFIRM_TIMEOUT_MS = 12000;
const LANGUAGE_STORAGE_KEY = "yyt1771-ui-language";
let workspaceDetailState = null;
let workspaceSummaryState = null;
let workspaceStageState = null;
let workspaceActiveSelectionState = null;
let workspaceAdjustmentState = null;
let workspaceAfasState = null;
let workspaceAfasRefreshTimer = null;
let workspaceAfasRequestToken = 0;
let homeCompactResultState = null;
let precheckState = null;
let recentSessionsState = [];
let probeControlsDirty = false;
let fixtureVideoSwitchBusy = false;
let tempSerialPortBusy = false;
let tempSerialPortBackend = "";
let newLiveTestConfirmationTimer = null;
let newLiveTestPendingConfirmation = false;
let currentLocale = "zh";
const liveRunState = {
  runId: "",
  detail: null,
  previewObjectUrl: "",
  previewStreamUrl: "",
  previewStreamActive: false,
  previewStreamRecovering: false,
  previewFrozenAvailable: false,
  lastPreviewFrameId: null,
  previewSize: null,
  previewSourceSize: null,
  measurementSourceSize: null,
  roiConfirmed: false,
  confirmedRoiSignature: "",
  activeTool: "",
  overlayDrag: null,
  definitionDirty: false,
  setupRecomputeTimer: null,
  setupRecomputeInFlight: false,
  setupRecomputeDetail: "",
  setupRecomputeActiveToken: 0,
  directionProjectionOverlay: null,
  confirmedTemperatureSettings: null,
  currentTemperatureCelsius: null,
  currentTemperatureTimer: null,
  previewStatusTimer: null,
  liveTrackingTimer: null,
  latestTelemetry: null,
  liveProcessResult: null,
  resolvedDirectionProjectionMode: "max_chord",
};
const LIVE_SETUP_RUN_STORAGE_KEY = "yyt1771-live-setup-run-id";
const AFAS_OVERVIEW_CHANNEL_COLORS = ["#8B9DC3", "#C4A4A4", "#A4B8A4", "#D4B896", "#B4A4C4", "#9CB8C4"];
const AFAS_CHART_THEME = {
  primary: "#8B9DC3",
  highlight: "#E8E4E0",
  rose: "#C4A4A4",
  green: "#A4B8A4",
  apricot: "#D4B896",
  purple: "#B4A4C4",
  cyan: "#9CB8C4",
  grid: "rgba(255,255,255,0.06)",
  axis: "#8A8A9A",
  labelBackground: "rgba(26, 26, 46, 0.85)",
  labelBorder: "rgba(255,255,255,0.15)",
  markerStroke: "rgba(255,255,255,0.6)",
};

const WORKSPACE_SOURCE_LABELS = {
  imported_afas_dataset: {
    zh: "导入数据集",
    en: "Imported Dataset",
  },
  live_run: {
    zh: "实时测试",
    en: "Live Run",
  },
  replay: {
    zh: "回放",
    en: "Replay",
  },
  mock: {
    zh: "模拟",
    en: "Mock",
  },
  summary: {
    zh: "摘要",
    en: "Summary",
  },
  "n/a": {
    zh: "n/a",
    en: "n/a",
  },
};
const TRANSLATIONS = {
  zh: {
    "common.yes": "是",
    "common.no": "否",
    "common.na": "N/A",
    "common.not_applicable": "n/a",
    "status.ok": "正常",
    "status.pass": "通过",
    "status.warn": "警告",
    "status.fail": "失败",
    "state.completed": "已完成",
    "state.failed": "失败",
    "state.aborted": "已中止",
    "state.running": "运行中",
    "state.invalidated": "已失效",
    "state.stopping": "停止中",
    "state.run_ready": "可启动",
    "state.empty": "空",
    "state.missing": "缺失",
    "state.available": "可用",
    "state.ok": "正常",
    "state.pass": "通过",
    "state.warn": "警告",
    "state.fail": "失败",
    "state.loading": "加载中",
    "state.unknown": "未知",
    "state.not_ready": "未就绪",
    "home.meta.source_frame": "源帧",
    "home.meta.display_frame": "显示帧",
    "home.actions.new_test": "新测试",
    "home.actions.confirm_new_test": "确认新测试",
    "home.messages.new_test_confirm": "再次点击“确认新测试”才会清空当前结果并开始下一次测试。",
    "home.sections.temperature.completion_mode": "结束方式",
    "home.sections.temperature.serial_port": "温控串口",
    "home.options.serial_loading": "正在读取串口...",
    "home.options.completion_target_reached": "到目标温度自动停止",
    "home.options.completion_manual_stop_only": "只手动停止",
    "home.actions.refresh_serial_ports": "刷新串口",
    "home.actions.apply_serial_port": "使用并读取",
    "workspace.step_status.todo": "待处理",
    "workspace.step_status.active": "进行中",
    "workspace.step_status.done": "已完成",
    "workspace.step_status.error": "异常",
    "workspace.step_status.upcoming": "未开始",
  },
  en: {
    "common.language_label": "Language",
    "common.language_group": "Interface language",
    "common.na": "N/A",
    "common.not_applicable": "n/a",
    "common.loading": "Loading...",
    "common.yes": "Yes",
    "common.no": "No",
    "common.open_workspace": "Open Analysis Studio",
    "status.ok": "ok",
    "status.pass": "pass",
    "status.warn": "warn",
    "status.fail": "fail",
    "state.completed": "completed",
    "state.failed": "failed",
    "state.aborted": "aborted",
    "state.running": "running",
    "state.invalidated": "invalidated",
    "state.stopping": "stopping",
    "state.run_ready": "run_ready",
    "state.empty": "empty",
    "state.missing": "missing",
    "state.available": "available",
    "state.ok": "ok",
    "state.pass": "pass",
    "state.warn": "warn",
    "state.fail": "fail",
    "state.loading": "loading",
    "state.unknown": "unknown",
    "state.not_ready": "not ready",
    "home.meta.title": "Live Test",
    "home.hero.title": "Launch & Control Cockpit",
    "home.hero.subtitle":
      "Bring live setup back to the home path. Freeze the frame, define the rotated ROI, confirm detection, and open Analysis Studio only when a session is worth reading.",
    "home.hero.journey_tag": "Operator Journey",
    "home.journey.step1.title": "Device Ready",
    "home.journey.step1.copy": "Confirm health, profile, and the live shell are ready.",
    "home.journey.step2.title": "Freeze Preview",
    "home.journey.step2.copy": "Freeze the live preview before setup work begins.",
    "home.journey.step3.title": "Define ROI",
    "home.journey.step3.copy": "ROI stays primary and angle remains operator-visible.",
    "home.journey.step4.title": "Confirm A/B",
    "home.journey.step4.copy": "Review the latest automatic A/B result and recompute from a fresh frame when needed.",
    "home.journey.step5.title": "Confirm Temperature Settings",
    "home.journey.step5.copy": "Confirm target temperature, manual mode, and power as one setup bundle.",
    "home.journey.step6.title": "Start Run",
    "home.journey.step6.copy": "Start the live run here and hand off later.",
    "home.status.system": "System",
    "home.status.ready_label": "Device Status",
    "home.status.profile": "Profile",
    "home.status.mode": "Mode",
    "home.status.current_temp": "Current Temp (°C)",
    "home.status.current_temp_compact": "Current Temp (°C)",
    "home.fixture_video.label": "Fixture Video",
    "home.main_stage.tag": "Main Stage",
    "home.main_stage.title": "Live Preview",
    "home.main_stage.copy": "Keep preview dominant. Freeze first, then define ROI and confirm ROI-local A/B only when needed.",
    "home.main_stage.preview_alt": "Live preview frame",
    "home.main_stage.overlay_label": "Live preview overlay",
    "home.actions.freeze": "Freeze",
    "home.actions.unfreeze": "Unfreeze",
    "home.actions.enter_analysis": "Enter Analysis",
    "home.actions.save_data": "Save Data",
    "home.actions.new_test": "New Test",
    "home.actions.confirm_new_test": "Confirm New Test",
    "home.messages.new_test_confirm": "Click Confirm New Test again to clear the current result and start the next test.",
    "home.actions.target_confirmed": "Settings Confirmed",
    "home.actions.recompute_ab": "Recompute A/B",
    "home.foldouts.metrics": "Open Live Metrics and Preset",
    "home.foldouts.more_tools": "More Tools and Diagnostics",
    "home.foldouts.runtime_details": "Open Runtime Details and Probe Controls",
    "home.foldouts.recent_sessions": "Open Recent Sessions and Result Payload",
    "home.meta.run_id": "Run ID",
    "home.meta.status": "Status",
    "home.meta.preset": "Preset",
    "home.meta.source_frame": "Source Frame",
    "home.meta.display_frame": "Display Frame",
    "home.meta.preview_fps": "Preview FPS",
    "home.meta.measurement_hz": "Measurement Hz",
    "home.meta.setup_type": "Live Setup Type",
    "home.options.balloon": "Balloon",
    "home.options.guidewire": "Guidewire",
    "home.current_task.tag": "Current Task",
    "home.sections.roi.title_minimal": "ROI Selection",
    "home.sections.roi.title": "ROI Definition",
    "home.actions.draw_roi": "Draw ROI",
    "home.sections.roi.copy": "ROI stays primary. Keep angle visible and move full geometry fields into an on-demand review layer.",
    "home.sections.roi.angle": "ROI Angle",
    "home.foldouts.roi_geometry": "Show ROI Geometry Fields",
    "home.foldouts.roi_parameters": "Show ROI Parameters",
    "home.sections.roi.center_x": "Center X",
    "home.sections.roi.center_y": "Center Y",
    "home.sections.roi.width": "Width",
    "home.sections.roi.height": "Height",
    "home.sections.detection.title": "Detection",
    "home.sections.detection.copy": "Keep sensitivity as the only default-visible control.",
    "home.sections.detection.sensitivity": "Sensitivity",
    "home.sections.detection.sensitivity_note":
      "Higher values make weak connections merge into one target more easily; lower values separate object and blank more strictly.",
    "home.foldouts.detection": "Open Detection Tuning",
    "home.sections.detection.foreground": "Foreground",
    "home.options.dark_on_light": "Dark on Light",
    "home.options.light_on_dark": "Light on Dark",
    "home.sections.detection.threshold": "Threshold Mode",
    "home.options.threshold_adaptive": "Adaptive",
    "home.options.threshold_binary": "Binary",
    "home.options.threshold_otsu": "Otsu",
    "home.sections.detection.projection_mode": "Point Mode",
    "home.options.projection_max_chord": "Max Chord",
    "home.options.projection_envelope_max_width": "Envelope Width",
    "home.options.projection_mask_projection": "Mask Projection",
    "home.sections.detection.target_geometry": "Target Type",
    "home.options.geometry_single_component": "Single Body",
    "home.options.geometry_line_bundle": "Line Bundle",
    "home.options.geometry_mesh_lattice": "Mesh / Lattice",
    "home.sections.detection.side_guard": "Side Guard Ratio",
    "home.sections.detection.envelope_min_support": "Envelope Min Support (px)",
    "home.sections.detection.envelope_quantile": "Envelope Quantile Trim",
    "home.sections.detection.min_area": "Min Area",
    "home.sections.detection.ignore_texture": "Ignore Texture",
    "home.sections.ab.title": "A/B Status",
    "home.sections.ab.point_a_summary": "Point A",
    "home.sections.ab.point_b_summary": "Point B",
    "home.sections.temperature.title": "Temperature",
    "home.sections.temperature.title_minimal": "Temperature Setup",
    "home.sections.temperature.copy": "Confirm the temperature bundle here before handing off to runtime.",
    "home.sections.temperature.target": "Target Temp (°C)",
    "home.sections.temperature.control_mode": "Control Mode",
    "home.sections.temperature.completion_mode": "Stop Mode",
    "home.sections.temperature.serial_port": "Temp Serial Port",
    "home.sections.temperature.power": "Temperature Power (%)",
    "home.sections.temperature.controller_confirm": "Confirm Settings",
    "home.sections.temperature.controller_target": "Confirmed Settings",
    "home.options.serial_loading": "Loading serial ports...",
    "home.options.control_mode_manual": "Manual",
    "home.options.completion_target_reached": "Auto at Target",
    "home.options.completion_manual_stop_only": "Manual Stop Only",
    "home.actions.refresh_serial_ports": "Refresh Ports",
    "home.actions.apply_serial_port": "Use and Read",
    "home.actions.confirm_target": "Confirm Temperature Settings",
    "home.actions.save_definition": "Save Definition",
    "home.actions.start_live_run": "Start Live Run",
    "home.actions.stop_live_run": "Stop Live Run",
    "home.foldouts.diagnostics": "Open Diagnostics and Offline Tools",
    "home.diagnostics.tag": "Ops & Diagnostics",
    "home.diagnostics.tag_minimal": "Diagnostics",
    "home.diagnostics.title": "System Precheck / Probe Camera",
    "home.diagnostics.title_minimal": "Device Check / Probe Camera",
    "home.diagnostics.copy": "Use this to validate the environment or probe hardware, not during the main operator path.",
    "home.actions.refresh_precheck": "Refresh Precheck",
    "home.actions.probe_camera": "Probe Camera",
    "home.diagnostics.probe_mode": "Probe Mode",
    "home.options.protocol_any": "Protocol Any",
    "home.options.pinned_device": "Pinned Device",
    "home.diagnostics.allowed_models": "Allowed Models",
    "home.placeholders.allowed_models": "MV-CU060-10GM, OTHER-MODEL",
    "home.diagnostics.serial_number": "Serial Number",
    "home.placeholders.optional": "Optional",
    "home.diagnostics.ip": "IP",
    "home.diagnostics.local_hint":
      "For Mac local bring-up, copy <code>configs/dev_lab.local.example.yaml</code> to <code>configs/dev_lab.local.yaml</code>, then use precheck to confirm <code>camera_sdk_runtime</code> before the first real probe.",
    "home.diagnostics.overall": "Overall",
    "home.foldouts.precheck_output": "Show Precheck Items and Probe Output",
    "home.engineering.tag": "Engineering Mode",
    "home.engineering.title": "Session Launcher / Recent Sessions",
    "home.engineering.copy": "Keep mock and replay launchers close for QA and development without letting them dominate the cockpit.",
    "home.actions.run_mock": "Run Mock Session",
    "home.actions.run_replay": "Run Replay Session",
    "home.import.label": "Import AFAS Dataset",
    "home.import.hint":
      "Accepts the canonical <code>afas_dataset.json</code>. Reusing the artifact exported by an existing session is recommended.",
    "home.actions.import_afas_dataset": "Import AFAS Dataset",
    "home.compact_result.tag": "Compact Result",
    "home.compact_result.title": "Latest Session Entry",
    "home.compact_result.copy": "Keep a single workspace handoff here, not a mini analysis page.",
    "home.actions.open_workspace": "Open Analysis Studio",
    "home.compact_result.session_id": "Session ID",
    "home.compact_result.state": "State",
    "home.compact_result.af95": "Af95",
    "home.foldouts.payload_snapshot": "Show Payload and Replay Snapshot",
    "home.compact_result.point_count": "Point Count",
    "home.compact_result.replay_curve_label": "Replay curve",
    "workspace.meta.title": "Analysis Studio",
    "workspace.hero.title": "Analysis Studio",
    "workspace.hero.subtitle":
      "Review replay, run AFAS postprocessing, and make adjustment decisions for one session at a time.",
    "workspace.session.tag": "Session",
    "workspace.session.subtitle": "Keep session context lightweight and let AFAS analysis, parameters, and export own the main surface.",
    "workspace.sidebar.data_entry_tag": "Data Entry",
    "workspace.sidebar.data_entry_title": "Data and Session",
    "workspace.sidebar.data_entry_copy":
      "Go back home when you need to switch samples or import new data. This page stays focused on analysis work.",
    "workspace.sidebar.analysis_setup_title": "Analysis Setup",
    "workspace.sidebar.analysis_setup_copy":
      "Keep channel and parameter controls on the left so the right side can stay focused on charts and results.",
    "workspace.import.hint": "Choose an afas_dataset.json file to open a new analysis workspace directly.",
    "workspace.rail.tag": "Journey Rail",
    "workspace.rail.title": "Process",
    "workspace.rail.copy": "Keep the rail light and sticky so replay review, AFAS, and decision-making stay central.",
    "workspace.replay.tag": "Replay",
    "workspace.replay.context_title": "Replay Context",
    "workspace.replay.context_copy":
      "Replay stays as session context. Expand it when needed instead of letting it dominate the first screen.",
    "workspace.replay.title": "Replay Curve",
    "workspace.replay.copy": "Metric raw vs. temperature from the replay detail artifact.",
    "workspace.replay.axis_x": "X: Temperature (°C)",
    "workspace.replay.axis_y": "Y: metric_raw",
    "workspace.replay.curve_label": "Workspace replay curve",
    "workspace.afas.title": "AFAS Analysis",
    "workspace.afas.copy": "Keep the first screen on replay outcome, AFAS answer quality, and immediate export decisions.",
    "workspace.afas.copy_aligned":
      "Borrow AFAS's analysis organization and move process-heavy session information behind explicit reveals.",
    "workspace.afas.surface_copy":
      "Keep the right side focused on the overview chart, the single-channel tangent chart, and the final result card.",
    "workspace.afas.empty_title": "This session does not have AFAS data yet",
    "workspace.afas.empty_copy":
      "Session context is still available here, but the AFAS overview, tangent chart, and exports cannot be shown.",
    "workspace.actions.run_afas": "Run AFAS Analysis",
    "workspace.actions.export_png": "Export PNG",
    "workspace.actions.export_excel": "Export Excel",
    "workspace.actions.import_data": "Import Data",
    "workspace.afas.channel_section": "Channel Selection",
    "workspace.afas.channel": "Channel",
    "workspace.afas.channel_copy": "Choose the channel you want to judge when multiple channels are available.",
    "workspace.afas.quickbar_copy": "Keep the selected channel visible and tuck deeper tuning away until needed.",
    "workspace.afas.parameters_title": "Analysis Parameters",
    "workspace.afas.parameters_copy": "Keep preprocessing and tangent controls grouped with AFAS semantics.",
    "workspace.afas.preprocessing_group": "Data Preprocessing",
    "workspace.afas.tangent_group": "Tangent Adjustment",
    "workspace.afas.result_card.title": "AFAS Result Card",
    "workspace.afas.result_card.copy": "Answer first: what changed, is it readable, and what settings produced the answer.",
    "workspace.afas.result_status": "Result Status",
    "workspace.afas.max_slope_temp": "Max Slope Temp",
    "workspace.foldouts.afas_warnings": "Show Warnings and Preprocessing Notes",
    "workspace.afas.outlier_count": "Outlier Count",
    "workspace.afas.smoothed_points": "Smoothed Points",
    "workspace.afas.overview": "Overview",
    "workspace.afas.overview_chart_label": "AFAS overview chart",
    "workspace.afas.selected_channel": "Selected Channel",
    "workspace.afas.analysis_chart_label": "AFAS tangent analysis chart",
    "workspace.afas.analysis_empty": "The single-channel tangent chart will appear here once analysis loads.",
    "workspace.foldouts.afas_parameters": "Tune AFAS Parameters",
    "workspace.foldouts.keyframes": "Show Key Frames",
    "workspace.foldouts.adjustment_stack": "Open Adjustment, Versions, and Traceability",
    "workspace.foldouts.engineering_workspace": "Open Process and Engineering Context",
    "workspace.afas.savgol_window": "Savgol Window",
    "workspace.afas.savgol_polyorder": "Savgol Polyorder",
    "workspace.afas.low_range_start": "Low Range Start (°C)",
    "workspace.afas.low_range_end": "Low Range End (°C)",
    "workspace.afas.high_range_start": "High Range Start (°C)",
    "workspace.afas.high_range_end": "High Range End (°C)",
    "workspace.afas.tangent_offset": "Tangent Offset",
    "workspace.second_screen.tag": "Second Screen",
    "workspace.keyframes.title": "Key Frames",
    "workspace.keyframes.copy": "Show the first, middle, and last replay frames when detail is available.",
    "workspace.adjustment.title": "Adjustment MVP",
    "workspace.adjustment.copy": "Review automatic results, prepare a draft override, and apply the latest Af95 adjustment.",
    "workspace.adjustment.auto_result": "Automatic Result",
    "workspace.adjustment.auto_af95": "Auto Af95",
    "workspace.adjustment.auto_source": "Auto Result Source",
    "workspace.adjustment.auto_point_count": "Auto Point Count",
    "workspace.adjustment.latest_result": "Latest Result",
    "workspace.adjustment.latest_af95": "Latest Af95",
    "workspace.adjustment.latest_source": "Latest Result Source",
    "workspace.adjustment.latest_version": "Latest Version",
    "workspace.adjustment.draft_editor": "Draft Editor",
    "workspace.adjustment.draft_af95": "Draft Af95",
    "workspace.placeholders.af95_override": "Enter Af95 override",
    "workspace.adjustment.reason": "Reason",
    "workspace.placeholders.adjustment_reason": "Describe why this adjustment is needed",
    "workspace.actions.save_draft": "Save Draft",
    "workspace.actions.apply_adjustment": "Apply Adjustment",
    "workspace.adjustment.notes": "Adjustment Notes",
    "workspace.adjustment.notes_item_1": "Current MVP only supports Af95 result-level adjustment.",
    "workspace.adjustment.notes_item_2": "Auto result, latest result, draft, and applied versions remain separate.",
    "workspace.adjustment.notes_item_3": "As / Af / Af-tan and parameter-level tuning remain reserved for later phases.",
    "workspace.foldouts.traceability": "Open Traceability Context",
    "workspace.adjustment.automatic_basis": "Automatic Basis",
    "workspace.common.source": "Source",
    "workspace.common.point_count": "Point Count",
    "workspace.common.keyframe_count": "Key Frame Count",
    "workspace.common.current_stage": "Current Stage",
    "workspace.common.detail_available": "Detail Available",
    "workspace.common.active_selection": "Active Selection",
    "workspace.adjustment.context": "Extraction & Analysis Context",
    "workspace.foldouts.future_controls": "Preview Future Adjustment Controls",
    "workspace.adjustment.future_controls": "Future Adjustment Controls",
    "workspace.adjustment.image_processing": "Image Processing Parameters",
    "workspace.adjustment.threshold": "Threshold",
    "workspace.adjustment.baseline_lock": "Baseline Lock",
    "workspace.adjustment.curve_analysis": "Curve Analysis Parameters",
    "workspace.adjustment.smoothing": "Smoothing",
    "workspace.adjustment.normalization_basis": "Normalization Basis",
    "workspace.adjustment.af95_threshold": "Af95 Threshold",
    "workspace.adjustment.result_override": "Result Override",
    "workspace.actions.save_adjustment": "Save Adjustment",
    "workspace.summary.current_stage": "Current Stage",
    "workspace.summary.session_state": "Session State",
    "workspace.summary.mode_source": "Mode / Source",
    "workspace.summary.session_summary": "Session Summary",
    "workspace.summary.session_id": "Session ID",
    "workspace.summary.detail_status": "Detail Status",
    "workspace.summary.detail_points": "Detail Points",
    "workspace.summary.keyframes": "Key Frames",
    "workspace.summary.active_selection": "Active Selection",
    "workspace.summary.label": "Label",
    "workspace.summary.timestamp": "Timestamp",
    "workspace.summary.celsius": "Celsius",
    "workspace.foldouts.selection_diagnostics": "Open Selection Diagnostics",
    "workspace.summary.adjustment_status": "Adjustment Status",
    "workspace.summary.has_draft": "Has Draft",
    "workspace.summary.applied_count": "Applied Count",
    "workspace.summary.manual_override": "Manual Override",
    "workspace.summary.draft_updated": "Draft Updated",
    "workspace.summary.version_history": "Version History",
    "workspace.foldouts.version_timeline": "Browse Version Timeline",
    "workspace.summary.quick_actions": "Quick Actions",
    "workspace.summary.quick_actions_copy": "Return and refresh stay in the top strip. This area keeps engineering-only links.",
    "workspace.actions.return_home": "Return Home",
    "workspace.actions.refresh_workspace": "Refresh Workspace",
    "workspace.foldouts.engineering_links": "Open Engineering Links",
    "workspace.actions.open_summary_api": "Open Summary API",
    "workspace.actions.open_detail_api": "Open Detail API",
    "workspace.step_status.todo": "todo",
    "workspace.step_status.active": "active",
    "workspace.step_status.done": "done",
    "workspace.step_status.error": "error",
    "workspace.step_status.upcoming": "upcoming",
  },
};

const ANALYSIS_ROI_FLOAT_EPSILON = 0.5;
const METRIC_BOX_POINT_FLOAT_EPSILON = 2.0;

function getSavedLocale() {
  try {
    return window.localStorage.getItem(LANGUAGE_STORAGE_KEY) || "";
  } catch (error) {
    return "";
  }
}

function saveLocale(locale) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, locale);
  } catch (error) {
    return;
  }
}

function formatTemplate(template, variables = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => String(variables[key] ?? ""));
}

function t(key, variables = {}, fallback = key) {
  const localeMap = TRANSLATIONS[currentLocale] || {};
  const template = localeMap[key] ?? fallback;
  return formatTemplate(template, variables);
}

function localizeStateLabel(state) {
  const normalized = String(state || "").trim();
  return t(`state.${normalized}`, {}, normalized || t("common.na", {}, "N/A"));
}

function restoreLocalizedNode(node, datasetKey, fallbackGetter, setter) {
  if (!node.dataset[datasetKey]) {
    node.dataset[datasetKey] = fallbackGetter();
  }
  if (currentLocale === "zh") {
    setter(node.dataset[datasetKey]);
    return;
  }
  const key =
    datasetKey === "i18nDefaultText"
      ? node.dataset.i18n
      : datasetKey === "i18nDefaultHtml"
        ? node.dataset.i18nHtml
        : datasetKey === "i18nDefaultPlaceholder"
          ? node.dataset.i18nPlaceholder
          : datasetKey === "i18nDefaultAriaLabel"
            ? node.dataset.i18nAriaLabel
            : node.dataset.i18nAlt;
  const translated = key ? TRANSLATIONS.en?.[key] : null;
  setter(translated || node.dataset[datasetKey]);
}

function applyStaticTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    restoreLocalizedNode(
      node,
      "i18nDefaultText",
      () => node.textContent || "",
      (value) => {
        node.textContent = value;
      },
    );
  });
  document.querySelectorAll("[data-i18n-html]").forEach((node) => {
    restoreLocalizedNode(
      node,
      "i18nDefaultHtml",
      () => node.innerHTML,
      (value) => {
        node.innerHTML = value;
      },
    );
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    restoreLocalizedNode(
      node,
      "i18nDefaultPlaceholder",
      () => node.getAttribute("placeholder") || "",
      (value) => {
        node.setAttribute("placeholder", value);
      },
    );
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    restoreLocalizedNode(
      node,
      "i18nDefaultAriaLabel",
      () => node.getAttribute("aria-label") || "",
      (value) => {
        node.setAttribute("aria-label", value);
      },
    );
  });
  document.querySelectorAll("[data-i18n-alt]").forEach((node) => {
    restoreLocalizedNode(
      node,
      "i18nDefaultAlt",
      () => node.getAttribute("alt") || "",
      (value) => {
        node.setAttribute("alt", value);
      },
    );
  });
  workspaceStepNodes.forEach((node, index) => {
    const labelNode = node.querySelector(".workspace-step-label");
    if (!labelNode) {
      return;
    }
    labelNode.textContent = currentLocale === "en" ? WORKSPACE_STEP_LABELS_EN[index] || labelNode.textContent : WORKSPACE_STEPS[index];
  });
}

function syncLanguageToggleUi() {
  languageToggleButtons.forEach((button) => {
    const isActive = button.dataset.languageToggle === currentLocale;
    button.classList.toggle("language-switch-btn--active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function refreshLocalizedRuntimeUi() {
  resetNewLiveTestConfirmation();
  applyStaticTranslations();
  syncCameraProbeControls();
  if (healthStatusNode?.dataset.healthState) {
    updateHealthStatusBadge(healthStatusNode.dataset.healthState);
  }
  renderHomeCompactResultSummary(homeCompactResultState);
  renderHomeTaskState();
  if (liveRunState.detail) {
    renderLiveRunDetail(liveRunState.detail);
  }
  if (precheckState) {
    renderPrecheck(precheckState);
  }
  renderRecentSessions(recentSessionsState);
  if (workspaceSummaryState) {
    renderWorkspaceSummary(workspaceSummaryState);
  }
  if (workspaceDetailState) {
    renderWorkspaceDetail(workspaceDetailState);
  }
  if (workspaceActiveSelectionState) {
    renderActiveSelection(workspaceActiveSelectionState);
  }
  renderWorkspaceAfas(workspaceAfasState);
  if (workspaceAdjustmentState) {
    renderAdjustmentState(workspaceAdjustmentState);
  }
}

function setLocale(locale) {
  currentLocale = locale === "en" ? "en" : "zh";
  document.body.dataset.locale = currentLocale;
  document.documentElement.lang = currentLocale === "en" ? "en" : "zh-CN";
  saveLocale(currentLocale);
  syncLanguageToggleUi();
  refreshLocalizedRuntimeUi();
}

function workspaceUrl(sessionId) {
  return `/workspace/${encodeURIComponent(sessionId)}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSessionResult(payload) {
  if (!sessionResultNode) {
    return;
  }
  sessionResultNode.textContent = JSON.stringify(payload, null, 2);
  renderHomeCompactResultSummary(payload);
}

function clearHomeResultDisplays() {
  if (sessionResultNode) {
    sessionResultNode.textContent = currentLocale === "en" ? "No session has run yet." : "尚未运行任何会话。";
  }
  if (detailAf95Node) {
    detailAf95Node.textContent = "n/a";
  }
  if (detailPointCountNode) {
    detailPointCountNode.textContent = "0";
  }
  renderCurve([]);
  renderKeyFrames([]);
  renderHomeCompactResultSummary(null);
}

function renderCameraProbeResult(payload) {
  if (!cameraProbeResultNode) {
    return;
  }
  cameraProbeResultNode.textContent = JSON.stringify(payload, null, 2);
}

function parseCommaSeparatedList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function syncCameraProbeControls() {
  if (!probeModeSelect || !probeModeHintNode) {
    return;
  }

  if (probeModeSelect.value === "pinned") {
    probeModeHintNode.textContent =
      currentLocale === "en"
        ? "Pinned Device requires allowed models plus serial number or IP before probing."
        : "固定设备模式要求在探测前提供允许型号，以及序列号或 IP。";
    return;
  }

  probeModeHintNode.textContent =
    currentLocale === "en"
      ? "Protocol Any allows the first discovered device when serial number and IP are empty. You can still fill identity fields for a directed hit."
      : "当序列号和 IP 为空时，协议任意模式会接受首个发现的设备；你仍然可以填写身份字段来做定向探测。";
}

function syncCameraProbeDefaults(profileName) {
  if (probeControlsDirty || !probeModeSelect) {
    return;
  }
  probeModeSelect.value = profileName === "prod_win" ? "pinned" : "protocol_any";
  syncCameraProbeControls();
}

function buildCameraProbeRequest() {
  if (!probeControlsDirty) {
    return null;
  }

  return {
    probe_mode: probeModeSelect ? probeModeSelect.value : "protocol_any",
    allowed_models: probeAllowedModelsInput ? parseCommaSeparatedList(probeAllowedModelsInput.value) : [],
    serial_number: probeSerialNumberInput ? probeSerialNumberInput.value.trim() : "",
    ip: probeIpInput ? probeIpInput.value.trim() : "",
  };
}

function buildRealOfflineLiveProbeRequest() {
  if (!hasLocallyCompleteDefinition()) {
    return null;
  }
  return buildLiveDefinitionPayload({ coordinateSpace: "source" });
}

function hasLiveSetupUi() {
  return Boolean(liveRunIdNode && liveRunStatusNode && liveRunPresetNode);
}

function parseErrorDetail(payload, fallback) {
  if (!payload) {
    return fallback;
  }
  if (typeof payload.detail === "string" && payload.detail) {
    return payload.detail;
  }
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return fallback;
}

function normalizeTemperatureValue(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.round(numeric * 10) / 10 : null;
}

function normalizePowerPercent(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.round(numeric * 10) / 10 : null;
}

function getCurrentTargetTemperature() {
  return normalizeTemperatureValue(getNumericInputValue(liveTargetTemperatureInput, 25));
}

function getCurrentControlMode() {
  return String(liveControlModeSelect?.value || "manual");
}

function getCurrentCompletionMode() {
  return String(liveCompletionModeSelect?.value || "target_reached");
}

function getCurrentOutputPowerPercent() {
  return normalizePowerPercent(getNumericInputValue(liveOutputPowerInput, 100));
}

function getCurrentTemperatureSettings() {
  return {
    target_temperature_celsius: getCurrentTargetTemperature(),
    control_mode: getCurrentControlMode(),
    completion_mode: getCurrentCompletionMode(),
    output_power_percent: getCurrentOutputPowerPercent(),
  };
}

function formatCompletionMode(value) {
  const completionMode = String(value || "target_reached");
  if (completionMode === "manual_stop_only") {
    return currentLocale === "en" ? "manual stop only" : "只手动停止";
  }
  return currentLocale === "en" ? "auto at target" : "到目标温度自动停止";
}

function formatConfirmedTemperatureSettings(settings) {
  if (!settings) {
    return "--";
  }
  const confirmedTarget = normalizeTemperatureValue(
    settings.confirmed_target_temperature_celsius ?? settings.target_temperature_celsius,
  );
  const powerPercent = normalizePowerPercent(settings.output_power_percent);
  const controlMode = String(settings.control_mode || "manual");
  const completionMode = formatCompletionMode(settings.completion_mode);
  if (confirmedTarget === null || powerPercent === null) {
    return "--";
  }
  return currentLocale === "en"
    ? `${confirmedTarget.toFixed(1)} °C / ${controlMode} / ${completionMode} / ${powerPercent.toFixed(0)}%`
    : `${confirmedTarget.toFixed(1)} °C / 手动方式 / ${completionMode} / ${powerPercent.toFixed(0)}%`;
}

function isTemperatureSettingsConfirmed() {
  const confirmed = liveRunState.confirmedTemperatureSettings;
  const current = getCurrentTemperatureSettings();
  if (!confirmed || current.target_temperature_celsius === null || current.output_power_percent === null) {
    return false;
  }
  return (
    Math.abs(current.target_temperature_celsius - Number(confirmed.target_temperature_celsius)) < 0.05 &&
    Math.abs(current.output_power_percent - Number(confirmed.output_power_percent)) < 0.05 &&
    String(current.control_mode) === String(confirmed.control_mode) &&
    String(current.completion_mode) === String(confirmed.completion_mode || "target_reached")
  );
}

function getNumericInputValue(node, fallback = 0) {
  if (!node || node.value === "") {
    return fallback;
  }
  const value = Number(node.value);
  return Number.isFinite(value) ? value : fallback;
}

function getOptionalNumericInputValue(node) {
  if (!node) {
    return null;
  }
  const raw = String(node.value || "").trim();
  if (!raw) {
    return null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function setInputIfBlank(node, value) {
  if (node && !node.value) {
    node.value = String(value);
  }
}

function setLiveRunMessage(message, tone = "neutral") {
  if (!liveRunMessageNode) {
    return;
  }
  liveRunMessageNode.textContent = message;
  liveRunMessageNode.className = `live-message live-message--${tone}`;
}

function syncHomeJourneySteps(activeStep, stepStatus) {
  if (!homeJourneyStepNodes.length) {
    return;
  }
  homeJourneyStepNodes.forEach((node) => {
    const index = Number(node.dataset.homeStepIndex || "0");
    const status = stepStatus[index - 1] || (index === activeStep ? "active" : index < activeStep ? "done" : "upcoming");
    node.classList.remove("journey-step--done", "journey-step--active", "journey-step--upcoming", "journey-step--error");
    node.classList.add(`journey-step--${status}`);
  });
}

function renderHomeCompactResultSummary(payload) {
  if (!homeCompactResultSessionIdNode || !homeCompactResultStateNode || !homeCompactResultSummaryNode) {
    return;
  }
  homeCompactResultState = payload;
  const hasTarget = Boolean(payload && payload.session_id);
  const sessionId = hasTarget ? payload.session_id : currentLocale === "en" ? "No target" : "暂无目标";
  const sessionStateRaw = hasTarget && (payload.state || payload.status) ? payload.state || payload.status : "empty";
  const sessionState = localizeStateLabel(sessionStateRaw);
  homeCompactResultSessionIdNode.textContent = sessionId;
  homeCompactResultStateNode.textContent = sessionState;
  homeCompactResultSummaryNode.textContent =
    !hasTarget
      ? ""
      : currentLocale === "en"
        ? `Analysis will open session ${sessionId}.`
        : `进入分析时将打开会话 ${sessionId}。`;
  if (homeCompletionDockNode) {
    homeCompletionDockNode.hidden = !hasTarget;
  }
  if (sessionWorkspaceLinkNode) {
    if (hasTarget) {
      sessionWorkspaceLinkNode.href = workspaceUrl(sessionId);
      sessionWorkspaceLinkNode.classList.remove("workspace-link--hidden");
    } else {
      sessionWorkspaceLinkNode.href = "#";
      sessionWorkspaceLinkNode.classList.add("workspace-link--hidden");
    }
  }
  if (saveSessionDataButton) {
    saveSessionDataButton.disabled = !hasTarget;
  }
}

function renderHomeTaskState() {
  if (!hasLiveSetupUi()) {
    return;
  }
  const status = liveRunState.detail ? String(liveRunState.detail.status || "") : "";
  const previewState = getPreviewStatePayload();
  const hasRun = Boolean(liveRunState.runId);
  const hasPreview = Boolean(liveRunState.previewSize);
  const roiReady = hasValidAnalysisRoi() && liveRunState.roiConfirmed;
  const hasPoints = hasValidPointInputs();
  const temperatureSettingsConfirmed = isTemperatureSettingsConfirmed();
  const isRunActive = ["running", "invalidated", "stopping"].includes(status);
  const isTerminal = ["completed", "failed", "aborted"].includes(status);
  const abReviewNeeded = Boolean(
    liveRunState.setupRecomputeInFlight ||
      (roiReady && !hasPoints),
  );

  let activeStep = 1;
  let title = currentLocale === "en" ? "Prepare the device and live shell" : "准备设备与 live shell";
  let copy =
    currentLocale === "en"
      ? "Check shell status first, then let the preview warm up before touching ROI or runtime controls."
      : "先确认 shell 状态，再让预览稳定，然后再去操作 ROI 或 runtime 控件。";
  let stepBadge = currentLocale === "en" ? "Step 1 of 6" : "第 1 / 6 步";
  const stepStatus = ["active", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming"];

  if (!hasRun || !liveRunState.detail) {
    activeStep = 1;
  } else if (previewState.stream_active || !hasPreview) {
    activeStep = 2;
    title = currentLocale === "en" ? "Freeze the preview" : "冻结预览";
    copy =
      currentLocale === "en"
        ? "Capture a still frame first. ROI editing and A/B status stay locked until the preview is frozen."
        : "先抓取静帧。冻结前，ROI 编辑和 A/B 状态都保持锁定。";
  } else if (!roiReady) {
    activeStep = 3;
    title = currentLocale === "en" ? "Define the ROI" : "定义 ROI";
    copy =
      currentLocale === "en"
        ? "Set the rotated ROI first. Everything else in setup keys off this geometry."
        : "先定义旋转 ROI，setup 里的其他项都以这块几何为准。";
  } else if (abReviewNeeded) {
    activeStep = 4;
    title = currentLocale === "en" ? "Review ROI-local A/B" : "复核 ROI 内 A/B";
    copy = liveRunState.setupRecomputeInFlight
      ? currentLocale === "en"
        ? "A/B anchors are being recalculated from a newly captured frame. Wait for the latest result before starting."
        : "系统正在基于新抓取的画面重算 A/B 锚点，等待最新结果后再继续。"
      : currentLocale === "en"
        ? "A/B stays diagnostic-only. Review the latest automatic anchors and recompute if needed."
        : "A/B 只作为诊断结果出现。请复核当前自动结果，必要时重新计算。";
  } else if (!temperatureSettingsConfirmed) {
    activeStep = 5;
    title = currentLocale === "en" ? "Confirm temperature settings" : "确认温控设置";
    copy =
      currentLocale === "en"
        ? "Confirm target temperature, manual mode, and output power as one bundled step."
        : "把目标温度、手动方式和温度功率作为一个设置包整体确认。";
  } else {
    activeStep = 6;
    title = isRunActive
      ? currentLocale === "en"
        ? "Live run in progress"
        : "实时测试进行中"
      : isTerminal
        ? currentLocale === "en"
          ? "Open Analysis Studio when ready"
          : "可在准备好后打开分析工作台"
        : currentLocale === "en"
          ? "Start the live run"
          : "开始实时测试";
    copy = isRunActive
      ? currentLocale === "en"
        ? "The run is active. Keep the cockpit focused on control and move to Analysis Studio only when the session is worth reading."
        : "当前 run 正在进行。让 cockpit 保持在控制与监看职责上，只在 session 值得阅读时进入分析工作台。"
      : isTerminal
        ? currentLocale === "en"
        ? "The run has completed or stopped. Save the result or enter analysis."
        : "当前 run 已完成或已停止。现在可以保存数据或进入分析。"
        : currentLocale === "en"
            ? "The live setup is ready. Start the run once ROI, A/B, and the bundled temperature settings are confirmed."
            : "live setup 已准备好。确认 ROI、A/B 和温控设置包后即可开始测试。";
  }

  stepBadge = currentLocale === "en" ? `Step ${activeStep} of 6` : `第 ${activeStep} / 6 步`;
  for (let index = 0; index < stepStatus.length; index += 1) {
    if (index + 1 < activeStep) {
      stepStatus[index] = "done";
    } else if (index + 1 === activeStep) {
      stepStatus[index] = status === "failed" || status === "aborted" ? "error" : "active";
    } else {
      stepStatus[index] = "upcoming";
    }
  }
  if (isTerminal && status === "completed") {
    for (let index = 0; index < stepStatus.length; index += 1) {
      stepStatus[index] = "done";
    }
  }

  if (homeCurrentTaskTitleNode) {
    homeCurrentTaskTitleNode.textContent = title;
  }
  if (homeCurrentTaskCopyNode) {
    homeCurrentTaskCopyNode.textContent = copy;
  }
  if (homeCurrentTaskStepNode) {
    homeCurrentTaskStepNode.textContent = stepBadge;
    homeCurrentTaskStepNode.className = `status-pill ${
      isRunActive || status === "completed" ? "status-ok" : stepStatus[activeStep - 1] === "error" ? "status-fail" : "status-pending"
    }`;
  }
  if (homeAbStateNode) {
    homeAbStateNode.textContent = !roiReady
      ? currentLocale === "en"
        ? "Waiting for ROI"
        : "等待 ROI"
      : liveRunState.setupRecomputeInFlight
        ? currentLocale === "en"
          ? "Recomputing"
          : "正在重算"
        : hasPoints
          ? currentLocale === "en"
            ? "Auto-detected"
            : "已自动检测"
          : currentLocale === "en"
            ? "Needs review"
            : "需要复核";
    homeAbStateNode.className = `status-pill ${
      !roiReady ? "status-pending" : abReviewNeeded ? "status-warn" : "status-ok"
    }`;
  }
  document.body.dataset.homeStep = String(activeStep);
  syncHomeJourneySteps(activeStep, stepStatus);
}

function renderCurrentTemperature(payload) {
  if (!liveCurrentTemperatureInput) {
    return;
  }
  const celsius = normalizeTemperatureValue(payload?.temperature_celsius);
  liveRunState.currentTemperatureCelsius = celsius;
  liveCurrentTemperatureInput.value = celsius === null ? "--" : celsius.toFixed(1);
}

function setTempSerialPortStatus(message, tone = "info") {
  if (!tempSerialPortStatusNode) {
    return;
  }
  tempSerialPortStatusNode.textContent = message;
  tempSerialPortStatusNode.className = `operator-inline-note temp-serial-status temp-serial-status--${tone}`;
}

function renderTempSerialPorts(payload) {
  if (!tempSerialPortSelect) {
    return;
  }
  const backend = String(payload?.backend || "");
  tempSerialPortBackend = backend;
  const ports = Array.isArray(payload?.ports) ? payload.ports : [];
  const selectedPort = String(payload?.selected_port || payload?.configured_port || "");
  const portOptions = ports.map((port) => {
    const device = String(port.device || "");
    const description = String(port.description || "");
    const label = description && description !== device ? `${device} - ${description}` : device;
    return { device, label };
  });
  if (selectedPort && !portOptions.some((port) => port.device === selectedPort)) {
    portOptions.unshift({
      device: selectedPort,
      label: currentLocale === "en" ? `${selectedPort} (configured, not visible)` : `${selectedPort}（当前配置，未发现）`,
    });
  }
  if (!portOptions.length) {
    tempSerialPortSelect.innerHTML = `<option value="">${
      currentLocale === "en" ? "No serial ports found" : "未发现串口"
    }</option>`;
    tempSerialPortSelect.value = "";
  } else {
    tempSerialPortSelect.innerHTML = portOptions
      .map((port) => `<option value="${escapeHtml(port.device)}">${escapeHtml(port.label)}</option>`)
      .join("");
    tempSerialPortSelect.value = selectedPort && portOptions.some((port) => port.device === selectedPort)
      ? selectedPort
      : portOptions[0].device;
  }
  if (backend !== "lu92xx_modbus_rtu") {
    setTempSerialPortStatus(
      currentLocale === "en"
        ? `Serial selection is inactive for ${backend || "missing"} temperature backend.`
        : `当前温控后端为 ${backend || "missing"}，不启用硬件串口选择。`,
      "warning",
    );
  } else if (!portOptions.length) {
    setTempSerialPortStatus(currentLocale === "en" ? "No visible serial ports." : "未发现可见串口。", "warning");
  } else {
    setTempSerialPortStatus(
      currentLocale === "en" ? "Choose a port, then use and read temperature." : "请选择串口，然后点击“使用并读取”。",
      "info",
    );
  }
  updateLiveRunControls();
}

async function refreshTempSerialPorts({ silent = false } = {}) {
  if (!tempSerialPortSelect) {
    return null;
  }
  if (refreshTempSerialPortsButton) {
    refreshTempSerialPortsButton.disabled = true;
  }
  try {
    const response = await fetch("/api/system/temp/serial-ports");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Serial port discovery failed: ${response.status}`));
    }
    renderTempSerialPorts(payload);
    return payload;
  } catch (error) {
    if (!silent) {
      setTempSerialPortStatus(String(error), "error");
    }
    return null;
  } finally {
    if (refreshTempSerialPortsButton) {
      refreshTempSerialPortsButton.disabled = false;
    }
    updateLiveRunControls();
  }
}

async function applyTempSerialPort() {
  if (!tempSerialPortSelect || tempSerialPortBusy) {
    return;
  }
  const selectedPort = String(tempSerialPortSelect.value || "").trim();
  if (!selectedPort) {
    setTempSerialPortStatus(currentLocale === "en" ? "Choose a serial port first." : "请先选择一个串口。", "error");
    return;
  }
  tempSerialPortBusy = true;
  stopCurrentTemperaturePolling();
  setTempSerialPortStatus(
    currentLocale === "en" ? `Using ${selectedPort} and reading temperature...` : `正在使用 ${selectedPort} 并读取温度...`,
    "info",
  );
  updateLiveRunControls();
  try {
    const response = await fetch("/api/system/temp/serial-port", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ port: selectedPort }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Serial port selection failed: ${response.status}`));
    }
    renderCurrentTemperature(payload);
    liveRunState.confirmedTemperatureSettings = null;
    refreshTemperatureSettingsSummary();
    setTempSerialPortStatus(
      currentLocale === "en"
        ? `Using ${payload.selected_port}; current temperature ${Number(payload.temperature_celsius).toFixed(1)} °C.`
        : `已使用 ${payload.selected_port}；当前温度 ${Number(payload.temperature_celsius).toFixed(1)} °C。`,
      "success",
    );
  } catch (error) {
    setTempSerialPortStatus(String(error), "error");
  } finally {
    tempSerialPortBusy = false;
    startCurrentTemperaturePolling();
    updateLiveRunControls();
  }
}

function formatPointSummary(point) {
  if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
    return "--";
  }
  return `(${Math.round(Number(point.x))}, ${Math.round(Number(point.y))})`;
}

function updatePointSummaries() {
  if (livePointASummaryInput) {
    livePointASummaryInput.value = hasValidPointInputs() ? formatPointSummary(getCurrentPointA()) : "--";
  }
  if (livePointBSummaryInput) {
    livePointBSummaryInput.value = hasValidPointInputs() ? formatPointSummary(getCurrentPointB()) : "--";
  }
}

function updateHealthStatusBadge(status) {
  if (!healthStatusNode) {
    return;
  }
  const normalized = String(status || "unknown");
  healthStatusNode.dataset.healthState = normalized;
  const isReady = normalized === "ok";
  healthStatusNode.textContent = isReady ? (currentLocale === "en" ? "Ready" : "已就绪") : currentLocale === "en" ? "Not Ready" : "未就绪";
  healthStatusNode.className = `status-pill ${isReady ? "status-ok" : normalized === "warn" ? "status-warn" : "status-fail"}`;
}

async function refreshCurrentTemperature({ silent = false } = {}) {
  if (!hasLiveSetupUi()) {
    return null;
  }
  const response = await fetch("/api/system/temp/current");
  const payload = await response.json();
  if (!response.ok) {
    renderCurrentTemperature(null);
    if (!silent) {
      throw new Error(parseErrorDetail(payload, `Current temperature request failed: ${response.status}`));
    }
    return null;
  }
  renderCurrentTemperature(payload);
  updateLiveRunControls();
  return payload;
}

function stopCurrentTemperaturePolling() {
  if (liveRunState.currentTemperatureTimer) {
    window.clearInterval(liveRunState.currentTemperatureTimer);
    liveRunState.currentTemperatureTimer = null;
  }
}

function startCurrentTemperaturePolling() {
  if (!hasLiveSetupUi() || liveRunState.currentTemperatureTimer) {
    return;
  }
  const poll = () => {
    void refreshCurrentTemperature({ silent: true });
  };
  poll();
  liveRunState.currentTemperatureTimer = window.setInterval(poll, 1000);
}

function refreshTemperatureSettingsSummary() {
  if (liveConfirmedTargetTemperatureInput) {
    liveConfirmedTargetTemperatureInput.value = formatConfirmedTemperatureSettings(liveRunState.confirmedTemperatureSettings);
  }
}

function clearTemperatureSettingsConfirmation() {
  refreshTemperatureSettingsSummary();
  updateLiveRunControls();
}

async function confirmTargetTemperature() {
  const currentSettings = getCurrentTemperatureSettings();
  if (
    currentSettings.target_temperature_celsius === null ||
    currentSettings.target_temperature_celsius < TARGET_TEMPERATURE_MIN_C ||
    currentSettings.target_temperature_celsius > TARGET_TEMPERATURE_MAX_C
  ) {
    setLiveRunMessage(
      `Target temperature must stay within ${TARGET_TEMPERATURE_MIN_C} to ${TARGET_TEMPERATURE_MAX_C} °C before confirmation.`,
      "error",
    );
    return;
  }
  if (currentSettings.output_power_percent === null || currentSettings.output_power_percent < 0 || currentSettings.output_power_percent > 100) {
    setLiveRunMessage(
      currentLocale === "en"
        ? "Temperature power must stay within 0 to 100% before confirmation."
        : "确认前，温度功率必须保持在 0 到 100% 之间。",
      "error",
    );
    return;
  }
  if (confirmTargetTemperatureButton) {
    confirmTargetTemperatureButton.disabled = true;
  }
  stopCurrentTemperaturePolling();
  setLiveRunMessage(
    currentLocale === "en"
      ? "Confirming bundled temperature settings on the controller..."
      : "正在确认温控设置包...",
    "info",
  );
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/temperature-settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentSettings),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Temperature settings update failed: ${response.status}`));
    }
    renderLiveRunDetail(payload);
    const confirmedSettings = payload?.temperature_settings || null;
    liveRunState.confirmedTemperatureSettings = confirmedSettings;
    if (liveTargetTemperatureInput && confirmedSettings?.confirmed_target_temperature_celsius != null) {
      liveTargetTemperatureInput.value = Number(confirmedSettings.confirmed_target_temperature_celsius).toFixed(1);
    }
    if (liveControlModeSelect && confirmedSettings?.control_mode) {
      liveControlModeSelect.value = String(confirmedSettings.control_mode);
    }
    if (liveCompletionModeSelect && confirmedSettings?.completion_mode) {
      liveCompletionModeSelect.value = String(confirmedSettings.completion_mode);
    }
    if (liveOutputPowerInput && confirmedSettings?.output_power_percent != null) {
      liveOutputPowerInput.value = String(Number(confirmedSettings.output_power_percent));
    }
    refreshTemperatureSettingsSummary();
    setLiveRunMessage(
      currentLocale === "en"
        ? `Temperature settings confirmed: ${formatConfirmedTemperatureSettings(confirmedSettings)}.`
        : `温控设置已确认：${formatConfirmedTemperatureSettings(confirmedSettings)}。`,
      "success",
    );
  } catch (error) {
    refreshTemperatureSettingsSummary();
    setLiveRunMessage(String(error), "error");
  } finally {
    startCurrentTemperaturePolling();
    if (confirmTargetTemperatureButton) {
      confirmTargetTemperatureButton.disabled = false;
    }
    updateLiveRunControls();
  }
}

function getStoredLiveSetupRunId() {
  try {
    return window.sessionStorage.getItem(LIVE_SETUP_RUN_STORAGE_KEY) || "";
  } catch (error) {
    return "";
  }
}

function storeLiveSetupRunId(runId) {
  try {
    if (runId) {
      window.sessionStorage.setItem(LIVE_SETUP_RUN_STORAGE_KEY, runId);
    } else {
      window.sessionStorage.removeItem(LIVE_SETUP_RUN_STORAGE_KEY);
    }
  } catch (error) {
    return;
  }
}

function setLivePointPickerStatus(message) {
  if (!livePointPickerStatusNode) {
    return;
  }
  livePointPickerStatusNode.textContent = message;
}

function setSetupRecomputeState({ inFlight = false, detail = "" } = {}) {
  liveRunState.setupRecomputeInFlight = inFlight;
  liveRunState.setupRecomputeDetail = detail;
  renderLiveToolPrompt();
  updateLiveRunControls();
}

function formatRateValue(value, unit, { target = null } = {}) {
  if (!Number.isFinite(value) || Number(value) <= 0) {
    if (Number.isFinite(target) && Number(target) > 0) {
      return currentLocale === "en"
        ? `target ${Number(target).toFixed(1)} ${unit}`
        : `目标 ${Number(target).toFixed(1)} ${unit}`;
    }
    return t("common.not_applicable", {}, "n/a");
  }
  return `${Number(value).toFixed(1)} ${unit}`;
}

function formatFrameSize(size) {
  if (!size || !Number.isFinite(size.width) || !Number.isFinite(size.height) || size.width <= 0 || size.height <= 0) {
    return t("common.not_applicable", {}, "n/a");
  }
  return `${Math.round(size.width)}×${Math.round(size.height)}`;
}

function readMeasurementSourceSize(payload) {
  const roi = payload?.measurement_profile?.acquisition_roi;
  if (!roi || !Number.isFinite(roi.width) || !Number.isFinite(roi.height) || roi.width <= 0 || roi.height <= 0) {
    return null;
  }
  return { width: Number(roi.width), height: Number(roi.height) };
}

function renderLivePreviewMeta() {
  const rates = liveRunState.detail?.rates || {};
  const displaySize =
    liveRunState.previewSize ||
    (livePreviewImageNode && livePreviewImageNode.naturalWidth && livePreviewImageNode.naturalHeight
      ? { width: livePreviewImageNode.naturalWidth, height: livePreviewImageNode.naturalHeight }
      : null);
  const sourceSize = liveRunState.previewSourceSize || liveRunState.measurementSourceSize;
  if (liveSourceFrameSizeNode) {
    liveSourceFrameSizeNode.textContent = formatFrameSize(sourceSize);
  }
  if (liveDisplayFrameSizeNode) {
    liveDisplayFrameSizeNode.textContent = formatFrameSize(displaySize);
  }
  if (livePreviewRateNode) {
    livePreviewRateNode.textContent = formatRateValue(rates.preview_display_fps, "fps", {
      target: rates.preview_target_fps,
    });
  }
  if (liveMeasurementRateNode) {
    liveMeasurementRateNode.textContent = formatRateValue(rates.measurement_sample_hz, "Hz", {
      target: rates.measurement_target_hz,
    });
  }
}

function stopLivePreviewStatusPolling() {
  if (liveRunState.previewStatusTimer) {
    window.clearTimeout(liveRunState.previewStatusTimer);
    liveRunState.previewStatusTimer = null;
  }
}

function startLivePreviewStatusPolling() {
  stopLivePreviewStatusPolling();
  const tick = async () => {
    if (!liveRunState.runId || !liveRunState.previewStreamActive) {
      liveRunState.previewStatusTimer = null;
      return;
    }
    try {
      await refreshLiveRunDetail(liveRunState.runId);
    } catch (error) {
      // Status polling is only used to keep preview metadata current.
    }
    if (liveRunState.runId && liveRunState.previewStreamActive) {
      liveRunState.previewStatusTimer = window.setTimeout(tick, LIVE_PREVIEW_STATUS_POLL_MS);
    } else {
      liveRunState.previewStatusTimer = null;
    }
  };
  liveRunState.previewStatusTimer = window.setTimeout(tick, LIVE_PREVIEW_STATUS_POLL_MS);
}

function revokeLivePreviewUrl() {
  if (liveRunState.previewObjectUrl) {
    URL.revokeObjectURL(liveRunState.previewObjectUrl);
    liveRunState.previewObjectUrl = "";
  }
}

function clearLivePreviewImage() {
  stopLivePreviewStatusPolling();
  revokeLivePreviewUrl();
  liveRunState.previewSize = null;
  liveRunState.previewSourceSize = null;
  liveRunState.previewFrozenAvailable = false;
  liveRunState.lastPreviewFrameId = null;
  if (livePreviewImageNode) {
    livePreviewImageNode.removeAttribute("src");
    livePreviewImageNode.hidden = true;
  }
  if (livePreviewStageNode) {
    livePreviewStageNode.hidden = true;
  }
  if (livePreviewOverlayNode) {
    livePreviewOverlayNode.hidden = true;
    livePreviewOverlayNode.innerHTML = "";
    livePreviewOverlayNode.removeAttribute("viewBox");
  }
  if (livePreviewEmptyNode) {
    livePreviewEmptyNode.hidden = false;
  }
  renderLivePreviewMeta();
  setSetupRecomputeState({ inFlight: false, detail: "" });
}

function showLivePreviewStage() {
  if (livePreviewStageNode) {
    livePreviewStageNode.hidden = false;
  }
  if (livePreviewImageNode) {
    livePreviewImageNode.hidden = false;
  }
  if (livePreviewOverlayNode) {
    livePreviewOverlayNode.hidden = false;
  }
  if (livePreviewEmptyNode) {
    livePreviewEmptyNode.hidden = true;
  }
  renderLivePreviewMeta();
  renderLiveToolPrompt();
}

function updateLiveToolButtons() {
  if (drawAnalysisRoiButton) {
    drawAnalysisRoiButton.classList.toggle("button-active", liveRunState.activeTool === "draw-roi");
  }
}

function renderLiveToolPrompt() {
  if (!livePointPromptNode || !livePointPromptTitleNode || !livePointPromptBodyNode) {
    return;
  }
  if (liveRunState.setupRecomputeInFlight) {
    livePointPromptNode.hidden = false;
    livePointPromptTitleNode.textContent = currentLocale === "en" ? "Recomputing Locked Points" : "正在重算锁定点";
    livePointPromptBodyNode.textContent =
      liveRunState.setupRecomputeDetail ||
      (currentLocale === "en"
        ? "Capturing a new frame before recalculating ROI-local A/B. Wait for the points to update or an error message to appear."
        : "正在先抓取新画面，再重算 ROI 内 A/B。请等待点位更新，或查看是否出现错误提示。");
    return;
  }
  livePointPromptNode.hidden = true;
}

function getPreviewStatePayload() {
  const detailPreview = liveRunState.detail && liveRunState.detail.preview ? liveRunState.detail.preview : null;
  const streamActive = Boolean(liveRunState.previewStreamActive || (detailPreview && detailPreview.stream_active));
  return {
    stream_active: streamActive,
    frozen_frame_available: !streamActive && Boolean(
      liveRunState.previewFrozenAvailable || (detailPreview && detailPreview.frozen_frame_available),
    ),
    last_frame_id:
      liveRunState.lastPreviewFrameId != null
        ? liveRunState.lastPreviewFrameId
        : detailPreview
          ? detailPreview.last_frame_id
          : null,
  };
}

function getCurrentRoiBox() {
  return {
    center_x: getNumericInputValue(liveAnalysisRoiXInput),
    center_y: getNumericInputValue(liveAnalysisRoiYInput),
    width: getNumericInputValue(liveAnalysisRoiWidthInput),
    height: getNumericInputValue(liveAnalysisRoiHeightInput),
    angle_deg: getNumericInputValue(liveAnalysisRoiAngleInput, 0),
  };
}

function boundingRectForMetricBox(box) {
  const corners = metricBoxCorners(box);
  const xs = corners.map((point) => point.x);
  const ys = corners.map((point) => point.y);
  const minX = Math.floor(Math.min(...xs));
  const maxX = Math.ceil(Math.max(...xs));
  const minY = Math.floor(Math.min(...ys));
  const maxY = Math.ceil(Math.max(...ys));
  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

function axisAlignedRectForRoiBox(box) {
  const width = Math.max(1, Math.round(Number(box.width)));
  const height = Math.max(1, Math.round(Number(box.height)));
  return {
    x: Math.floor(Number(box.center_x) - width / 2),
    y: Math.floor(Number(box.center_y) - height / 2),
    width,
    height,
  };
}

function metricBoxForDirectionalRoi(box) {
  return {
    center_x: Math.round(Number(box.center_x)),
    center_y: Math.round(Number(box.center_y)),
    width: Math.max(1, Math.round(Number(box.width))),
    height: Math.max(1, Math.round(Number(box.height))),
    angle_deg: Number(Number(box.angle_deg || 0).toFixed(1)),
  };
}

function metricBoxFromRect(rect) {
  return {
    center_x: Math.round(Number(rect.x) + Number(rect.width) / 2),
    center_y: Math.round(Number(rect.y) + Number(rect.height) / 2),
    width: Math.max(1, Math.round(Number(rect.width))),
    height: Math.max(1, Math.round(Number(rect.height))),
    angle_deg: 0,
  };
}

function getCurrentAnalysisRoi() {
  if (!hasValidAnalysisRoi()) {
    return {
      x: getNumericInputValue(liveAnalysisRoiXInput),
      y: getNumericInputValue(liveAnalysisRoiYInput),
      width: getNumericInputValue(liveAnalysisRoiWidthInput),
      height: getNumericInputValue(liveAnalysisRoiHeightInput),
    };
  }
  return boundingRectForMetricBox(getCurrentRoiBox());
}

function getCurrentMetricBox() {
  return metricBoxForDirectionalRoi(getCurrentRoiBox());
}

function getCurrentPointA() {
  return {
    x: getNumericInputValue(livePointAXInput),
    y: getNumericInputValue(livePointAYInput),
  };
}

function getCurrentPointB() {
  return {
    x: getNumericInputValue(livePointBXInput),
    y: getNumericInputValue(livePointBYInput),
  };
}

function getAnalysisRoiSignature(roi = null) {
  const targetRoi = roi || getCurrentRoiBox();
  if (!targetRoi || targetRoi.width <= 0 || targetRoi.height <= 0) {
    return "";
  }
  return [
    Math.round(Number(targetRoi.center_x)),
    Math.round(Number(targetRoi.center_y)),
    Math.round(Number(targetRoi.width)),
    Math.round(Number(targetRoi.height)),
    Math.round(Number(targetRoi.angle_deg) * 10),
  ].join(":");
}

function getPreviewCoordinateSpace() {
  const preview = liveRunState.previewSize;
  const source = liveRunState.previewSourceSize || preview;
  if (!preview || !source || preview.width <= 0 || preview.height <= 0 || source.width <= 0 || source.height <= 0) {
    return {
      previewWidth: 1,
      previewHeight: 1,
      sourceWidth: 1,
      sourceHeight: 1,
      scaleX: 1,
      scaleY: 1,
    };
  }
  return {
    previewWidth: preview.width,
    previewHeight: preview.height,
    sourceWidth: source.width,
    sourceHeight: source.height,
    scaleX: source.width / preview.width,
    scaleY: source.height / preview.height,
  };
}

function convertPointToSource(point) {
  const { scaleX, scaleY, sourceWidth, sourceHeight } = getPreviewCoordinateSpace();
  return {
    x: clamp(Math.round(point.x * scaleX), 0, Math.max(0, sourceWidth - 1)),
    y: clamp(Math.round(point.y * scaleY), 0, Math.max(0, sourceHeight - 1)),
  };
}

function convertPointToPreview(point) {
  const { scaleX, scaleY, previewWidth, previewHeight } = getPreviewCoordinateSpace();
  return {
    x: clamp(Math.round(point.x / scaleX), 0, Math.max(0, previewWidth - 1)),
    y: clamp(Math.round(point.y / scaleY), 0, Math.max(0, previewHeight - 1)),
  };
}

function convertRectToSource(rect) {
  const { scaleX, scaleY, sourceWidth, sourceHeight } = getPreviewCoordinateSpace();
  const sourceX = clamp(Math.round(rect.x * scaleX), 0, Math.max(0, sourceWidth - 1));
  const sourceY = clamp(Math.round(rect.y * scaleY), 0, Math.max(0, sourceHeight - 1));
  const maxWidth = Math.max(1, sourceWidth - sourceX);
  const maxHeight = Math.max(1, sourceHeight - sourceY);
  return {
    x: sourceX,
    y: sourceY,
    width: clamp(Math.round(rect.width * scaleX), 1, maxWidth),
    height: clamp(Math.round(rect.height * scaleY), 1, maxHeight),
  };
}

function convertRectToPreview(rect) {
  const { scaleX, scaleY, previewWidth, previewHeight } = getPreviewCoordinateSpace();
  const previewX = clamp(Math.round(rect.x / scaleX), 0, Math.max(0, previewWidth - 1));
  const previewY = clamp(Math.round(rect.y / scaleY), 0, Math.max(0, previewHeight - 1));
  const maxWidth = Math.max(1, previewWidth - previewX);
  const maxHeight = Math.max(1, previewHeight - previewY);
  return {
    x: previewX,
    y: previewY,
    width: clamp(Math.round(rect.width / scaleX), 1, maxWidth),
    height: clamp(Math.round(rect.height / scaleY), 1, maxHeight),
  };
}

function convertMetricBoxToSource(box) {
  const { scaleX, scaleY } = getPreviewCoordinateSpace();
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const halfWidthVector = {
    x: Math.cos(angleRad) * (Number(box.width) / 2),
    y: Math.sin(angleRad) * (Number(box.width) / 2),
  };
  const halfHeightVector = {
    x: -Math.sin(angleRad) * (Number(box.height) / 2),
    y: Math.cos(angleRad) * (Number(box.height) / 2),
  };
  const sourceHalfWidthVector = {
    x: halfWidthVector.x * scaleX,
    y: halfWidthVector.y * scaleY,
  };
  const sourceHalfHeightVector = {
    x: halfHeightVector.x * scaleX,
    y: halfHeightVector.y * scaleY,
  };
  return {
    center_x: convertPointToSource({ x: Number(box.center_x), y: Number(box.center_y) }).x,
    center_y: convertPointToSource({ x: Number(box.center_x), y: Number(box.center_y) }).y,
    width: Math.max(1, Math.round(Math.hypot(sourceHalfWidthVector.x, sourceHalfWidthVector.y) * 2)),
    height: Math.max(1, Math.round(Math.hypot(sourceHalfHeightVector.x, sourceHalfHeightVector.y) * 2)),
    angle_deg: (Math.atan2(sourceHalfWidthVector.y, sourceHalfWidthVector.x) * 180) / Math.PI,
  };
}

function convertMetricBoxToPreview(box) {
  const { scaleX, scaleY } = getPreviewCoordinateSpace();
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const halfWidthVector = {
    x: Math.cos(angleRad) * (Number(box.width) / 2),
    y: Math.sin(angleRad) * (Number(box.width) / 2),
  };
  const halfHeightVector = {
    x: -Math.sin(angleRad) * (Number(box.height) / 2),
    y: Math.cos(angleRad) * (Number(box.height) / 2),
  };
  const previewHalfWidthVector = {
    x: halfWidthVector.x / scaleX,
    y: halfWidthVector.y / scaleY,
  };
  const previewHalfHeightVector = {
    x: halfHeightVector.x / scaleX,
    y: halfHeightVector.y / scaleY,
  };
  return {
    center_x: convertPointToPreview({ x: Number(box.center_x), y: Number(box.center_y) }).x,
    center_y: convertPointToPreview({ x: Number(box.center_x), y: Number(box.center_y) }).y,
    width: Math.max(1, Math.round(Math.hypot(previewHalfWidthVector.x, previewHalfWidthVector.y) * 2)),
    height: Math.max(1, Math.round(Math.hypot(previewHalfHeightVector.x, previewHalfHeightVector.y) * 2)),
    angle_deg: (Math.atan2(previewHalfWidthVector.y, previewHalfWidthVector.x) * 180) / Math.PI,
  };
}

function convertDirectionAngleForCoordinateSpace(angleDeg, coordinateSpace = "preview") {
  const { scaleX, scaleY } = getPreviewCoordinateSpace();
  const angleRad = (Number(angleDeg || 0) * Math.PI) / 180;
  const vector = {
    x: Math.cos(angleRad),
    y: Math.sin(angleRad),
  };
  const scaled =
    coordinateSpace === "source"
      ? { x: vector.x * scaleX, y: vector.y * scaleY }
      : { x: vector.x / scaleX, y: vector.y / scaleY };
  return (Math.atan2(scaled.y, scaled.x) * 180) / Math.PI;
}

function currentDirectionProjectionMode() {
  if (liveDirectionProjectionModeSelect && isDirectionProjectionMode(liveDirectionProjectionModeSelect.value)) {
    return liveDirectionProjectionModeSelect.value;
  }
  return isDirectionProjectionMode(liveRunState.resolvedDirectionProjectionMode)
    ? liveRunState.resolvedDirectionProjectionMode
    : "max_chord";
}

function isDirectionProjectionMode(value) {
  return value === "auto" || value === "max_chord" || value === "mask_projection" || value === "envelope_max_width";
}

function currentTargetGeometryMode() {
  const value = liveTargetGeometryModeSelect ? liveTargetGeometryModeSelect.value : "";
  return value === "line_bundle" || value === "mesh_lattice" || value === "single_component" ? value : "single_component";
}

function currentSideGuardRatio() {
  const rawValue = getNumericInputValue(liveSideGuardRatioInput, 0);
  return clamp(Number.isFinite(rawValue) ? rawValue : 0, 0, 0.45);
}

function currentEnvelopeMinSupportPx() {
  const rawValue = getNumericInputValue(liveEnvelopeMinSupportInput, 3);
  return Math.round(clamp(Number.isFinite(rawValue) ? rawValue : 3, 2, 500));
}

function currentEnvelopeQuantile() {
  const rawValue = getNumericInputValue(liveEnvelopeQuantileInput, 0);
  return clamp(Number.isFinite(rawValue) ? rawValue : 0, 0, 0.2);
}

function mapDefinitionToCoordinateSpace(definition, coordinateSpace = "preview") {
  if (!definition) {
    return null;
  }
  const convertRect = coordinateSpace === "source" ? convertRectToSource : convertRectToPreview;
  const convertBox = coordinateSpace === "source" ? convertMetricBoxToSource : convertMetricBoxToPreview;
  const convertPoint = coordinateSpace === "source" ? convertPointToSource : convertPointToPreview;
  const metricBox = definition.metric_box
    ? convertBox(definition.metric_box)
    : definition.analysis_roi
      ? metricBoxFromRect(convertRect(definition.analysis_roi))
      : null;
  const analysisRoi = metricBox ? boundingRectForMetricBox(metricBox) : definition.analysis_roi ? convertRect(definition.analysis_roi) : undefined;
  return {
    ...definition,
    analysis_roi: analysisRoi,
    metric_box: metricBox,
    direction_angle_deg:
      definition.direction_angle_deg != null
        ? convertDirectionAngleForCoordinateSpace(definition.direction_angle_deg, coordinateSpace)
        : definition.direction_angle_deg,
    point_a_px: definition.point_a_px ? clampPointToRect(convertPoint(definition.point_a_px), analysisRoi) : undefined,
    point_b_px: definition.point_b_px ? clampPointToRect(convertPoint(definition.point_b_px), analysisRoi) : undefined,
  };
}

function clampPointToRect(point, rect) {
  if (!point || !rect) {
    return point;
  }
  return {
    x: clamp(Math.round(Number(point.x)), Number(rect.x), Number(rect.x) + Number(rect.width) - 1),
    y: clamp(Math.round(Number(point.y)), Number(rect.y), Number(rect.y) + Number(rect.height) - 1),
  };
}

function hasValidAnalysisRoi() {
  const centerX = getOptionalNumericInputValue(liveAnalysisRoiXInput);
  const centerY = getOptionalNumericInputValue(liveAnalysisRoiYInput);
  const width = getOptionalNumericInputValue(liveAnalysisRoiWidthInput);
  const height = getOptionalNumericInputValue(liveAnalysisRoiHeightInput);
  const angle = getOptionalNumericInputValue(liveAnalysisRoiAngleInput);
  return centerX != null && centerY != null && width != null && height != null && angle != null && width > 0 && height > 0;
}

function hasValidPointInputs() {
  const ax = getOptionalNumericInputValue(livePointAXInput);
  const ay = getOptionalNumericInputValue(livePointAYInput);
  const bx = getOptionalNumericInputValue(livePointBXInput);
  const by = getOptionalNumericInputValue(livePointBYInput);
  return ax != null && ay != null && bx != null && by != null && (ax !== bx || ay !== by);
}

function hasValidMetricBoxInputs() {
  return hasValidAnalysisRoi();
}

function pointWithinAnalysisRoi(point, roi) {
  return point.x >= roi.x && point.y >= roi.y && point.x < roi.x + roi.width && point.y < roi.y + roi.height;
}

function pointWithinAnalysisRoiFloat(point, roi, epsilon = ANALYSIS_ROI_FLOAT_EPSILON) {
  return (
    point.x >= roi.x - epsilon &&
    point.y >= roi.y - epsilon &&
    point.x <= roi.x + roi.width + epsilon &&
    point.y <= roi.y + roi.height + epsilon
  );
}

function metricBoxWithinAnalysisRoi(box, roi, epsilon = ANALYSIS_ROI_FLOAT_EPSILON) {
  return metricBoxCorners(box).every((point) => pointWithinAnalysisRoiFloat(point, roi, epsilon));
}

function metricBoxWithinPreviewFrame(box) {
  if (!box || !liveRunState.previewSize) {
    return true;
  }
  const bounds = boundingRectForMetricBox(box);
  return (
    bounds.x >= 0 &&
    bounds.y >= 0 &&
    bounds.x + bounds.width <= liveRunState.previewSize.width &&
    bounds.y + bounds.height <= liveRunState.previewSize.height
  );
}

function hasLocallyCompleteDefinition() {
  if (!hasValidAnalysisRoi() || !hasValidPointInputs() || !hasValidMetricBoxInputs()) {
    return false;
  }
  const roi = getCurrentAnalysisRoi();
  const box = getCurrentMetricBox();
  const pointA = getCurrentPointA();
  const pointB = getCurrentPointB();
  return (
    pointWithinAnalysisRoi(pointA, roi) &&
    pointWithinAnalysisRoi(pointB, roi) &&
    metricBoxWithinAnalysisRoi(box, roi) &&
    pointInRotatedMetricBox(box, pointA.x, pointA.y) &&
    pointInRotatedMetricBox(box, pointB.x, pointB.y)
  );
}

function normalizeDefinitionForComparison(definition) {
  if (!definition) {
    return null;
  }
  const normalizedMetricBox = (definition.metric_box || definition.analysis_roi)
    ? {
        center_x: Number((definition.metric_box || metricBoxFromRect(definition.analysis_roi)).center_x),
        center_y: Number((definition.metric_box || metricBoxFromRect(definition.analysis_roi)).center_y),
        width: Number((definition.metric_box || metricBoxFromRect(definition.analysis_roi)).width),
        height: Number((definition.metric_box || metricBoxFromRect(definition.analysis_roi)).height),
        angle_deg: Number((definition.metric_box || metricBoxFromRect(definition.analysis_roi)).angle_deg || 0),
      }
    : null;
  return {
    analysis_roi: {
      x: Number(definition.analysis_roi.x),
      y: Number(definition.analysis_roi.y),
      width: Number(definition.analysis_roi.width),
      height: Number(definition.analysis_roi.height),
    },
    metric_box: normalizedMetricBox,
    point_a_px: {
      x: Number(definition.point_a_px.x),
      y: Number(definition.point_a_px.y),
    },
    point_b_px: {
      x: Number(definition.point_b_px.x),
      y: Number(definition.point_b_px.y),
    },
    observation_axis: String(definition.observation_axis || "long_axis"),
    foreground_polarity: String(definition.foreground_polarity),
    threshold_mode: String(definition.threshold_mode),
    ignore_internal_texture: Boolean(definition.ignore_internal_texture),
    min_target_area_px: Number(definition.min_target_area_px),
    sensitivity: Number(definition.sensitivity ?? 50),
    direction_angle_deg: definition.direction_angle_deg == null ? null : Number(definition.direction_angle_deg),
    direction_projection_mode: definition.direction_projection_mode || currentDirectionProjectionMode(),
    target_geometry_mode: definition.target_geometry_mode || currentTargetGeometryMode(),
    side_guard_ratio: Number(definition.side_guard_ratio ?? currentSideGuardRatio()),
    envelope_min_support_px: Number(definition.envelope_min_support_px ?? currentEnvelopeMinSupportPx()),
    envelope_quantile: Number(definition.envelope_quantile ?? currentEnvelopeQuantile()),
  };
}

function syncLiveDefinitionDirtyState() {
  const savedDefinition = liveRunState.detail ? normalizeDefinitionForComparison(liveRunState.detail.definition) : null;
  const currentDefinition = normalizeDefinitionForComparison(buildLiveDefinitionPayload({ coordinateSpace: "source" }));
  liveRunState.definitionDirty = Boolean(savedDefinition) && JSON.stringify(savedDefinition) !== JSON.stringify(currentDefinition);
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function pointInRotatedMetricBox(box, x, y, epsilon = METRIC_BOX_POINT_FLOAT_EPSILON) {
  if (!Number.isFinite(Number(box.width)) || !Number.isFinite(Number(box.height)) || Number(box.width) <= 0 || Number(box.height) <= 0) {
    return false;
  }
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  const translatedX = x - Number(box.center_x);
  const translatedY = y - Number(box.center_y);
  const localX = translatedX * cosTheta + translatedY * sinTheta;
  const localY = -translatedX * sinTheta + translatedY * cosTheta;
  return Math.abs(localX) <= Number(box.width) / 2 + epsilon && Math.abs(localY) <= Number(box.height) / 2 + epsilon;
}

function applyMetricBoxToInputs(box) {
  const normalizedBox = {
    center_x: Math.round(Number(box.center_x)),
    center_y: Math.round(Number(box.center_y)),
    width: Math.max(1, Math.round(Number(box.width))),
    height: Math.max(1, Math.round(Number(box.height))),
    angle_deg: Number(Number(box.angle_deg).toFixed(1)),
  };
  if (liveAnalysisRoiXInput) {
    liveAnalysisRoiXInput.value = String(normalizedBox.center_x);
  }
  if (liveAnalysisRoiYInput) {
    liveAnalysisRoiYInput.value = String(normalizedBox.center_y);
  }
  if (liveAnalysisRoiWidthInput) {
    liveAnalysisRoiWidthInput.value = String(normalizedBox.width);
  }
  if (liveAnalysisRoiHeightInput) {
    liveAnalysisRoiHeightInput.value = String(normalizedBox.height);
  }
  if (liveAnalysisRoiAngleInput) {
    liveAnalysisRoiAngleInput.value = normalizedBox.angle_deg.toFixed(1);
  }
}

function previewPointFromPayload(point) {
  if (!point) {
    return null;
  }
  return convertPointToPreview({ x: Number(point.x), y: Number(point.y) });
}

function directionProjectionOverlayFromAutoPayload(payload) {
  if (payload?.direction_projection_mode !== "envelope_max_width") {
    return null;
  }
  return {
    projection_point_mode: "envelope_max_width",
    target_geometry_mode: payload.target_geometry_mode || currentTargetGeometryMode(),
    side_guard_ratio: Number(payload.side_guard_ratio ?? currentSideGuardRatio()),
    envelope_support_px: payload.envelope_support_px ?? null,
    envelope_candidate_count: payload.envelope_candidate_count ?? null,
  };
}

function previewPointFromTelemetryArray(point) {
  if (!Array.isArray(point) || point.length !== 2) {
    return null;
  }
  return { x: Number(point[0]), y: Number(point[1]) };
}

function directionProjectionOverlayFromTelemetry(latestTelemetry, pointA, pointB) {
  if (latestTelemetry?.projection_point_mode !== "envelope_max_width") {
    return null;
  }
  return {
    projection_point_mode: "envelope_max_width",
    target_geometry_mode: latestTelemetry.target_geometry_mode || currentTargetGeometryMode(),
    side_guard_ratio: Number(latestTelemetry.side_guard_ratio ?? currentSideGuardRatio()),
    envelope_support_px: latestTelemetry.envelope_support_px ?? null,
    envelope_candidate_count: latestTelemetry.envelope_candidate_count ?? null,
    point_a_px: pointA,
    point_b_px: pointB,
  };
}

function ensureMetricBoxWithinAnalysisRoi() {
  if (!hasValidAnalysisRoi() || !liveRunState.previewSize) {
    return;
  }
  const previewWidth = liveRunState.previewSize.width;
  const previewHeight = liveRunState.previewSize.height;
  let candidate = {
    ...getCurrentRoiBox(),
    center_x: clamp(getCurrentRoiBox().center_x, 0, previewWidth - 1),
    center_y: clamp(getCurrentRoiBox().center_y, 0, previewHeight - 1),
    width: clamp(getCurrentRoiBox().width, 1, previewWidth),
    height: clamp(getCurrentRoiBox().height, 1, previewHeight),
  };
  let guard = 0;
  while (guard < 64) {
    const boundingRect = boundingRectForMetricBox(candidate);
    const inside =
      boundingRect.x >= 0 &&
      boundingRect.y >= 0 &&
      boundingRect.x + boundingRect.width <= previewWidth &&
      boundingRect.y + boundingRect.height <= previewHeight;
    if (inside) {
      break;
    }
    candidate = {
      ...candidate,
      width: Math.max(1, candidate.width - 1),
      height: Math.max(1, candidate.height - 1),
      center_x: clamp(candidate.center_x, 0, previewWidth - 1),
      center_y: clamp(candidate.center_y, 0, previewHeight - 1),
    };
    guard += 1;
  }
  applyMetricBoxToInputs(candidate);
}

function metricBoxCorners(box) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  const halfWidth = Number(box.width) / 2;
  const halfHeight = Number(box.height) / 2;
  return [
    [-halfWidth, -halfHeight],
    [halfWidth, -halfHeight],
    [halfWidth, halfHeight],
    [-halfWidth, halfHeight],
  ].map(([localX, localY]) => ({
    x: Number(box.center_x) + localX * cosTheta - localY * sinTheta,
    y: Number(box.center_y) + localX * sinTheta + localY * cosTheta,
  }));
}

function worldPointFromMetricBoxLocal(box, localX, localY) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  return {
    x: Number(box.center_x) + localX * cosTheta - localY * sinTheta,
    y: Number(box.center_y) + localX * sinTheta + localY * cosTheta,
  };
}

function localizePointInMetricBox(box, x, y) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  const translatedX = x - Number(box.center_x);
  const translatedY = y - Number(box.center_y);
  return {
    x: translatedX * cosTheta + translatedY * sinTheta,
    y: -translatedX * sinTheta + translatedY * cosTheta,
  };
}

function resizeMetricBoxFromFixedCorner(box, fixedCorner, dragPoint, minSize = 8) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  const deltaX = Number(dragPoint.x) - Number(fixedCorner.x);
  const deltaY = Number(dragPoint.y) - Number(fixedCorner.y);
  const localDeltaX = deltaX * cosTheta + deltaY * sinTheta;
  const localDeltaY = -deltaX * sinTheta + deltaY * cosTheta;
  const widthSign = localDeltaX >= 0 ? 1 : -1;
  const heightSign = localDeltaY >= 0 ? 1 : -1;
  const width = Math.max(minSize, Math.abs(localDeltaX));
  const height = Math.max(minSize, Math.abs(localDeltaY));
  const diagonalX = widthSign * width * cosTheta - heightSign * height * sinTheta;
  const diagonalY = widthSign * width * sinTheta + heightSign * height * cosTheta;
  return {
    center_x: Number(fixedCorner.x) + diagonalX / 2,
    center_y: Number(fixedCorner.y) + diagonalY / 2,
    width,
    height,
    angle_deg: Number(box.angle_deg || 0),
  };
}

function rotateMetricBoxAroundCenter(box, dragPoint) {
  const angleDeg = (Math.atan2(Number(dragPoint.y) - Number(box.center_y), Number(dragPoint.x) - Number(box.center_x)) * 180) / Math.PI + 90;
  return {
    center_x: Number(box.center_x),
    center_y: Number(box.center_y),
    width: Number(box.width),
    height: Number(box.height),
    angle_deg: angleDeg,
  };
}

function metricBoxRotationHandle(box, offset = 28) {
  const topCenter = worldPointFromMetricBoxLocal(box, 0, -Number(box.height) / 2);
  const handle = worldPointFromMetricBoxLocal(box, 0, -(Number(box.height) / 2 + offset));
  return { topCenter, handle };
}

function metricBoxResizeHandles(box) {
  return metricBoxCorners(box).map((point, index) => ({ ...point, index }));
}

function distanceBetweenPoints(pointA, pointB) {
  return Math.hypot(Number(pointA.x) - Number(pointB.x), Number(pointA.y) - Number(pointB.y));
}

function renderLivePreviewOverlay() {
  if (!livePreviewOverlayNode || !liveRunState.previewSize) {
    return;
  }
  const { width, height } = liveRunState.previewSize;
  livePreviewOverlayNode.setAttribute("viewBox", `0 0 ${width} ${height}`);
  showLivePreviewStage();

  const roi = getCurrentAnalysisRoi();
  const box = hasValidMetricBoxInputs() ? getCurrentMetricBox() : null;
  const directionBox = hasValidMetricBoxInputs() ? getCurrentRoiBox() : null;
  const pointA = hasValidPointInputs() ? getCurrentPointA() : null;
  const pointB = hasValidPointInputs() ? getCurrentPointB() : null;
  const fragments = [];
  if (hasValidAnalysisRoi()) {
    const roiPoints = metricBoxCorners(box)
      .map((point) => `${point.x},${point.y}`)
      .join(" ");
    const { topCenter, handle } = metricBoxRotationHandle(directionBox);
    fragments.push(`<polygon class="live-overlay-roi" points="${roiPoints}"></polygon>`);
    fragments.push(
      `<line class="live-overlay-rotate-link" x1="${topCenter.x}" y1="${topCenter.y}" x2="${handle.x}" y2="${handle.y}"></line>`,
    );
    fragments.push(
      `<circle class="live-overlay-rotate-handle" cx="${handle.x}" cy="${handle.y}" r="8"></circle>`,
    );
    for (const corner of metricBoxResizeHandles(box)) {
      fragments.push(
        `<rect class="live-overlay-resize-handle" x="${corner.x - 5}" y="${corner.y - 5}" width="10" height="10" rx="2" ry="2"></rect>`,
      );
    }
  }
  if (directionBox) {
    const localHalfWidth = Number(directionBox.width) / 2;
    const leftAnchor = worldPointFromMetricBoxLocal(directionBox, -localHalfWidth, 0);
    const rightAnchor = worldPointFromMetricBoxLocal(directionBox, localHalfWidth, 0);
    fragments.push(
      `<line class="live-overlay-centerline" x1="${leftAnchor.x}" y1="${leftAnchor.y}" x2="${rightAnchor.x}" y2="${rightAnchor.y}"></line>`,
    );
  }
  renderEnvelopeDebugOverlay(fragments, directionBox, pointA, pointB);
  if (pointA) {
    fragments.push(`<circle class="live-overlay-point" cx="${pointA.x}" cy="${pointA.y}" r="6"></circle>`);
    fragments.push(`<text class="live-overlay-point-label" x="${pointA.x + 10}" y="${pointA.y - 10}">A</text>`);
  }
  if (pointB) {
    fragments.push(`<circle class="live-overlay-point" cx="${pointB.x}" cy="${pointB.y}" r="6"></circle>`);
    fragments.push(`<text class="live-overlay-point-label" x="${pointB.x + 10}" y="${pointB.y - 10}">B</text>`);
  }
  const playbackBadge = liveRunPlaybackBadge(width);
  if (playbackBadge) {
    fragments.push(playbackBadge);
  }
  livePreviewOverlayNode.innerHTML = fragments.join("");
}

function renderEnvelopeDebugOverlay(fragments, directionBox, pointA, pointB) {
  const overlay = liveRunState.directionProjectionOverlay || {};
  const projectionMode = overlay.projection_point_mode || currentDirectionProjectionMode();
  if (!directionBox || projectionMode !== "envelope_max_width") {
    return;
  }
  const sideGuardRatio = clamp(Number(overlay.side_guard_ratio ?? currentSideGuardRatio()), 0, 0.45);
  if (sideGuardRatio > 0) {
    const guardWidth = Number(directionBox.width) * sideGuardRatio;
    const halfWidth = Number(directionBox.width) / 2;
    const halfHeight = Number(directionBox.height) / 2;
    const leftGuard = metricBoxLocalPolygon(directionBox, [
      [-halfWidth, -halfHeight],
      [-halfWidth + guardWidth, -halfHeight],
      [-halfWidth + guardWidth, halfHeight],
      [-halfWidth, halfHeight],
    ]);
    const rightGuard = metricBoxLocalPolygon(directionBox, [
      [halfWidth - guardWidth, -halfHeight],
      [halfWidth, -halfHeight],
      [halfWidth, halfHeight],
      [halfWidth - guardWidth, halfHeight],
    ]);
    fragments.push(`<polygon class="live-overlay-envelope-side-guard" points="${leftGuard}"></polygon>`);
    fragments.push(`<polygon class="live-overlay-envelope-side-guard" points="${rightGuard}"></polygon>`);
  }
  if (pointA && pointB) {
    fragments.push(
      `<line class="live-overlay-envelope-bin" x1="${pointA.x}" y1="${pointA.y}" x2="${pointB.x}" y2="${pointB.y}"></line>`,
    );
  }
}

function metricBoxLocalPolygon(box, localPoints) {
  return localPoints
    .map(([localX, localY]) => worldPointFromMetricBoxLocal(box, localX, localY))
    .map((point) => `${point.x},${point.y}`)
    .join(" ");
}

function liveRunPlaybackBadge(width) {
  const status = liveRunState.detail ? liveRunState.detail.status : "";
  if (!["running", "invalidated", "stopping"].includes(String(status || ""))) {
    return "";
  }
  const latest = liveRunState.latestTelemetry || {};
  const frameId = Number(latest.frame_id ?? liveRunState.lastPreviewFrameId);
  const sampleIndex = Number(latest.sample_index);
  const sampleLabel = Number.isFinite(sampleIndex) ? `S${sampleIndex + 1}` : "S--";
  const frameLabel = Number.isFinite(frameId) && frameId > 0 ? `F${frameId}` : "F--";
  const rateLabel = liveMeasurementRateNode ? liveMeasurementRateNode.textContent || "n/a" : "n/a";
  const label =
    currentLocale === "en"
      ? `LIVE ${frameLabel} ${sampleLabel} ${rateLabel}`
      : `实时回放 ${frameLabel} ${sampleLabel} ${rateLabel}`;
  const badgeWidth = Math.min(Math.max(250, label.length * 9 + 48), Math.max(250, Number(width) - 24));
  return `
    <g class="live-overlay-run-badge" transform="translate(12 12)">
      <rect class="live-overlay-run-badge-bg" width="${badgeWidth}" height="34" rx="8" ry="8"></rect>
      <circle class="live-overlay-run-badge-dot" cx="17" cy="17" r="5"></circle>
      <text class="live-overlay-run-badge-text" x="32" y="22">${label}</text>
    </g>
  `;
}

function setActiveLiveTool(tool) {
  liveRunState.activeTool = tool;
  updateLiveRunControls();
  const labels = {
    "draw-roi":
      currentLocale === "en" ? "Drag on the preview to draw the analysis ROI." : "在预览上拖拽以绘制分析 ROI。",
  };
  setLivePointPickerStatus(labels[tool] || (currentLocale === "en" ? "Tool idle." : "工具空闲。"));
  renderLiveToolPrompt();
}

function updateLiveRunControls() {
  const hasRun = Boolean(liveRunState.runId);
  const hasPreview = Boolean(liveRunState.previewSize);
  const previewState = getPreviewStatePayload();
  const status = liveRunState.detail ? liveRunState.detail.status : "";
  const isRunActive = ["running", "invalidated", "stopping"].includes(status);
  const isRunTerminal = isLiveRunTerminalStatus(status);
  const isSetupBusy = liveRunState.setupRecomputeInFlight;
  const canEditOverlay = hasPreview && !previewState.stream_active && !isRunActive && !isRunTerminal;
  const hasRoi = hasValidAnalysisRoi();
  const roiReady = hasRoi && liveRunState.roiConfirmed;
  const canSaveDefinition =
    hasRun && !isRunActive && !isRunTerminal && !previewState.stream_active && hasPreview && roiReady && hasLocallyCompleteDefinition();
  const temperatureSettingsConfirmed = isTemperatureSettingsConfirmed();

  if (stopLivePreviewStreamButton) {
    stopLivePreviewStreamButton.disabled = isRunActive || !previewState.stream_active;
    stopLivePreviewStreamButton.textContent = isRunActive
      ? currentLocale === "en"
        ? "Running"
        : "测试中"
      : t("home.actions.freeze", {}, currentLocale === "en" ? "Freeze" : "冻结画面");
  }
  if (startLivePreviewStreamButton) {
    startLivePreviewStreamButton.disabled = !hasRun || previewState.stream_active || isRunActive || isRunTerminal;
    startLivePreviewStreamButton.textContent = isRunActive
      ? currentLocale === "en"
        ? "Live replay"
        : "实时回放"
      : t("home.actions.unfreeze", {}, currentLocale === "en" ? "Unfreeze" : "解除冻结");
  }
  if (saveLiveDefinitionButton) {
    saveLiveDefinitionButton.disabled = !canSaveDefinition || isSetupBusy;
  }
  if (drawAnalysisRoiButton) {
    drawAnalysisRoiButton.disabled = !canEditOverlay;
    drawAnalysisRoiButton.classList.add("live-tool-button");
  }
  if (recomputeDefinitionButton) {
    recomputeDefinitionButton.disabled = !canEditOverlay || !roiReady || isSetupBusy;
  }
  if (confirmTargetTemperatureButton) {
    confirmTargetTemperatureButton.disabled = !hasRun || isRunActive || isRunTerminal;
    confirmTargetTemperatureButton.textContent = temperatureSettingsConfirmed
      ? t("home.actions.target_confirmed", {}, currentLocale === "en" ? "Settings Confirmed" : "已确认")
      : t("home.actions.confirm_target", {}, currentLocale === "en" ? "Confirm Temperature Settings" : "确认温控设置");
  }
  if (refreshTempSerialPortsButton) {
    refreshTempSerialPortsButton.disabled = tempSerialPortBusy || isRunActive;
  }
  if (applyTempSerialPortButton) {
    applyTempSerialPortButton.disabled =
      tempSerialPortBusy ||
      isRunActive ||
      tempSerialPortBackend !== "lu92xx_modbus_rtu" ||
      !tempSerialPortSelect ||
      !tempSerialPortSelect.value;
  }
  refreshTemperatureSettingsSummary();
  if (startLiveRunButton) {
    const hasCompleteLocalDefinition =
      hasRun && !previewState.stream_active && hasPreview && roiReady && hasLocallyCompleteDefinition();
    const hasPendingAbReview = Boolean(isSetupBusy || (roiReady && !hasValidPointInputs()));
    startLiveRunButton.disabled =
      !hasCompleteLocalDefinition || isRunActive || isRunTerminal || !temperatureSettingsConfirmed || hasPendingAbReview;
  }
  if (stopLiveRunButton) {
    stopLiveRunButton.disabled = !isRunActive;
  }
  if (newLiveTestButton) {
    newLiveTestButton.disabled = isRunActive;
    if (isRunActive) {
      resetNewLiveTestConfirmation();
    }
  }
  if (fixtureVideoSelectNode && !fixtureVideoSwitchNode?.hidden) {
    fixtureVideoSelectNode.disabled = fixtureVideoSwitchBusy || isRunActive;
  }
  updatePointSummaries();
  updateLiveToolButtons();
  renderHomeTaskState();
}

function fillLiveDefinitionInputs(definition, { updatePoints = true } = {}) {
  if (!definition) {
    return;
  }
  const uiDefinition = mapDefinitionToCoordinateSpace(definition, "preview");
  const roiBox = uiDefinition.metric_box || metricBoxFromRect(uiDefinition.analysis_roi);
  liveRunState.roiConfirmed = true;
  liveRunState.confirmedRoiSignature = getAnalysisRoiSignature(roiBox);
  if (liveAnalysisRoiXInput) {
    liveAnalysisRoiXInput.value = String(roiBox.center_x);
  }
  if (liveAnalysisRoiYInput) {
    liveAnalysisRoiYInput.value = String(roiBox.center_y);
  }
  if (liveAnalysisRoiWidthInput) {
    liveAnalysisRoiWidthInput.value = String(roiBox.width);
  }
  if (liveAnalysisRoiHeightInput) {
    liveAnalysisRoiHeightInput.value = String(roiBox.height);
  }
  if (liveAnalysisRoiAngleInput) {
    liveAnalysisRoiAngleInput.value = String(uiDefinition.direction_angle_deg ?? roiBox.angle_deg);
  }
  if (updatePoints && livePointAXInput) {
    livePointAXInput.value = String(uiDefinition.point_a_px.x);
  }
  if (updatePoints && livePointAYInput) {
    livePointAYInput.value = String(uiDefinition.point_a_px.y);
  }
  if (updatePoints && livePointBXInput) {
    livePointBXInput.value = String(uiDefinition.point_b_px.x);
  }
  if (updatePoints && livePointBYInput) {
    livePointBYInput.value = String(uiDefinition.point_b_px.y);
  }
  if (liveForegroundPolaritySelect) {
    liveForegroundPolaritySelect.value = uiDefinition.foreground_polarity;
  }
  if (liveThresholdModeSelect) {
    liveThresholdModeSelect.value = uiDefinition.threshold_mode;
  }
  if (liveDirectionProjectionModeSelect) {
    liveDirectionProjectionModeSelect.value = uiDefinition.direction_projection_mode || "max_chord";
  }
  if (liveTargetGeometryModeSelect) {
    liveTargetGeometryModeSelect.value = uiDefinition.target_geometry_mode || "single_component";
  }
  if (liveSideGuardRatioInput) {
    liveSideGuardRatioInput.value = String(uiDefinition.side_guard_ratio ?? 0);
  }
  if (liveEnvelopeMinSupportInput) {
    liveEnvelopeMinSupportInput.value = String(uiDefinition.envelope_min_support_px ?? 3);
  }
  if (liveEnvelopeQuantileInput) {
    liveEnvelopeQuantileInput.value = String(uiDefinition.envelope_quantile ?? 0);
  }
  if (liveIgnoreInternalTextureInput) {
    liveIgnoreInternalTextureInput.checked = Boolean(uiDefinition.ignore_internal_texture);
  }
  if (liveMinTargetAreaInput) {
    liveMinTargetAreaInput.value = String(uiDefinition.min_target_area_px);
  }
  if (liveSensitivityInput) {
    liveSensitivityInput.value = String(uiDefinition.sensitivity ?? 50);
  }
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
}

function seedLiveDefinitionDefaults(width, height) {
  for (const node of [
    liveAnalysisRoiXInput,
    liveAnalysisRoiYInput,
    liveAnalysisRoiWidthInput,
    liveAnalysisRoiHeightInput,
    liveAnalysisRoiAngleInput,
    livePointAXInput,
    livePointAYInput,
    livePointBXInput,
    livePointBYInput,
  ]) {
    if (node) {
      node.value = "";
    }
  }
  if (liveSensitivityInput && !liveSensitivityInput.value) {
    liveSensitivityInput.value = "50";
  }
  if (liveDirectionProjectionModeSelect) {
    liveDirectionProjectionModeSelect.value = "max_chord";
  }
  if (liveTargetGeometryModeSelect) {
    liveTargetGeometryModeSelect.value = "single_component";
  }
  if (liveSideGuardRatioInput) {
    liveSideGuardRatioInput.value = "0";
  }
  liveRunState.roiConfirmed = false;
  liveRunState.confirmedRoiSignature = "";
  liveRunState.directionProjectionOverlay = null;
  liveRunState.resolvedDirectionProjectionMode = "max_chord";
  if (liveDirectionProjectionModeSelect) {
    liveDirectionProjectionModeSelect.value = "max_chord";
  }
  if (liveTargetGeometryModeSelect) {
    liveTargetGeometryModeSelect.value = "single_component";
  }
  if (liveSideGuardRatioInput) {
    liveSideGuardRatioInput.value = "0";
  }
  setSetupRecomputeState({ inFlight: false, detail: "" });
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  setLivePointPickerStatus(
    currentLocale === "en"
      ? "Preview frozen. Draw the ROI to place ROI-local A/B."
      : "画面已冻结，请框选 ROI。",
  );
}

function resetLiveDefinitionInputs() {
  for (const node of [
    liveAnalysisRoiXInput,
    liveAnalysisRoiYInput,
    liveAnalysisRoiWidthInput,
    liveAnalysisRoiHeightInput,
    liveAnalysisRoiAngleInput,
    livePointAXInput,
    livePointAYInput,
    livePointBXInput,
    livePointBYInput,
  ]) {
    if (node) {
      node.value = "";
    }
  }
  liveRunState.definitionDirty = false;
  liveRunState.roiConfirmed = false;
  liveRunState.confirmedRoiSignature = "";
  liveRunState.activeTool = "";
  liveRunState.overlayDrag = null;
  liveRunState.directionProjectionOverlay = null;
  liveRunState.resolvedDirectionProjectionMode = "max_chord";
  setSetupRecomputeState({ inFlight: false, detail: "" });
  renderLivePreviewOverlay();
  renderLiveToolPrompt();
}

function clearPointInputs() {
  for (const node of [livePointAXInput, livePointAYInput, livePointBXInput, livePointBYInput]) {
    if (node) {
      node.value = "";
    }
  }
  liveRunState.directionProjectionOverlay = null;
  liveRunState.resolvedDirectionProjectionMode = "max_chord";
}

function clearMetricBoxInputs() {
  return;
}

function scheduleRoiPointRecompute({ message = "" } = {}) {
  if (!liveRunState.runId || !hasValidAnalysisRoi() || getPreviewStatePayload().stream_active) {
    return;
  }
  if (liveRunState.setupRecomputeTimer) {
    window.clearTimeout(liveRunState.setupRecomputeTimer);
  }
  const recomputeToken = liveRunState.setupRecomputeActiveToken + 1;
  liveRunState.setupRecomputeActiveToken = recomputeToken;
  clearPointInputs();
  renderLivePreviewOverlay();
  setLivePointPickerStatus(
    currentLocale === "en" ? "Capturing a new frame and recomputing ROI-local A/B points..." : "正在抓取新画面并重算 ROI 内 A/B...",
  );
  setSetupRecomputeState({
    inFlight: true,
    detail:
      "Capturing a new frame to recalculate ROI-local A/B from the current ROI and sensitivity settings.",
  });
  liveRunState.setupRecomputeTimer = window.setTimeout(async () => {
    liveRunState.setupRecomputeTimer = null;
    let reusedCachedFrame = false;
    try {
      try {
        await loadFrozenPreviewFrame({
          runId: liveRunState.runId,
          cached: false,
          refreshDetail: false,
          seedDefaults: false,
        });
      } catch (error) {
        await loadFrozenPreviewFrame({
          runId: liveRunState.runId,
          cached: true,
          refreshDetail: false,
          seedDefaults: false,
        });
        reusedCachedFrame = true;
      }
      await autoDetectLiveDefinition({ silent: true, origin: "roi-refresh", recomputeToken });
      if (recomputeToken !== liveRunState.setupRecomputeActiveToken) {
        return;
      }
      if (message && reusedCachedFrame) {
        setLiveRunMessage(
          currentLocale === "en"
            ? `${message} Fresh capture was unavailable, so the cached frozen frame was reused.`
            : `${message} 新抓帧不可用，已回退为当前缓存静帧继续重算。`,
          "info",
        );
      } else if (message) {
        setLiveRunMessage(message, "info");
      } else if (reusedCachedFrame) {
        setLiveRunMessage(
          currentLocale === "en"
            ? "Fresh capture was unavailable. Reused the cached frozen frame and recomputed ROI-local A/B."
            : "新抓帧不可用，已回退为当前缓存静帧并重算 ROI 内 A/B。",
          "info",
        );
      }
    } catch (error) {
      if (recomputeToken !== liveRunState.setupRecomputeActiveToken) {
        return;
      }
      setLivePointPickerStatus(
        currentLocale === "en" ? "Point recompute failed. Adjust ROI or sensitivity and try again." : "A/B 重算失败，请调整 ROI 或灵敏度后重试。",
      );
      setLiveRunMessage(`Failed to recompute ROI-local A/B: ${String(error)}`, "error");
    } finally {
      if (recomputeToken === liveRunState.setupRecomputeActiveToken) {
        setSetupRecomputeState({ inFlight: false, detail: "" });
      }
    }
  }, 120);
}

function commitAnalysisRoiSelection({ force = false, message = "", recompute = true, constrain = true } = {}) {
  updateLiveDefinitionAfterLocalEdit({ constrain });
  if (!hasValidAnalysisRoi()) {
    liveRunState.roiConfirmed = false;
    liveRunState.confirmedRoiSignature = "";
    updateLiveRunControls();
    return;
  }
  const roiSignature = getAnalysisRoiSignature();
  const roiChanged = roiSignature !== liveRunState.confirmedRoiSignature;
  if ((roiChanged || force) && hasValidPointInputs()) {
    clearPointInputs();
  }
  liveRunState.roiConfirmed = force || liveRunState.roiConfirmed || roiChanged;
  liveRunState.confirmedRoiSignature = roiSignature;
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  updateLiveRunControls();
  if (!metricBoxWithinPreviewFrame(getCurrentMetricBox())) {
    setLivePointPickerStatus(
      currentLocale === "en"
        ? "ROI is outside the preview. Move or shrink it before recomputing A/B."
        : "ROI 超出画面，请先移动或缩小 ROI 后再重算 A/B。",
    );
    setLiveRunMessage(
      currentLocale === "en"
        ? "ROI is outside the preview. Its size was preserved; adjust position or size before recomputing A/B."
        : "ROI 超出画面。已保留当前尺寸，请先移动或缩小 ROI 后再重算 A/B。",
      "warning",
    );
    return;
  }
  setLivePointPickerStatus(
    currentLocale === "en" ? "ROI ready. Capturing a new frame and recomputing A/B along the current ROI axis." : "ROI 已就绪，正在抓取新画面并沿当前 ROI 轴线重算 A/B。",
  );
  if (message) {
    setLiveRunMessage(message, "info");
  }
  if (recompute && (roiChanged || force || !hasValidPointInputs())) {
    scheduleRoiPointRecompute({ message });
  }
}

function handleAnalysisRoiInputsChanged({ recompute = false } = {}) {
  if (!hasValidAnalysisRoi()) {
    liveRunState.roiConfirmed = false;
    liveRunState.confirmedRoiSignature = "";
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  commitAnalysisRoiSelection({ recompute });
}

function handlePointInputsChanged() {
  updateLiveDefinitionAfterLocalEdit();
}

function renderLiveRunDetail(payload) {
  if (!hasLiveSetupUi() || !payload) {
    return;
  }
  const serverPreview = payload.preview || {};
  liveRunState.detail = payload;
  liveRunState.runId = payload.run_id || "";
  liveRunState.measurementSourceSize = readMeasurementSourceSize(payload);
  if (isDirectionProjectionMode(payload.definition?.direction_projection_mode)) {
    liveRunState.resolvedDirectionProjectionMode = payload.definition.direction_projection_mode;
  }
  liveRunState.previewStreamActive = Boolean(
    serverPreview.stream_active || (liveRunState.previewStreamActive && liveRunState.previewStreamUrl),
  );
  liveRunState.previewFrozenAvailable = Boolean(
    !liveRunState.previewStreamActive && (serverPreview.frozen_frame_available || liveRunState.previewFrozenAvailable),
  );
  liveRunState.lastPreviewFrameId =
    liveRunState.lastPreviewFrameId != null ? liveRunState.lastPreviewFrameId : (serverPreview.last_frame_id ?? null);
  liveRunIdNode.textContent = liveRunState.runId || (currentLocale === "en" ? "Not created" : "尚未创建");
  liveRunStatusNode.textContent = localizeStateLabel(payload.status || "unknown");
  liveRunPresetNode.textContent = payload.preset || (liveRunPresetSelect ? liveRunPresetSelect.value : "balloon");
  renderLivePreviewMeta();
  const isRunActive = ["running", "invalidated", "stopping"].includes(String(payload.status || ""));
  if (payload.definition) {
    fillLiveDefinitionInputs(payload.definition, { updatePoints: !isRunActive });
  } else {
    syncLiveDefinitionDirtyState();
  }
  liveRunState.confirmedTemperatureSettings = payload.temperature_settings || null;
  if (liveTargetTemperatureInput && payload.temperature_settings?.target_temperature_celsius != null) {
    liveTargetTemperatureInput.value = Number(payload.temperature_settings.target_temperature_celsius).toFixed(1);
  }
  if (liveControlModeSelect && payload.temperature_settings?.control_mode) {
    liveControlModeSelect.value = String(payload.temperature_settings.control_mode);
  }
  if (liveCompletionModeSelect && payload.temperature_settings?.completion_mode) {
    liveCompletionModeSelect.value = String(payload.temperature_settings.completion_mode);
  }
  if (liveOutputPowerInput && payload.temperature_settings?.output_power_percent != null) {
    liveOutputPowerInput.value = String(Number(payload.temperature_settings.output_power_percent));
  }
  refreshTemperatureSettingsSummary();
  renderLivePreviewOverlay();
  updateLiveRunControls();
}

async function refreshLiveRunDetail(runId) {
  const response = await fetch(`/api/runs/${runId}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(parseErrorDetail(payload, `Failed to load run detail: ${response.status}`));
  }
  renderLiveRunDetail(payload);
  return payload;
}

function isLiveRunTerminalStatus(status) {
  return ["completed", "failed", "aborted"].includes(String(status || ""));
}

async function waitForLiveRunTerminalDetail(runId, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastPayload = null;
  while (Date.now() < deadline) {
    lastPayload = await refreshLiveRunDetail(runId);
    if (isLiveRunTerminalStatus(lastPayload.status)) {
      return lastPayload;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 250));
  }
  throw new Error(`Live run did not reach a terminal state within ${timeoutMs} ms.`);
}

function applyTrackedPointInputs(latestTelemetry) {
  if (!latestTelemetry) {
    return;
  }
  liveRunState.latestTelemetry = latestTelemetry;
  const pointA = Array.isArray(latestTelemetry.point_a_preview_px)
    ? { x: Number(latestTelemetry.point_a_preview_px[0]), y: Number(latestTelemetry.point_a_preview_px[1]) }
    : Array.isArray(latestTelemetry.point_a_px)
      ? convertPointToPreview({ x: Number(latestTelemetry.point_a_px[0]), y: Number(latestTelemetry.point_a_px[1]) })
      : null;
  const pointB = Array.isArray(latestTelemetry.point_b_preview_px)
    ? { x: Number(latestTelemetry.point_b_preview_px[0]), y: Number(latestTelemetry.point_b_preview_px[1]) }
    : Array.isArray(latestTelemetry.point_b_px)
      ? convertPointToPreview({ x: Number(latestTelemetry.point_b_px[0]), y: Number(latestTelemetry.point_b_px[1]) })
      : null;
  if (pointA) {
    if (livePointAXInput) {
      livePointAXInput.value = String(pointA.x);
    }
    if (livePointAYInput) {
      livePointAYInput.value = String(pointA.y);
    }
  }
  if (pointB) {
    if (livePointBXInput) {
      livePointBXInput.value = String(pointB.x);
    }
    if (livePointBYInput) {
      livePointBYInput.value = String(pointB.y);
    }
  }
  liveRunState.directionProjectionOverlay = directionProjectionOverlayFromTelemetry(latestTelemetry, pointA, pointB);
  updatePointSummaries();
}

async function refreshTrackingPreviewFrame(runId) {
  try {
    await loadFrozenPreviewFrame({
      runId,
      cached: true,
      refreshDetail: false,
      seedDefaults: false,
      tracking: true,
    });
    return true;
  } catch (error) {
    return false;
  }
}

function formatLiveProcessTemperature(value) {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)} °C` : "--";
}

function liveProcessOutlierCount(curve) {
  return (Array.isArray(curve) ? curve : []).filter((point) => liveProcessPointIsOutlier(point)).length;
}

function liveProcessStatusLabel(status, latest) {
  if (latest && String(latest.tracking_state || "") === "invalidated") {
    return currentLocale === "en" ? "Attention" : "异常";
  }
  if (["running", "stopping", "invalidated"].includes(String(status || ""))) {
    return currentLocale === "en" ? "Normal" : "正常";
  }
  if (!status) {
    return currentLocale === "en" ? "Waiting" : "等待";
  }
  return localizeStateLabel(status);
}

function liveProcessStatusTone(status, latest) {
  if (latest && String(latest.tracking_state || "") === "invalidated") {
    return "fail";
  }
  if (["running", "completed"].includes(String(status || ""))) {
    return "ok";
  }
  if (["aborted", "stopping", "invalidated"].includes(String(status || ""))) {
    return "warn";
  }
  return "pending";
}

function resetLiveProcessTelemetry({ show = false } = {}) {
  liveRunState.liveProcessResult = null;
  liveRunState.latestTelemetry = null;
  if (liveProcessPanelNode) {
    liveProcessPanelNode.hidden = !show;
  }
  if (liveProcessStatusPillNode) {
    liveProcessStatusPillNode.className = "status-pill status-pending";
    liveProcessStatusPillNode.textContent = currentLocale === "en" ? "Waiting" : "等待";
  }
  if (liveProcessChartLayersNode) {
    liveProcessChartLayersNode.innerHTML = "";
  }
  if (liveProcessChartEmptyNode) {
    liveProcessChartEmptyNode.hidden = false;
    liveProcessChartEmptyNode.style.display = "block";
    liveProcessChartEmptyNode.textContent = currentLocale === "en" ? "No data" : "暂无数据";
  }
  if (liveProcessChannelStatusNode) {
    liveProcessChannelStatusNode.textContent = currentLocale === "en" ? "Waiting" : "等待";
  }
  if (liveProcessPointCountNode) {
    liveProcessPointCountNode.textContent = "0";
  }
  if (liveProcessOutlierCountNode) {
    liveProcessOutlierCountNode.textContent = "0";
  }
  if (liveProcessAsValueNode) {
    liveProcessAsValueNode.textContent = "--";
  }
  if (liveProcessAfTanValueNode) {
    liveProcessAfTanValueNode.textContent = "--";
  }
}

function renderLiveProcessChart(curve, { status = "" } = {}) {
  if (!liveProcessChartLayersNode || !liveProcessChartEmptyNode) {
    return;
  }
  const rawSamples = (Array.isArray(curve) ? curve : [])
    .filter((point) => Number.isFinite(Number(point.space1_px)))
    .filter((point) => !liveProcessPointIsOutlier(point));
  const chartSeries = buildLiveProcessChartSeries(rawSamples, { status });
  const samples = chartSeries.samples;
  const useTemperatureAxis = chartSeries.useTemperatureAxis;
  if (!samples.length) {
    liveProcessChartLayersNode.innerHTML = "";
    liveProcessChartEmptyNode.hidden = false;
    liveProcessChartEmptyNode.style.display = "block";
    return;
  }
  const xValues = chartSeries.xValues;
  const displaySamples = smoothLiveProcessDisplaySamples(samples);
  const displayYValues = displaySamples.map((point) => Number(point.space1_px));
  const yValues = samples
    .map((point) => Number(point.space1_px))
    .concat(displayYValues);
  const width = 640;
  const height = 220;
  const padding = { top: 20, right: 18, bottom: 46, left: 58 };
  const scaler = buildChartScaler(xValues, yValues, width, height, padding, {
    minXSpan: useTemperatureAxis ? null : 12,
  });
  const smoothedPath = buildLiveProcessSmoothPath(
    displaySamples.map((point, index) => ({
      x: scaler.x(xValues[index]),
      y: scaler.y(Number(point.space1_px)),
    })),
  );
  const xLabel = currentLocale === "en" ? "Temperature (°C)" : "温度 (°C)";
  const yLabel = currentLocale === "en" ? "Deformation / Space1 (px)" : "形变 / Space1 (px)";
  liveProcessChartLayersNode.innerHTML = `
    ${renderWorkspaceChartGrid(width, height, padding, 5, 4)}
    <path class="live-process-chart-line live-process-chart-smooth-line" fill="none" stroke="${AFAS_CHART_THEME.highlight}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="${smoothedPath}"></path>
    ${renderChartAxes(width, height, padding, scaler, {
      xLabel,
      yLabel,
      xFormatter: formatChartTick,
      yFormatter: formatChartTick,
    })}
  `;
  liveProcessChartEmptyNode.hidden = true;
  liveProcessChartEmptyNode.style.display = "none";
}

function smoothLiveProcessDisplaySamples(samples) {
  const sourceSamples = Array.isArray(samples) ? samples : [];
  if (sourceSamples.length < 5) {
    return sourceSamples;
  }
  const windowSize = liveProcessSmoothingWindowSize(sourceSamples.length);
  const halfWindow = Math.floor(windowSize / 2);
  return sourceSamples.map((point, index) => {
    const start = Math.max(0, index - halfWindow);
    const end = Math.min(sourceSamples.length, index + halfWindow + 1);
    const values = sourceSamples
      .slice(start, end)
      .map((sample) => Number(sample.space1_px))
      .filter((value) => Number.isFinite(value));
    if (!values.length) {
      return point;
    }
    return {
      ...point,
      space1_px: weightedAverage(values),
      raw_space1_px: Number(point.space1_px),
      display_smoothing: "moving_weighted_average",
      display_smoothing_window: windowSize,
    };
  });
}

function liveProcessSmoothingWindowSize(sampleCount) {
  const count = Math.max(0, Number(sampleCount) || 0);
  if (count < 5) {
    return 1;
  }
  const scaled = Math.max(5, Math.min(21, Math.floor(count / 16) * 2 + 5));
  return scaled % 2 === 1 ? scaled : scaled + 1;
}

function weightedAverage(values) {
  const numericValues = (Array.isArray(values) ? values : [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  if (!numericValues.length) {
    return null;
  }
  const center = (numericValues.length - 1) / 2;
  let weightedSum = 0;
  let weightTotal = 0;
  numericValues.forEach((value, index) => {
    const weight = numericValues.length - Math.abs(index - center);
    weightedSum += value * weight;
    weightTotal += weight;
  });
  return weightedSum / weightTotal;
}

function buildLiveProcessSmoothPath(points) {
  const pathPoints = (Array.isArray(points) ? points : []).filter(
    (point) => Number.isFinite(point.x) && Number.isFinite(point.y),
  );
  if (!pathPoints.length) {
    return "";
  }
  if (pathPoints.length === 1) {
    return `M ${pathPoints[0].x} ${pathPoints[0].y}`;
  }
  if (pathPoints.length < 4) {
    return pathPoints
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
      .join(" ");
  }
  const commands = [`M ${pathPoints[0].x} ${pathPoints[0].y}`];
  for (let index = 0; index < pathPoints.length - 1; index += 1) {
    const previous = pathPoints[Math.max(0, index - 1)];
    const current = pathPoints[index];
    const next = pathPoints[index + 1];
    const afterNext = pathPoints[Math.min(pathPoints.length - 1, index + 2)];
    const controlOne = {
      x: current.x + (next.x - previous.x) / 6,
      y: current.y + (next.y - previous.y) / 6,
    };
    const controlTwo = {
      x: next.x - (afterNext.x - current.x) / 6,
      y: next.y - (afterNext.y - current.y) / 6,
    };
    commands.push(`C ${controlOne.x} ${controlOne.y}, ${controlTwo.x} ${controlTwo.y}, ${next.x} ${next.y}`);
  }
  return commands.join(" ");
}

function liveProcessPointIsOutlier(point) {
  const trackingState = String(point?.tracking_state || "");
  const quality = Number(point?.tracking_quality);
  return trackingState === "holding_last_good" || trackingState === "invalidated" || (Number.isFinite(quality) && quality < 0.5);
}

function buildLiveProcessChartSeries(rawSamples, { status = "" } = {}) {
  const samples = Array.isArray(rawSamples) ? rawSamples : [];
  void status;
  const finiteTemperatures = samples
    .map((point) => Number(point.temperature_celsius))
    .filter((value) => Number.isFinite(value));
  const useTemperatureAxis = finiteTemperatures.length >= 1;
  if (!useTemperatureAxis) {
    return {
      useTemperatureAxis: true,
      samples: [],
      xValues: [],
    };
  }

  const buckets = new Map();
  samples.forEach((point, index) => {
    const temperature = Number(point.temperature_celsius);
    const value = Number(point.space1_px);
    if (!Number.isFinite(temperature) || !Number.isFinite(value)) {
      return;
    }
    const key = temperature.toFixed(2);
    if (!buckets.has(key)) {
      buckets.set(key, {
        temperature,
        values: [],
        firstIndex: index,
      });
    }
    const bucket = buckets.get(key);
    bucket.values.push(value);
  });
  const temperatureSamples = Array.from(buckets.values())
    .map((bucket) => ({
      temperature_celsius: bucket.temperature,
      space1_px: medianNumber(bucket.values),
      sample_index: bucket.firstIndex,
    }))
    .sort((first, second) => Number(first.temperature_celsius) - Number(second.temperature_celsius));
  return {
    useTemperatureAxis: true,
    samples: temperatureSamples,
    xValues: temperatureSamples.map((point) => Number(point.temperature_celsius)),
  };
}

function medianNumber(values) {
  const numericValues = (Array.isArray(values) ? values : [])
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
    .sort((first, second) => first - second);
  if (!numericValues.length) {
    return null;
  }
  const middle = Math.floor(numericValues.length / 2);
  if (numericValues.length % 2 === 1) {
    return numericValues[middle];
  }
  return (numericValues[middle - 1] + numericValues[middle]) / 2;
}

function renderLiveProcessTelemetry(telemetryPayload, resultPayload = null) {
  if (!liveProcessPanelNode) {
    return;
  }
  if (resultPayload) {
    liveRunState.liveProcessResult = resultPayload;
  }
  const result = resultPayload || liveRunState.liveProcessResult;
  const curve = Array.isArray(telemetryPayload?.curve) ? telemetryPayload.curve : [];
  const latest = telemetryPayload?.latest || curve[curve.length - 1] || null;
  const status = telemetryPayload?.status || liveRunState.detail?.status || "";
  const statusLabel = liveProcessStatusLabel(status, latest);
  const statusTone = liveProcessStatusTone(status, latest);
  liveProcessPanelNode.hidden = false;
  if (liveProcessStatusPillNode) {
    liveProcessStatusPillNode.className = `status-pill status-${statusTone}`;
    liveProcessStatusPillNode.textContent = statusLabel;
  }
  if (liveProcessChannelStatusNode) {
    liveProcessChannelStatusNode.textContent = statusLabel;
  }
  if (liveProcessPointCountNode) {
    liveProcessPointCountNode.textContent = String(curve.length);
  }
  if (liveProcessOutlierCountNode) {
    liveProcessOutlierCountNode.textContent = String(liveProcessOutlierCount(curve));
  }
  if (liveProcessAsValueNode) {
    liveProcessAsValueNode.textContent = formatLiveProcessTemperature(result?.as_value);
  }
  if (liveProcessAfTanValueNode) {
    liveProcessAfTanValueNode.textContent = formatLiveProcessTemperature(result?.af_value);
  }
  renderLiveProcessChart(curve, { status });
}

function stopLiveTrackingLoop() {
  if (liveRunState.liveTrackingTimer) {
    window.clearInterval(liveRunState.liveTrackingTimer);
    liveRunState.liveTrackingTimer = null;
  }
}

function startLiveTrackingLoop(runId) {
  stopLiveTrackingLoop();
  let trackingInFlight = false;
  let terminalHandled = false;
  const tick = async () => {
    if (trackingInFlight) {
      return;
    }
    trackingInFlight = true;
    try {
      const detail = await refreshLiveRunDetail(runId);
      const telemetryResponse = await fetch(`/api/runs/${runId}/telemetry`);
      const telemetryPayload = telemetryResponse.ok ? await telemetryResponse.json() : null;
      if (telemetryPayload?.latest) {
        renderCurrentTemperature({ temperature_celsius: telemetryPayload.latest.temperature_celsius });
        applyTrackedPointInputs(telemetryPayload.latest);
        renderLivePreviewOverlay();
      }
      if (telemetryPayload) {
        renderLiveProcessTelemetry(telemetryPayload);
      }
      await refreshTrackingPreviewFrame(runId);
      if (isLiveRunTerminalStatus(detail.status) && !terminalHandled) {
        terminalHandled = true;
        stopLiveTrackingLoop();
        startCurrentTemperaturePolling();
        await loadRecentSessions();
        if (detail.status === "completed") {
          const resultResponse = await fetch(`/api/runs/${runId}/result`);
          const resultPayload = resultResponse.ok ? await resultResponse.json() : null;
          renderLiveProcessTelemetry(telemetryPayload, resultPayload);
          await hydrateHomeResultForSession(runId, resultPayload);
          setLiveRunMessage(
            currentLocale === "en"
              ? `Live run completed. point_count=${resultPayload?.point_count ?? "n/a"} af95=${resultPayload?.af95 ?? "n/a"}.`
              : `实时测试已完成。点数=${resultPayload?.point_count ?? "n/a"} af95=${resultPayload?.af95 ?? "n/a"}。`,
            "success",
          );
        } else if (detail.status === "aborted") {
          const fallbackPayload = {
            session_id: runId,
            state: "aborted",
            point_count: telemetryPayload?.curve?.length ?? 0,
            af95: null,
          };
          renderLiveProcessTelemetry(telemetryPayload, fallbackPayload);
          await hydrateHomeResultForSession(runId, fallbackPayload);
          setLiveRunMessage(
            currentLocale === "en"
              ? `Live run stopped. samples=${telemetryPayload?.curve?.length ?? "n/a"}. You can save data or open analysis.`
              : `实时测试已停止。采样数=${telemetryPayload?.curve?.length ?? "n/a"}。现在可以保存数据或进入分析。`,
            "warning",
          );
        } else {
          setLiveRunMessage(
            currentLocale === "en" ? `Live run ended with status=${detail.status}.` : `实时测试结束，状态=${detail.status}。`,
            "error",
          );
        }
      }
    } catch (error) {
      stopLiveTrackingLoop();
      startCurrentTemperaturePolling();
      setLiveRunMessage(String(error), "error");
    } finally {
      trackingInFlight = false;
      updateLiveRunControls();
    }
  };
  void tick();
  liveRunState.liveTrackingTimer = window.setInterval(() => {
    void tick();
  }, LIVE_TRACKING_POLL_MS);
}

function buildLiveDefinitionBasePayload({ coordinateSpace = "preview" } = {}) {
  const roiBox = getCurrentRoiBox();
  const metricBox = getCurrentMetricBox();
  const payload = {
    analysis_roi: boundingRectForMetricBox(roiBox),
    metric_box: metricBox,
    direction_angle_deg: Number(roiBox.angle_deg || 0),
    direction_projection_mode: currentDirectionProjectionMode(),
    // Use the same contour-direction path for preset and live run. The backend
    // still receives the rotated ROI box and clips the contour search to it.
    observation_axis: "long_axis",
    foreground_polarity: liveForegroundPolaritySelect ? liveForegroundPolaritySelect.value : "dark_on_light",
    threshold_mode: liveThresholdModeSelect ? liveThresholdModeSelect.value : "adaptive",
    target_geometry_mode: currentTargetGeometryMode(),
    side_guard_ratio: currentSideGuardRatio(),
    envelope_min_support_px: currentEnvelopeMinSupportPx(),
    envelope_quantile: currentEnvelopeQuantile(),
    ignore_internal_texture: liveIgnoreInternalTextureInput ? liveIgnoreInternalTextureInput.checked : false,
    min_target_area_px: getNumericInputValue(liveMinTargetAreaInput, 200),
    sensitivity: getNumericInputValue(liveSensitivityInput, 50),
  };
  return coordinateSpace === "source" ? mapDefinitionToCoordinateSpace(payload, "source") : payload;
}

function buildLiveDefinitionPayload({ coordinateSpace = "preview" } = {}) {
  const payload = {
    ...buildLiveDefinitionBasePayload(),
    point_a_px: {
      x: getNumericInputValue(livePointAXInput),
      y: getNumericInputValue(livePointAYInput),
    },
    point_b_px: {
      x: getNumericInputValue(livePointBXInput),
      y: getNumericInputValue(livePointBYInput),
    },
  };
  return coordinateSpace === "source" ? mapDefinitionToCoordinateSpace(payload, "source") : payload;
}

async function createLiveRun({ autoStartPreview = false, silent = false, forceReset = true } = {}) {
  if (!silent) {
    setLiveRunMessage("Creating live setup session...", "info");
  }
  try {
    if (forceReset) {
      stopLiveTrackingLoop();
      await stopLivePreviewStream({ clearImage: true, silent: true });
      resetLiveDefinitionInputs();
      resetLiveProcessTelemetry();
      liveRunState.confirmedTemperatureSettings = null;
      clearTemperatureSettingsConfirmation();
    }
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        preset: liveRunPresetSelect ? liveRunPresetSelect.value : "balloon",
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Failed to create live run: ${response.status}`));
    }
    await refreshLiveRunDetail(payload.run_id);
    storeLiveSetupRunId(payload.run_id);
    if (liveRunPresetSelect) {
      liveRunPresetNode.textContent = liveRunPresetSelect.value;
    }
    if (autoStartPreview) {
      await startLivePreviewStream({ silent: true });
      setLivePointPickerStatus(
        currentLocale === "en"
          ? "Live preview is running. Press Freeze to capture a still frame, then draw the ROI."
          : "实时预览正在运行，请先冻结画面，再框选 ROI。",
      );
      if (!silent) {
        setLiveRunMessage(
          currentLocale === "en" ? "Live setup session created. Live preview started automatically." : "已创建 live setup 会话，实时预览已自动启动。",
          "success",
        );
      }
    } else if (!silent) {
      setLiveRunMessage(currentLocale === "en" ? "Live setup session created." : "已创建 live setup 会话。", "success");
    }
    return payload.run_id;
  } catch (error) {
    if (!silent) {
      setLiveRunMessage(String(error), "error");
    }
    throw error;
  } finally {
    updateLiveRunControls();
  }
}

async function fetchLivePreview() {
  if (!liveRunState.runId) {
    return;
  }
  setLiveRunMessage(currentLocale === "en" ? "Fetching preview frame..." : "正在获取预览画面...", "info");
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    await loadFrozenPreviewFrame({ runId: liveRunState.runId, cached: false });
    setLivePointPickerStatus(
      currentLocale === "en" ? "Preview loaded. Draw the ROI first; ROI-local A/B will be recomputed automatically." : "预览已加载，请先框选 ROI。",
    );
    setLiveRunMessage(currentLocale === "en" ? "Preview frame loaded." : "预览画面已加载。", "success");
  } catch (error) {
    liveRunState.previewSize = null;
    liveRunState.previewSourceSize = null;
    setLiveRunMessage(String(error), "error");
  }
  updateLiveRunControls();
}

async function startLivePreviewStream({ silent = false } = {}) {
  if (!liveRunState.runId || !livePreviewImageNode) {
    return;
  }
  if (!silent) {
    setLiveRunMessage(currentLocale === "en" ? "Starting live preview stream..." : "正在启动实时预览...", "info");
  }
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    revokeLivePreviewUrl();
    liveRunState.previewStreamRecovering = false;
    liveRunState.previewStreamUrl = `/api/runs/${liveRunState.runId}/preview/stream?ts=${Date.now()}`;
    liveRunState.previewStreamActive = true;
    liveRunState.previewFrozenAvailable = false;
    showLivePreviewStage();
    livePreviewImageNode.src = liveRunState.previewStreamUrl;
    updateLiveRunControls();
    startLivePreviewStatusPolling();
    setActiveLiveTool("");
    setLivePointPickerStatus(
      currentLocale === "en" ? "Live preview is running. Press Freeze to capture an editable still frame." : "实时预览正在运行。按“冻结画面”抓取静帧。",
    );
    if (!silent) {
      setLiveRunMessage(
        currentLocale === "en" ? "Live preview stream started. Press Freeze to capture an editable still frame." : "实时预览已启动。按“冻结画面”抓取静帧。",
        "success",
      );
    }
    try {
      await refreshLiveRunDetail(liveRunState.runId);
    } catch (error) {
      if (!silent) {
        setLiveRunMessage(String(error), "error");
      }
    }
  } catch (error) {
    liveRunState.previewStreamActive = false;
    liveRunState.previewStreamUrl = "";
    stopLivePreviewStatusPolling();
    if (!silent) {
      setLiveRunMessage(String(error), "error");
    }
  } finally {
    updateLiveRunControls();
  }
}

async function recoverLivePreviewStreamError() {
  if (liveRunState.previewStreamRecovering) {
    return;
  }
  const runId = liveRunState.runId;
  if (!runId) {
    return;
  }
  liveRunState.previewStreamRecovering = true;
  liveRunState.previewStreamActive = false;
  liveRunState.previewStreamUrl = "";
  stopLivePreviewStatusPolling();
  if (livePreviewImageNode) {
    livePreviewImageNode.removeAttribute("src");
    livePreviewImageNode.hidden = true;
  }
  updateLiveRunControls();
  try {
    try {
      await fetch(`/api/runs/${runId}/preview/stream/stop`, { method: "POST" });
    } catch (error) {
      // Best effort only. The browser-side stream request may already be gone.
    }
    await loadFrozenPreviewFrame({
      runId,
      cached: true,
      refreshDetail: true,
      seedDefaults: false,
    });
    liveRunState.previewFrozenAvailable = true;
    setActiveLiveTool("");
    setLivePointPickerStatus(
      currentLocale === "en"
        ? "Live preview stream interrupted. Recovered the last cached frame for editing."
        : "实时预览流已中断，已恢复最后一帧静帧供继续编辑。",
    );
    setLiveRunMessage(
      currentLocale === "en"
        ? "Live preview stream failed. Restored the last cached frame for editing."
        : "实时预览流已中断，已恢复最后一帧静帧。",
      "error",
    );
  } catch (error) {
    refreshLiveRunDetail(runId).catch(() => {});
    setLiveRunMessage(
      currentLocale === "en"
        ? "Live preview stream failed and the cached frame could not be restored automatically."
        : "实时预览流已中断，且未能自动恢复最后一帧静帧。",
      "error",
    );
  } finally {
    liveRunState.previewStreamRecovering = false;
    updateLiveRunControls();
  }
}

async function stopLivePreviewStream({ clearImage = false, silent = false } = {}) {
  const hadActiveStream = liveRunState.previewStreamActive;
  const streamRunId = liveRunState.runId;
  const hydrateFrozenFrame = hadActiveStream && !clearImage && !silent;
  liveRunState.previewStreamActive = false;
  liveRunState.previewStreamUrl = "";
  stopLivePreviewStatusPolling();
  if (hadActiveStream && livePreviewImageNode) {
    livePreviewImageNode.removeAttribute("src");
    livePreviewImageNode.hidden = true;
  }
  if (clearImage) {
    clearLivePreviewImage();
  }
  if (hadActiveStream && streamRunId) {
    try {
      const response = await fetch(`/api/runs/${streamRunId}/preview/stream/stop`, { method: "POST" });
      const payload = await response.json();
      if (response.ok) {
        renderLiveRunDetail(payload);
      }
    } catch (error) {
      // Best effort only; the browser closing the img request normally releases the stream.
    }
  }
  if (hydrateFrozenFrame && streamRunId) {
    try {
      await loadFrozenPreviewFrame({ runId: streamRunId, cached: true });
    } catch (error) {
      if (!silent) {
        setLiveRunMessage(String(error), "error");
      }
    }
  }
  if (!silent) {
    setActiveLiveTool("");
    setLivePointPickerStatus(
      currentLocale === "en" ? "Preview frozen. Draw the ROI first; ROI-local A/B will be recomputed automatically." : "画面已冻结，请先框选 ROI。",
    );
    if (!hydrateFrozenFrame) {
      setLiveRunMessage(currentLocale === "en" ? "Preview frozen on the last frame." : "画面已冻结。", "info");
    } else {
      setLiveRunMessage(currentLocale === "en" ? "Preview frozen. Refreshed the still frame for editing." : "画面已冻结，并已刷新为可编辑静帧。", "info");
    }
  }
  updateLiveRunControls();
}

async function loadFrozenPreviewFrame({ runId, cached = false, refreshDetail = true, seedDefaults = true, tracking = false }) {
  const queryParams = new URLSearchParams();
  if (cached) {
    queryParams.set("cached", "1");
  }
  if (tracking) {
    queryParams.set("tracking", "1");
  }
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  const response = await fetch(`/api/runs/${runId}/preview/frame${query}`, {
    method: "POST",
  });
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch (jsonError) {
      payload = null;
    }
    throw new Error(parseErrorDetail(payload, `Preview fetch failed: ${response.status}`));
  }
  const width = Number(response.headers.get("X-Frame-Width") || "0");
  const height = Number(response.headers.get("X-Frame-Height") || "0");
  const sourceWidth = Number(response.headers.get("X-Frame-Source-Width") || String(width || 0));
  const sourceHeight = Number(response.headers.get("X-Frame-Source-Height") || String(height || 0));
  const frameId = Number(response.headers.get("X-Frame-Id") || "0");
  const blob = await response.blob();
  revokeLivePreviewUrl();
  liveRunState.previewObjectUrl = URL.createObjectURL(blob);
  liveRunState.previewSize = width > 0 && height > 0 ? { width, height } : null;
  liveRunState.previewSourceSize =
    sourceWidth > 0 && sourceHeight > 0 ? { width: sourceWidth, height: sourceHeight } : liveRunState.previewSize;
  renderLivePreviewMeta();
  if (Number.isFinite(frameId) && frameId > 0) {
    liveRunState.lastPreviewFrameId = frameId;
  }
  if (livePreviewImageNode) {
    livePreviewImageNode.src = liveRunState.previewObjectUrl;
    showLivePreviewStage();
  }
  if (seedDefaults && liveRunState.previewSize) {
    seedLiveDefinitionDefaults(liveRunState.previewSize.width, liveRunState.previewSize.height);
  }
  if (refreshDetail) {
    await refreshLiveRunDetail(runId);
  }
}

async function autoDetectLiveDefinition({ silent = false, origin = "button", recomputeToken = null } = {}) {
  if (!liveRunState.runId || !hasValidAnalysisRoi()) {
    return;
  }
  if (!silent) {
    setLiveRunMessage("Auto-detecting locked points along the contour direction...", "info");
  }
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/definition/auto`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildLiveDefinitionBasePayload({ coordinateSpace: "source" })),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Auto detect failed: ${response.status}`));
    }
    if (recomputeToken != null && recomputeToken !== liveRunState.setupRecomputeActiveToken) {
      return;
    }
    const sourceDefinition = {
      ...buildLiveDefinitionBasePayload({ coordinateSpace: "source" }),
      point_a_px: payload.point_a_px,
      point_b_px: payload.point_b_px,
    };
    const previewDefinition = mapDefinitionToCoordinateSpace(sourceDefinition, "preview");
    const previewBox = {
      ...(previewDefinition.metric_box || metricBoxFromRect(previewDefinition.analysis_roi)),
      angle_deg: Number(previewDefinition.direction_angle_deg ?? previewDefinition.metric_box?.angle_deg ?? 0),
    };
    applyMetricBoxToInputs(previewBox);
    if (livePointAXInput) {
      livePointAXInput.value = String(previewDefinition.point_a_px.x);
    }
    if (livePointAYInput) {
      livePointAYInput.value = String(previewDefinition.point_a_px.y);
    }
    if (livePointBXInput) {
      livePointBXInput.value = String(previewDefinition.point_b_px.x);
    }
    if (livePointBYInput) {
      livePointBYInput.value = String(previewDefinition.point_b_px.y);
    }
    liveRunState.directionProjectionOverlay = directionProjectionOverlayFromAutoPayload(payload);
    liveRunState.resolvedDirectionProjectionMode = isDirectionProjectionMode(payload.direction_projection_mode)
      ? String(payload.direction_projection_mode)
      : "max_chord";
    if (liveDirectionProjectionModeSelect) {
      liveDirectionProjectionModeSelect.value = liveRunState.resolvedDirectionProjectionMode;
    }
    if (liveTargetGeometryModeSelect && payload.target_geometry_mode) {
      liveTargetGeometryModeSelect.value = String(payload.target_geometry_mode);
    }
    if (liveSideGuardRatioInput && payload.side_guard_ratio != null) {
      liveSideGuardRatioInput.value = String(payload.side_guard_ratio);
    }
    if (liveEnvelopeMinSupportInput && payload.envelope_min_support_px != null) {
      liveEnvelopeMinSupportInput.value = String(payload.envelope_min_support_px);
    }
    if (liveEnvelopeQuantileInput && payload.envelope_quantile != null) {
      liveEnvelopeQuantileInput.value = String(payload.envelope_quantile);
    }
    if (liveThresholdModeSelect && payload.threshold_mode_used) {
      liveThresholdModeSelect.value = String(payload.threshold_mode_used);
    }
    if (liveForegroundPolaritySelect && payload.foreground_polarity_used) {
      liveForegroundPolaritySelect.value = String(payload.foreground_polarity_used);
    }
    liveRunState.definitionDirty = true;
    syncLiveDefinitionDirtyState();
    renderLivePreviewOverlay();
    setLivePointPickerStatus(
      currentLocale === "en"
        ? "ROI-local A/B is ready. Review the result and recompute from a fresh frame if needed."
        : "ROI 内 A/B 已就绪。如有需要，请基于新画面重新计算。",
    );
    if (!silent || payload.detail) {
      setLiveRunMessage(
        payload.detail ||
          `ROI-local A/B updated. quality=${payload.quality.toFixed(2)} span=${payload.metric_raw?.toFixed(2) ?? "n/a"}.`,
        payload.detail ? "info" : "success",
      );
    }
  } catch (error) {
    if (recomputeToken != null && recomputeToken !== liveRunState.setupRecomputeActiveToken) {
      return;
    }
    if (!silent || origin !== "roi-refresh") {
      setLiveRunMessage(String(error), "error");
    }
    throw error;
  }
  updateLiveRunControls();
}

async function persistLiveDefinition({ announce = true } = {}) {
  if (!liveRunState.runId) {
    return null;
  }
  if (!hasLocallyCompleteDefinition()) {
    throw new Error(currentLocale === "en" ? "ROI and A/B must be valid before starting." : "需要先让 ROI 和 A/B 进入有效状态。");
  }
  if (saveLiveDefinitionButton) {
    saveLiveDefinitionButton.disabled = true;
  }
  if (announce) {
    setLiveRunMessage(currentLocale === "en" ? "Syncing live setup..." : "正在同步实时测试参数...", "info");
  }
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/definition`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildLiveDefinitionPayload({ coordinateSpace: "source" })),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Definition save failed: ${response.status}`));
    }
    renderLiveRunDetail(payload);
    liveRunState.definitionDirty = false;
    if (announce) {
      setLiveRunMessage(
        payload.status === "run_ready"
          ? currentLocale === "en"
            ? "Setup synced. You can start the live run now."
            : "参数已同步，现在可以开始实时测试。"
          : currentLocale === "en"
            ? "Setup synced."
            : "参数已同步。",
        "success",
      );
    }
    return payload;
  } catch (error) {
    if (announce) {
      setLiveRunMessage(String(error), "error");
    }
    throw error;
  } finally {
    if (saveLiveDefinitionButton) {
      saveLiveDefinitionButton.disabled = false;
    }
    updateLiveRunControls();
  }
}

async function saveLiveDefinition() {
  await persistLiveDefinition({ announce: true });
}

function updateLiveDefinitionAfterLocalEdit({ constrain = true } = {}) {
  liveRunState.resolvedDirectionProjectionMode = "max_chord";
  if (constrain) {
    ensureMetricBoxWithinAnalysisRoi();
  }
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  updateLiveRunControls();
}

function getOverlayCoordinates(event) {
  if (!livePreviewOverlayNode || !liveRunState.previewSize) {
    return null;
  }
  const rect = livePreviewOverlayNode.getBoundingClientRect();
  const xRatio = liveRunState.previewSize.width / rect.width;
  const yRatio = liveRunState.previewSize.height / rect.height;
  return {
    x: Math.max(0, Math.min(liveRunState.previewSize.width - 1, Math.round((event.clientX - rect.left) * xRatio))),
    y: Math.max(0, Math.min(liveRunState.previewSize.height - 1, Math.round((event.clientY - rect.top) * yRatio))),
  };
}

function hitTestRoiInteraction(point) {
  if (!hasValidAnalysisRoi()) {
    return null;
  }
  const box = getCurrentRoiBox();
  const metricBox = getCurrentMetricBox();
  const { handle } = metricBoxRotationHandle(box);
  if (distanceBetweenPoints(point, handle) <= 14) {
    return { tool: "rotate-roi", box };
  }
  const corners = metricBoxCorners(metricBox);
  for (const corner of metricBoxResizeHandles(metricBox)) {
    if (distanceBetweenPoints(point, corner) <= 12) {
      return {
        tool: "resize-roi",
        box,
        cornerIndex: corner.index,
        fixedCorner: corners[(corner.index + 2) % 4],
      };
    }
  }
  if (pointInRotatedMetricBox(metricBox, point.x, point.y)) {
    return { tool: "move-roi", box };
  }
  return null;
}

function handleLivePreviewPointerDown(event) {
  if (!liveRunState.previewSize || !livePreviewOverlayNode) {
    return;
  }
  const point = getOverlayCoordinates(event);
  if (!point) {
    return;
  }
  if (!liveRunState.activeTool) {
    const hit = hitTestRoiInteraction(point);
    if (!hit) {
      return;
    }
    liveRunState.overlayDrag = {
      ...hit,
      startX: point.x,
      startY: point.y,
      originalCenterX: hit.box.center_x,
      originalCenterY: hit.box.center_y,
      originalAngleDeg: hit.box.angle_deg,
    };
    livePreviewOverlayNode.setPointerCapture(event.pointerId);
    return;
  }
  liveRunState.overlayDrag = {
    tool: liveRunState.activeTool,
    startX: point.x,
    startY: point.y,
  };
  livePreviewOverlayNode.setPointerCapture(event.pointerId);
}

function handleLivePreviewPointerMove(event) {
  if (!liveRunState.overlayDrag) {
    return;
  }
  const point = getOverlayCoordinates(event);
  if (!point) {
    return;
  }
  const drag = liveRunState.overlayDrag;
  if (drag.tool === "draw-roi") {
    const x = Math.min(drag.startX, point.x);
    const y = Math.min(drag.startY, point.y);
    const width = Math.max(1, Math.abs(point.x - drag.startX) + 1);
    const height = Math.max(1, Math.abs(point.y - drag.startY) + 1);
    applyMetricBoxToInputs({
      center_x: Math.round(x + width / 2),
      center_y: Math.round(y + height / 2),
      width,
      height,
      angle_deg: 0,
    });
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "move-roi") {
    applyMetricBoxToInputs({
      center_x: drag.originalCenterX + (point.x - drag.startX),
      center_y: drag.originalCenterY + (point.y - drag.startY),
      width: drag.box.width,
      height: drag.box.height,
      angle_deg: drag.originalAngleDeg,
    });
    ensureMetricBoxWithinAnalysisRoi();
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "resize-roi") {
    applyMetricBoxToInputs(resizeMetricBoxFromFixedCorner(drag.box, drag.fixedCorner, point));
    ensureMetricBoxWithinAnalysisRoi();
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "rotate-roi") {
    const box = getCurrentRoiBox();
    applyMetricBoxToInputs(rotateMetricBoxAroundCenter(box, point));
    updateLiveDefinitionAfterLocalEdit({ constrain: false });
  }
}

function handleLivePreviewPointerUp(event) {
  if (!liveRunState.overlayDrag || !livePreviewOverlayNode) {
    return;
  }
  livePreviewOverlayNode.releasePointerCapture(event.pointerId);
  const completedTool = liveRunState.overlayDrag.tool;
  liveRunState.overlayDrag = null;
  if (completedTool === "draw-roi") {
    commitAnalysisRoiSelection({
      force: true,
      message: currentLocale === "en" ? "ROI updated from the preview overlay." : "ROI 已从预览中更新。",
    });
  } else if (["move-roi", "resize-roi"].includes(completedTool)) {
    commitAnalysisRoiSelection({
      force: true,
      message:
        currentLocale === "en" ? "ROI adjusted. Capturing a new frame to recompute ROI-local A/B." : "ROI 已调整，正在抓取新画面并重算 ROI 内 A/B。",
    });
  } else if (completedTool === "rotate-roi") {
    commitAnalysisRoiSelection({
      force: true,
      constrain: false,
      message:
        currentLocale === "en" ? "ROI adjusted. Capturing a new frame to recompute ROI-local A/B." : "ROI 已调整，正在抓取新画面并重算 ROI 内 A/B。",
    });
  }
  setActiveLiveTool("");
}

async function startLiveRun() {
  if (!liveRunState.runId || !startLiveRunButton) {
    return;
  }
  if (!isTemperatureSettingsConfirmed()) {
    setLiveRunMessage(
      currentLocale === "en"
        ? "Confirm the bundled temperature settings before starting the live run."
        : "开始实时测试前，请先确认整包温控设置。",
      "warning",
    );
    updateLiveRunControls();
    return;
  }
  if (!hasLocallyCompleteDefinition()) {
    setLiveRunMessage(
      currentLocale === "en"
        ? "ROI and A/B must be valid before starting the live run."
        : "开始实时测试前，需要先确认有效的 ROI 和 A/B。",
      "warning",
    );
    updateLiveRunControls();
    return;
  }
  startLiveRunButton.disabled = true;
  stopCurrentTemperaturePolling();
  resetLiveProcessTelemetry({ show: true });
  setLiveRunMessage(currentLocale === "en" ? "Starting live run..." : "正在开始实时测试...", "info");
  try {
    if (liveRunState.definitionDirty || !liveRunState.detail || liveRunState.detail.status !== "run_ready") {
      await persistLiveDefinition({ announce: false });
    }
    await stopLivePreviewStream({ clearImage: false, silent: true });
    const response = await fetch(`/api/runs/${liveRunState.runId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_temperature_celsius: getNumericInputValue(liveTargetTemperatureInput, 25),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Live run start failed: ${response.status}`));
    }
    await refreshLiveRunDetail(liveRunState.runId);
    startLiveTrackingLoop(liveRunState.runId);
    setLiveRunMessage(
      currentLocale === "en"
        ? `Live run started. session=${payload.session_id}.`
        : `实时测试已开始。session=${payload.session_id}。`,
      "success",
    );
  } catch (error) {
    startCurrentTemperaturePolling();
    setLiveRunMessage(String(error), "error");
  } finally {
    startLiveRunButton.disabled = false;
    updateLiveRunControls();
  }
}

async function stopLiveRun() {
  if (!liveRunState.runId || !stopLiveRunButton) {
    return;
  }
  stopLiveRunButton.disabled = true;
  setLiveRunMessage(currentLocale === "en" ? "Stopping live run..." : "正在停止实时测试...", "info");
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/stop`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Live run stop failed: ${response.status}`));
    }
    renderLiveRunDetail(payload);
    startLiveTrackingLoop(liveRunState.runId);
    setLiveRunMessage(currentLocale === "en" ? "Stopping live run..." : "正在停止实时测试...", "info");
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    updateLiveRunControls();
  }
}

async function loadHealth() {
  const response = await fetch("/health");
  const payload = await response.json();
  updateHealthStatusBadge(payload.status);
}

async function loadProfile() {
  const response = await fetch("/api/system/profile");
  const payload = await response.json();
  if (profileNameNode) {
    profileNameNode.textContent = payload.profile;
  }
  if (profileModeNode) {
    profileModeNode.textContent = payload.mode;
  }
  syncCameraProbeDefaults(payload.profile);
}

function hideFixtureVideoSwitch() {
  if (fixtureVideoSwitchNode) {
    fixtureVideoSwitchNode.hidden = true;
  }
}

function renderFixtureVideoSwitch(payload) {
  if (!fixtureVideoSwitchNode || !fixtureVideoSelectNode) {
    return;
  }
  const videos = Array.isArray(payload?.videos) ? payload.videos : [];
  if (videos.length < 2) {
    hideFixtureVideoSwitch();
    return;
  }
  fixtureVideoSelectNode.innerHTML = videos
    .map((video) => {
      const key = String(video.key || "");
      const label = String(video.label || key);
      return `<option value="${escapeHtml(key)}">${escapeHtml(label)}</option>`;
    })
    .join("");
  fixtureVideoSelectNode.value = String(payload.current || videos[0].key || "");
  fixtureVideoSelectNode.dataset.currentKey = fixtureVideoSelectNode.value;
  fixtureVideoSelectNode.disabled = fixtureVideoSwitchBusy;
  fixtureVideoSwitchNode.hidden = false;
}

async function loadFixtureVideoSwitch() {
  if (!fixtureVideoSwitchNode || !fixtureVideoSelectNode) {
    return;
  }
  try {
    const response = await fetch("/api/debug/fixture-videos");
    if (!response.ok) {
      hideFixtureVideoSwitch();
      return;
    }
    renderFixtureVideoSwitch(await response.json());
  } catch (error) {
    hideFixtureVideoSwitch();
  }
}

async function switchFixtureVideo(videoKey) {
  if (!fixtureVideoSelectNode || fixtureVideoSwitchBusy) {
    return;
  }
  const key = String(videoKey || "");
  if (!key) {
    return;
  }
  const previousKey = fixtureVideoSelectNode.dataset.currentKey || fixtureVideoSelectNode.value;
  fixtureVideoSwitchBusy = true;
  fixtureVideoSelectNode.disabled = true;
  setLiveRunMessage(currentLocale === "en" ? "Switching fixture video..." : "正在切换模拟素材...", "info");
  try {
    stopLiveTrackingLoop();
    await stopLivePreviewStream({ clearImage: true, silent: true });
    storeLiveSetupRunId("");
    liveRunState.runId = "";
    liveRunState.detail = null;
    resetLiveDefinitionInputs();
    const response = await fetch("/api/debug/fixture-videos/current", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Fixture video switch failed: ${response.status}`));
    }
    renderFixtureVideoSwitch(payload);
    await Promise.all([loadHealth(), loadProfile()]);
    await ensureLiveSetupBootstrapped({ forceRestart: true });
    setLiveRunMessage(
      currentLocale === "en"
        ? `Fixture video switched to ${payload.current_label || payload.current || key}.`
        : `模拟素材已切换为 ${payload.current_label || payload.current || key}。`,
      "success",
    );
  } catch (error) {
    fixtureVideoSelectNode.value = previousKey;
    setLiveRunMessage(String(error), "error");
  } finally {
    fixtureVideoSwitchBusy = false;
    fixtureVideoSelectNode.disabled = false;
    updateLiveRunControls();
  }
}

function renderStatusPill(status) {
  return `<span class="status-pill status-${status}">${escapeHtml(localizeStateLabel(status))}</span>`;
}

function renderPrecheck(payload) {
  if (!precheckStatusNode || !precheckItemsNode) {
    return;
  }
  precheckState = payload;
  precheckStatusNode.innerHTML = renderStatusPill(payload.status);
  precheckItemsNode.innerHTML = (payload.items || [])
    .map(
      (item) => `
        <li class="session-item">
          <div class="session-meta">${renderStatusPill(item.status)}</div>
          <strong>${item.name}</strong>
          <div class="session-meta">${item.detail}</div>
        </li>
      `,
    )
    .join("");
}

async function loadPrecheck() {
  const response = await fetch("/api/system/precheck");
  const payload = await response.json();
  renderPrecheck(payload);
}

async function runCameraProbe() {
  if (!probeCameraButton) {
    return;
  }
  probeCameraButton.disabled = true;
  probeCameraButton.textContent = currentLocale === "en" ? "Probing..." : "正在探测...";
  try {
    const requestPayload = buildCameraProbeRequest();
    const response = await fetch("/api/system/camera/probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestPayload ? JSON.stringify(requestPayload) : null,
    });
    const cameraProbePayload = await response.json();
    const alignmentDefinition = buildRealOfflineLiveProbeRequest();
    const combinedPayload = {
      camera_probe: cameraProbePayload,
      real_offline_alignment_live_probe: null,
      real_offline_alignment_definition_attached: Boolean(alignmentDefinition),
    };
    if (alignmentDefinition) {
      const alignmentResponse = await fetch("/api/system/real-offline-alignment/live-probe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(alignmentDefinition),
      });
      combinedPayload.real_offline_alignment_live_probe = await alignmentResponse.json();
    } else {
      combinedPayload.real_offline_alignment_live_probe = {
        status: "not_attempted",
        detail:
          currentLocale === "en"
            ? "Draw and confirm ROI-local A/B before probing real-frame formal A/B alignment."
            : "请先框选 ROI 并确认 ROI 内 A/B，再探测真机帧正式 A/B 对齐。",
      };
    }
    renderCameraProbeResult(combinedPayload);
  } catch (error) {
    renderCameraProbeResult({ status: "fail", detail: String(error) });
  } finally {
    probeCameraButton.disabled = false;
    probeCameraButton.textContent = currentLocale === "en" ? "Probe Camera" : "探测相机";
  }
}

function renderRecentSessions(items) {
  if (!recentSessionsNode) {
    return;
  }
  recentSessionsState = Array.isArray(items) ? items : [];
  if (!items.length) {
    recentSessionsNode.innerHTML =
      `<li class="session-item session-item--empty">${currentLocale === "en" ? "No sessions have been recorded yet." : "尚未记录任何会话。"}</li>`;
    return;
  }

  recentSessionsNode.innerHTML = items
    .map(
      (item) => `
        <li class="session-item">
          <strong>${item.session_id}</strong>
          <div class="session-meta">
            ${currentLocale === "en" ? "state" : "状态"}=${escapeHtml(localizeStateLabel(item.state))} |
            ${currentLocale === "en" ? "point_count" : "点数"}=${item.point_count} |
            af95=${item.af95 === null ? t("common.not_applicable", {}, "n/a") : item.af95
            }
          </div>
          <a class="workspace-link" href="${workspaceUrl(item.session_id)}">${t("common.open_workspace", {}, "打开分析工作台")}</a>
        </li>
      `,
    )
    .join("");
}

async function loadRecentSessions() {
  const response = await fetch("/api/session");
  const payload = await response.json();
  renderRecentSessions(payload.items || []);
}

function renderCurve(points) {
  if (!detailCurveNode) {
    return;
  }
  if (!points.length) {
    detailCurveNode.setAttribute("points", "");
    if (detailCurveLayersNode) {
      detailCurveLayersNode.innerHTML = "";
    }
    return;
  }

  const width = 320;
  const height = 180;
  const padding = { top: 14, right: 12, bottom: 42, left: 52 };
  const finiteTemperatures = points
    .map((point) => Number(point.celsius))
    .filter((value) => Number.isFinite(value));
  const useTemperatureAxis =
    finiteTemperatures.length >= 2 && Math.max(...finiteTemperatures) - Math.min(...finiteTemperatures) > 1e-9;
  const chartPoints = points
    .map((point, index) => {
      const y = Number.isFinite(Number(point.metric_raw))
        ? Number(point.metric_raw)
        : Number.isFinite(Number(point.metric_norm))
          ? Number(point.metric_norm)
          : null;
      const x = useTemperatureAxis && Number.isFinite(Number(point.celsius)) ? Number(point.celsius) : index;
      return y === null ? null : { x, y };
    })
    .filter(Boolean);
  if (!chartPoints.length) {
    detailCurveNode.setAttribute("points", "");
    if (detailCurveLayersNode) {
      detailCurveLayersNode.innerHTML = "";
    }
    return;
  }
  const xValues = chartPoints.map((point) => point.x);
  const yValues = chartPoints.map((point) => point.y);
  const scaler = buildChartScaler(xValues, yValues, width, height, padding);
  const polylinePoints = chartPoints.map((point) => `${scaler.x(point.x)},${scaler.y(point.y)}`).join(" ");

  detailCurveNode.setAttribute("points", polylinePoints);
  if (detailCurveLayersNode) {
    detailCurveLayersNode.innerHTML = `
      ${renderWorkspaceChartGrid(width, height, padding, 4, 4)}
      ${renderChartAxes(width, height, padding, scaler, {
        xLabel: useTemperatureAxis
          ? currentLocale === "en"
            ? "Temperature (°C)"
            : "温度 (°C)"
          : currentLocale === "en"
            ? "Sample"
            : "样本点",
        yLabel: currentLocale === "en" ? "Deformation" : "形变",
        xFormatter: useTemperatureAxis ? formatChartTick : formatChartIntegerTick,
        yFormatter: formatChartTick,
        xTicks: 4,
        yTicks: 4,
      })}
    `;
  }
}

function renderKeyFrames(keyFrames) {
  if (!detailKeyFramesNode) {
    return;
  }
  if (!keyFrames.length) {
    detailKeyFramesNode.innerHTML = '<p class="session-item--empty">No replay detail loaded.</p>';
    return;
  }

  detailKeyFramesNode.innerHTML = keyFrames
    .map(
      (frame, index) => `
        <article class="key-frame-card">
          <h3>${frame.label}</h3>
          <canvas id="key-frame-canvas-${index}" class="key-frame-canvas"></canvas>
          <p>timestamp=${frame.timestamp_ms} | metric_raw=${frame.metric_raw === null ? "n/a" : frame.metric_raw}</p>
        </article>
      `,
    )
    .join("");

  keyFrames.forEach((frame, index) => {
    const canvas = document.getElementById(`key-frame-canvas-${index}`);
    if (!canvas) {
      return;
    }
    drawFrameImage(canvas, frame.image, frame.feature_point_px);
  });
}

function drawFrameImage(canvas, image, featurePoint) {
  const height = image.length;
  const width = image[0] ? image[0].length : 0;
  const scale = 12;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  image.forEach((row, y) => {
    row.forEach((value, x) => {
      context.fillStyle = `rgb(${value}, ${value}, ${value})`;
      context.fillRect(x * scale, y * scale, scale, scale);
    });
  });

  if (featurePoint) {
    context.strokeStyle = "#cf1124";
    context.lineWidth = 2;
    context.strokeRect(featurePoint[0] * scale, featurePoint[1] * scale, scale, scale);
  }
}

function renderWorkspaceSummary(summary) {
  if (!summary) {
    return;
  }
  workspaceSummaryState = summary;
  if (workspaceSessionIdNode) {
    workspaceSessionIdNode.textContent = summary.session_id;
  }
  if (workspaceSessionStateNode) {
    workspaceSessionStateNode.textContent = localizeStateLabel(summary.state);
    workspaceSessionStateNode.className = `status-pill status-${summary.state === "completed" ? "ok" : "warn"}`;
  }
  if (workspaceSideStateNode) {
    workspaceSideStateNode.textContent = localizeStateLabel(summary.state);
  }
  if (workspacePointCountNode) {
    workspacePointCountNode.textContent = String(summary.point_count);
  }
  if (workspaceAf95Node) {
    workspaceAf95Node.textContent = summary.af95 === null ? t("common.na", {}, "N/A") : `${summary.af95} °C`;
  }
  const summaryCopyNode = document.getElementById("workspace-summary-copy");
  if (summaryCopyNode) {
    summaryCopyNode.textContent =
      currentLocale === "en"
        ? `Session ${summary.session_id} is currently recorded as ${localizeStateLabel(summary.state)} with ${summary.point_count} points.`
        : `当前记录：session ${summary.session_id}，状态 ${localizeStateLabel(summary.state)}，共 ${summary.point_count} 个点。`;
  }
  refreshWorkspaceStages();
}

function formatValue(value, empty = "N/A") {
  if (value === null || value === undefined || value === "") {
    return empty;
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : empty;
  }
  return String(value);
}

function formatResultValue(value, unit = "") {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  return unit ? `${value} ${unit}` : String(value);
}

function hasWorkspaceAfasUi() {
  return Boolean(
    workspaceAfasChannelNode &&
      workspaceAfasStatusNode &&
      workspaceAfasOverviewSeriesNode &&
      workspaceAfasAnalysisLayersNode,
  );
}

function isWorkspaceAfasAvailable() {
  return document.body.dataset.afasAvailable !== "0";
}

function getWorkspaceAfasUnavailableMessage() {
  return currentLocale === "en" ? "AFAS dataset is unavailable for this session." : "该 session 当前没有可用的 AFAS 数据集。";
}

function getWorkspaceAfasPendingMessage() {
  return currentLocale === "en" ? "Loading AFAS analysis for this session..." : "正在为当前 session 加载 AFAS 分析...";
}

function getWorkspaceAfasOverviewPendingMessage() {
  return currentLocale === "en" ? "Overview will appear once analysis loads." : "分析加载后，这里会显示总览图。";
}

function getWorkspaceAfasChannelNote(channelCount) {
  if (!isWorkspaceAfasAvailable()) {
    return getWorkspaceAfasUnavailableMessage();
  }
  if (channelCount <= 0) {
    return getWorkspaceAfasPendingMessage();
  }
  if (channelCount === 1) {
    return currentLocale === "en"
      ? "This dataset only has one valid channel, so the selector stays lightweight."
      : "当前数据只有一个有效通道，因此这里保持为轻量单通道状态。";
  }
  return currentLocale === "en"
    ? "Choose the channel you want to judge when multiple channels are available."
    : "多通道数据时，先选择要判读的通道。";
}

function syncWorkspaceAfasSurfaceAvailability(available) {
  if (workspaceAfasSurfaceNode) {
    workspaceAfasSurfaceNode.hidden = !available;
  }
  if (workspaceAfasEmptyStateNode) {
    workspaceAfasEmptyStateNode.hidden = available;
  }
  if (workspaceAfasChannelNoteNode && !available) {
    workspaceAfasChannelNoteNode.textContent = getWorkspaceAfasUnavailableMessage();
  }
}

function syncWorkspaceAfasAvailability() {
  if (!hasWorkspaceAfasUi()) {
    return;
  }
  const available = isWorkspaceAfasAvailable();
  syncWorkspaceAfasSurfaceAvailability(available);
  for (const node of [
    workspaceAfasRunButton,
    workspaceAfasExportPngButton,
    workspaceAfasExportXlsxButton,
    workspaceAfasSavgolWindowNode,
    workspaceAfasSavgolPolyorderNode,
    workspaceAfasLowStartNode,
    workspaceAfasLowEndNode,
    workspaceAfasHighStartNode,
    workspaceAfasHighEndNode,
    workspaceAfasTangentOffsetNode,
  ]) {
    if (node) {
      node.disabled = !available;
    }
  }
  if (workspaceAfasChannelNode) {
    workspaceAfasChannelNode.disabled = !available;
  }
}

function setWorkspaceAfasStatus(message, tone = "neutral") {
  if (!workspaceAfasStatusNode) {
    return;
  }
  workspaceAfasStatusNode.textContent = message;
  workspaceAfasStatusNode.className = `workspace-adjustment-status workspace-adjustment-status--${tone}`;
}

function localizeWorkspaceAfasDetail(detail) {
  const message = String(detail || "").trim();
  if (!message) {
    return message;
  }
  if (currentLocale !== "zh") {
    return message;
  }
  if (message === "Parameterized tangent analysis completed.") {
    return "参数化切线分析已完成。";
  }
  if (message === "AFAS analysis completed.") {
    return "AFAS 分析已完成。";
  }
  return message;
}

function localizeWorkspaceSourceLabel(source) {
  const key = String(source || "n/a").trim() || "n/a";
  const localized = WORKSPACE_SOURCE_LABELS[key];
  if (localized) {
    return localized[currentLocale] || localized.en;
  }
  return key;
}

function formatAfasTemperature(value) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} °C` : "N/A";
}

function setInputNumericString(node, value) {
  if (!node) {
    return;
  }
  if (value === null || value === undefined || value === "") {
    node.value = "";
    return;
  }
  const numeric = Number(value);
  node.value = Number.isFinite(numeric) ? String(numeric) : "";
}

function setInputRange(nodeStart, nodeEnd, range) {
  if (!Array.isArray(range) || range.length !== 2) {
    setInputNumericString(nodeStart, null);
    setInputNumericString(nodeEnd, null);
    return;
  }
  setInputNumericString(nodeStart, range[0]);
  setInputNumericString(nodeEnd, range[1]);
}

function collectWorkspaceAfasPayload() {
  const lowStart = getOptionalNumericInputValue(workspaceAfasLowStartNode);
  const lowEnd = getOptionalNumericInputValue(workspaceAfasLowEndNode);
  const highStart = getOptionalNumericInputValue(workspaceAfasHighStartNode);
  const highEnd = getOptionalNumericInputValue(workspaceAfasHighEndNode);
  return {
    channel_name: workspaceAfasChannelNode ? workspaceAfasChannelNode.value || null : null,
    savgol_window_length: getOptionalNumericInputValue(workspaceAfasSavgolWindowNode),
    savgol_polyorder: getOptionalNumericInputValue(workspaceAfasSavgolPolyorderNode),
    tangent_offset: getOptionalNumericInputValue(workspaceAfasTangentOffsetNode),
    low_range_celsius: lowStart !== null && lowEnd !== null ? [lowStart, lowEnd] : null,
    high_range_celsius: highStart !== null && highEnd !== null ? [highStart, highEnd] : null,
  };
}

function queueWorkspaceAfasRefresh({ delay = 140, silent = true } = {}) {
  if (!hasWorkspaceAfasUi() || !isWorkspaceAfasAvailable()) {
    return;
  }
  const sessionId = getWorkspaceSessionId();
  if (!sessionId) {
    return;
  }
  window.clearTimeout(workspaceAfasRefreshTimer);
  workspaceAfasRefreshTimer = window.setTimeout(() => {
    workspaceAfasRefreshTimer = null;
    void loadWorkspaceAfasAnalysis(sessionId, { silent });
  }, delay);
}

function normalizeChartDomain(values, fallback = [0, 1]) {
  const numericValues = (values || []).map((value) => Number(value)).filter((value) => Number.isFinite(value));
  if (!numericValues.length) {
    return fallback;
  }
  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);
  if (min === max) {
    return [min - 1, max + 1];
  }
  return [min, max];
}

function normalizeChartPadding(padding) {
  if (typeof padding === "number") {
    return {
      top: padding,
      right: padding,
      bottom: padding,
      left: padding,
    };
  }
  return {
    top: Number(padding?.top ?? 28),
    right: Number(padding?.right ?? 28),
    bottom: Number(padding?.bottom ?? 28),
    left: Number(padding?.left ?? 28),
  };
}

function formatChartNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "";
  }
  const absolute = Math.abs(numeric);
  const decimals = absolute >= 100 ? 0 : absolute >= 10 ? 1 : 2;
  return numeric
    .toFixed(decimals)
    .replace(/\.0+$/, "")
    .replace(/(\.\d*[1-9])0+$/, "$1");
}

function formatChartTick(value) {
  return formatChartNumber(value);
}

function formatChartIntegerTick(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "";
  }
  return String(Math.round(numeric));
}

function buildChartTicks(minValue, maxValue, tickCount) {
  const min = Number(minValue);
  const max = Number(maxValue);
  const count = Math.max(1, Number.isFinite(Number(tickCount)) ? Math.round(Number(tickCount)) : 4);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [];
  }
  if (Math.abs(max - min) < 1e-9) {
    return [min];
  }
  return Array.from({ length: count + 1 }, (_, index) => min + ((max - min) * index) / count);
}

function expandChartDomain([minValue, maxValue], minSpan) {
  const spanFloor = Number(minSpan);
  if (!Number.isFinite(spanFloor) || spanFloor <= 0) {
    return [minValue, maxValue];
  }
  const min = Number(minValue);
  const max = Number(maxValue);
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [minValue, maxValue];
  }
  const span = Math.max(0, max - min);
  if (span >= spanFloor) {
    return [min, max];
  }
  const center = (min + max) / 2;
  const halfSpan = spanFloor / 2;
  return [center - halfSpan, center + halfSpan];
}

function buildChartScaler(xValues, yValues, width, height, padding, options = {}) {
  const chartPadding = normalizeChartPadding(padding);
  const [minX, maxX] = expandChartDomain(normalizeChartDomain(xValues, [0, 1]), options.minXSpan);
  const [minY, maxY] = expandChartDomain(normalizeChartDomain(yValues, [0, 1]), options.minYSpan);
  const xSpan = Math.max(maxX - minX, 1);
  const ySpan = Math.max(maxY - minY, 1);
  const plotWidth = Math.max(1, width - chartPadding.left - chartPadding.right);
  const plotHeight = Math.max(1, height - chartPadding.top - chartPadding.bottom);
  return {
    minX,
    maxX,
    minY,
    maxY,
    padding: chartPadding,
    x(value) {
      return chartPadding.left + ((Number(value) - minX) / xSpan) * plotWidth;
    },
    y(value) {
      return height - chartPadding.bottom - ((Number(value) - minY) / ySpan) * plotHeight;
    },
  };
}

function renderWorkspaceChartGrid(width, height, padding, xTicks = 5, yTicks = 4) {
  const chartPadding = normalizeChartPadding(padding);
  const plotWidth = Math.max(1, width - chartPadding.left - chartPadding.right);
  const plotHeight = Math.max(1, height - chartPadding.top - chartPadding.bottom);
  const verticalLines = Array.from({ length: xTicks + 1 }, (_, index) => {
    const x = chartPadding.left + (plotWidth / xTicks) * index;
    return `<line x1="${x}" y1="${chartPadding.top}" x2="${x}" y2="${height - chartPadding.bottom}" stroke="${AFAS_CHART_THEME.grid}" stroke-width="1"></line>`;
  }).join("");
  const horizontalLines = Array.from({ length: yTicks + 1 }, (_, index) => {
    const y = chartPadding.top + (plotHeight / yTicks) * index;
    return `<line x1="${chartPadding.left}" y1="${y}" x2="${width - chartPadding.right}" y2="${y}" stroke="${AFAS_CHART_THEME.grid}" stroke-width="1"></line>`;
  }).join("");
  return `${verticalLines}${horizontalLines}`;
}

function renderChartAxes(width, height, padding, scaler, options = {}) {
  const chartPadding = normalizeChartPadding(padding);
  const plotWidth = Math.max(1, width - chartPadding.left - chartPadding.right);
  const plotHeight = Math.max(1, height - chartPadding.top - chartPadding.bottom);
  const axisY = height - chartPadding.bottom;
  const axisX = chartPadding.left;
  const xFormatter = options.xFormatter || formatChartTick;
  const yFormatter = options.yFormatter || formatChartTick;
  const xTicks = buildChartTicks(scaler.minX, scaler.maxX, options.xTicks ?? 5);
  const yTicks = buildChartTicks(scaler.minY, scaler.maxY, options.yTicks ?? 4);
  const xTickLabels = xTicks
    .map(
      (value) =>
        `<text class="chart-axis-tick" x="${scaler.x(value)}" y="${axisY + 18}" text-anchor="middle">${escapeHtml(xFormatter(value))}</text>`,
    )
    .join("");
  const yTickLabels = yTicks
    .map(
      (value) =>
        `<text class="chart-axis-tick" x="${axisX - 8}" y="${scaler.y(value) + 4}" text-anchor="end">${escapeHtml(yFormatter(value))}</text>`,
    )
    .join("");
  const xLabel = options.xLabel
    ? `<text class="chart-axis-label" x="${chartPadding.left + plotWidth / 2}" y="${height - 8}" text-anchor="middle">${escapeHtml(options.xLabel)}</text>`
    : "";
  const yLabel = options.yLabel
    ? `<text class="chart-axis-label" x="${14}" y="${chartPadding.top + plotHeight / 2}" text-anchor="middle" transform="rotate(-90 14 ${chartPadding.top + plotHeight / 2})">${escapeHtml(options.yLabel)}</text>`
    : "";
  return `
    <line x1="${axisX}" y1="${axisY}" x2="${width - chartPadding.right}" y2="${axisY}" stroke="${AFAS_CHART_THEME.axis}" stroke-width="1.25"></line>
    <line x1="${axisX}" y1="${chartPadding.top}" x2="${axisX}" y2="${axisY}" stroke="${AFAS_CHART_THEME.axis}" stroke-width="1.25"></line>
    ${xTickLabels}
    ${yTickLabels}
    ${xLabel}
    ${yLabel}
  `;
}

function renderWorkspaceAfasOverview(overview, activeChannel) {
  if (!workspaceAfasOverviewSeriesNode || !workspaceAfasOverviewSummaryNode) {
    return;
  }
  const items = Array.isArray(overview) ? overview : [];
  if (!items.length) {
    workspaceAfasOverviewSeriesNode.innerHTML = "";
    const emptyMessage = isWorkspaceAfasAvailable() ? getWorkspaceAfasOverviewPendingMessage() : getWorkspaceAfasUnavailableMessage();
    workspaceAfasOverviewSummaryNode.innerHTML = `<p class="session-item--empty">${emptyMessage}</p>`;
    return;
  }

  const allTemps = items.flatMap((item) => (item.series ? item.series.temperature_celsius || [] : []));
  const allValues = items.flatMap((item) => (item.series ? item.series.values || [] : []));
  const width = 640;
  const height = 220;
  const padding = { top: 20, right: 18, bottom: 46, left: 58 };
  const scaler = buildChartScaler(allTemps, allValues, width, height, padding);
  const grid = renderWorkspaceChartGrid(width, height, padding, 5, 4);
  const axes = renderChartAxes(width, height, padding, scaler, {
    xLabel: currentLocale === "en" ? "Temperature (°C)" : "温度 (°C)",
    yLabel: currentLocale === "en" ? "Deformation" : "形变",
  });
  const seriesLayers = items
    .map((item, index) => {
      const temperatures = item.series ? item.series.temperature_celsius || [] : [];
      const values = item.series ? item.series.values || [] : [];
      const points = temperatures
        .map((temperature, pointIndex) => `${scaler.x(temperature)},${scaler.y(values[pointIndex])}`)
        .join(" ");
      const isActive = item.channel_name === activeChannel;
      const accentColor = AFAS_OVERVIEW_CHANNEL_COLORS[index % AFAS_OVERVIEW_CHANNEL_COLORS.length];
      const stroke = isActive ? AFAS_CHART_THEME.highlight : AFAS_OVERVIEW_CHANNEL_COLORS[index % AFAS_OVERVIEW_CHANNEL_COLORS.length];
      return `
        <polyline
          fill="none"
          stroke="${stroke}"
          stroke-width="${isActive ? 4 : 2.5}"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="${isActive ? 1 : 0.72}"
          points="${points}"
        ></polyline>
      `;
    })
    .join("");
  workspaceAfasOverviewSeriesNode.innerHTML = `${grid}${seriesLayers}${axes}`;
  workspaceAfasOverviewSummaryNode.innerHTML = items
    .map(
      (item, index) => `
        <article
          class="workspace-afas-overview-item${item.channel_name === activeChannel ? " workspace-afas-overview-item--active" : ""}"
          style="--workspace-series-accent: ${AFAS_OVERVIEW_CHANNEL_COLORS[index % AFAS_OVERVIEW_CHANNEL_COLORS.length]};"
        >
          <strong>${escapeHtml(item.channel_name)}</strong>
          <p>${currentLocale === "en" ? "status" : "状态"}=${escapeHtml(localizeStateLabel(item.result_status))}</p>
          <p>${currentLocale === "en" ? "points" : "点数"}=${item.point_count} ${currentLocale === "en" ? "outliers" : "离群点"}=${item.outlier_count}</p>
          <p>As=${item.as_value === null ? "N/A" : item.as_value.toFixed(2)} Af-tan=${item.af_tan === null ? "N/A" : item.af_tan.toFixed(2)}</p>
        </article>
      `,
    )
    .join("");
}

function renderWorkspaceAfasAnalysisChart(analysis) {
  if (!workspaceAfasAnalysisLayersNode || !workspaceAfasAnalysisEmptyNode) {
    return;
  }
  const series = analysis && analysis.series ? analysis.series : null;
  const fit = analysis && analysis.fit ? analysis.fit : null;
  const result = analysis && analysis.result ? analysis.result : null;
  const temperatures = series ? series.temperature_celsius || [] : [];
  const values = series ? series.values || [] : [];
  if (!temperatures.length || !values.length) {
    workspaceAfasAnalysisLayersNode.innerHTML = "";
    workspaceAfasAnalysisEmptyNode.hidden = false;
    return;
  }

  const width = 640;
  const height = 280;
  const padding = { top: 22, right: 18, bottom: 48, left: 58 };
  const fitLines = [];
  if (fit?.low_baseline?.range_celsius) {
    fitLines.push(...fit.low_baseline.range_celsius);
  }
  if (fit?.high_baseline?.range_celsius) {
    fitLines.push(...fit.high_baseline.range_celsius);
  }
  if (result?.As !== null && result?.As !== undefined) {
    fitLines.push(result.As);
  }
  if (result?.Af_tan !== null && result?.Af_tan !== undefined) {
    fitLines.push(result.Af_tan);
  }
  if (result?.max_slope_temp !== null && result?.max_slope_temp !== undefined) {
    fitLines.push(result.max_slope_temp);
  }
  const scaler = buildChartScaler(temperatures.concat(fitLines), values, width, height, padding);
  const curvePoints = temperatures.map((temperature, index) => `${scaler.x(temperature)},${scaler.y(values[index])}`).join(" ");
  const grid = renderWorkspaceChartGrid(width, height, padding, 5, 4);
  const axes = renderChartAxes(width, height, padding, scaler, {
    xLabel: currentLocale === "en" ? "Temperature (°C)" : "温度 (°C)",
    yLabel: currentLocale === "en" ? "Deformation" : "形变",
  });

  function renderLineSegment(line, color, dash = "8 6") {
    if (!line || !Array.isArray(line.range_celsius)) {
      return "";
    }
    const [start, end] = line.range_celsius;
    const y1 = line.slope * start + line.intercept;
    const y2 = line.slope * end + line.intercept;
    return `<line x1="${scaler.x(start)}" y1="${scaler.y(y1)}" x2="${scaler.x(end)}" y2="${scaler.y(y2)}" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-dasharray="${dash}"></line>`;
  }

  function renderInfiniteLine(line, color) {
    if (!line) {
      return "";
    }
    const start = Math.min(...temperatures);
    const end = Math.max(...temperatures);
    const y1 = line.slope * start + line.intercept;
    const y2 = line.slope * end + line.intercept;
    return `<line x1="${scaler.x(start)}" y1="${scaler.y(y1)}" x2="${scaler.x(end)}" y2="${scaler.y(y2)}" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-dasharray="8 6"></line>`;
  }

  function renderMarker(xValue, yValue, label, color, shape = "circle") {
    if (!Number.isFinite(xValue) || !Number.isFinite(yValue)) {
      return "";
    }
    const cx = scaler.x(xValue);
    const cy = scaler.y(yValue);
    const labelWidth = Math.max(label.length * 7 + 18, 56);
    const rectX = Math.min(Math.max(cx + 10, 12), width - labelWidth - 12);
    const rectY = Math.max(cy - 28, 10);
    const marker =
      shape === "diamond"
        ? `<rect x="${cx - 5}" y="${cy - 5}" width="10" height="10" fill="${color}" stroke="${AFAS_CHART_THEME.markerStroke}" stroke-width="2" transform="rotate(45 ${cx} ${cy})"></rect>`
        : `<circle cx="${cx}" cy="${cy}" r="6.5" fill="${color}" stroke="${AFAS_CHART_THEME.markerStroke}" stroke-width="2"></circle>`;
    return `
      ${marker}
      <rect x="${rectX}" y="${rectY}" width="${labelWidth}" height="20" rx="8" fill="${AFAS_CHART_THEME.labelBackground}" stroke="${AFAS_CHART_THEME.labelBorder}" stroke-width="1"></rect>
      <text x="${rectX + 9}" y="${rectY + 13}" fill="${color}" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace">${escapeHtml(label)}</text>
    `;
  }

  const asY = result?.As !== null && result?.As !== undefined && fit?.tangent
    ? fit.tangent.slope * result.As + fit.tangent.intercept
    : null;
  const afY = result?.Af_tan !== null && result?.Af_tan !== undefined && fit?.tangent
    ? fit.tangent.slope * result.Af_tan + fit.tangent.intercept
    : null;
  const maxSlopeY = result?.max_slope_temp !== null && result?.max_slope_temp !== undefined && fit?.tangent
    ? fit.tangent.slope * result.max_slope_temp + fit.tangent.intercept
    : null;

  workspaceAfasAnalysisLayersNode.innerHTML = `
    ${grid}
    <polyline fill="none" stroke="${AFAS_CHART_THEME.primary}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${curvePoints}"></polyline>
    ${renderLineSegment(fit?.low_baseline, AFAS_CHART_THEME.green)}
    ${renderLineSegment(fit?.high_baseline, AFAS_CHART_THEME.apricot)}
    ${renderInfiniteLine(fit?.tangent, AFAS_CHART_THEME.rose)}
    ${renderMarker(
      result?.As,
      asY,
      Number.isFinite(Number(result?.As)) ? `As=${Number(result.As).toFixed(2)}` : "As",
      AFAS_CHART_THEME.green,
    )}
    ${renderMarker(
      result?.Af_tan,
      afY,
      Number.isFinite(Number(result?.Af_tan)) ? `Af-tan=${Number(result.Af_tan).toFixed(2)}` : "Af-tan",
      AFAS_CHART_THEME.apricot,
    )}
    ${renderMarker(
      result?.max_slope_temp,
      maxSlopeY,
      Number.isFinite(Number(result?.max_slope_temp)) ? `Slope=${Number(result.max_slope_temp).toFixed(2)}` : "Slope",
      AFAS_CHART_THEME.rose,
      "diamond",
    )}
    ${axes}
  `;
  workspaceAfasAnalysisEmptyNode.hidden = true;
}

function renderWorkspaceAfasResults(state) {
  if (
    !workspaceAfasResultStatusNode ||
    !workspaceAfasResultAsNode ||
    !workspaceAfasResultAfTanNode ||
    !workspaceAfasResultDeltaNode ||
    !workspaceAfasResultMaxSlopeNode ||
    !workspaceAfasParameterSummaryNode ||
    !workspaceAfasResultHintNode ||
    !workspaceAfasOutlierCountNode ||
    !workspaceAfasSmoothedCountNode ||
    !workspaceAfasWarningListNode
  ) {
    return;
  }
  if (!state) {
    workspaceAfasResultStatusNode.textContent = "N/A";
    workspaceAfasResultAsNode.textContent = "N/A";
    workspaceAfasResultAfTanNode.textContent = "N/A";
    workspaceAfasResultDeltaNode.textContent = "N/A";
    workspaceAfasResultMaxSlopeNode.textContent = "N/A";
    workspaceAfasParameterSummaryNode.textContent = isWorkspaceAfasAvailable()
      ? currentLocale === "en"
        ? "Parameter summary will appear here once analysis loads."
        : "分析加载后，这里会显示参数摘要。"
      : getWorkspaceAfasUnavailableMessage();
    workspaceAfasResultHintNode.textContent = isWorkspaceAfasAvailable()
      ? currentLocale === "en"
        ? "AFAS will load automatically for the current channel and committed parameter values."
        : "当前通道与已提交参数会自动触发 AFAS 分析，无需再手动点击运行。"
      : getWorkspaceAfasUnavailableMessage();
    workspaceAfasOutlierCountNode.textContent = "0";
    workspaceAfasSmoothedCountNode.textContent = "0";
    workspaceAfasWarningListNode.innerHTML = `<p class="session-item--empty">${currentLocale === "en" ? "Warnings will appear here when analysis runs." : "分析运行后，这里会显示告警。"}</p>`;
    return;
  }

  const preprocessing = state.preprocessing || {};
  const analysis = state.analysis || {};
  const result = analysis.result || {};
  const warnings = [...(preprocessing.warnings || []), ...(analysis.warnings || [])];
  const resolvedLowRange = analysis.parameters?.resolved_low_range_celsius || [];
  const resolvedHighRange = analysis.parameters?.resolved_high_range_celsius || [];
  const delta =
    Number.isFinite(Number(result.As)) && Number.isFinite(Number(result.Af_tan))
      ? Number(result.Af_tan) - Number(result.As)
      : null;
  const summaryParts = [
    state.active_channel ? (currentLocale === "en" ? `Channel ${state.active_channel}` : `通道 ${state.active_channel}`) : null,
    Number.isFinite(Number(preprocessing.parameters?.savgol_window_length))
      ? `Savgol ${preprocessing.parameters.savgol_window_length}/${preprocessing.parameters?.savgol_polyorder ?? "?"}`
      : null,
    resolvedLowRange.length === 2
      ? currentLocale === "en"
        ? `Low ${resolvedLowRange[0]}-${resolvedLowRange[1]} °C`
        : `低温 ${resolvedLowRange[0]}-${resolvedLowRange[1]} °C`
      : null,
    resolvedHighRange.length === 2
      ? currentLocale === "en"
        ? `High ${resolvedHighRange[0]}-${resolvedHighRange[1]} °C`
        : `高温 ${resolvedHighRange[0]}-${resolvedHighRange[1]} °C`
      : null,
    Number.isFinite(Number(preprocessing.parameters?.tangent_offset))
      ? currentLocale === "en"
        ? `Offset ${preprocessing.parameters.tangent_offset}`
        : `偏移 ${preprocessing.parameters.tangent_offset}`
      : null,
  ].filter(Boolean);
  workspaceAfasResultStatusNode.textContent = analysis.result_status ? localizeStateLabel(analysis.result_status) : "N/A";
  workspaceAfasResultAsNode.textContent = formatAfasTemperature(result.As);
  workspaceAfasResultAfTanNode.textContent = formatAfasTemperature(result.Af_tan);
  workspaceAfasResultDeltaNode.textContent = delta === null ? "N/A" : `${delta.toFixed(2)} °C`;
  workspaceAfasResultMaxSlopeNode.textContent = formatAfasTemperature(result.max_slope_temp);
  workspaceAfasParameterSummaryNode.textContent = summaryParts.length
    ? summaryParts.join(" · ")
    : currentLocale === "en"
      ? "Parameter summary is unavailable for this AFAS run."
      : "本次 AFAS 运行暂时没有参数摘要。";
  workspaceAfasResultHintNode.textContent =
    analysis.result_status === "ok"
      ? currentLocale === "en"
        ? "Result is readable. Review the charts, then export or move into adjustment."
        : "结果可读。请先复核图表，再决定导出或进入调整。"
      : analysis.detail ||
        (currentLocale === "en"
          ? "Result is incomplete. Try adjusting the tangent parameters before exporting."
          : "结果尚不完整。导出前请先尝试调整切线参数。");
  workspaceAfasOutlierCountNode.textContent = String(preprocessing.outlier_repair?.outlier_count ?? 0);
  workspaceAfasSmoothedCountNode.textContent = String((preprocessing.smoothed?.temperature_celsius || []).length);
  workspaceAfasWarningListNode.innerHTML = warnings.length
    ? `<ul class="workspace-adjustment-notes-list">${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>`
    : `<p class="session-item--empty">${currentLocale === "en" ? "No preprocessing or analysis warnings." : "当前没有预处理或分析告警。"}</p>`;
}

function syncWorkspaceAfasControls(state) {
  if (!state) {
    if (workspaceAfasChannelNoteNode) {
      workspaceAfasChannelNoteNode.textContent = getWorkspaceAfasChannelNote(0);
    }
    return;
  }
  const availableChannels = Array.isArray(state.available_channels) ? state.available_channels : [];
  if (workspaceAfasChannelNode) {
    const currentValue = workspaceAfasChannelNode.value;
    workspaceAfasChannelNode.innerHTML = availableChannels
      .map(
        (channel) =>
          `<option value="${escapeHtml(channel)}"${channel === state.active_channel ? " selected" : ""}>${escapeHtml(channel)}</option>`,
      )
      .join("");
    if (!currentValue && state.active_channel) {
      workspaceAfasChannelNode.value = state.active_channel;
    }
    workspaceAfasChannelNode.disabled = !isWorkspaceAfasAvailable() || availableChannels.length <= 1;
  }
  if (workspaceAfasChannelNoteNode) {
    workspaceAfasChannelNoteNode.textContent = getWorkspaceAfasChannelNote(availableChannels.length);
  }

  const preprocessingParameters = state.preprocessing?.parameters || {};
  const analysisParameters = state.analysis?.parameters || {};
  setInputNumericString(workspaceAfasSavgolWindowNode, preprocessingParameters.savgol_window_length);
  setInputNumericString(workspaceAfasSavgolPolyorderNode, preprocessingParameters.savgol_polyorder);
  setInputRange(workspaceAfasLowStartNode, workspaceAfasLowEndNode, analysisParameters.resolved_low_range_celsius);
  setInputRange(workspaceAfasHighStartNode, workspaceAfasHighEndNode, analysisParameters.resolved_high_range_celsius);
  setInputNumericString(workspaceAfasTangentOffsetNode, preprocessingParameters.tangent_offset ?? analysisParameters.tangent_offset);
}

function renderWorkspaceAfas(state) {
  workspaceAfasState = state;
  if (!hasWorkspaceAfasUi()) {
    return;
  }
  if (!state) {
    syncWorkspaceAfasAvailability();
    syncWorkspaceAfasSurfaceAvailability(isWorkspaceAfasAvailable());
    renderWorkspaceAfasOverview([], "");
    renderWorkspaceAfasAnalysisChart(null);
    renderWorkspaceAfasResults(null);
    setWorkspaceAfasStatus(
      isWorkspaceAfasAvailable()
        ? currentLocale === "en"
          ? "AFAS analysis is waiting for the current session context."
          : "AFAS 分析正在等待当前 session 上下文。"
        : getWorkspaceAfasUnavailableMessage(),
      isWorkspaceAfasAvailable() ? "neutral" : "info",
    );
    refreshWorkspaceStages();
    return;
  }
  syncWorkspaceAfasAvailability();
  syncWorkspaceAfasSurfaceAvailability(true);
  syncWorkspaceAfasControls(state);
  renderWorkspaceAfasOverview(state.overview || [], state.active_channel);
  renderWorkspaceAfasAnalysisChart(state.analysis || null);
  renderWorkspaceAfasResults(state);
  const analysis = state.analysis || {};
  const detail = localizeWorkspaceAfasDetail(
    analysis.detail || (currentLocale === "en" ? "AFAS analysis completed." : "AFAS 分析已完成。"),
  );
  setWorkspaceAfasStatus(detail, analysis.result_status === "ok" ? "success" : "info");
  refreshWorkspaceStages();
}

async function loadWorkspaceAfasAnalysis(sessionId, { silent = false } = {}) {
  if (!hasWorkspaceAfasUi()) {
    return null;
  }
  if (!isWorkspaceAfasAvailable()) {
    renderWorkspaceAfas(null);
    return null;
  }
  const requestToken = ++workspaceAfasRequestToken;
  if (workspaceAfasRunButton) {
    workspaceAfasRunButton.disabled = true;
  }
  setWorkspaceAfasStatus(
    currentLocale === "en" ? "Loading AFAS preprocessing and tangent analysis..." : "正在加载 AFAS 预处理与切线分析...",
    "info",
  );
  try {
    const response = await fetch(`/api/session/${sessionId}/afas/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectWorkspaceAfasPayload()),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `AFAS analysis request failed: ${response.status}`);
    }
    if (requestToken !== workspaceAfasRequestToken) {
      return payload;
    }
    renderWorkspaceAfas(payload);
    return payload;
  } catch (error) {
    if (requestToken !== workspaceAfasRequestToken) {
      return null;
    }
    renderWorkspaceAfas(null);
    if (!silent) {
      setWorkspaceAfasStatus(String(error), "error");
    }
    return null;
  } finally {
    if (workspaceAfasRunButton) {
      workspaceAfasRunButton.disabled = !isWorkspaceAfasAvailable();
    }
  }
}

function extractFilenameFromDisposition(headerValue, fallback) {
  if (!headerValue) {
    return fallback;
  }
  const match = /filename=\"?([^\";]+)\"?/i.exec(headerValue);
  return match ? match[1] : fallback;
}

async function exportWorkspaceAfasArtifact(kind) {
  const sessionId = getWorkspaceSessionId();
  if (!sessionId || !hasWorkspaceAfasUi()) {
    return;
  }
  if (!isWorkspaceAfasAvailable()) {
    renderWorkspaceAfas(null);
    return;
  }
  const button = kind === "png" ? workspaceAfasExportPngButton : workspaceAfasExportXlsxButton;
  if (button) {
    button.disabled = true;
  }
  setWorkspaceAfasStatus(`Preparing AFAS ${kind.toUpperCase()} export...`, "info");
  try {
    const endpoint = kind === "png" ? "export.png" : "report.xlsx";
    const response = await fetch(`/api/session/${sessionId}/afas/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectWorkspaceAfasPayload()),
    });
    if (!response.ok) {
      let detail = `AFAS ${kind.toUpperCase()} export failed: ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (error) {
        // Keep the generic error when the response body is not JSON.
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = extractFilenameFromDisposition(
      response.headers.get("Content-Disposition"),
      kind === "png" ? "afas-analysis.png" : "afas-report.xlsx",
    );
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(downloadUrl);
    setWorkspaceAfasStatus(`AFAS ${kind.toUpperCase()} export is ready.`, "success");
  } catch (error) {
    setWorkspaceAfasStatus(String(error), "error");
  } finally {
    if (button) {
      button.disabled = !isWorkspaceAfasAvailable();
    }
  }
}

function setAdjustmentStatusMessage(message, tone = "neutral") {
  if (!adjustmentDraftStatusNode) {
    return;
  }
  adjustmentDraftStatusNode.textContent = message;
  adjustmentDraftStatusNode.className = `workspace-adjustment-status workspace-adjustment-status--${tone}`;
}

function getWorkspaceSessionId() {
  return document.body.dataset.sessionId || "";
}

function collectDraftPayload() {
  const af95Value = adjustmentDraftAf95Node ? adjustmentDraftAf95Node.value.trim() : "";
  const reason = adjustmentDraftReasonNode ? adjustmentDraftReasonNode.value.trim() : "";
  return {
    overrides: {
      af95: af95Value === "" ? null : Number(af95Value),
    },
    reason,
  };
}

function renderAdjustmentState(state) {
  workspaceAdjustmentState = state;
  if (!state) {
    if (adjustmentApplyButton) {
      adjustmentApplyButton.disabled = true;
    }
    setAdjustmentStatusMessage(currentLocale === "en" ? "Adjustment state is unavailable." : "当前无法获取 adjustment 状态。", "error");
    return;
  }

  const autoResult = state.auto_result || {};
  const latestResult = state.latest_result || {};
  const appliedVersions = state.applied_versions || [];
  const draft = state.draft;
  const hasManualOverride = appliedVersions.length > 0;
  const latestVersion = appliedVersions.length ? appliedVersions[appliedVersions.length - 1].version : null;

  if (adjustmentAutoAf95Node) {
    adjustmentAutoAf95Node.textContent = formatResultValue(autoResult.af95, "°C");
  }
  if (adjustmentAutoSourceNode) {
    adjustmentAutoSourceNode.textContent =
      workspaceDetailState?.source && workspaceDetailState.source !== "n/a" ? workspaceDetailState.source : "summary";
  }
  if (adjustmentAutoPointCountNode) {
    adjustmentAutoPointCountNode.textContent = String(workspaceSummaryState?.point_count ?? 0);
  }
  if (adjustmentLatestAf95Node) {
    adjustmentLatestAf95Node.textContent = formatResultValue(latestResult.af95, "°C");
  }
  if (adjustmentLatestSourceNode) {
    adjustmentLatestSourceNode.textContent = hasManualOverride ? "adjusted" : "auto";
  }
  if (adjustmentLatestVersionNode) {
    adjustmentLatestVersionNode.textContent = latestVersion === null ? "N/A" : `v${latestVersion}`;
  }
  if (adjustmentLatestNoteNode) {
    adjustmentLatestNoteNode.textContent = hasManualOverride
      ? currentLocale === "en"
        ? "Latest result reflects the newest applied adjustment version."
        : "最新结果已反映最近一次应用的 adjustment 版本。"
      : currentLocale === "en"
        ? "Latest result currently matches the automatic result."
        : "当前最新结果与自动结果一致。";
  }
  if (adjustmentHasDraftNode) {
    adjustmentHasDraftNode.textContent = draft ? t("common.yes", {}, "Yes") : t("common.no", {}, "No");
  }
  if (adjustmentAppliedCountNode) {
    adjustmentAppliedCountNode.textContent = String(appliedVersions.length);
  }
  if (adjustmentIsManualNode) {
    adjustmentIsManualNode.textContent = hasManualOverride ? t("common.yes", {}, "Yes") : t("common.no", {}, "No");
  }
  if (adjustmentDraftUpdatedNode) {
    adjustmentDraftUpdatedNode.textContent = draft ? formatValue(draft.updated_at_ms) : t("common.na", {}, "N/A");
  }
  if (adjustmentDraftAf95Node) {
    adjustmentDraftAf95Node.value = draft && draft.overrides ? formatValue(draft.overrides.af95, "") : "";
  }
  if (adjustmentDraftReasonNode) {
    adjustmentDraftReasonNode.value = draft ? draft.reason : "";
  }
  if (adjustmentApplyButton) {
    adjustmentApplyButton.disabled = !draft;
  }
  if (adjustmentVersionHistoryNode) {
    if (!appliedVersions.length) {
      adjustmentVersionHistoryNode.innerHTML =
        `<p class="session-item--empty">${currentLocale === "en" ? "No applied adjustment versions yet." : "尚无已应用的 adjustment 版本。"}</p>`;
    } else {
      adjustmentVersionHistoryNode.innerHTML = appliedVersions
        .slice()
        .reverse()
        .map(
          (version) => `
            <article class="workspace-version-item" data-testid="adjustment-version-item">
              <strong>v${version.version}</strong>
              <p>reason=${escapeHtml(version.reason)}</p>
              <p>created_at_ms=${version.created_at_ms}</p>
              <p>before.af95=${version.result_before.af95 === null ? "N/A" : version.result_before.af95}</p>
              <p>after.af95=${version.result_after.af95 === null ? "N/A" : version.result_after.af95}</p>
            </article>
          `,
        )
        .join("");
    }
  }

  if (draft) {
    setAdjustmentStatusMessage(
      currentLocale === "en" ? `Draft ready: ${draft.reason}` : `草稿已就绪：${draft.reason}`,
      "info",
    );
  } else if (hasManualOverride) {
    setAdjustmentStatusMessage(
      currentLocale === "en"
        ? `Applied ${appliedVersions.length} adjustment version(s).`
        : `已应用 ${appliedVersions.length} 个 adjustment 版本。`,
      "success",
    );
  } else {
    setAdjustmentStatusMessage(currentLocale === "en" ? "No draft loaded." : "尚未加载草稿。", "neutral");
  }
}

function updateWorkspaceAdjustmentPreview(selection) {
  if (
    !workspaceAdjustmentSourceNode ||
    !workspaceAdjustmentPointCountNode ||
    !workspaceAdjustmentKeyframeCountNode ||
    !workspaceAdjustmentAf95Node ||
    !workspaceAdjustmentStageNode ||
    !workspaceAdjustmentDetailStatusNode ||
    !workspaceAdjustmentActiveSummaryNode ||
    !workspaceAdjustmentBasisCopyNode ||
    !workspaceAdjustmentRoiNode ||
    !workspaceAdjustmentFeaturePointNode ||
    !workspaceAdjustmentBaselineNode ||
    !workspaceAdjustmentQualityNode ||
    !workspaceAdjustmentThresholdNode ||
    !workspaceAdjustmentComponentAreaNode ||
    !workspaceAdjustmentMetricNormNode ||
    !workspaceAdjustmentContextStageNode
  ) {
    return;
  }

  const detail = workspaceDetailState || { points: [], key_frames: [], af95: null, source: "n/a" };
  const stage = workspaceStageState?.currentStage || "计算";
  const detailAvailable = (detail.points || []).length > 0;

  workspaceAdjustmentSourceNode.textContent = formatValue(detail.source);
  workspaceAdjustmentPointCountNode.textContent = String((detail.points || []).length);
  workspaceAdjustmentKeyframeCountNode.textContent = String((detail.key_frames || []).length);
  workspaceAdjustmentAf95Node.textContent = detail.af95 === null ? "N/A" : `${detail.af95} °C`;
  workspaceAdjustmentStageNode.textContent = stage;
  workspaceAdjustmentDetailStatusNode.textContent = detailAvailable ? "Yes" : "No";

  if (!selection) {
    workspaceAdjustmentActiveSummaryNode.textContent = "N/A";
    workspaceAdjustmentBasisCopyNode.textContent =
      detailAvailable
        ? currentLocale === "en"
          ? "Automatic basis is available, but no point or key frame is currently selected."
          : "自动分析依据已可用，但当前尚未选中任何点或关键帧。"
        : currentLocale === "en"
          ? "Automatic analysis basis will appear here when detail data is available."
          : "detail 数据可用后，这里会显示自动分析依据。";
    workspaceAdjustmentRoiNode.textContent = "N/A";
    workspaceAdjustmentFeaturePointNode.textContent = "N/A";
    workspaceAdjustmentBaselineNode.textContent = "N/A";
    workspaceAdjustmentQualityNode.textContent = "N/A";
    workspaceAdjustmentThresholdNode.textContent = "N/A";
    workspaceAdjustmentComponentAreaNode.textContent = "N/A";
    workspaceAdjustmentMetricNormNode.textContent = "N/A";
    workspaceAdjustmentContextStageNode.textContent = stage;
    return;
  }

  workspaceAdjustmentActiveSummaryNode.textContent =
    currentLocale === "en"
      ? `${selection.label || "point"} @ ${formatValue(selection.timestamp_ms)} ms, metric_raw=${formatValue(selection.metric_raw)}`
      : `${selection.label || "点"} @ ${formatValue(selection.timestamp_ms)} ms，metric_raw=${formatValue(selection.metric_raw)}`;
  workspaceAdjustmentBasisCopyNode.textContent =
    currentLocale === "en"
      ? `Automatic basis is using ${formatValue(detail.source)} detail with ${String((detail.points || []).length)} points and the current selection context.`
      : `自动依据当前正在使用 ${formatValue(detail.source)} detail、${String((detail.points || []).length)} 个点，以及当前选中的上下文。`;
  workspaceAdjustmentRoiNode.textContent = formatValue(selection.roi);
  workspaceAdjustmentFeaturePointNode.textContent = formatValue(selection.feature_point_px);
  workspaceAdjustmentBaselineNode.textContent = formatValue(selection.baseline_px);
  workspaceAdjustmentQualityNode.textContent = formatValue(selection.quality);
  workspaceAdjustmentThresholdNode.textContent = formatValue(selection.threshold_value);
  workspaceAdjustmentComponentAreaNode.textContent = formatValue(selection.component_area);
  workspaceAdjustmentMetricNormNode.textContent = formatValue(selection.metric_norm);
  workspaceAdjustmentContextStageNode.textContent = stage;
}

function renderActiveSelection(selection) {
  workspaceActiveSelectionState = selection;
  if (
    !workspaceActiveLabelNode ||
    !workspaceActiveTimestampNode ||
    !workspaceActiveCelsiusNode ||
    !workspaceActiveMetricRawNode ||
    !workspaceActiveMetricNormNode ||
    !workspaceActiveFeaturePointNode ||
    !workspaceActiveQualityNode ||
    !workspaceActivePointNode
  ) {
    return;
  }

  if (!selection) {
    workspaceActiveLabelNode.textContent = "N/A";
    workspaceActiveTimestampNode.textContent = "N/A";
    workspaceActiveCelsiusNode.textContent = "N/A";
    workspaceActiveMetricRawNode.textContent = "N/A";
    workspaceActiveMetricNormNode.textContent = "N/A";
    workspaceActiveFeaturePointNode.textContent = "N/A";
    workspaceActiveQualityNode.textContent = "N/A";
    workspaceActivePointNode.textContent = currentLocale === "en" ? "No point selected." : "尚未选中任何点。";
    updateWorkspaceAdjustmentPreview(null);
    return;
  }

  workspaceActiveLabelNode.textContent = selection.label || "point";
  workspaceActiveTimestampNode.textContent = String(selection.timestamp_ms ?? "N/A");
  workspaceActiveCelsiusNode.textContent = selection.celsius ?? "N/A";
  workspaceActiveMetricRawNode.textContent = selection.metric_raw ?? "N/A";
  workspaceActiveMetricNormNode.textContent = selection.metric_norm ?? "N/A";
  workspaceActiveFeaturePointNode.textContent = selection.feature_point_px ? selection.feature_point_px.join(", ") : "N/A";
  workspaceActiveQualityNode.textContent = selection.quality ?? "N/A";
  workspaceActivePointNode.textContent =
    currentLocale === "en"
      ? `Selected ${selection.label || "point"} at ${selection.timestamp_ms} ms, metric_raw=${selection.metric_raw ?? "N/A"}.`
      : `已选择 ${selection.label || "点"}，时间 ${selection.timestamp_ms} ms，metric_raw=${selection.metric_raw ?? "N/A"}。`;
  updateWorkspaceAdjustmentPreview(selection);
}

function mapWorkspaceStages(summary, detail, afasState) {
  const hasSummary = Boolean(summary);
  const hasDetail = Boolean(detail && (detail.points || []).length);
  const isFailed = summary && summary.state === "failed";
  const source = detail && detail.source ? detail.source : "mock";
  const hasAfasResult = Boolean(afasState && afasState.analysis);
  const afasReady = Boolean(afasState && afasState.analysis && afasState.analysis.result_status === "ok");

  const statuses = WORKSPACE_STEPS.map((name) => ({ name, status: "todo" }));
  if (!hasSummary) {
    return {
      currentStage: "打开分析",
      statuses,
      mode: source,
      description: currentLocale === "en" ? "No session summary is available yet." : "当前还没有可用的 session 摘要。",
    };
  }

  for (let index = 0; index < 6; index += 1) {
    statuses[index].status = "done";
  }
  statuses[6].status = hasDetail ? "done" : "active";
  if (isFailed) {
    statuses[7].status = "error";
  } else if (afasReady) {
    statuses[7].status = "done";
  } else {
    statuses[7].status = "active";
  }

  return {
    currentStage: isFailed ? "打开分析" : hasAfasResult ? "AFAS 出点 / 导出" : "打开分析",
    statuses,
    mode: source,
    description: isFailed
      ? currentLocale === "en"
        ? "The session did not complete cleanly. Review the replay context before trusting any downstream result."
        : "该 session 并未正常完成。在信任任何下游结果之前，请先复核 replay 上下文。"
      : hasAfasResult
        ? currentLocale === "en"
          ? "Replay and AFAS are both in view. Confirm the answer card, then export or continue into adjustment."
          : "Replay 与 AFAS 都已就位。先确认答案卡，再决定导出或进入 adjustment。"
        : hasDetail
          ? currentLocale === "en"
            ? `${source} detail is loaded. Run AFAS or review the decision context from the first screen.`
            : `${source} detail 已加载。你可以运行 AFAS，或者先在第一屏复核决策上下文。`
          : currentLocale === "en"
            ? `${source} detail is not available, so Analysis Studio is staying in summary-only mode.`
            : `${source} detail 暂不可用，因此分析工作台保持在 summary-only 模式。`,
  };
}

function refreshWorkspaceStages() {
  if (!workspaceSummaryState) {
    return;
  }
  renderWorkspaceStages(
    mapWorkspaceStages(workspaceSummaryState, workspaceDetailState, workspaceAfasState),
    workspaceSummaryState.state,
  );
}

function renderWorkspaceStages(stageView, sessionState) {
  workspaceStageState = stageView;
  if (workspaceCurrentStageNode) {
    workspaceCurrentStageNode.textContent = stageView.currentStage;
  }
  if (workspaceStageDescriptionNode) {
    workspaceStageDescriptionNode.textContent = stageView.description;
  }
  workspaceStepNodes.forEach((node, index) => {
    const stage = stageView.statuses[index];
    if (!stage) {
      return;
    }
    node.classList.remove(
      "workspace-step--done",
      "workspace-step--active",
      "workspace-step--todo",
      "workspace-step--upcoming",
      "workspace-step--error",
    );
    node.classList.add(`workspace-step--${stage.status}`);
    const statusNode = node.querySelector("[data-testid='workspace-step-status']");
    if (statusNode) {
      statusNode.textContent = t(`workspace.step_status.${stage.status}`, {}, stage.status);
    }
  });
  if (workspaceSessionStateNode) {
    workspaceSessionStateNode.className = `status-pill status-${sessionState === "completed" ? "ok" : sessionState === "failed" ? "fail" : "warn"}`;
  }
  updateWorkspaceAdjustmentPreview(workspaceActiveSelectionState);
}

function renderWorkspaceCurve(detail) {
  if (!workspaceCurveNode || !workspaceCurvePointsNode || !workspaceCurveEmptyNode || !workspaceAf95LineNode) {
    return;
  }

  const points = detail.points || [];
  if (!points.length) {
    workspaceCurveNode.setAttribute("points", "");
    if (workspaceCurveLayersNode) {
      workspaceCurveLayersNode.innerHTML = "";
    }
    workspaceCurvePointsNode.innerHTML = "";
    workspaceAf95LineNode.setAttribute("x1", "0");
    workspaceAf95LineNode.setAttribute("x2", "0");
    workspaceAf95LineNode.setAttribute("y1", "0");
    workspaceAf95LineNode.setAttribute("y2", "0");
    workspaceCurveEmptyNode.textContent = currentLocale === "en" ? "No replay detail available." : "暂无 replay detail。";
    workspaceCurveEmptyNode.hidden = false;
    return;
  }

  const width = 640;
  const height = 260;
  const padding = { top: 22, right: 18, bottom: 48, left: 58 };
  const scaledPoints = points
    .map((point, index) => {
      const celsius = Number(point.celsius);
      const metricRaw = Number(point.metric_raw);
      if (!Number.isFinite(celsius) || !Number.isFinite(metricRaw)) {
        return null;
      }
      return { ...point, celsius, metric_raw: metricRaw, index };
    })
    .filter(Boolean);
  if (!scaledPoints.length) {
    workspaceCurveNode.setAttribute("points", "");
    if (workspaceCurveLayersNode) {
      workspaceCurveLayersNode.innerHTML = "";
    }
    workspaceCurvePointsNode.innerHTML = "";
    workspaceCurveEmptyNode.textContent = currentLocale === "en" ? "No replay detail available." : "暂无 replay detail。";
    workspaceCurveEmptyNode.hidden = false;
    return;
  }
  const xValues = scaledPoints.map((point) => point.celsius);
  const yValues = scaledPoints.map((point) => point.metric_raw);
  const scaler = buildChartScaler(xValues, yValues, width, height, padding);
  const plottedPoints = scaledPoints.map((point) => ({
    ...point,
    x: scaler.x(point.celsius),
    y: scaler.y(point.metric_raw),
  }));

  workspaceCurveNode.setAttribute(
    "points",
    plottedPoints.map((point) => `${point.x},${point.y}`).join(" "),
  );
  if (workspaceCurveLayersNode) {
    workspaceCurveLayersNode.innerHTML = `
      ${renderWorkspaceChartGrid(width, height, padding, 5, 4)}
      ${renderChartAxes(width, height, padding, scaler, {
        xLabel: currentLocale === "en" ? "Temperature (°C)" : "温度 (°C)",
        yLabel: currentLocale === "en" ? "Deformation" : "形变",
      })}
    `;
  }
  workspaceCurvePointsNode.innerHTML = plottedPoints
    .map(
      (point) =>
        `<circle class="workspace-curve-point" data-point-index="${point.index}" cx="${point.x}" cy="${point.y}" r="6"></circle>`,
    )
    .join("");
  workspaceCurvePointsNode.querySelectorAll(".workspace-curve-point").forEach((node) => {
    node.addEventListener("click", () => {
      const pointIndex = Number(node.dataset.pointIndex || "0");
      setActiveWorkspacePoint(pointIndex);
    });
  });

  if (detail.af95 === null) {
    workspaceAf95LineNode.setAttribute("x1", "0");
    workspaceAf95LineNode.setAttribute("x2", "0");
    workspaceAf95LineNode.setAttribute("y1", "0");
    workspaceAf95LineNode.setAttribute("y2", "0");
  } else {
    const af95X = scaler.x(detail.af95);
    workspaceAf95LineNode.setAttribute("x1", String(af95X));
    workspaceAf95LineNode.setAttribute("x2", String(af95X));
    workspaceAf95LineNode.setAttribute("y1", String(padding.top));
    workspaceAf95LineNode.setAttribute("y2", String(height - padding.bottom));
  }

  workspaceCurveEmptyNode.hidden = true;
}

function setActiveWorkspacePoint(index) {
  if (!workspaceCurvePointsNode || !workspaceKeyframesNode) {
    return;
  }
  workspaceCurvePointsNode.querySelectorAll(".workspace-curve-point").forEach((node) => {
    node.classList.toggle("workspace-curve-point--active", node.dataset.pointIndex === String(index));
  });
  workspaceKeyframesNode.querySelectorAll(".key-frame-card").forEach((node) => {
    node.classList.toggle("workspace-keyframe-card--active", node.dataset.pointIndex === String(index));
  });

  if (!workspaceDetailState) {
    renderActiveSelection(null);
    return;
  }

  const point = workspaceDetailState.points?.[index] || null;
  const frame = (workspaceDetailState.key_frames || []).find((item) => item.timestamp_ms === point?.timestamp_ms) || null;
  renderActiveSelection({
    label: frame?.label || `point-${index + 1}`,
    timestamp_ms: point?.timestamp_ms ?? frame?.timestamp_ms ?? null,
    celsius: point?.celsius ?? null,
    metric_raw: point?.metric_raw ?? frame?.metric_raw ?? null,
    metric_norm: point?.metric_norm ?? null,
    feature_point_px: frame?.feature_point_px ?? null,
    quality: point?.quality ?? null,
    roi: frame?.roi ?? null,
    baseline_px: frame?.baseline_px ?? null,
    threshold_value: frame?.threshold_value ?? null,
    component_area: frame?.component_area ?? null,
  });
}

function renderWorkspaceKeyframes(detail) {
  if (!workspaceKeyframesNode) {
    return;
  }
  const keyFrames = detail.key_frames || [];
  if (!keyFrames.length) {
    workspaceKeyframesNode.innerHTML = `<p class="session-item--empty">${currentLocale === "en" ? "No replay detail available." : "暂无 replay detail。"}</p>`;
    return;
  }

  const pointIndexByTimestamp = new Map((detail.points || []).map((point, index) => [point.timestamp_ms, index]));
  workspaceKeyframesNode.innerHTML = keyFrames
    .map((frame, index) => {
      const pointIndex = pointIndexByTimestamp.get(frame.timestamp_ms) ?? index;
      return `
        <article class="key-frame-card" data-point-index="${pointIndex}" data-testid="workspace-keyframe-card">
          <h3>${escapeHtml(frame.label)}</h3>
          <canvas id="workspace-keyframe-canvas-${index}" class="key-frame-canvas"></canvas>
          <p>timestamp=${frame.timestamp_ms}</p>
          <p>metric_raw=${frame.metric_raw === null ? "n/a" : frame.metric_raw}</p>
          <p>feature_point=${frame.feature_point_px === null ? "n/a" : frame.feature_point_px.join(", ")}</p>
        </article>
      `;
    })
    .join("");

  keyFrames.forEach((frame, index) => {
    const canvas = document.getElementById(`workspace-keyframe-canvas-${index}`);
    if (canvas) {
      drawFrameImage(canvas, frame.image, frame.feature_point_px);
    }
  });

  workspaceKeyframesNode.querySelectorAll(".key-frame-card").forEach((node) => {
    node.addEventListener("click", () => {
      const pointIndex = Number(node.dataset.pointIndex || "0");
      setActiveWorkspacePoint(pointIndex);
    });
  });

  setActiveWorkspacePoint(Number(workspaceKeyframesNode.querySelector(".key-frame-card")?.dataset.pointIndex || "0"));
}

function renderWorkspaceDetail(detail) {
  workspaceDetailState = detail;
  if (workspaceSourceNode) {
    workspaceSourceNode.textContent = localizeWorkspaceSourceLabel(detail.source);
  }
  if (workspaceDetailPointCountNode) {
    workspaceDetailPointCountNode.textContent = String((detail.points || []).length);
  }
  if (workspaceKeyframeCountNode) {
    workspaceKeyframeCountNode.textContent = String((detail.key_frames || []).length);
  }
  if (workspaceDetailStatusNode) {
    workspaceDetailStatusNode.textContent = (detail.points || []).length
      ? localizeStateLabel("available")
      : localizeStateLabel("missing");
  }
  if (workspaceAf95Node) {
    workspaceAf95Node.textContent = detail.af95 === null ? "N/A" : `${detail.af95} °C`;
  }
  renderWorkspaceCurve(detail);
  renderWorkspaceKeyframes(detail);
  if (!(detail.key_frames || []).length) {
    renderActiveSelection(null);
  } else {
    updateWorkspaceAdjustmentPreview(null);
  }
  refreshWorkspaceStages();
}

async function loadWorkspaceAdjustmentState(sessionId) {
  const response = await fetch(`/api/session/${sessionId}/adjustment`);
  if (!response.ok) {
    throw new Error(`adjustment request failed: ${response.status}`);
  }
  const payload = await response.json();
  renderAdjustmentState(payload);
  return payload;
}

function renderReplayDetail(detail) {
  if (!detailAf95Node || !detailPointCountNode) {
    return;
  }
  detailAf95Node.textContent = detail.af95 === null ? "n/a" : String(detail.af95);
  detailPointCountNode.textContent = String(detail.point_count);
  renderCurve(detail.points || []);
  renderKeyFrames(detail.key_frames || []);
}

async function loadSessionDetail(sessionId) {
  const response = await fetch(`/api/session/${sessionId}/detail`);
  if (!response.ok) {
    throw new Error(`detail request failed: ${response.status}`);
  }
  const payload = await response.json();
  renderReplayDetail(payload);
}

async function hydrateHomeResultForSession(sessionId, fallbackPayload = null) {
  if (!sessionId) {
    if (fallbackPayload) {
      renderSessionResult(fallbackPayload);
    }
    return;
  }
  let summaryLoaded = false;
  try {
    const summaryResponse = await fetch(`/api/session/${sessionId}`);
    if (summaryResponse.ok) {
      const summaryPayload = await summaryResponse.json();
      renderSessionResult(summaryPayload);
      summaryLoaded = true;
    }
  } catch (error) {
    // Best effort only; keep the fallback payload if summary hydration fails.
  }
  try {
    await loadSessionDetail(sessionId);
  } catch (error) {
    // Compact result still stays useful when replay detail is unavailable.
  }
  if (!summaryLoaded && fallbackPayload) {
    renderSessionResult(fallbackPayload);
  }
}

async function saveSessionData() {
  const sessionId = homeCompactResultState?.session_id || "";
  if (!sessionId || !saveSessionDataButton) {
    setLiveRunMessage(currentLocale === "en" ? "No recorded session is available to save." : "当前没有可保存的会话数据。", "warning");
    return;
  }

  saveSessionDataButton.disabled = true;
  setLiveRunMessage(currentLocale === "en" ? "Preparing session data..." : "正在准备保存数据...", "info");
  try {
    const [summaryResponse, detailResponse] = await Promise.allSettled([
      fetch(`/api/session/${sessionId}`),
      fetch(`/api/session/${sessionId}/detail`),
    ]);

    let summaryPayload = null;
    if (summaryResponse.status === "fulfilled" && summaryResponse.value.ok) {
      summaryPayload = await summaryResponse.value.json();
    }

    let detailPayload = null;
    if (detailResponse.status === "fulfilled" && detailResponse.value.ok) {
      detailPayload = await detailResponse.value.json();
    }

    if (!summaryPayload && !detailPayload) {
      throw new Error(currentLocale === "en" ? "Session artifacts are not available yet." : "当前会话的数据产物暂不可用。");
    }

    const bundle = {
      exported_at: new Date().toISOString(),
      session_id: sessionId,
      summary: summaryPayload,
      detail: detailPayload,
    };
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const objectUrl = URL.createObjectURL(blob);
    const downloadLink = document.createElement("a");
    downloadLink.href = objectUrl;
    downloadLink.download = `${sessionId}-session-data.json`;
    downloadLink.click();
    URL.revokeObjectURL(objectUrl);
    setLiveRunMessage(currentLocale === "en" ? "Session data saved to a local file." : "测试数据已保存为本地文件。", "success");
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    saveSessionDataButton.disabled = false;
    renderHomeCompactResultSummary(homeCompactResultState);
  }
}

async function runSession(endpoint, button, idleLabel) {
  button.disabled = true;
  button.textContent = currentLocale === "en" ? "Running..." : "运行中...";
  try {
    const runResponse = await fetch(endpoint, { method: "POST" });
    const runPayload = await runResponse.json();
    renderSessionResult(runPayload);

    if (runPayload.session_id) {
      await hydrateHomeResultForSession(runPayload.session_id, runPayload);
    }
    await loadRecentSessions();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  } finally {
    button.disabled = false;
    button.textContent = idleLabel;
  }
}

async function runMockSession() {
  await runSession("/api/session/run-mock", runMockButton, currentLocale === "en" ? "Run Mock Session" : "运行 Mock 会话");
}

async function runReplaySession() {
  runReplayButton.disabled = true;
  runReplayButton.textContent = currentLocale === "en" ? "Running..." : "运行中...";
  try {
    const runResponse = await fetch("/api/session/run-replay", { method: "POST" });
    const runPayload = await runResponse.json();
    renderSessionResult(runPayload);
    if (runPayload.session_id) {
      await hydrateHomeResultForSession(runPayload.session_id, runPayload);
    }
    await loadRecentSessions();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  } finally {
    runReplayButton.disabled = false;
    runReplayButton.textContent = currentLocale === "en" ? "Run Replay Session" : "运行 Replay 会话";
  }
}

async function submitImportedAfasDataset(file) {
  const parsedPayload = JSON.parse(await file.text());
  const response = await fetch("/api/session/import-afas-dataset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsedPayload),
  });
  const responsePayload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(responsePayload.detail || `HTTP ${response.status}`);
  }
  return responsePayload;
}

async function importAfasDataset() {
  if (!importAfasDatasetButton || !importAfasDatasetFileInput) {
    return;
  }
  const file = importAfasDatasetFileInput.files?.[0];
  if (!file) {
    renderSessionResult({
      detail:
        currentLocale === "en"
          ? "Choose an afas_dataset.json file before importing."
          : "请先选择一个 afas_dataset.json 文件再导入。",
    });
    return;
  }

  importAfasDatasetButton.disabled = true;
  importAfasDatasetButton.textContent = currentLocale === "en" ? "Importing..." : "导入中...";
  try {
    const responsePayload = await submitImportedAfasDataset(file);
    renderSessionResult(responsePayload);
    if (responsePayload.session_id) {
      await hydrateHomeResultForSession(responsePayload.session_id, responsePayload);
    }
    importAfasDatasetFileInput.value = "";
    await loadRecentSessions();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  } finally {
    importAfasDatasetButton.disabled = false;
    importAfasDatasetButton.textContent = t(
      "home.actions.import_afas_dataset",
      {},
      currentLocale === "en" ? "Import AFAS Dataset" : "导入 AFAS 数据集",
    );
  }
}

function setWorkspaceImportHint(message) {
  if (workspaceImportAfasDatasetHintNode) {
    workspaceImportAfasDatasetHintNode.textContent = message;
  }
}

async function importWorkspaceAfasDataset() {
  if (!workspaceImportAfasDatasetButton || !workspaceImportAfasDatasetFileInput) {
    return;
  }
  const file = workspaceImportAfasDatasetFileInput.files?.[0];
  if (!file) {
    setWorkspaceImportHint(
      currentLocale === "en"
        ? "Choose an afas_dataset.json file before importing."
        : "请先选择一个 afas_dataset.json 文件再导入。",
    );
    return;
  }

  workspaceImportAfasDatasetButton.disabled = true;
  workspaceImportAfasDatasetButton.textContent = currentLocale === "en" ? "Importing..." : "导入中...";
  setWorkspaceImportHint(
    currentLocale === "en"
      ? "Importing the dataset and opening the new analysis workspace..."
      : "正在导入数据，并打开新的分析页面...",
  );
  try {
    const responsePayload = await submitImportedAfasDataset(file);
    if (!responsePayload.session_id) {
      throw new Error(currentLocale === "en" ? "Import completed without a session id." : "导入完成，但没有返回会话 ID。");
    }
    setWorkspaceImportHint(
      currentLocale === "en"
        ? "Import succeeded. Redirecting to the new analysis workspace..."
        : "导入成功，正在打开新的分析页面...",
    );
    window.location.assign(`/workspace/${encodeURIComponent(responsePayload.session_id)}`);
  } catch (error) {
    setWorkspaceImportHint(String(error));
  } finally {
    workspaceImportAfasDatasetButton.disabled = false;
    workspaceImportAfasDatasetButton.textContent = t(
      "workspace.actions.import_data",
      {},
      currentLocale === "en" ? "Import Data" : "导入数据",
    );
    workspaceImportAfasDatasetFileInput.value = "";
  }
}

function isLiveSetupReusable(detail) {
  if (!detail || !detail.run_id) {
    return false;
  }
  return !["completed", "failed", "aborted"].includes(String(detail.status || ""));
}

function buildTerminalRunFallbackPayload(runId, status, telemetryPayload = null) {
  return {
    session_id: runId,
    state: status || "completed",
    point_count: Array.isArray(telemetryPayload?.curve) ? telemetryPayload.curve.length : 0,
    af95: null,
  };
}

async function fetchRunTelemetryPayload(runId) {
  try {
    const response = await fetch(`/api/runs/${runId}/telemetry`);
    return response.ok ? await response.json() : null;
  } catch (error) {
    return null;
  }
}

async function fetchRunResultPayload(runId) {
  try {
    const response = await fetch(`/api/runs/${runId}/result`);
    return response.ok ? await response.json() : null;
  } catch (error) {
    return null;
  }
}

async function fetchSessionSummaryPayload(sessionId) {
  try {
    const response = await fetch(`/api/session/${sessionId}`);
    return response.ok ? await response.json() : null;
  } catch (error) {
    return null;
  }
}

function buildTerminalRunDetailFromSessionSummary(summary) {
  return {
    run_id: summary.session_id,
    status: summary.state,
    point_count: summary.point_count,
    af95: summary.af95,
    session_summary_only: true,
    preset: liveRunPresetSelect ? liveRunPresetSelect.value : "balloon",
    definition: null,
    rates: {},
    preview: {
      stream_active: false,
      frozen_frame_available: false,
      last_frame_id: null,
    },
    temperature_settings: null,
  };
}

async function restoreTerminalLiveRunHomeState(runId, detail = null) {
  stopLiveTrackingLoop();
  stopCurrentTemperaturePolling();
  liveRunState.previewStreamActive = false;
  liveRunState.previewStreamUrl = "";
  if (detail) {
    renderLiveRunDetail(detail);
  }

  const sessionSummaryOnly = Boolean(detail?.session_summary_only);
  const telemetryPayload = sessionSummaryOnly ? null : await fetchRunTelemetryPayload(runId);
  const status = String(detail?.status || telemetryPayload?.status || "completed");
  const resultPayload =
    (sessionSummaryOnly
      ? {
          session_id: runId,
          state: status,
          point_count: Number(detail?.point_count || 0),
          af95: detail?.af95 ?? null,
        }
      : await fetchRunResultPayload(runId)) || buildTerminalRunFallbackPayload(runId, status, telemetryPayload);

  if (telemetryPayload?.latest) {
    renderCurrentTemperature({ temperature_celsius: telemetryPayload.latest.temperature_celsius });
    applyTrackedPointInputs(telemetryPayload.latest);
  }
  if (telemetryPayload) {
    renderLiveProcessTelemetry(telemetryPayload, resultPayload);
  }
  if (sessionSummaryOnly) {
    liveRunState.previewSize = null;
    liveRunState.previewFrozenAvailable = false;
    renderLivePreviewOverlay();
  } else {
    try {
      await refreshTrackingPreviewFrame(runId);
      if (telemetryPayload?.latest) {
        applyTrackedPointInputs(telemetryPayload.latest);
        renderLivePreviewOverlay();
      }
    } catch (error) {
      liveRunState.previewSize = null;
      liveRunState.previewFrozenAvailable = false;
      renderLivePreviewOverlay();
    }
  }
  await hydrateHomeResultForSession(runId, resultPayload);
  setLiveRunMessage(
    currentLocale === "en"
      ? `Restored completed test ${runId}. Use New Test only when you want to clear this result.`
      : `已恢复当前测试 ${runId}。只有点击“新测试”才会清空并开始下一次测试。`,
    "success",
  );
  updateLiveRunControls();
}

function resetNewLiveTestConfirmation({ resetLabel = true, resetMessage = false } = {}) {
  if (newLiveTestConfirmationTimer) {
    window.clearTimeout(newLiveTestConfirmationTimer);
    newLiveTestConfirmationTimer = null;
  }
  newLiveTestPendingConfirmation = false;
  if (!newLiveTestButton) {
    return;
  }
  newLiveTestButton.classList.remove("new-live-test-confirming");
  newLiveTestButton.setAttribute("aria-pressed", "false");
  if (resetLabel) {
    newLiveTestButton.textContent = t("home.actions.new_test", {}, currentLocale === "en" ? "New Test" : "新测试");
  }
  if (resetMessage && liveRunState.runId && isLiveRunTerminalStatus(liveRunState.detail?.status)) {
    setLiveRunMessage(
      currentLocale === "en"
        ? `Restored completed test ${liveRunState.runId}. Use New Test only when you want to clear this result.`
        : `已恢复当前测试 ${liveRunState.runId}。只有点击“新测试”才会清空并开始下一次测试。`,
      "success",
    );
  }
}

function requestNewLiveTestConfirmation() {
  if (!newLiveTestButton || newLiveTestButton.disabled) {
    return;
  }
  if (newLiveTestConfirmationTimer) {
    window.clearTimeout(newLiveTestConfirmationTimer);
  }
  newLiveTestPendingConfirmation = true;
  newLiveTestButton.classList.add("new-live-test-confirming");
  newLiveTestButton.setAttribute("aria-pressed", "true");
  newLiveTestButton.textContent = t(
    "home.actions.confirm_new_test",
    {},
    currentLocale === "en" ? "Confirm New Test" : "确认新测试",
  );
  setLiveRunMessage(
    t(
      "home.messages.new_test_confirm",
      {},
      currentLocale === "en"
        ? "Click Confirm New Test again to clear the current result and start the next test."
        : "再次点击“确认新测试”才会清空当前结果并开始下一次测试。",
    ),
    "warning",
  );
  newLiveTestConfirmationTimer = window.setTimeout(() => {
    resetNewLiveTestConfirmation({ resetMessage: true });
  }, NEW_LIVE_TEST_CONFIRM_TIMEOUT_MS);
}

function handleNewLiveTestClick() {
  if (!newLiveTestPendingConfirmation) {
    requestNewLiveTestConfirmation();
    return;
  }
  void startNewLiveTest();
}

async function startNewLiveTest() {
  if (!hasLiveSetupUi() || !newLiveTestButton) {
    return;
  }
  resetNewLiveTestConfirmation();
  newLiveTestButton.disabled = true;
  setLiveRunMessage(currentLocale === "en" ? "Starting a new test..." : "正在开始新测试...", "info");
  try {
    stopLiveTrackingLoop();
    await stopLivePreviewStream({ clearImage: true, silent: true });
    storeLiveSetupRunId("");
    clearHomeResultDisplays();
    resetLiveProcessTelemetry();
    liveRunState.confirmedTemperatureSettings = null;
    clearTemperatureSettingsConfirmation();
    const runId = await createLiveRun({ autoStartPreview: true, silent: true, forceReset: true });
    startCurrentTemperaturePolling();
    setLiveRunMessage(
      currentLocale === "en"
        ? `New test ${runId} is ready. Freeze the preview to define ROI.`
        : `新测试 ${runId} 已就绪。请先冻结画面再框选 ROI。`,
      "success",
    );
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    resetNewLiveTestConfirmation();
    newLiveTestButton.disabled = false;
    updateLiveRunControls();
  }
}

async function ensureLiveSetupBootstrapped({ forceRestart = false } = {}) {
  if (!hasLiveSetupUi()) {
    return;
  }
  let runId = forceRestart ? "" : getStoredLiveSetupRunId();
  let detail = null;
  if (runId) {
    try {
      detail = await refreshLiveRunDetail(runId);
    } catch (error) {
      const summary = await fetchSessionSummaryPayload(runId);
      if (summary && isLiveRunTerminalStatus(summary.state)) {
        storeLiveSetupRunId(runId);
        await restoreTerminalLiveRunHomeState(runId, buildTerminalRunDetailFromSessionSummary(summary));
        return;
      }
      runId = "";
      storeLiveSetupRunId("");
    }
  }
  if (runId && detail && isLiveRunTerminalStatus(detail.status)) {
    storeLiveSetupRunId(runId);
    await restoreTerminalLiveRunHomeState(runId, detail);
    return;
  }
  if (!isLiveSetupReusable(detail)) {
    runId = await createLiveRun({ autoStartPreview: false, silent: true, forceReset: true });
    detail = await refreshLiveRunDetail(runId);
  }
  storeLiveSetupRunId(runId);
  await startLivePreviewStream({ silent: true });
  setLiveRunMessage(
    currentLocale === "en"
      ? "Live preview started automatically. Press Freeze when you are ready to define the ROI."
      : "实时预览已自动启动。准备定义 ROI 时请按“冻结画面”。",
    "success",
  );
}

async function bootstrap() {
  try {
    renderHomeCompactResultSummary(null);
    resetLiveProcessTelemetry();
    await Promise.all([
      loadHealth(),
      loadProfile(),
      loadFixtureVideoSwitch(),
      loadPrecheck(),
      loadRecentSessions(),
      refreshTempSerialPorts({ silent: true }),
    ]);
    if (liveRunPresetNode && liveRunPresetSelect) {
      liveRunPresetNode.textContent = liveRunPresetSelect.value;
    }
    startCurrentTemperaturePolling();
    await ensureLiveSetupBootstrapped();
    updateLiveRunControls();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
    if (hasLiveSetupUi()) {
      setLiveRunMessage(String(error), "error");
    }
  }
}

async function bootstrapWorkspace() {
  if (!workspaceShellNode) {
    return;
  }

  const sessionId = document.body.dataset.sessionId;
  if (!sessionId) {
    return;
  }

  syncWorkspaceAfasAvailability();
  const [summaryResponse, detailResponse, adjustmentResponse, afasResponse] = await Promise.allSettled([
    fetch(`/api/session/${sessionId}`),
    fetch(`/api/session/${sessionId}/detail`),
    fetch(`/api/session/${sessionId}/adjustment`),
    hasWorkspaceAfasUi() && isWorkspaceAfasAvailable() ? loadWorkspaceAfasAnalysis(sessionId, { silent: true }) : Promise.resolve(null),
  ]);

  if (summaryResponse.status !== "fulfilled" || !summaryResponse.value.ok) {
    return;
  }

  const summary = await summaryResponse.value.json();
  renderWorkspaceSummary(summary);

  if (detailResponse.status === "fulfilled" && detailResponse.value.ok) {
    const detail = await detailResponse.value.json();
    renderWorkspaceDetail(detail);
  } else {
    const emptyDetail = {
      source: "n/a",
      af95: summary.af95,
      points: [],
      key_frames: [],
    };
    renderWorkspaceDetail(emptyDetail);
  }

  if (adjustmentResponse.status === "fulfilled" && adjustmentResponse.value.ok) {
    renderAdjustmentState(await adjustmentResponse.value.json());
  } else {
    renderAdjustmentState(null);
  }

  if (afasResponse.status === "fulfilled" && afasResponse.value) {
    renderWorkspaceAfas(afasResponse.value);
  } else if (hasWorkspaceAfasUi()) {
    renderWorkspaceAfas(null);
  }
}

async function saveWorkspaceDraft() {
  const sessionId = getWorkspaceSessionId();
  if (!sessionId || !adjustmentSaveDraftButton || !adjustmentApplyButton) {
    return;
  }
  const payload = collectDraftPayload();
  if (!payload.reason) {
    setAdjustmentStatusMessage("Reason is required before saving a draft.", "error");
    return;
  }
  if (payload.overrides.af95 !== null && Number.isNaN(payload.overrides.af95)) {
    setAdjustmentStatusMessage("Draft Af95 must be a number or empty.", "error");
    return;
  }

  adjustmentSaveDraftButton.disabled = true;
  adjustmentApplyButton.disabled = true;
  setAdjustmentStatusMessage("Saving draft...", "info");
  try {
    const response = await fetch(`/api/session/${sessionId}/adjustment/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const responsePayload = await response.json();
    if (!response.ok) {
      throw new Error(responsePayload.detail || `draft save failed: ${response.status}`);
    }
    renderAdjustmentState(responsePayload);
    setAdjustmentStatusMessage("Draft saved.", "success");
  } catch (error) {
    setAdjustmentStatusMessage(String(error), "error");
  } finally {
    adjustmentSaveDraftButton.disabled = false;
    adjustmentApplyButton.disabled = !(workspaceAdjustmentState && workspaceAdjustmentState.draft);
  }
}

async function applyWorkspaceAdjustment() {
  const sessionId = getWorkspaceSessionId();
  if (!sessionId || !adjustmentSaveDraftButton || !adjustmentApplyButton) {
    return;
  }

  adjustmentSaveDraftButton.disabled = true;
  adjustmentApplyButton.disabled = true;
  setAdjustmentStatusMessage("Applying adjustment...", "info");
  try {
    const response = await fetch(`/api/session/${sessionId}/adjustment/apply`, {
      method: "POST",
    });
    const responsePayload = await response.json();
    if (!response.ok) {
      throw new Error(responsePayload.detail || `adjustment apply failed: ${response.status}`);
    }
    renderAdjustmentState(responsePayload);
    setAdjustmentStatusMessage("Adjustment applied.", "success");
  } catch (error) {
    setAdjustmentStatusMessage(String(error), "error");
  } finally {
    adjustmentSaveDraftButton.disabled = false;
    adjustmentApplyButton.disabled = !(workspaceAdjustmentState && workspaceAdjustmentState.draft);
  }
}

if (runMockButton) {
  runMockButton.addEventListener("click", runMockSession);
}
if (runReplayButton) {
  runReplayButton.addEventListener("click", runReplaySession);
}
if (refreshPrecheckButton) {
  refreshPrecheckButton.addEventListener("click", loadPrecheck);
}
if (probeModeSelect) {
  probeModeSelect.addEventListener("change", () => {
    probeControlsDirty = true;
    syncCameraProbeControls();
  });
}
for (const probeInput of [probeAllowedModelsInput, probeSerialNumberInput, probeIpInput]) {
  if (probeInput) {
    probeInput.addEventListener("input", () => {
      probeControlsDirty = true;
      syncCameraProbeControls();
    });
  }
}
if (probeCameraButton) {
  probeCameraButton.addEventListener("click", runCameraProbe);
}
if (fixtureVideoSelectNode) {
  fixtureVideoSelectNode.addEventListener("change", () => {
    void switchFixtureVideo(fixtureVideoSelectNode.value);
  });
}
if (liveRunPresetSelect && liveRunPresetNode) {
  liveRunPresetSelect.addEventListener("change", () => {
    liveRunPresetNode.textContent = liveRunPresetSelect.value;
    if (hasLiveSetupUi()) {
      void ensureLiveSetupBootstrapped({ forceRestart: true });
    }
  });
}
if (importAfasDatasetButton) {
  importAfasDatasetButton.addEventListener("click", () => {
    void importAfasDataset();
  });
}
if (workspaceImportAfasDatasetButton && workspaceImportAfasDatasetFileInput) {
  workspaceImportAfasDatasetButton.addEventListener("click", () => {
    workspaceImportAfasDatasetFileInput.click();
  });
  workspaceImportAfasDatasetFileInput.addEventListener("change", () => {
    void importWorkspaceAfasDataset();
  });
}
if (saveSessionDataButton) {
  saveSessionDataButton.addEventListener("click", () => {
    void saveSessionData();
  });
}
if (newLiveTestButton) {
  newLiveTestButton.addEventListener("click", () => {
    handleNewLiveTestClick();
  });
}
if (stopLivePreviewStreamButton) {
  stopLivePreviewStreamButton.addEventListener("click", () => {
    void stopLivePreviewStream();
  });
}
if (saveLiveDefinitionButton) {
  saveLiveDefinitionButton.addEventListener("click", saveLiveDefinition);
}
if (startLiveRunButton) {
  startLiveRunButton.addEventListener("click", startLiveRun);
}
if (confirmTargetTemperatureButton) {
  confirmTargetTemperatureButton.addEventListener("click", confirmTargetTemperature);
}
if (refreshTempSerialPortsButton) {
  refreshTempSerialPortsButton.addEventListener("click", () => {
    void refreshTempSerialPorts();
  });
}
if (applyTempSerialPortButton) {
  applyTempSerialPortButton.addEventListener("click", () => {
    void applyTempSerialPort();
  });
}
if (stopLiveRunButton) {
  stopLiveRunButton.addEventListener("click", stopLiveRun);
}
if (startLivePreviewStreamButton) {
  startLivePreviewStreamButton.addEventListener("click", () => {
    void startLivePreviewStream();
  });
}
if (recomputeDefinitionButton) {
  recomputeDefinitionButton.addEventListener("click", () => {
    scheduleRoiPointRecompute({
      message:
        currentLocale === "en"
          ? "Captured a new frame and recomputed ROI-local A/B."
          : "已抓取新画面并重新计算 ROI 内 A/B。",
    });
  });
}
for (const temperatureInput of [liveTargetTemperatureInput, liveControlModeSelect, liveCompletionModeSelect, liveOutputPowerInput]) {
  if (!temperatureInput) {
    continue;
  }
  for (const eventName of ["input", "change"]) {
    temperatureInput.addEventListener(eventName, clearTemperatureSettingsConfirmation);
  }
}
if (drawAnalysisRoiButton) {
  drawAnalysisRoiButton.addEventListener("click", () => setActiveLiveTool("draw-roi"));
}
for (const liveInput of [
  liveForegroundPolaritySelect,
  liveThresholdModeSelect,
  liveDirectionProjectionModeSelect,
  liveTargetGeometryModeSelect,
  liveSideGuardRatioInput,
  liveIgnoreInternalTextureInput,
  liveMinTargetAreaInput,
]) {
  if (liveInput) {
    liveInput.addEventListener("input", updateLiveDefinitionAfterLocalEdit);
    liveInput.addEventListener("change", updateLiveDefinitionAfterLocalEdit);
  }
}
for (const envelopeInput of [liveDirectionProjectionModeSelect, liveTargetGeometryModeSelect, liveSideGuardRatioInput]) {
  if (envelopeInput) {
    envelopeInput.addEventListener("change", () => {
      scheduleRoiPointRecompute({
        message:
          currentLocale === "en"
            ? "Detection mode updated. Captured a new frame and recomputed ROI-local A/B."
            : "检测模式已更新，已抓取新画面并重新计算 ROI 内 A/B。",
      });
    });
  }
}
for (const roiInput of [
  liveAnalysisRoiXInput,
  liveAnalysisRoiYInput,
  liveAnalysisRoiWidthInput,
  liveAnalysisRoiHeightInput,
  liveAnalysisRoiAngleInput,
]) {
  if (roiInput) {
    roiInput.addEventListener("input", () => handleAnalysisRoiInputsChanged({ recompute: false }));
    roiInput.addEventListener("change", () => handleAnalysisRoiInputsChanged({ recompute: true }));
  }
}
if (liveSensitivityInput) {
  liveSensitivityInput.addEventListener("input", updateLiveDefinitionAfterLocalEdit);
  liveSensitivityInput.addEventListener("change", () => {
    updateLiveDefinitionAfterLocalEdit();
    scheduleRoiPointRecompute({ message: "Sensitivity updated. Captured a new frame and recomputed ROI-local A/B." });
  });
}
for (const pointInput of [livePointAXInput, livePointAYInput, livePointBXInput, livePointBYInput]) {
  if (pointInput) {
    pointInput.addEventListener("input", handlePointInputsChanged);
    pointInput.addEventListener("change", handlePointInputsChanged);
  }
}
if (livePreviewImageNode) {
  livePreviewImageNode.addEventListener("load", () => {
    if (!liveRunState.previewSize && livePreviewImageNode.naturalWidth && livePreviewImageNode.naturalHeight) {
      liveRunState.previewSize = {
        width: livePreviewImageNode.naturalWidth,
        height: livePreviewImageNode.naturalHeight,
      };
      if (!liveRunState.previewSourceSize) {
        liveRunState.previewSourceSize = {
          width: liveRunState.measurementSourceSize?.width || livePreviewImageNode.naturalWidth,
          height: liveRunState.measurementSourceSize?.height || livePreviewImageNode.naturalHeight,
        };
      }
      seedLiveDefinitionDefaults(liveRunState.previewSize.width, liveRunState.previewSize.height);
    }
    showLivePreviewStage();
    syncLiveDefinitionDirtyState();
    renderLivePreviewMeta();
    renderLivePreviewOverlay();
    updateLiveRunControls();
  });
  livePreviewImageNode.addEventListener("error", () => {
    if (!liveRunState.previewStreamActive) {
      return;
    }
    void recoverLivePreviewStreamError();
  });
}
if (livePreviewOverlayNode) {
  livePreviewOverlayNode.addEventListener("pointerdown", handleLivePreviewPointerDown);
  livePreviewOverlayNode.addEventListener("pointermove", handleLivePreviewPointerMove);
  livePreviewOverlayNode.addEventListener("pointerup", handleLivePreviewPointerUp);
  livePreviewOverlayNode.addEventListener("pointercancel", handleLivePreviewPointerUp);
}
if (workspaceRefreshButton) {
  workspaceRefreshButton.addEventListener("click", bootstrapWorkspace);
}
if (workspaceAfasRunButton) {
  workspaceAfasRunButton.addEventListener("click", () => {
    const sessionId = getWorkspaceSessionId();
    if (!sessionId) {
      return;
    }
    void loadWorkspaceAfasAnalysis(sessionId);
  });
}
if (workspaceAfasExportPngButton) {
  workspaceAfasExportPngButton.addEventListener("click", () => {
    void exportWorkspaceAfasArtifact("png");
  });
}
if (workspaceAfasExportXlsxButton) {
  workspaceAfasExportXlsxButton.addEventListener("click", () => {
    void exportWorkspaceAfasArtifact("xlsx");
  });
}
if (workspaceAfasChannelNode) {
  workspaceAfasChannelNode.addEventListener("change", () => {
    queueWorkspaceAfasRefresh({ delay: 0, silent: true });
  });
}
for (const node of [
  workspaceAfasSavgolWindowNode,
  workspaceAfasSavgolPolyorderNode,
  workspaceAfasLowStartNode,
  workspaceAfasLowEndNode,
  workspaceAfasHighStartNode,
  workspaceAfasHighEndNode,
  workspaceAfasTangentOffsetNode,
]) {
  if (!node) {
    continue;
  }
  node.addEventListener("change", () => {
    queueWorkspaceAfasRefresh({ delay: 120, silent: true });
  });
}
if (adjustmentSaveDraftButton) {
  adjustmentSaveDraftButton.addEventListener("click", saveWorkspaceDraft);
}
if (adjustmentApplyButton) {
  adjustmentApplyButton.addEventListener("click", applyWorkspaceAdjustment);
}
currentLocale = getSavedLocale() || document.body.dataset.locale || "zh";
applyStaticTranslations();
syncLanguageToggleUi();
languageToggleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setLocale(button.dataset.languageToggle || "zh");
  });
});
if (document.body.dataset.page === "home") {
  syncCameraProbeControls();
  bootstrap();
}
if (document.body.dataset.page === "workspace") {
  bootstrapWorkspace();
}
