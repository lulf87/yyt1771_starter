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

function workspaceUrl(sessionId) {
  return `/workspace/${encodeURIComponent(sessionId)}`;
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

  const summaryResponse = await fetch(`/api/session/${sessionId}`);
  if (!summaryResponse.ok) {
    return;
  }
  const summary = await summaryResponse.json();
  const summaryCopyNode = document.getElementById("workspace-summary-copy");
  const summaryStateNode = document.getElementById("workspace-summary-state");
  if (summaryCopyNode) {
    summaryCopyNode.textContent =
      `Session ${summary.session_id} is currently recorded as ${summary.state} with ${summary.point_count} points.`;
  }
  if (summaryStateNode) {
    summaryStateNode.textContent = summary.state;
    summaryStateNode.className = `status-pill status-${summary.state === "completed" ? "ok" : "warn"}`;
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
if (document.body.dataset.page === "home") {
  bootstrap();
}
if (document.body.dataset.page === "workspace") {
  bootstrapWorkspace();
}
