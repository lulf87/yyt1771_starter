const healthStatusNode = document.getElementById("health-status");
const profileNameNode = document.getElementById("profile-name");
const profileModeNode = document.getElementById("profile-mode");
const sessionResultNode = document.getElementById("session-result");
const recentSessionsNode = document.getElementById("recent-sessions");
const runMockButton = document.getElementById("run-mock-btn");
const runReplayButton = document.getElementById("run-replay-btn");
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
const livePreviewRateNode = document.getElementById("live-preview-rate");
const liveMeasurementRateNode = document.getElementById("live-measurement-rate");
const createLiveRunButton = document.getElementById("create-live-run-btn");
const fetchLivePreviewButton = document.getElementById("fetch-live-preview-btn");
const startLivePreviewStreamButton = document.getElementById("start-live-preview-stream-btn");
const stopLivePreviewStreamButton = document.getElementById("stop-live-preview-stream-btn");
const autoDetectDefinitionButton = document.getElementById("auto-detect-definition-btn");
const saveLiveDefinitionButton = document.getElementById("save-live-definition-btn");
const startLiveRunButton = document.getElementById("start-live-run-btn");
const stopLiveRunButton = document.getElementById("stop-live-run-btn");
const drawAnalysisRoiButton = document.getElementById("draw-analysis-roi-btn");
const drawObservationWindowButton = document.getElementById("draw-observation-window-btn");
const rotateObservationWindowButton = document.getElementById("rotate-observation-window-btn");
const livePreviewStageNode = document.getElementById("live-preview-stage");
const livePreviewImageNode = document.getElementById("live-preview-img");
const livePreviewOverlayNode = document.getElementById("live-preview-overlay");
const livePreviewEmptyNode = document.getElementById("live-preview-empty");
const livePointPickerStatusNode = document.getElementById("live-point-picker-status");
const liveRunMessageNode = document.getElementById("live-run-message");
const pickPointAButton = document.getElementById("pick-point-a-btn");
const pickPointBButton = document.getElementById("pick-point-b-btn");
const liveAnalysisRoiXInput = document.getElementById("live-analysis-roi-x");
const liveAnalysisRoiYInput = document.getElementById("live-analysis-roi-y");
const liveAnalysisRoiWidthInput = document.getElementById("live-analysis-roi-width");
const liveAnalysisRoiHeightInput = document.getElementById("live-analysis-roi-height");
const liveMetricBoxCenterXInput = document.getElementById("live-metric-box-center-x");
const liveMetricBoxCenterYInput = document.getElementById("live-metric-box-center-y");
const liveMetricBoxWidthInput = document.getElementById("live-metric-box-width");
const liveMetricBoxHeightInput = document.getElementById("live-metric-box-height");
const liveMetricBoxAngleInput = document.getElementById("live-metric-box-angle");
const livePointAXInput = document.getElementById("live-point-a-x");
const livePointAYInput = document.getElementById("live-point-a-y");
const livePointBXInput = document.getElementById("live-point-b-x");
const livePointBYInput = document.getElementById("live-point-b-y");
const liveForegroundPolaritySelect = document.getElementById("live-foreground-polarity");
const liveThresholdModeSelect = document.getElementById("live-threshold-mode");
const liveIgnoreInternalTextureInput = document.getElementById("live-ignore-internal-texture");
const liveMinTargetAreaInput = document.getElementById("live-min-target-area");
const liveTargetTemperatureInput = document.getElementById("live-target-temperature");
const refreshPrecheckButton = document.getElementById("refresh-precheck-btn");
const precheckStatusNode = document.getElementById("precheck-status");
const precheckItemsNode = document.getElementById("precheck-items");
const cameraProbeResultNode = document.getElementById("camera-probe-result");
const detailAf95Node = document.getElementById("detail-af95");
const detailPointCountNode = document.getElementById("detail-point-count");
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
const workspaceCurveNode = document.getElementById("workspace-curve-line");
const workspaceCurvePointsNode = document.getElementById("workspace-curve-points");
const workspaceCurveEmptyNode = document.getElementById("workspace-curve-empty");
const workspaceAf95LineNode = document.getElementById("workspace-af95-line");
const workspaceKeyframesNode = document.getElementById("workspace-keyframes");
const workspaceCurrentStageNode = document.getElementById("workspace-current-stage");
const workspaceStageDescriptionNode = document.getElementById("workspace-stage-description");
const workspaceDetailStatusNode = document.getElementById("workspace-detail-status");
const workspaceRefreshButton = document.getElementById("workspace-refresh-btn");
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

const WORKSPACE_STEPS = ["准备", "采集", "处理", "计算", "调整", "存储"];
let workspaceDetailState = null;
let workspaceSummaryState = null;
let workspaceStageState = null;
let workspaceActiveSelectionState = null;
let workspaceAdjustmentState = null;
let probeControlsDirty = false;
const liveRunState = {
  runId: "",
  detail: null,
  previewObjectUrl: "",
  previewStreamUrl: "",
  previewStreamActive: false,
  previewFrozenAvailable: false,
  lastPreviewFrameId: null,
  previewSize: null,
  activeTool: "",
  overlayDrag: null,
  definitionDirty: false,
};

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
  if (sessionWorkspaceLinkNode && payload.session_id) {
    sessionWorkspaceLinkNode.href = workspaceUrl(payload.session_id);
    sessionWorkspaceLinkNode.classList.remove("workspace-link--hidden");
  }
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
      "Pinned Device requires allowed models plus serial number or IP before probing.";
    return;
  }

  probeModeHintNode.textContent =
    "Protocol Any allows first discovered probe when serial and IP are empty. You can still fill identity fields for a directed hit.";
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

