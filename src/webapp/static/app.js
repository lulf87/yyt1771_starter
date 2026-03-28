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
const stopLivePreviewStreamButton = document.getElementById("stop-live-preview-stream-btn");
const saveLiveDefinitionButton = document.getElementById("save-live-definition-btn");
const startLiveRunButton = document.getElementById("start-live-run-btn");
const stopLiveRunButton = document.getElementById("stop-live-run-btn");
const drawAnalysisRoiButton = document.getElementById("draw-analysis-roi-btn");
const livePreviewStageNode = document.getElementById("live-preview-stage");
const livePointPromptNode = document.getElementById("live-point-prompt");
const livePointPromptTitleNode = document.getElementById("live-point-prompt-title");
const livePointPromptBodyNode = document.getElementById("live-point-prompt-body");
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
const liveAnalysisRoiAngleInput = document.getElementById("live-analysis-roi-angle");
const livePointAXInput = document.getElementById("live-point-a-x");
const livePointAYInput = document.getElementById("live-point-a-y");
const livePointBXInput = document.getElementById("live-point-b-x");
const livePointBYInput = document.getElementById("live-point-b-y");
const liveForegroundPolaritySelect = document.getElementById("live-foreground-polarity");
const liveThresholdModeSelect = document.getElementById("live-threshold-mode");
const liveIgnoreInternalTextureInput = document.getElementById("live-ignore-internal-texture");
const liveMinTargetAreaInput = document.getElementById("live-min-target-area");
const liveSensitivityInput = document.getElementById("live-sensitivity");
const liveCurrentTemperatureInput = document.getElementById("live-current-temperature");
const liveTargetTemperatureInput = document.getElementById("live-target-temperature");
const confirmTargetTemperatureButton = document.getElementById("confirm-target-temperature-btn");
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
const workspaceAfasOverviewChartNode = document.getElementById("workspace-afas-overview-chart");
const workspaceAfasOverviewSeriesNode = document.getElementById("workspace-afas-overview-series");
const workspaceAfasOverviewSummaryNode = document.getElementById("workspace-afas-overview-summary");
const workspaceAfasAnalysisChartNode = document.getElementById("workspace-afas-analysis-chart");
const workspaceAfasAnalysisLayersNode = document.getElementById("workspace-afas-analysis-layers");
const workspaceAfasAnalysisEmptyNode = document.getElementById("workspace-afas-analysis-empty");
const workspaceAfasResultStatusNode = document.getElementById("workspace-afas-result-status");
const workspaceAfasResultAsNode = document.getElementById("workspace-afas-result-as");
const workspaceAfasResultAfTanNode = document.getElementById("workspace-afas-result-af-tan");
const workspaceAfasResultMaxSlopeNode = document.getElementById("workspace-afas-result-max-slope");
const workspaceAfasOutlierCountNode = document.getElementById("workspace-afas-outlier-count");
const workspaceAfasSmoothedCountNode = document.getElementById("workspace-afas-smoothed-count");
const workspaceAfasWarningListNode = document.getElementById("workspace-afas-warning-list");
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
let workspaceAfasState = null;
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
  previewSourceSize: null,
  roiConfirmed: false,
  confirmedRoiSignature: "",
  activeTool: "",
  overlayDrag: null,
  definitionDirty: false,
  setupRecomputeTimer: null,
  setupRecomputeInFlight: false,
  setupRecomputeDetail: "",
  setupRecomputeActiveToken: 0,
  targetTemperatureConfirmed: null,
  currentTemperatureCelsius: null,
  currentTemperatureTimer: null,
  liveTrackingTimer: null,
};
const LIVE_SETUP_RUN_STORAGE_KEY = "yyt1771-live-setup-run-id";

const ANALYSIS_ROI_FLOAT_EPSILON = 0.5;

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

function normalizeTemperatureValue(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.round(numeric * 10) / 10 : null;
}

function getCurrentTargetTemperature() {
  return normalizeTemperatureValue(getNumericInputValue(liveTargetTemperatureInput, 75));
}

