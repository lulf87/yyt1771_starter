const healthStatusNode = document.getElementById("health-status");
const profileNameNode = document.getElementById("profile-name");
const profileModeNode = document.getElementById("profile-mode");
const sessionResultNode = document.getElementById("session-result");
const recentSessionsNode = document.getElementById("recent-sessions");
const runMockButton = document.getElementById("run-mock-btn");
const runReplayButton = document.getElementById("run-replay-btn");

function renderSessionResult(payload) {
  sessionResultNode.textContent = JSON.stringify(payload, null, 2);
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

function renderRecentSessions(items) {
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
  await runSession("/api/session/run-replay", runReplayButton, "Run Replay Session");
}

async function bootstrap() {
  try {
    await Promise.all([loadHealth(), loadProfile(), loadRecentSessions()]);
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  }
}

runMockButton.addEventListener("click", runMockSession);
runReplayButton.addEventListener("click", runReplaySession);
bootstrap();