function getNumericInputValue(node, fallback = 0) {
  if (!node || node.value === "") {
    return fallback;
  }
  const value = Number(node.value);
  return Number.isFinite(value) ? value : fallback;
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

function setLivePointPickerStatus(message) {
  if (!livePointPickerStatusNode) {
    return;
  }
  livePointPickerStatusNode.textContent = message;
}

function formatRateValue(value, unit) {
  if (!Number.isFinite(value) || Number(value) <= 0) {
    return "n/a";
  }
  return `${Number(value).toFixed(1)} ${unit}`;
}

function revokeLivePreviewUrl() {
  if (liveRunState.previewObjectUrl) {
    URL.revokeObjectURL(liveRunState.previewObjectUrl);
    liveRunState.previewObjectUrl = "";
  }
}

function clearLivePreviewImage() {
  revokeLivePreviewUrl();
  liveRunState.previewSize = null;
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
}

function updateLiveToolButtons() {
  for (const [button, tool] of [
    [drawAnalysisRoiButton, "draw-roi"],
    [drawObservationWindowButton, "draw-box"],
    [rotateObservationWindowButton, "rotate-box"],
    [pickPointAButton, "pick-a"],
    [pickPointBButton, "pick-b"],
  ]) {
    if (!button) {
      continue;
    }
    button.classList.toggle("button-active", liveRunState.activeTool === tool);
  }
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

function getCurrentAnalysisRoi() {
  return {
    x: getNumericInputValue(liveAnalysisRoiXInput),
    y: getNumericInputValue(liveAnalysisRoiYInput),
    width: getNumericInputValue(liveAnalysisRoiWidthInput),
    height: getNumericInputValue(liveAnalysisRoiHeightInput),
  };
}

function getCurrentMetricBox() {
  return {
    center_x: getNumericInputValue(liveMetricBoxCenterXInput),
    center_y: getNumericInputValue(liveMetricBoxCenterYInput),
    width: getNumericInputValue(liveMetricBoxWidthInput),
    height: getNumericInputValue(liveMetricBoxHeightInput),
    angle_deg: getNumericInputValue(liveMetricBoxAngleInput, 0),
  };
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

function normalizeDefinitionForComparison(definition) {
  if (!definition) {
    return null;
  }
  return {
    analysis_roi: {
      x: Number(definition.analysis_roi.x),
      y: Number(definition.analysis_roi.y),
      width: Number(definition.analysis_roi.width),
      height: Number(definition.analysis_roi.height),
    },
    metric_box: {
      center_x: Number(definition.metric_box.center_x),
      center_y: Number(definition.metric_box.center_y),
      width: Number(definition.metric_box.width),
      height: Number(definition.metric_box.height),
      angle_deg: Number(definition.metric_box.angle_deg),
    },
    point_a_px: {
      x: Number(definition.point_a_px.x),
      y: Number(definition.point_a_px.y),
    },
    point_b_px: {
      x: Number(definition.point_b_px.x),
      y: Number(definition.point_b_px.y),
    },
    foreground_polarity: String(definition.foreground_polarity),
    threshold_mode: String(definition.threshold_mode),
    ignore_internal_texture: Boolean(definition.ignore_internal_texture),
    min_target_area_px: Number(definition.min_target_area_px),
  };
}

function syncLiveDefinitionDirtyState() {
  const savedDefinition = liveRunState.detail ? normalizeDefinitionForComparison(liveRunState.detail.definition) : null;
  const currentDefinition = normalizeDefinitionForComparison(buildLiveDefinitionPayload());
  liveRunState.definitionDirty = Boolean(savedDefinition) && JSON.stringify(savedDefinition) !== JSON.stringify(currentDefinition);
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function pointInRotatedMetricBox(box, x, y) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const cosTheta = Math.cos(angleRad);
  const sinTheta = Math.sin(angleRad);
  const translatedX = x - Number(box.center_x);
  const translatedY = y - Number(box.center_y);
  const localX = translatedX * cosTheta + translatedY * sinTheta;
  const localY = -translatedX * sinTheta + translatedY * cosTheta;
  return Math.abs(localX) <= Number(box.width) / 2 && Math.abs(localY) <= Number(box.height) / 2;
}

function seedPointsForMetricBox(box) {
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const offsetX = Math.cos(angleRad) * (Number(box.width) * 0.3);
  const offsetY = Math.sin(angleRad) * (Number(box.width) * 0.3);
  if (livePointAXInput) {
    livePointAXInput.value = String(Math.round(Number(box.center_x) - offsetX));
  }
  if (livePointAYInput) {
    livePointAYInput.value = String(Math.round(Number(box.center_y) - offsetY));
  }
  if (livePointBXInput) {
    livePointBXInput.value = String(Math.round(Number(box.center_x) + offsetX));
  }
  if (livePointBYInput) {
    livePointBYInput.value = String(Math.round(Number(box.center_y) + offsetY));
  }
}

function ensureMetricBoxWithinAnalysisRoi() {
  const roi = getCurrentAnalysisRoi();
  if (roi.width <= 0 || roi.height <= 0) {
    return;
  }
  const box = getCurrentMetricBox();
  const clampedWidth = clamp(box.width || Math.round(roi.width * 0.8), 1, roi.width);
  const clampedHeight = clamp(box.height || Math.round(roi.height * 0.35), 1, roi.height);
  const centerX = clamp(box.center_x || Math.round(roi.x + roi.width / 2), roi.x + clampedWidth / 2, roi.x + roi.width - clampedWidth / 2);
  const centerY = clamp(box.center_y || Math.round(roi.y + roi.height / 2), roi.y + clampedHeight / 2, roi.y + roi.height - clampedHeight / 2);
  if (liveMetricBoxCenterXInput) {
    liveMetricBoxCenterXInput.value = String(Math.round(centerX));
  }
  if (liveMetricBoxCenterYInput) {
    liveMetricBoxCenterYInput.value = String(Math.round(centerY));
  }
  if (liveMetricBoxWidthInput) {
    liveMetricBoxWidthInput.value = String(Math.round(clampedWidth));
  }
  if (liveMetricBoxHeightInput) {
    liveMetricBoxHeightInput.value = String(Math.round(clampedHeight));
  }
  const nextBox = getCurrentMetricBox();
  const pointA = getCurrentPointA();
  const pointB = getCurrentPointB();
  if (!pointInRotatedMetricBox(nextBox, pointA.x, pointA.y) || !pointInRotatedMetricBox(nextBox, pointB.x, pointB.y)) {
    seedPointsForMetricBox(nextBox);
  }
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

function renderLivePreviewOverlay() {
  if (!livePreviewOverlayNode || !liveRunState.previewSize) {
    return;
  }
  const { width, height } = liveRunState.previewSize;
  livePreviewOverlayNode.setAttribute("viewBox", `0 0 ${width} ${height}`);
  showLivePreviewStage();

  const roi = getCurrentAnalysisRoi();
  const box = getCurrentMetricBox();
  const pointA = getCurrentPointA();
  const pointB = getCurrentPointB();
  const boxPoints = metricBoxCorners(box)
    .map((point) => `${point.x},${point.y}`)
    .join(" ");
  const angleRad = (Number(box.angle_deg) * Math.PI) / 180;
  const centerlineX = Math.cos(angleRad) * (Number(box.width) / 2);
  const centerlineY = Math.sin(angleRad) * (Number(box.width) / 2);

  livePreviewOverlayNode.innerHTML = `
    <rect class="live-overlay-roi" x="${roi.x}" y="${roi.y}" width="${roi.width}" height="${roi.height}"></rect>
    <polygon class="live-overlay-window" points="${boxPoints}"></polygon>
    <line
      class="live-overlay-centerline"
      x1="${Number(box.center_x) - centerlineX}"
      y1="${Number(box.center_y) - centerlineY}"
      x2="${Number(box.center_x) + centerlineX}"
      y2="${Number(box.center_y) + centerlineY}"
    ></line>
    <circle class="live-overlay-point" cx="${pointA.x}" cy="${pointA.y}" r="6"></circle>
    <text class="live-overlay-point-label" x="${pointA.x + 10}" y="${pointA.y - 10}">A</text>
    <circle class="live-overlay-point" cx="${pointB.x}" cy="${pointB.y}" r="6"></circle>
    <text class="live-overlay-point-label" x="${pointB.x + 10}" y="${pointB.y - 10}">B</text>
  `;
}

function setActiveLiveTool(tool) {
  liveRunState.activeTool = tool;
  updateLiveRunControls();
  const labels = {
    "draw-roi": "Drag on the preview to draw the analysis ROI.",
    "draw-box": "Drag on the preview to draw the observation window.",
    "rotate-box": "Drag around the observation window center to rotate it.",
    "pick-a": "Click on the preview to place Point A.",
    "pick-b": "Click on the preview to place Point B.",
  };
  setLivePointPickerStatus(labels[tool] || "Tool idle.");
}

function updateLiveRunControls() {
  const hasRun = Boolean(liveRunState.runId);
  const hasPreview = Boolean(liveRunState.previewSize);
  const previewState = getPreviewStatePayload();
  const status = liveRunState.detail ? liveRunState.detail.status : "";
  const isRunReady = status === "run_ready";
  const isRunActive = ["running", "invalidated", "stopping"].includes(status);
  const canEditOverlay = hasPreview && !previewState.stream_active && !isRunActive;

  if (createLiveRunButton) {
    createLiveRunButton.disabled = isRunActive;
  }
  if (fetchLivePreviewButton) {
    fetchLivePreviewButton.disabled = !hasRun || isRunActive;
  }
  if (startLivePreviewStreamButton) {
    startLivePreviewStreamButton.disabled = !hasRun || previewState.stream_active || isRunActive;
  }
  if (stopLivePreviewStreamButton) {
    stopLivePreviewStreamButton.disabled = !previewState.stream_active;
  }
  if (autoDetectDefinitionButton) {
    autoDetectDefinitionButton.disabled = !(hasRun && hasPreview) || isRunActive || previewState.stream_active;
  }
  if (saveLiveDefinitionButton) {
    saveLiveDefinitionButton.disabled = !hasRun || isRunActive || !hasPreview;
  }
  if (drawAnalysisRoiButton) {
    drawAnalysisRoiButton.disabled = !canEditOverlay;
    drawAnalysisRoiButton.classList.add("live-tool-button");
  }
  if (drawObservationWindowButton) {
    drawObservationWindowButton.disabled = !canEditOverlay;
    drawObservationWindowButton.classList.add("live-tool-button");
  }
  if (rotateObservationWindowButton) {
    rotateObservationWindowButton.disabled = !canEditOverlay;
    rotateObservationWindowButton.classList.add("live-tool-button");
  }
  if (pickPointAButton) {
    pickPointAButton.disabled = !canEditOverlay;
  }
  if (pickPointBButton) {
    pickPointBButton.disabled = !canEditOverlay;
  }
  if (startLiveRunButton) {
    startLiveRunButton.disabled = !isRunReady || isRunActive || liveRunState.definitionDirty;
  }
  if (stopLiveRunButton) {
    stopLiveRunButton.disabled = !isRunActive;
  }
  updateLiveToolButtons();
}

function fillLiveDefinitionInputs(definition) {
  if (!definition) {
    return;
  }
  if (liveAnalysisRoiXInput) {
    liveAnalysisRoiXInput.value = String(definition.analysis_roi.x);
  }
  if (liveAnalysisRoiYInput) {
    liveAnalysisRoiYInput.value = String(definition.analysis_roi.y);
  }
  if (liveAnalysisRoiWidthInput) {
    liveAnalysisRoiWidthInput.value = String(definition.analysis_roi.width);
  }
  if (liveAnalysisRoiHeightInput) {
    liveAnalysisRoiHeightInput.value = String(definition.analysis_roi.height);
  }
  if (liveMetricBoxCenterXInput) {
    liveMetricBoxCenterXInput.value = String(definition.metric_box.center_x);
  }
  if (liveMetricBoxCenterYInput) {
    liveMetricBoxCenterYInput.value = String(definition.metric_box.center_y);
  }
  if (liveMetricBoxWidthInput) {
    liveMetricBoxWidthInput.value = String(definition.metric_box.width);
  }
  if (liveMetricBoxHeightInput) {
    liveMetricBoxHeightInput.value = String(definition.metric_box.height);
  }
  if (liveMetricBoxAngleInput) {
    liveMetricBoxAngleInput.value = String(definition.metric_box.angle_deg);
  }
  if (livePointAXInput) {
    livePointAXInput.value = String(definition.point_a_px.x);
  }
  if (livePointAYInput) {
    livePointAYInput.value = String(definition.point_a_px.y);
  }
  if (livePointBXInput) {
    livePointBXInput.value = String(definition.point_b_px.x);
  }
  if (livePointBYInput) {
    livePointBYInput.value = String(definition.point_b_px.y);
  }
  if (liveForegroundPolaritySelect) {
    liveForegroundPolaritySelect.value = definition.foreground_polarity;
  }
  if (liveThresholdModeSelect) {
    liveThresholdModeSelect.value = definition.threshold_mode;
  }
  if (liveIgnoreInternalTextureInput) {
    liveIgnoreInternalTextureInput.checked = Boolean(definition.ignore_internal_texture);
  }
  if (liveMinTargetAreaInput) {
    liveMinTargetAreaInput.value = String(definition.min_target_area_px);
  }
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
}

function seedLiveDefinitionDefaults(width, height) {
  setInputIfBlank(liveAnalysisRoiXInput, 0);
  setInputIfBlank(liveAnalysisRoiYInput, 0);
  setInputIfBlank(liveAnalysisRoiWidthInput, width);
  setInputIfBlank(liveAnalysisRoiHeightInput, height);
  setInputIfBlank(liveMetricBoxCenterXInput, Math.round(width / 2));
  setInputIfBlank(liveMetricBoxCenterYInput, Math.round(height / 2));
  setInputIfBlank(liveMetricBoxWidthInput, Math.max(8, Math.round(width * 0.8)));
  setInputIfBlank(liveMetricBoxHeightInput, Math.max(8, Math.round(height * 0.35)));
  setInputIfBlank(liveMetricBoxAngleInput, 0);
  setInputIfBlank(livePointAXInput, Math.round(width * 0.2));
  setInputIfBlank(livePointAYInput, Math.round(height / 2));
  setInputIfBlank(livePointBXInput, Math.round(width * 0.8));
  setInputIfBlank(livePointBYInput, Math.round(height / 2));
  ensureMetricBoxWithinAnalysisRoi();
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
}

function resetLiveDefinitionInputs() {
  for (const node of [
    liveAnalysisRoiXInput,
    liveAnalysisRoiYInput,
    liveAnalysisRoiWidthInput,
    liveAnalysisRoiHeightInput,
    liveMetricBoxCenterXInput,
    liveMetricBoxCenterYInput,
    liveMetricBoxWidthInput,
    liveMetricBoxHeightInput,
    liveMetricBoxAngleInput,
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
  liveRunState.activeTool = "";
  liveRunState.overlayDrag = null;
  renderLivePreviewOverlay();
}

function renderLiveRunDetail(payload) {
  if (!hasLiveSetupUi() || !payload) {
    return;
  }
  const serverPreview = payload.preview || {};
  liveRunState.detail = payload;
  liveRunState.runId = payload.run_id || "";
  liveRunState.previewStreamActive = Boolean(
    serverPreview.stream_active || (liveRunState.previewStreamActive && liveRunState.previewStreamUrl),
  );
  liveRunState.previewFrozenAvailable = Boolean(
    !liveRunState.previewStreamActive && (serverPreview.frozen_frame_available || liveRunState.previewFrozenAvailable),
  );
  liveRunState.lastPreviewFrameId =
    liveRunState.lastPreviewFrameId != null ? liveRunState.lastPreviewFrameId : (serverPreview.last_frame_id ?? null);
  liveRunIdNode.textContent = liveRunState.runId || "Not created";
  liveRunStatusNode.textContent = payload.status || "unknown";
  liveRunPresetNode.textContent = payload.preset || (liveRunPresetSelect ? liveRunPresetSelect.value : "balloon");
  if (livePreviewRateNode) {
    livePreviewRateNode.textContent = formatRateValue(payload.rates?.preview_display_fps, "fps");
  }
  if (liveMeasurementRateNode) {
    liveMeasurementRateNode.textContent = formatRateValue(payload.rates?.measurement_sample_hz, "Hz");
  }
  if (payload.definition) {
    fillLiveDefinitionInputs(payload.definition);
  } else {
    syncLiveDefinitionDirtyState();
  }
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

function buildLiveDefinitionBasePayload() {
  return {
    analysis_roi: {
      x: getNumericInputValue(liveAnalysisRoiXInput),
      y: getNumericInputValue(liveAnalysisRoiYInput),
      width: getNumericInputValue(liveAnalysisRoiWidthInput),
      height: getNumericInputValue(liveAnalysisRoiHeightInput),
    },
    metric_box: {
      center_x: getNumericInputValue(liveMetricBoxCenterXInput),
      center_y: getNumericInputValue(liveMetricBoxCenterYInput),
      width: getNumericInputValue(liveMetricBoxWidthInput),
      height: getNumericInputValue(liveMetricBoxHeightInput),
      angle_deg: getNumericInputValue(liveMetricBoxAngleInput, 0),
    },
    foreground_polarity: liveForegroundPolaritySelect ? liveForegroundPolaritySelect.value : "dark_on_light",
    threshold_mode: liveThresholdModeSelect ? liveThresholdModeSelect.value : "adaptive",
    ignore_internal_texture: liveIgnoreInternalTextureInput ? liveIgnoreInternalTextureInput.checked : false,
    min_target_area_px: getNumericInputValue(liveMinTargetAreaInput, 200),
  };
}

function buildLiveDefinitionPayload() {
  return {
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
}

async function createLiveRun() {
  if (!createLiveRunButton) {
    return;
  }
  createLiveRunButton.disabled = true;
  setLiveRunMessage("Creating live run draft...", "info");
  try {
    await stopLivePreviewStream({ clearImage: true, silent: true });
    resetLiveDefinitionInputs();
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
    if (liveRunPresetSelect) {
      liveRunPresetNode.textContent = liveRunPresetSelect.value;
    }
    setLiveRunMessage("Live run draft created. Fetch a preview frame to continue.", "success");
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    createLiveRunButton.disabled = false;
    updateLiveRunControls();
  }
}

async function fetchLivePreview() {
  if (!liveRunState.runId || !fetchLivePreviewButton) {
    return;
  }
  fetchLivePreviewButton.disabled = true;
  setLiveRunMessage("Fetching preview frame...", "info");
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    await loadFrozenPreviewFrame({ runId: liveRunState.runId, cached: false });
    setLivePointPickerStatus("Preview loaded. Use image click or auto detect to set points.");
    setLiveRunMessage("Preview frame loaded.", "success");
  } catch (error) {
    liveRunState.previewSize = null;
    setLiveRunMessage(String(error), "error");
  } finally {
    fetchLivePreviewButton.disabled = false;
    updateLiveRunControls();
  }
}

async function startLivePreviewStream() {
  if (!liveRunState.runId || !startLivePreviewStreamButton || !livePreviewImageNode) {
    return;
  }
  startLivePreviewStreamButton.disabled = true;
  setLiveRunMessage("Starting live preview stream...", "info");
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    revokeLivePreviewUrl();
    liveRunState.previewStreamUrl = `/api/runs/${liveRunState.runId}/preview/stream?ts=${Date.now()}`;
    liveRunState.previewStreamActive = true;
    liveRunState.previewFrozenAvailable = false;
    showLivePreviewStage();
    livePreviewImageNode.src = liveRunState.previewStreamUrl;
    updateLiveRunControls();
    setActiveLiveTool("");
    setLivePointPickerStatus("Live preview streaming in motion-first mode. Stop the stream to freeze an editable still frame.");
    setLiveRunMessage("Live preview stream started. This stream is optimized for motion; stop it to refresh an editable still frame.", "success");
    try {
      await refreshLiveRunDetail(liveRunState.runId);
    } catch (error) {
      setLiveRunMessage(String(error), "error");
    }
  } finally {
    startLivePreviewStreamButton.disabled = false;
    updateLiveRunControls();
  }
}

async function stopLivePreviewStream({ clearImage = false, silent = false } = {}) {
  const hadActiveStream = liveRunState.previewStreamActive;
  const streamRunId = liveRunState.runId;
  const hydrateFrozenFrame = hadActiveStream && !clearImage && !silent;
  liveRunState.previewStreamActive = false;
  liveRunState.previewStreamUrl = "";
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
    setLivePointPickerStatus("Live preview stopped. A full-quality frozen frame is now available for editing.");
    if (!hydrateFrozenFrame) {
      setLiveRunMessage("Live preview frozen on the last frame.", "info");
    } else {
      setLiveRunMessage("Live preview stopped. Refreshed the frozen still frame for editing.", "info");
    }
  }
  updateLiveRunControls();
}

async function loadFrozenPreviewFrame({ runId, cached = false }) {
  const query = cached ? "?cached=1" : "";
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
  const blob = await response.blob();
  revokeLivePreviewUrl();
  liveRunState.previewObjectUrl = URL.createObjectURL(blob);
  liveRunState.previewSize = width > 0 && height > 0 ? { width, height } : null;
  if (livePreviewImageNode) {
    livePreviewImageNode.src = liveRunState.previewObjectUrl;
    showLivePreviewStage();
  }
  if (liveRunState.previewSize) {
    seedLiveDefinitionDefaults(liveRunState.previewSize.width, liveRunState.previewSize.height);
  }
  await refreshLiveRunDetail(runId);
}

async function autoDetectLiveDefinition() {
  if (!liveRunState.runId || !autoDetectDefinitionButton) {
    return;
  }
  autoDetectDefinitionButton.disabled = true;
  setLiveRunMessage("Auto-detecting locked points from the preview frame...", "info");
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/definition/auto`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildLiveDefinitionBasePayload()),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Auto detect failed: ${response.status}`));
    }
    fillLiveDefinitionInputs(payload.definition);
    liveRunState.definitionDirty = true;
    renderLivePreviewOverlay();
    setLivePointPickerStatus("Auto-detect complete. Overlay updated. Adjust ROI, window, or points manually if needed.");
    setLiveRunMessage(
      payload.detail || `Auto-detect complete. quality=${payload.quality.toFixed(2)} distance=${payload.metric_raw?.toFixed(2) ?? "n/a"}`,
      payload.detail ? "info" : "success",
    );
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    autoDetectDefinitionButton.disabled = false;
    updateLiveRunControls();
  }
}

async function saveLiveDefinition() {
  if (!liveRunState.runId || !saveLiveDefinitionButton) {
    return;
  }
  saveLiveDefinitionButton.disabled = true;
  setLiveRunMessage("Saving live definition...", "info");
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/definition`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildLiveDefinitionPayload()),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Definition save failed: ${response.status}`));
    }
    renderLiveRunDetail(payload);
    liveRunState.definitionDirty = false;
    setLiveRunMessage(
      payload.status === "run_ready"
        ? "Definition saved. Live run is ready for the Phase 3 start flow."
        : "Definition saved.",
      "success",
    );
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    saveLiveDefinitionButton.disabled = false;
    updateLiveRunControls();
  }
}

