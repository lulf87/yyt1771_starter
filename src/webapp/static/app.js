const healthStatusNode = document.getElementById("health-status");
const profileNameNode = document.getElementById("profile-name");
const profileModeNode = document.getElementById("profile-mode");
const sessionResultNode = document.getElementById("session-result");
const recentSessionsNode = document.getElementById("recent-sessions");
const runMockButton = document.getElementById("run-mock-btn");
const runReplayButton = document.getElementById("run-replay-btn");
const refreshPrecheckButton = document.getElementById("refresh-precheck-btn");
const precheckStatusNode = document.getElementById("precheck-status");
const precheckItemsNode = document.getElementById("precheck-items");
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
const workspaceStepNodes = Array.from(document.querySelectorAll("[data-testid='workspace-step']"));

const WORKSPACE_STEPS = ["准备", "采集", "处理", "计算", "调整", "存储"];
let workspaceDetailState = null;

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

function renderActiveSelection(selection) {
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
  statuses[4].status = "todo";
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
    node.classList.remove("workspace-step--done", "workspace-step--active", "workspace-step--todo", "workspace-step--error");
    node.classList.add(`workspace-step--${stage.status}`);
    const statusNode = node.querySelector("[data-testid='workspace-step-status']");
    if (statusNode) {
      statusNode.textContent = stage.status;
    }
  });
  if (workspaceSessionStateNode) {
    workspaceSessionStateNode.className = `status-pill status-${sessionState === "completed" ? "ok" : sessionState === "failed" ? "fail" : "warn"}`;
  }
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
  }
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

  const [summaryResponse, detailResponse] = await Promise.allSettled([
    fetch(`/api/session/${sessionId}`),
    fetch(`/api/session/${sessionId}/detail`),
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
if (workspaceRefreshButton) {
  workspaceRefreshButton.addEventListener("click", bootstrapWorkspace);
}
if (document.body.dataset.page === "home") {
  bootstrap();
}
if (document.body.dataset.page === "workspace") {
  bootstrapWorkspace();
}
