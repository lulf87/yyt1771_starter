const healthStatusNode = document.getElementById("health-status");
const profileNameNode = document.getElementById("profile-name");
const profileModeNode = document.getElementById("profile-mode");
const sessionResultNode = document.getElementById("session-result");
const runMockButton = document.getElementById("run-mock-btn");

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

async function runMockSession() {
  runMockButton.disabled = true;
  runMockButton.textContent = "Running...";

  try {
    const runResponse = await fetch("/api/session/run-mock", { method: "POST" });
    const runPayload = await runResponse.json();
    renderSessionResult(runPayload);

    if (runPayload.session_id) {
      const summaryResponse = await fetch(`/api/session/${runPayload.session_id}`);
      const summaryPayload = await summaryResponse.json();
      renderSessionResult(summaryPayload);
    }
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  } finally {
    runMockButton.disabled = false;
    runMockButton.textContent = "Run Mock Session";
  }
}

async function bootstrap() {
  try {
    await Promise.all([loadHealth(), loadProfile()]);
  } catch (error) {
    renderSessionResult({ detail: String(error) });
  }
}

runMockButton.addEventListener("click", runMockSession);
bootstrap();