function setActivePointTarget(target) {
  if (target === "a") {
    setActiveLiveTool("pick-a");
  } else if (target === "b") {
    setActiveLiveTool("pick-b");
  } else {
    setActiveLiveTool("");
  }
}

function updateLiveDefinitionAfterLocalEdit() {
  ensureMetricBoxWithinAnalysisRoi();
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  updateLiveRunControls();
}

function setPointValue(target, x, y) {
  if (target === "a") {
    if (livePointAXInput) {
      livePointAXInput.value = String(x);
    }
    if (livePointAYInput) {
      livePointAYInput.value = String(y);
    }
    setLiveRunMessage(`Point A placed at (${x}, ${y}).`, "info");
  }
  if (target === "b") {
    if (livePointBXInput) {
      livePointBXInput.value = String(x);
    }
    if (livePointBYInput) {
      livePointBYInput.value = String(y);
    }
    setLiveRunMessage(`Point B placed at (${x}, ${y}).`, "info");
  }
  updateLiveDefinitionAfterLocalEdit();
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

function handleLivePreviewPointerDown(event) {
  if (!liveRunState.previewSize || !liveRunState.activeTool || !livePreviewOverlayNode) {
    return;
  }
  const point = getOverlayCoordinates(event);
  if (!point) {
    return;
  }
  if (liveRunState.activeTool === "pick-a") {
    setPointValue("a", point.x, point.y);
    setActiveLiveTool("");
    return;
  }
  if (liveRunState.activeTool === "pick-b") {
    setPointValue("b", point.x, point.y);
    setActiveLiveTool("");
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
    const width = Math.max(1, Math.abs(point.x - drag.startX));
    const height = Math.max(1, Math.abs(point.y - drag.startY));
    if (liveAnalysisRoiXInput) {
      liveAnalysisRoiXInput.value = String(x);
    }
    if (liveAnalysisRoiYInput) {
      liveAnalysisRoiYInput.value = String(y);
    }
    if (liveAnalysisRoiWidthInput) {
      liveAnalysisRoiWidthInput.value = String(width);
    }
    if (liveAnalysisRoiHeightInput) {
      liveAnalysisRoiHeightInput.value = String(height);
    }
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "draw-box") {
    const x = Math.min(drag.startX, point.x);
    const y = Math.min(drag.startY, point.y);
    const width = Math.max(1, Math.abs(point.x - drag.startX));
    const height = Math.max(1, Math.abs(point.y - drag.startY));
    if (liveMetricBoxCenterXInput) {
      liveMetricBoxCenterXInput.value = String(Math.round(x + width / 2));
    }
    if (liveMetricBoxCenterYInput) {
      liveMetricBoxCenterYInput.value = String(Math.round(y + height / 2));
    }
    if (liveMetricBoxWidthInput) {
      liveMetricBoxWidthInput.value = String(width);
    }
    if (liveMetricBoxHeightInput) {
      liveMetricBoxHeightInput.value = String(height);
    }
    if (liveMetricBoxAngleInput) {
      liveMetricBoxAngleInput.value = "0";
    }
    seedPointsForMetricBox(getCurrentMetricBox());
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "rotate-box") {
    const box = getCurrentMetricBox();
    const angleDeg = (Math.atan2(point.y - box.center_y, point.x - box.center_x) * 180) / Math.PI;
    if (liveMetricBoxAngleInput) {
      liveMetricBoxAngleInput.value = angleDeg.toFixed(1);
    }
    ensureMetricBoxWithinAnalysisRoi();
    updateLiveDefinitionAfterLocalEdit();
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
    setLiveRunMessage("Analysis ROI updated from the preview overlay.", "info");
  } else if (completedTool === "draw-box") {
    setLiveRunMessage("Observation window updated from the preview overlay.", "info");
  } else if (completedTool === "rotate-box") {
    setLiveRunMessage("Observation window angle updated from the preview overlay.", "info");
  }
  setActiveLiveTool("");
}

async function startLiveRun() {
  if (!liveRunState.runId || !startLiveRunButton) {
    return;
  }
  startLiveRunButton.disabled = true;
  setLiveRunMessage("Starting live run...", "info");
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    const response = await fetch(`/api/runs/${liveRunState.runId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_temperature_celsius: getNumericInputValue(liveTargetTemperatureInput, 75),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Live run start failed: ${response.status}`));
    }
    await refreshLiveRunDetail(liveRunState.runId);
    const terminalDetail = await waitForLiveRunTerminalDetail(liveRunState.runId);
    const [telemetryResponse, resultResponse] = await Promise.all([
      fetch(`/api/runs/${liveRunState.runId}/telemetry`),
      fetch(`/api/runs/${liveRunState.runId}/result`),
    ]);
    const telemetryPayload = telemetryResponse.ok ? await telemetryResponse.json() : null;
    const resultPayload = resultResponse.ok ? await resultResponse.json() : null;
    await loadRecentSessions();
    if (terminalDetail.status === "completed") {
      setLiveRunMessage(
        `Live run completed. session=${payload.session_id} point_count=${resultPayload?.point_count ?? "n/a"} samples=${
          telemetryPayload?.curve?.length ?? "n/a"
        } af95=${resultPayload?.af95 ?? "n/a"}`,
        "success",
      );
    } else if (terminalDetail.status === "aborted") {
      setLiveRunMessage(
        `Live run stopped. session=${payload.session_id} samples=${telemetryPayload?.curve?.length ?? "n/a"}.`,
        "warning",
      );
    } else {
      setLiveRunMessage(`Live run ended with status=${terminalDetail.status}.`, "error");
    }
  } catch (error) {
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
  setLiveRunMessage("Stopping live run...", "info");
  try {
    const response = await fetch(`/api/runs/${liveRunState.runId}/stop`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Live run stop failed: ${response.status}`));
    }
    renderLiveRunDetail(payload);
    const terminalDetail = await waitForLiveRunTerminalDetail(liveRunState.runId);
    const telemetryResponse = await fetch(`/api/runs/${liveRunState.runId}/telemetry`);
    const telemetryPayload = telemetryResponse.ok ? await telemetryResponse.json() : null;
    await loadRecentSessions();
    setLiveRunMessage(
      `Live run ${terminalDetail.status}. samples=${telemetryPayload?.curve?.length ?? "n/a"}.`,
      terminalDetail.status === "aborted" ? "warning" : "info",
    );
  } catch (error) {
    setLiveRunMessage(String(error), "error");
  } finally {
    updateLiveRunControls();
  }
}

async function loadHealth() {
  const response = await fetch("/health");
  const payload = await response.json();
  healthStatusNode.textContent = payload.status;
}

async function loadProfile() {
  const response = await fetch("/api/system/profile");
  const payload = await response.json();
  profileNameNode.textContent = payload.profile;
  profileModeNode.textContent = payload.mode;
  syncCameraProbeDefaults(payload.profile);
}

function renderStatusPill(status) {
  return `<span class="status-pill status-${status}">${status}</span>`;
}

function renderPrecheck(payload) {
  if (!precheckStatusNode || !precheckItemsNode) {
    return;
  }
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
  probeCameraButton.textContent = "Probing...";
  try {
    const requestPayload = buildCameraProbeRequest();
    const response = await fetch("/api/system/camera/probe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestPayload ? JSON.stringify(requestPayload) : null,
    });
    const payload = await response.json();
    renderCameraProbeResult(payload);
  } catch (error) {
    renderCameraProbeResult({ status: "fail", detail: String(error) });
  } finally {
    probeCameraButton.disabled = false;
    probeCameraButton.textContent = "Probe Camera";
  }
}

function renderRecentSessions(items) {
  if (!recentSessionsNode) {
    return;
  }
  if (!items.length) {
    recentSessionsNode.innerHTML =
      '<li class="session-item session-item--empty">No sessions have been recorded yet.</li>';
    return;
  }

  recentSessionsNode.innerHTML = items
    .map(
      (item) => `
        <li class="session-item">
          <strong>${item.session_id}</strong>
          <div class="session-meta">
            state=${item.state} | point_count=${item.point_count} | af95=${
              item.af95 === null ? "n/a" : item.af95
            }
          </div>
          <a class="workspace-link" href="${workspaceUrl(item.session_id)}">Open Workspace</a>
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
    return;
  }

  const width = 320;
  const height = 180;
  const padding = 16;
  const xs = points.map((_, index) => index);
  const ys = points.map((point) => (point.metric_norm === null ? 0 : point.metric_norm));
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const ySpan = Math.max(maxY - minY, 1);

  const polylinePoints = points
    .map((point, index) => {
      const x = padding + (index / maxX) * (width - padding * 2);
      const normalizedY = point.metric_norm === null ? 0 : (point.metric_norm - minY) / ySpan;
      const y = height - padding - normalizedY * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");

  detailCurveNode.setAttribute("points", polylinePoints);
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
    workspaceSessionStateNode.textContent = summary.state;
    workspaceSessionStateNode.className = `status-pill status-${summary.state === "completed" ? "ok" : "warn"}`;
  }
  if (workspaceSideStateNode) {
    workspaceSideStateNode.textContent = summary.state;
  }
  if (workspacePointCountNode) {
    workspacePointCountNode.textContent = String(summary.point_count);
  }
  if (workspaceAf95Node) {
    workspaceAf95Node.textContent = summary.af95 === null ? "N/A" : `${summary.af95} °C`;
  }
  const summaryCopyNode = document.getElementById("workspace-summary-copy");
  if (summaryCopyNode) {
    summaryCopyNode.textContent =
      `Session ${summary.session_id} is currently recorded as ${summary.state} with ${summary.point_count} points.`;
  }
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
    setAdjustmentStatusMessage("Adjustment state is unavailable.", "error");
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
      ? "Latest result reflects the newest applied adjustment version."
      : "Latest result currently matches the automatic result.";
  }
  if (adjustmentHasDraftNode) {
    adjustmentHasDraftNode.textContent = draft ? "Yes" : "No";
  }
  if (adjustmentAppliedCountNode) {
    adjustmentAppliedCountNode.textContent = String(appliedVersions.length);
  }
  if (adjustmentIsManualNode) {
    adjustmentIsManualNode.textContent = hasManualOverride ? "Yes" : "No";
  }
  if (adjustmentDraftUpdatedNode) {
    adjustmentDraftUpdatedNode.textContent = draft ? formatValue(draft.updated_at_ms) : "N/A";
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
        '<p class="session-item--empty">No applied adjustment versions yet.</p>';
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
    setAdjustmentStatusMessage(`Draft ready: ${draft.reason}`, "info");
  } else if (hasManualOverride) {
    setAdjustmentStatusMessage(`Applied ${appliedVersions.length} adjustment version(s).`, "success");
  } else {
    setAdjustmentStatusMessage("No draft loaded.", "neutral");
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
        ? "Automatic basis is available, but no point or key frame is currently selected."
        : "Automatic analysis basis will appear here when detail data is available.";
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
    `${selection.label || "point"} @ ${formatValue(selection.timestamp_ms)} ms, metric_raw=${formatValue(selection.metric_raw)}`;
  workspaceAdjustmentBasisCopyNode.textContent =
    `Automatic basis is using ${formatValue(detail.source)} detail with ${String((detail.points || []).length)} points and the current selection context.`;
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
    workspaceActivePointNode.textContent = "No point selected.";
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
    `Selected ${selection.label || "point"} at ${selection.timestamp_ms} ms, metric_raw=${selection.metric_raw ?? "N/A"}.`;
  updateWorkspaceAdjustmentPreview(selection);
}

function mapWorkspaceStages(summary, detail) {
  const hasSummary = Boolean(summary);
  const hasDetail = Boolean(detail && (detail.points || []).length);
  const hasKeyframes = Boolean(detail && (detail.key_frames || []).length);
  const isFailed = summary && summary.state === "failed";
  const source = detail && detail.source ? detail.source : "mock";

  const statuses = WORKSPACE_STEPS.map((name) => ({ name, status: "todo" }));
  if (!hasSummary) {
    return {
      currentStage: "准备",
      statuses,
      mode: source,
      description: "No session summary available yet.",
    };
  }

  statuses[0].status = "done";
  statuses[1].status = "done";
  statuses[2].status = hasDetail ? "done" : "done";
  statuses[3].status = isFailed ? "error" : "active";
  statuses[4].status = "upcoming";
  statuses[5].status = summary.state === "completed" ? "done" : isFailed ? "todo" : "done";

  return {
    currentStage: isFailed ? "计算" : "计算",
    statuses,
    mode: source,
    description: hasDetail
      ? `${source} detail is loaded; the workspace is focused on processing and calculation review.`
      : `${source} detail is not available; summary-only workspace view is active.`,
  };
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
      statusNode.textContent = stage.status;
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
    workspaceCurvePointsNode.innerHTML = "";
    workspaceAf95LineNode.setAttribute("x1", "0");
    workspaceAf95LineNode.setAttribute("x2", "0");
    workspaceAf95LineNode.setAttribute("y1", "0");
    workspaceAf95LineNode.setAttribute("y2", "0");
    workspaceCurveEmptyNode.textContent = "No replay detail available.";
    workspaceCurveEmptyNode.hidden = false;
    return;
  }

  const width = 640;
  const height = 260;
  const padding = 28;
  const xValues = points.map((point) => point.celsius);
  const yValues = points.map((point) => point.metric_raw);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const xSpan = Math.max(maxX - minX, 1);
  const ySpan = Math.max(maxY - minY, 1);

  const scaledPoints = points.map((point, index) => {
    const x = padding + ((point.celsius - minX) / xSpan) * (width - padding * 2);
    const y = height - padding - ((point.metric_raw - minY) / ySpan) * (height - padding * 2);
    return { ...point, x, y, index };
  });

  workspaceCurveNode.setAttribute(
    "points",
    scaledPoints.map((point) => `${point.x},${point.y}`).join(" "),
  );
  workspaceCurvePointsNode.innerHTML = scaledPoints
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
    const af95X = padding + ((detail.af95 - minX) / xSpan) * (width - padding * 2);
    workspaceAf95LineNode.setAttribute("x1", String(af95X));
    workspaceAf95LineNode.setAttribute("x2", String(af95X));
    workspaceAf95LineNode.setAttribute("y1", String(padding));
    workspaceAf95LineNode.setAttribute("y2", String(height - padding));
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
    workspaceKeyframesNode.innerHTML = '<p class="session-item--empty">No replay detail available.</p>';
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
    workspaceSourceNode.textContent = detail.source || "n/a";
  }
  if (workspaceDetailPointCountNode) {
    workspaceDetailPointCountNode.textContent = String((detail.points || []).length);
  }
  if (workspaceKeyframeCountNode) {
    workspaceKeyframeCountNode.textContent = String((detail.key_frames || []).length);
  }
  if (workspaceDetailStatusNode) {
    workspaceDetailStatusNode.textContent = (detail.points || []).length ? "available" : "missing";
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

async function runSession(endpoint, button, idleLabel) {
  button.disabled = true;
  button.textContent = "Running...";
  try {
    const runResponse = await fetch(endpoint, { method: "POST" });
    const runPayload = await runResponse.json();
    renderSessionResult(runPayload);

    if (runPayload.session_id) {
      const summaryResponse = await fetch(`/api/session/${runPayload.session_id}`);
      const summaryPayload = await summaryResponse.json();
      renderSessionResult(summaryPayload);
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
  await runSession("/api/session/run-mock", runMockButton, "Run Mock Session");
}

async function runReplaySession() {
  runReplayButton.disabled = true;
  runReplayButton.textContent = "Running...";
  try {
    const runResponse = await fetch("/api/session/run-replay", { method: "POST" });
    const runPayload = await runResponse.json();
    renderSessionResult(runPayload);
    if (runPayload.session_id) {
      const summaryResponse = await fetch(`/api/session/${runPayload.session_id}`);
      const summaryPayload = await summaryResponse.json();
      renderSessionResult(summaryPayload);
      await loadSessionDetail(runPayload.session_id);
    }
    await loadRecentSessions();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  } finally {
    runReplayButton.disabled = false;
    runReplayButton.textContent = "Run Replay Session";
  }
}

async function bootstrap() {
  try {
    await Promise.all([loadHealth(), loadProfile(), loadPrecheck(), loadRecentSessions()]);
    if (liveRunPresetNode && liveRunPresetSelect) {
      liveRunPresetNode.textContent = liveRunPresetSelect.value;
    }
    updateLiveRunControls();
  } catch (error) {
    renderSessionResult({ detail: String(error) });
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

  const [summaryResponse, detailResponse, adjustmentResponse] = await Promise.allSettled([
    fetch(`/api/session/${sessionId}`),
    fetch(`/api/session/${sessionId}/detail`),
    fetch(`/api/session/${sessionId}/adjustment`),
  ]);

  if (summaryResponse.status !== "fulfilled" || !summaryResponse.value.ok) {
    return;
  }

  const summary = await summaryResponse.value.json();
  renderWorkspaceSummary(summary);

  if (detailResponse.status === "fulfilled" && detailResponse.value.ok) {
    const detail = await detailResponse.value.json();
    renderWorkspaceDetail(detail);
    renderWorkspaceStages(mapWorkspaceStages(summary, detail), summary.state);
  } else {
    const emptyDetail = {
      source: "n/a",
      af95: summary.af95,
      points: [],
      key_frames: [],
    };
    renderWorkspaceDetail(emptyDetail);
    renderWorkspaceStages(mapWorkspaceStages(summary, null), summary.state);
  }

  if (adjustmentResponse.status === "fulfilled" && adjustmentResponse.value.ok) {
    renderAdjustmentState(await adjustmentResponse.value.json());
  } else {
    renderAdjustmentState(null);
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
if (liveRunPresetSelect && liveRunPresetNode) {
  liveRunPresetSelect.addEventListener("change", () => {
    if (!liveRunState.runId) {
      liveRunPresetNode.textContent = liveRunPresetSelect.value;
    }
  });
}
if (createLiveRunButton) {
  createLiveRunButton.addEventListener("click", createLiveRun);
}
if (fetchLivePreviewButton) {
  fetchLivePreviewButton.addEventListener("click", fetchLivePreview);
}
if (startLivePreviewStreamButton) {
  startLivePreviewStreamButton.addEventListener("click", startLivePreviewStream);
}
if (stopLivePreviewStreamButton) {
  stopLivePreviewStreamButton.addEventListener("click", () => {
    void stopLivePreviewStream();
  });
}
if (autoDetectDefinitionButton) {
  autoDetectDefinitionButton.addEventListener("click", autoDetectLiveDefinition);
}
if (saveLiveDefinitionButton) {
  saveLiveDefinitionButton.addEventListener("click", saveLiveDefinition);
}
if (startLiveRunButton) {
  startLiveRunButton.addEventListener("click", startLiveRun);
}
if (stopLiveRunButton) {
  stopLiveRunButton.addEventListener("click", stopLiveRun);
}
if (pickPointAButton) {
  pickPointAButton.addEventListener("click", () => setActivePointTarget("a"));
}
if (pickPointBButton) {
  pickPointBButton.addEventListener("click", () => setActivePointTarget("b"));
}
if (drawAnalysisRoiButton) {
  drawAnalysisRoiButton.addEventListener("click", () => setActiveLiveTool("draw-roi"));
}
if (drawObservationWindowButton) {
  drawObservationWindowButton.addEventListener("click", () => setActiveLiveTool("draw-box"));
}
if (rotateObservationWindowButton) {
  rotateObservationWindowButton.addEventListener("click", () => setActiveLiveTool("rotate-box"));
}
for (const liveInput of [
  liveAnalysisRoiXInput,
  liveAnalysisRoiYInput,
  liveAnalysisRoiWidthInput,
  liveAnalysisRoiHeightInput,
  liveMetricBoxCenterXInput,
  liveMetricBoxCenterYInput,
  liveMetricBoxWidthInput,
  liveMetricBoxHeightInput,
  liveMetricBoxAngleInput,
  livePointAXInput,
  livePointAYInput,
  livePointBXInput,
  livePointBYInput,
  liveForegroundPolaritySelect,
  liveThresholdModeSelect,
  liveIgnoreInternalTextureInput,
  liveMinTargetAreaInput,
]) {
  if (liveInput) {
    liveInput.addEventListener("input", updateLiveDefinitionAfterLocalEdit);
    liveInput.addEventListener("change", updateLiveDefinitionAfterLocalEdit);
  }
}
if (livePreviewImageNode) {
  livePreviewImageNode.addEventListener("load", () => {
    if (!liveRunState.previewSize && livePreviewImageNode.naturalWidth && livePreviewImageNode.naturalHeight) {
      liveRunState.previewSize = {
        width: livePreviewImageNode.naturalWidth,
        height: livePreviewImageNode.naturalHeight,
      };
      seedLiveDefinitionDefaults(liveRunState.previewSize.width, liveRunState.previewSize.height);
    }
    showLivePreviewStage();
    syncLiveDefinitionDirtyState();
    renderLivePreviewOverlay();
    updateLiveRunControls();
  });
  livePreviewImageNode.addEventListener("error", () => {
    if (!liveRunState.previewStreamActive) {
      return;
    }
    liveRunState.previewStreamActive = false;
    liveRunState.previewStreamUrl = "";
    setLiveRunMessage("Live preview stream failed. The last received frame is still available for editing.", "error");
    refreshLiveRunDetail(liveRunState.runId).catch(() => {});
    updateLiveRunControls();
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
if (adjustmentSaveDraftButton) {
  adjustmentSaveDraftButton.addEventListener("click", saveWorkspaceDraft);
}
if (adjustmentApplyButton) {
  adjustmentApplyButton.addEventListener("click", applyWorkspaceAdjustment);
}
if (document.body.dataset.page === "home") {
  syncCameraProbeControls();
  bootstrap();
}
if (document.body.dataset.page === "workspace") {
  bootstrapWorkspace();
}