function isTargetTemperatureConfirmed() {
  const confirmed = normalizeTemperatureValue(liveRunState.targetTemperatureConfirmed);
  const current = getCurrentTargetTemperature();
  return confirmed !== null && current !== null && Math.abs(confirmed - current) < 0.05;
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

function renderCurrentTemperature(payload) {
  if (!liveCurrentTemperatureInput) {
    return;
  }
  const celsius = normalizeTemperatureValue(payload?.temperature_celsius);
  liveRunState.currentTemperatureCelsius = celsius;
  liveCurrentTemperatureInput.value = celsius === null ? "--" : celsius.toFixed(1);
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

function clearTargetTemperatureConfirmation() {
  liveRunState.targetTemperatureConfirmed = null;
  updateLiveRunControls();
}

async function confirmTargetTemperature() {
  const current = getCurrentTargetTemperature();
  if (current === null || current <= 0) {
    setLiveRunMessage("Target temperature must be a positive number before confirmation.", "error");
    return;
  }
  if (confirmTargetTemperatureButton) {
    confirmTargetTemperatureButton.disabled = true;
  }
  stopCurrentTemperaturePolling();
  setLiveRunMessage("Confirming target temperature on the controller...", "info");
  try {
    const response = await fetch("/api/system/temp/target", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_temperature_celsius: current }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(parseErrorDetail(payload, `Target temperature update failed: ${response.status}`));
    }
    const confirmed = normalizeTemperatureValue(payload?.confirmed_target_temperature_celsius);
    liveRunState.targetTemperatureConfirmed = confirmed ?? current;
    if (liveTargetTemperatureInput && confirmed !== null) {
      liveTargetTemperatureInput.value = confirmed.toFixed(1);
    }
    updateLiveRunControls();
    setLiveRunMessage(
      `Target temperature confirmed on controller at ${(confirmed ?? current).toFixed(1)} °C.`,
      "success",
    );
  } catch (error) {
    clearTargetTemperatureConfirmation();
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
  renderLiveToolPrompt();
}

function updateLiveToolButtons() {
  for (const [button, tool] of [
    [drawAnalysisRoiButton, "draw-roi"],
    [pickPointAButton, "pick-a"],
    [pickPointBButton, "pick-b"],
  ]) {
    if (!button) {
      continue;
    }
    button.classList.toggle("button-active", liveRunState.activeTool === tool);
  }
}

function renderLiveToolPrompt() {
  if (!livePointPromptNode || !livePointPromptTitleNode || !livePointPromptBodyNode) {
    return;
  }
  if (liveRunState.setupRecomputeInFlight) {
    livePointPromptNode.hidden = false;
    livePointPromptTitleNode.textContent = "Recomputing Locked Points";
    livePointPromptBodyNode.textContent =
      liveRunState.setupRecomputeDetail ||
      "Refreshing the frozen frame and recalculating ROI-local A/B. Wait for the points to update or an error message to appear.";
    return;
  }
  const copyByTool = {
    "pick-a": {
      title: "Selecting Point A",
      body: "Point A selection is active. Click once on the frozen preview to place Point A.",
    },
    "pick-b": {
      title: "Selecting Point B",
      body: "Point B selection is active. Click once on the frozen preview to place Point B.",
    },
  };
  const prompt = copyByTool[liveRunState.activeTool];
  livePointPromptNode.hidden = !prompt;
  if (!prompt) {
    return;
  }
  livePointPromptTitleNode.textContent = prompt.title;
  livePointPromptBodyNode.textContent = prompt.body;
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
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    x: Math.round(minX),
    y: Math.round(minY),
    width: Math.max(1, Math.round(maxX - minX)),
    height: Math.max(1, Math.round(maxY - minY)),
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
  return getCurrentRoiBox();
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
  return {
    ...definition,
    analysis_roi: metricBox ? boundingRectForMetricBox(metricBox) : definition.analysis_roi ? convertRect(definition.analysis_roi) : undefined,
    metric_box: metricBox,
    point_a_px: definition.point_a_px ? convertPoint(definition.point_a_px) : undefined,
    point_b_px: definition.point_b_px ? convertPoint(definition.point_b_px) : undefined,
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
  return point.x >= roi.x && point.y >= roi.y && point.x <= roi.x + roi.width && point.y <= roi.y + roi.height;
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

function hasLocallyCompleteDefinition() {
  if (!hasValidAnalysisRoi() || !hasValidPointInputs() || !hasValidMetricBoxInputs()) {
    return false;
  }
  const roi = getCurrentAnalysisRoi();
  const box = getCurrentRoiBox();
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

function pointInRotatedMetricBox(box, x, y) {
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
  return Math.abs(localX) <= Number(box.width) / 2 && Math.abs(localY) <= Number(box.height) / 2;
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
  const pointA = hasValidPointInputs() ? getCurrentPointA() : null;
  const pointB = hasValidPointInputs() ? getCurrentPointB() : null;
  const fragments = [];
  if (hasValidAnalysisRoi()) {
    const roiPoints = metricBoxCorners(box)
      .map((point) => `${point.x},${point.y}`)
      .join(" ");
    const { topCenter, handle } = metricBoxRotationHandle(box);
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
  if (box) {
    const localHalfWidth = Number(box.width) / 2;
    const leftAnchor = worldPointFromMetricBoxLocal(box, -localHalfWidth, 0);
    const rightAnchor = worldPointFromMetricBoxLocal(box, localHalfWidth, 0);
    fragments.push(
      `<line class="live-overlay-centerline" x1="${leftAnchor.x}" y1="${leftAnchor.y}" x2="${rightAnchor.x}" y2="${rightAnchor.y}"></line>`,
    );
  }
  if (pointA) {
    fragments.push(`<circle class="live-overlay-point" cx="${pointA.x}" cy="${pointA.y}" r="6"></circle>`);
    fragments.push(`<text class="live-overlay-point-label" x="${pointA.x + 10}" y="${pointA.y - 10}">A</text>`);
  }
  if (pointB) {
    fragments.push(`<circle class="live-overlay-point" cx="${pointB.x}" cy="${pointB.y}" r="6"></circle>`);
    fragments.push(`<text class="live-overlay-point-label" x="${pointB.x + 10}" y="${pointB.y - 10}">B</text>`);
  }
  livePreviewOverlayNode.innerHTML = fragments.join("");
}

function setActiveLiveTool(tool) {
  liveRunState.activeTool = tool;
  updateLiveRunControls();
  const labels = {
    "draw-roi": "Drag on the preview to draw the analysis ROI.",
    "pick-a": "Click on the preview to place Point A.",
    "pick-b": "Click on the preview to place Point B.",
  };
  setLivePointPickerStatus(labels[tool] || "Tool idle.");
  renderLiveToolPrompt();
}

function updateLiveRunControls() {
  const hasRun = Boolean(liveRunState.runId);
  const hasPreview = Boolean(liveRunState.previewSize);
  const previewState = getPreviewStatePayload();
  const status = liveRunState.detail ? liveRunState.detail.status : "";
  const isRunReady = status === "run_ready";
  const isRunActive = ["running", "invalidated", "stopping"].includes(status);
  const isSetupBusy = liveRunState.setupRecomputeInFlight;
  const canEditOverlay = hasPreview && !previewState.stream_active && !isRunActive;
  const hasRoi = hasValidAnalysisRoi();
  const roiReady = hasRoi && liveRunState.roiConfirmed;
  const canSaveDefinition = hasRun && !isRunActive && !previewState.stream_active && hasPreview && roiReady && hasLocallyCompleteDefinition();
  const targetConfirmed = isTargetTemperatureConfirmed();

  if (stopLivePreviewStreamButton) {
    stopLivePreviewStreamButton.disabled = !previewState.stream_active;
    stopLivePreviewStreamButton.textContent = "Freeze";
  }
  if (saveLiveDefinitionButton) {
    saveLiveDefinitionButton.disabled = !canSaveDefinition || isSetupBusy;
  }
  if (drawAnalysisRoiButton) {
    drawAnalysisRoiButton.disabled = !canEditOverlay;
    drawAnalysisRoiButton.classList.add("live-tool-button");
  }
  if (pickPointAButton) {
    pickPointAButton.disabled = !canEditOverlay || !roiReady || isSetupBusy;
  }
  if (pickPointBButton) {
    pickPointBButton.disabled = !canEditOverlay || !roiReady || isSetupBusy;
  }
  if (confirmTargetTemperatureButton) {
    confirmTargetTemperatureButton.disabled = isRunActive;
    confirmTargetTemperatureButton.textContent = targetConfirmed ? "Target Confirmed" : "Confirm Target";
  }
  if (startLiveRunButton) {
    startLiveRunButton.disabled = !isRunReady || isRunActive || liveRunState.definitionDirty || !targetConfirmed || isSetupBusy;
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
    liveAnalysisRoiAngleInput.value = String(roiBox.angle_deg);
  }
  if (livePointAXInput) {
    livePointAXInput.value = String(uiDefinition.point_a_px.x);
  }
  if (livePointAYInput) {
    livePointAYInput.value = String(uiDefinition.point_a_px.y);
  }
  if (livePointBXInput) {
    livePointBXInput.value = String(uiDefinition.point_b_px.x);
  }
  if (livePointBYInput) {
    livePointBYInput.value = String(uiDefinition.point_b_px.y);
  }
  if (liveForegroundPolaritySelect) {
    liveForegroundPolaritySelect.value = uiDefinition.foreground_polarity;
  }
  if (liveThresholdModeSelect) {
    liveThresholdModeSelect.value = uiDefinition.threshold_mode;
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
  liveRunState.roiConfirmed = false;
  liveRunState.confirmedRoiSignature = "";
  setSetupRecomputeState({ inFlight: false, detail: "" });
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  setLivePointPickerStatus(`Preview frozen at ${width}x${height}. Draw the ROI to seed ROI-local A/B points.`);
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
  setLivePointPickerStatus("Recomputing ROI-local A/B points from a fresh frozen frame...");
  setSetupRecomputeState({
    inFlight: true,
    detail:
      "Refreshing the frozen frame and recalculating ROI-local A/B from the current ROI and sensitivity settings.",
  });
  liveRunState.setupRecomputeTimer = window.setTimeout(async () => {
    liveRunState.setupRecomputeTimer = null;
    try {
      await loadFrozenPreviewFrame({
        runId: liveRunState.runId,
        cached: false,
        refreshDetail: false,
        seedDefaults: false,
      });
      await autoDetectLiveDefinition({ silent: true, origin: "roi-refresh", recomputeToken });
      if (recomputeToken !== liveRunState.setupRecomputeActiveToken) {
        return;
      }
      if (message) {
        setLiveRunMessage(message, "info");
      }
    } catch (error) {
      if (recomputeToken !== liveRunState.setupRecomputeActiveToken) {
        return;
      }
      setLivePointPickerStatus("Point recompute failed. Adjust ROI or sensitivity and try again.");
      setLiveRunMessage(`Failed to recompute ROI-local A/B: ${String(error)}`, "error");
    } finally {
      if (recomputeToken === liveRunState.setupRecomputeActiveToken) {
        setSetupRecomputeState({ inFlight: false, detail: "" });
      }
    }
  }, 120);
}

function commitAnalysisRoiSelection({ force = false, message = "", recompute = true } = {}) {
  updateLiveDefinitionAfterLocalEdit();
  if (!hasValidAnalysisRoi()) {
    liveRunState.roiConfirmed = false;
    liveRunState.confirmedRoiSignature = "";
    updateLiveRunControls();
    return;
  }
  const roiSignature = getAnalysisRoiSignature();
  const roiChanged = roiSignature !== liveRunState.confirmedRoiSignature;
  if (roiChanged && hasValidPointInputs()) {
    clearPointInputs();
  }
  liveRunState.roiConfirmed = force || liveRunState.roiConfirmed || roiChanged;
  liveRunState.confirmedRoiSignature = roiSignature;
  syncLiveDefinitionDirtyState();
  renderLivePreviewOverlay();
  updateLiveRunControls();
  setLivePointPickerStatus("ROI ready. Recomputing ROI-local horizontal A/B points from the latest frozen frame.");
  if (message) {
    setLiveRunMessage(message, "info");
  }
  if (recompute && (roiChanged || force)) {
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

function applyTrackedPointInputs(latestTelemetry) {
  if (!latestTelemetry) {
    return;
  }
  const pointA = Array.isArray(latestTelemetry.point_a_px) ? latestTelemetry.point_a_px : null;
  const pointB = Array.isArray(latestTelemetry.point_b_px) ? latestTelemetry.point_b_px : null;
  if (pointA && pointA.length === 2) {
    if (livePointAXInput) {
      livePointAXInput.value = String(pointA[0]);
    }
    if (livePointAYInput) {
      livePointAYInput.value = String(pointA[1]);
    }
  }
  if (pointB && pointB.length === 2) {
    if (livePointBXInput) {
      livePointBXInput.value = String(pointB[0]);
    }
    if (livePointBYInput) {
      livePointBYInput.value = String(pointB[1]);
    }
  }
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
      await refreshTrackingPreviewFrame(runId);
      if (isLiveRunTerminalStatus(detail.status) && !terminalHandled) {
        terminalHandled = true;
        stopLiveTrackingLoop();
        startCurrentTemperaturePolling();
        await loadRecentSessions();
        if (detail.status === "completed") {
          const resultResponse = await fetch(`/api/runs/${runId}/result`);
          const resultPayload = resultResponse.ok ? await resultResponse.json() : null;
          setLiveRunMessage(
            `Live run completed. point_count=${resultPayload?.point_count ?? "n/a"} af95=${resultPayload?.af95 ?? "n/a"}.`,
            "success",
          );
        } else if (detail.status === "aborted") {
          setLiveRunMessage(
            `Live run stopped. samples=${telemetryPayload?.curve?.length ?? "n/a"}.`,
            "warning",
          );
        } else {
          setLiveRunMessage(`Live run ended with status=${detail.status}.`, "error");
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
  }, 250);
}

function buildLiveDefinitionBasePayload({ coordinateSpace = "preview" } = {}) {
  const roiBox = getCurrentRoiBox();
  const payload = {
    analysis_roi: boundingRectForMetricBox(roiBox),
    metric_box: roiBox,
    foreground_polarity: liveForegroundPolaritySelect ? liveForegroundPolaritySelect.value : "dark_on_light",
    threshold_mode: liveThresholdModeSelect ? liveThresholdModeSelect.value : "adaptive",
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
    observation_axis: "long_axis",
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
      clearTargetTemperatureConfirmation();
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
      setLivePointPickerStatus("Live preview is running. Press Freeze to capture a still frame, then draw the ROI.");
      if (!silent) {
        setLiveRunMessage("Live setup session created. Live preview started automatically.", "success");
      }
    } else if (!silent) {
      setLiveRunMessage("Live setup session created.", "success");
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
  setLiveRunMessage("Fetching preview frame...", "info");
  try {
    await stopLivePreviewStream({ clearImage: false, silent: true });
    await loadFrozenPreviewFrame({ runId: liveRunState.runId, cached: false });
    setLivePointPickerStatus("Preview loaded. Draw the ROI first; ROI-local A/B will be recomputed automatically.");
    setLiveRunMessage("Preview frame loaded.", "success");
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
    setLiveRunMessage("Starting live preview stream...", "info");
  }
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
    setLivePointPickerStatus("Live preview is running. Press Freeze to capture an editable still frame.");
    if (!silent) {
      setLiveRunMessage("Live preview stream started. Press Freeze to capture an editable still frame.", "success");
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
    if (!silent) {
      setLiveRunMessage(String(error), "error");
    }
  } finally {
    updateLiveRunControls();
  }
}

async function stopLivePreviewStream({ clearImage = false, silent = false } = {}) {
  const hadActiveStream = liveRunState.previewStreamActive;
  const streamRunId = liveRunState.runId;
  const hydrateFrozenFrame = hadActiveStream && !clearImage && !silent;
  liveRunState.previewStreamActive = false;
  liveRunState.previewStreamUrl = "";
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
    setLivePointPickerStatus("Preview frozen. Draw the ROI first; ROI-local A/B will be recomputed automatically.");
    if (!hydrateFrozenFrame) {
      setLiveRunMessage("Preview frozen on the last frame.", "info");
    } else {
      setLiveRunMessage("Preview frozen. Refreshed the still frame for editing.", "info");
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
  const blob = await response.blob();
  revokeLivePreviewUrl();
  liveRunState.previewObjectUrl = URL.createObjectURL(blob);
  liveRunState.previewSize = width > 0 && height > 0 ? { width, height } : null;
  liveRunState.previewSourceSize =
    sourceWidth > 0 && sourceHeight > 0 ? { width: sourceWidth, height: sourceHeight } : liveRunState.previewSize;
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
    setLiveRunMessage("Auto-detecting locked points from the ROI-local horizontal axis...", "info");
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
    const previewPoints = mapDefinitionToCoordinateSpace(
      {
        point_a_px: payload.point_a_px,
        point_b_px: payload.point_b_px,
      },
      "preview",
    );
    if (livePointAXInput) {
      livePointAXInput.value = String(previewPoints.point_a_px.x);
    }
    if (livePointAYInput) {
      livePointAYInput.value = String(previewPoints.point_a_px.y);
    }
    if (livePointBXInput) {
      livePointBXInput.value = String(previewPoints.point_b_px.x);
    }
    if (livePointBYInput) {
      livePointBYInput.value = String(previewPoints.point_b_px.y);
    }
    liveRunState.definitionDirty = true;
    syncLiveDefinitionDirtyState();
    renderLivePreviewOverlay();
    setLivePointPickerStatus("ROI-local A/B points are ready. Adjust ROI, sensitivity, or points manually if needed.");
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
      body: JSON.stringify(buildLiveDefinitionPayload({ coordinateSpace: "source" })),
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
  setLivePointPickerStatus("Point updated. Save Definition when the ROI and A/B look correct.");
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

function hitTestRoiInteraction(point) {
  if (!hasValidAnalysisRoi()) {
    return null;
  }
  const box = getCurrentRoiBox();
  const { handle } = metricBoxRotationHandle(box);
  if (distanceBetweenPoints(point, handle) <= 14) {
    return { tool: "rotate-roi", box };
  }
  const corners = metricBoxCorners(box);
  for (const corner of metricBoxResizeHandles(box)) {
    if (distanceBetweenPoints(point, corner) <= 12) {
      return {
        tool: "resize-roi",
        box,
        cornerIndex: corner.index,
        fixedCorner: corners[(corner.index + 2) % 4],
      };
    }
  }
  if (pointInRotatedMetricBox(box, point.x, point.y)) {
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
    const angleRad = (Number(drag.originalAngleDeg) * Math.PI) / 180;
    const cosTheta = Math.cos(angleRad);
    const sinTheta = Math.sin(angleRad);
    const relativeX = point.x - drag.fixedCorner.x;
    const relativeY = point.y - drag.fixedCorner.y;
    const localDx = relativeX * cosTheta + relativeY * sinTheta;
    const localDy = -relativeX * sinTheta + relativeY * cosTheta;
    const width = Math.max(8, Math.abs(localDx));
    const height = Math.max(8, Math.abs(localDy));
    const center = {
      x: drag.fixedCorner.x + (localDx / 2) * cosTheta - (localDy / 2) * sinTheta,
      y: drag.fixedCorner.y + (localDx / 2) * sinTheta + (localDy / 2) * cosTheta,
    };
    applyMetricBoxToInputs({
      center_x: center.x,
      center_y: center.y,
      width,
      height,
      angle_deg: drag.originalAngleDeg,
    });
    ensureMetricBoxWithinAnalysisRoi();
    updateLiveDefinitionAfterLocalEdit();
    return;
  }
  if (drag.tool === "rotate-roi") {
    const box = getCurrentRoiBox();
    const angleDeg = (Math.atan2(point.y - box.center_y, point.x - box.center_x) * 180) / Math.PI + 90;
    applyMetricBoxToInputs({
      center_x: box.center_x,
      center_y: box.center_y,
      width: box.width,
      height: box.height,
      angle_deg: angleDeg,
    });
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
    commitAnalysisRoiSelection({ force: true, message: "ROI updated from the preview overlay." });
  } else if (["move-roi", "resize-roi", "rotate-roi"].includes(completedTool)) {
    commitAnalysisRoiSelection({ force: true, message: "ROI adjusted. Recomputed ROI-local A/B from a fresh frozen frame." });
  }
  setActiveLiveTool("");
}

async function startLiveRun() {
  if (!liveRunState.runId || !startLiveRunButton) {
    return;
  }
  if (!isTargetTemperatureConfirmed()) {
    setLiveRunMessage("Confirm the target temperature before starting the live run.", "warning");
    updateLiveRunControls();
    return;
  }
  startLiveRunButton.disabled = true;
  stopCurrentTemperaturePolling();
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
    startLiveTrackingLoop(liveRunState.runId);
    setLiveRunMessage(
      `Live run started. session=${payload.session_id}. Tracking ROI-local A/B in real time...`,
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
    startLiveTrackingLoop(liveRunState.runId);
    setLiveRunMessage("Stopping live run...", "info");
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

function hasWorkspaceAfasUi() {
  return Boolean(
    workspaceAfasRunButton &&
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
  return "AFAS dataset is unavailable for this session.";
}

function syncWorkspaceAfasAvailability() {
  if (!hasWorkspaceAfasUi()) {
    return;
  }
  const available = isWorkspaceAfasAvailable();
  for (const node of [
    workspaceAfasRunButton,
    workspaceAfasExportPngButton,
    workspaceAfasExportXlsxButton,
    workspaceAfasChannelNode,
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
}

function setWorkspaceAfasStatus(message, tone = "neutral") {
  if (!workspaceAfasStatusNode) {
    return;
  }
  workspaceAfasStatusNode.textContent = message;
  workspaceAfasStatusNode.className = `workspace-adjustment-status workspace-adjustment-status--${tone}`;
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

function buildChartScaler(xValues, yValues, width, height, padding) {
  const [minX, maxX] = normalizeChartDomain(xValues, [0, 1]);
  const [minY, maxY] = normalizeChartDomain(yValues, [0, 1]);
  const xSpan = Math.max(maxX - minX, 1);
  const ySpan = Math.max(maxY - minY, 1);
  return {
    minX,
    maxX,
    minY,
    maxY,
    x(value) {
      return padding + ((Number(value) - minX) / xSpan) * (width - padding * 2);
    },
    y(value) {
      return height - padding - ((Number(value) - minY) / ySpan) * (height - padding * 2);
    },
  };
}

function renderWorkspaceAfasOverview(overview, activeChannel) {
  if (!workspaceAfasOverviewSeriesNode || !workspaceAfasOverviewSummaryNode) {
    return;
  }
  const items = Array.isArray(overview) ? overview : [];
  if (!items.length) {
    workspaceAfasOverviewSeriesNode.innerHTML = "";
    workspaceAfasOverviewSummaryNode.innerHTML = '<p class="session-item--empty">AFAS analysis is unavailable.</p>';
    return;
  }

  const allTemps = items.flatMap((item) => (item.series ? item.series.temperature_celsius || [] : []));
  const allValues = items.flatMap((item) => (item.series ? item.series.values || [] : []));
  const scaler = buildChartScaler(allTemps, allValues, 640, 220, 28);
  workspaceAfasOverviewSeriesNode.innerHTML = items
    .map((item, index) => {
      const temperatures = item.series ? item.series.temperature_celsius || [] : [];
      const values = item.series ? item.series.values || [] : [];
      const points = temperatures
        .map((temperature, pointIndex) => `${scaler.x(temperature)},${scaler.y(values[pointIndex])}`)
        .join(" ");
      const isActive = item.channel_name === activeChannel;
      const stroke = isActive ? "#cf1124" : ["#ffb454", "#36506c", "#0f766e", "#8b5e3c"][index % 4];
      return `
        <polyline
          fill="none"
          stroke="${stroke}"
          stroke-width="${isActive ? 4 : 2.5}"
          stroke-linecap="round"
          stroke-linejoin="round"
          opacity="${isActive ? 1 : 0.55}"
          points="${points}"
        ></polyline>
      `;
    })
    .join("");
  workspaceAfasOverviewSummaryNode.innerHTML = items
    .map(
      (item) => `
        <article class="workspace-afas-overview-item${item.channel_name === activeChannel ? " workspace-afas-overview-item--active" : ""}">
          <strong>${escapeHtml(item.channel_name)}</strong>
          <p>status=${escapeHtml(item.result_status)}</p>
          <p>points=${item.point_count} outliers=${item.outlier_count}</p>
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
  const padding = 32;
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

  function renderLineSegment(line, color, dash = "10 6") {
    if (!line || !Array.isArray(line.range_celsius)) {
      return "";
    }
    const [start, end] = line.range_celsius;
    const y1 = line.slope * start + line.intercept;
    const y2 = line.slope * end + line.intercept;
    return `<line x1="${scaler.x(start)}" y1="${scaler.y(y1)}" x2="${scaler.x(end)}" y2="${scaler.y(y2)}" stroke="${color}" stroke-width="2.5" stroke-dasharray="${dash}"></line>`;
  }

  function renderInfiniteLine(line, color) {
    if (!line) {
      return "";
    }
    const start = Math.min(...temperatures);
    const end = Math.max(...temperatures);
    const y1 = line.slope * start + line.intercept;
    const y2 = line.slope * end + line.intercept;
    return `<line x1="${scaler.x(start)}" y1="${scaler.y(y1)}" x2="${scaler.x(end)}" y2="${scaler.y(y2)}" stroke="${color}" stroke-width="2.5" stroke-dasharray="10 6"></line>`;
  }

  function renderMarker(xValue, yValue, label, color) {
    if (!Number.isFinite(xValue) || !Number.isFinite(yValue)) {
      return "";
    }
    return `
      <circle cx="${scaler.x(xValue)}" cy="${scaler.y(yValue)}" r="6.5" fill="${color}" stroke="#fffaf4" stroke-width="2"></circle>
      <text x="${scaler.x(xValue) + 10}" y="${scaler.y(yValue) - 10}" fill="${color}" font-size="12" font-weight="700">${escapeHtml(label)}</text>
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
    <polyline fill="none" stroke="#36506c" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${curvePoints}"></polyline>
    ${renderLineSegment(fit?.low_baseline, "#0f766e")}
    ${renderLineSegment(fit?.high_baseline, "#b45309")}
    ${renderInfiniteLine(fit?.tangent, "#cf1124")}
    ${renderMarker(result?.As, asY, "As", "#0f766e")}
    ${renderMarker(result?.Af_tan, afY, "Af-tan", "#b45309")}
    ${renderMarker(result?.max_slope_temp, maxSlopeY, "Slope", "#cf1124")}
  `;
  workspaceAfasAnalysisEmptyNode.hidden = true;
}

function renderWorkspaceAfasResults(state) {
  if (
    !workspaceAfasResultStatusNode ||
    !workspaceAfasResultAsNode ||
    !workspaceAfasResultAfTanNode ||
    !workspaceAfasResultMaxSlopeNode ||
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
    workspaceAfasResultMaxSlopeNode.textContent = "N/A";
    workspaceAfasOutlierCountNode.textContent = "0";
    workspaceAfasSmoothedCountNode.textContent = "0";
    workspaceAfasWarningListNode.innerHTML = '<p class="session-item--empty">Warnings will appear here when analysis runs.</p>';
    return;
  }

  const preprocessing = state.preprocessing || {};
  const analysis = state.analysis || {};
  const result = analysis.result || {};
  const warnings = [...(preprocessing.warnings || []), ...(analysis.warnings || [])];
  workspaceAfasResultStatusNode.textContent = analysis.result_status || "N/A";
  workspaceAfasResultAsNode.textContent = formatAfasTemperature(result.As);
  workspaceAfasResultAfTanNode.textContent = formatAfasTemperature(result.Af_tan);
  workspaceAfasResultMaxSlopeNode.textContent = formatAfasTemperature(result.max_slope_temp);
  workspaceAfasOutlierCountNode.textContent = String(preprocessing.outlier_repair?.outlier_count ?? 0);
  workspaceAfasSmoothedCountNode.textContent = String((preprocessing.smoothed?.temperature_celsius || []).length);
  workspaceAfasWarningListNode.innerHTML = warnings.length
    ? `<ul class="workspace-adjustment-notes-list">${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>`
    : '<p class="session-item--empty">No preprocessing or analysis warnings.</p>';
}

function syncWorkspaceAfasControls(state) {
  if (!state) {
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
    renderWorkspaceAfasOverview([], "");
    renderWorkspaceAfasAnalysisChart(null);
    renderWorkspaceAfasResults(null);
    setWorkspaceAfasStatus(
      isWorkspaceAfasAvailable() ? "AFAS analysis has not been loaded yet." : getWorkspaceAfasUnavailableMessage(),
      isWorkspaceAfasAvailable() ? "neutral" : "info",
    );
    return;
  }
  syncWorkspaceAfasAvailability();
  syncWorkspaceAfasControls(state);
  renderWorkspaceAfasOverview(state.overview || [], state.active_channel);
  renderWorkspaceAfasAnalysisChart(state.analysis || null);
  renderWorkspaceAfasResults(state);
  const analysis = state.analysis || {};
  const detail = analysis.detail || "AFAS analysis completed.";
  setWorkspaceAfasStatus(detail, analysis.result_status === "ok" ? "success" : "info");
}

async function loadWorkspaceAfasAnalysis(sessionId, { silent = false } = {}) {
  if (!hasWorkspaceAfasUi()) {
    return null;
  }
  if (!isWorkspaceAfasAvailable()) {
    renderWorkspaceAfas(null);
    return null;
  }
  if (workspaceAfasRunButton) {
    workspaceAfasRunButton.disabled = true;
  }
  setWorkspaceAfasStatus("Running AFAS preprocessing and tangent analysis...", "info");
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
    renderWorkspaceAfas(payload);
    return payload;
  } catch (error) {
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

function isLiveSetupReusable(detail) {
  if (!detail || !detail.run_id) {
    return false;
  }
  return !["completed", "failed", "aborted"].includes(String(detail.status || ""));
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
      runId = "";
      storeLiveSetupRunId("");
    }
  }
  if (!isLiveSetupReusable(detail)) {
    runId = await createLiveRun({ autoStartPreview: false, silent: true, forceReset: true });
    detail = await refreshLiveRunDetail(runId);
  }
  storeLiveSetupRunId(runId);
  if (!detail.preview?.stream_active) {
    await startLivePreviewStream({ silent: true });
    setLiveRunMessage("Live preview started automatically. Press Freeze when you are ready to define the ROI.", "success");
  } else {
    setLivePointPickerStatus("Live preview is running. Press Freeze to capture a still frame.");
  }
}

async function bootstrap() {
  try {
    await Promise.all([loadHealth(), loadProfile(), loadPrecheck(), loadRecentSessions()]);
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
if (liveRunPresetSelect && liveRunPresetNode) {
  liveRunPresetSelect.addEventListener("change", () => {
    liveRunPresetNode.textContent = liveRunPresetSelect.value;
    if (hasLiveSetupUi()) {
      void ensureLiveSetupBootstrapped({ forceRestart: true });
    }
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
if (stopLiveRunButton) {
  stopLiveRunButton.addEventListener("click", stopLiveRun);
}
if (liveTargetTemperatureInput) {
  for (const eventName of ["input", "change"]) {
    liveTargetTemperatureInput.addEventListener(eventName, clearTargetTemperatureConfirmation);
  }
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
for (const liveInput of [
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
    scheduleRoiPointRecompute({ message: "Sensitivity updated. Recomputed ROI-local A/B from a fresh frozen frame." });
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
          width: livePreviewImageNode.naturalWidth,
          height: livePreviewImageNode.naturalHeight,
        };
      }
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
    const sessionId = getWorkspaceSessionId();
    if (!sessionId) {
      return;
    }
    void loadWorkspaceAfasAnalysis(sessionId);
  });
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
