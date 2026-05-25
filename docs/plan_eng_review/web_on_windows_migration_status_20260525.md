# Web On Windows Migration Status - 2026-05-25

Status: ACTIVE_MAC_FINISH_DELIVERY_DIRECTION

## Purpose

This file records the delivery-direction refreeze after the `mac-finish`
checkpoint.

It supersedes older desktop-workstation migration wording when the question is:

- how to move the current project to Windows
- which delivery shell is the current operator-facing path
- whether `desktop_app` / PySide6 should be treated as the next implementation
  target

## Current Baseline

Current code checkpoint:

```text
tag: mac-finish
commit: 44933fa
branch at creation: codex/ab-outlier-reduction
```

Current primary product repository:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter
```

Current operator-facing delivery shell:

```text
src.webapp.serve
```

The current product direction is Web workstation first. Windows migration means
running and validating this Web workstation on Windows, not reviving the
PySide6 desktop shell by default.

## Active Run States

Only these two states should be treated as formal active debugging / migration
states unless this file is updated.

### Real Hardware State

```text
profile: dev_lab
camera: real Hik GigE / MVS
temperature controller: real LU92XX Modbus RTU
delivery shell: Web
```

Mac startup:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_lab
```

Windows startup target:

```powershell
.venv\Scripts\python -m src.webapp.serve --profile dev_lab
```

After editable install, the equivalent console script is:

```powershell
.venv\Scripts\yyt1771-web --profile dev_lab
```

Machine-specific camera identity, serial ports, logging paths, and runtime
paths must live in ignored local config files such as:

```text
configs/dev_lab.local.yaml
```

### Offline Material Replay State

```text
profile: dev_offline_capture
camera: offline_capture
temperature controller: offline_capture
delivery shell: Web
material: examples/runtime/camera_captures/20260522-183158-dev_lab
```

Mac startup:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_offline_capture
```

Windows startup target:

```powershell
.venv\Scripts\python -m src.webapp.serve --profile dev_offline_capture
```

After editable install, the equivalent console script is:

```powershell
.venv\Scripts\yyt1771-web --profile dev_offline_capture
```

## Paused Legacy Desktop Track

The following still exist in the repository, but they are no longer the active
delivery direction for `mac-finish`:

```text
src/desktop_app/
tests/desktop_app/
docs/requirements/desktop_workstation_migration_requirement_v1.md
docs/plan_eng_review/desktop_workstation_migration_plan_lock_v1.md
docs/plan_eng_review/desktop_workstation_migration_status_v1.md
```

They should be treated as paused historical / fallback material.

Do not use them as the default Windows migration instructions. Do not add new
desktop features unless the user explicitly reactivates the desktop track.

## Windows Config Interpretation

`configs/prod_win.yaml` is still present, but in the `mac-finish` direction it
is only a historical production-profile skeleton. It is not a verified
Windows-ready profile for the current Web workstation.

For Windows migration work, prefer:

1. start from `dev_lab`
2. create or update `configs/dev_lab.local.yaml` on that Windows machine
3. validate SDK import, camera open/read, LU92XX read/write, Web startup, ROI /
   A-B, live run, stop, and analysis
4. only after that, decide whether to promote a cleaned Windows production
   profile

## Windows Migration Checklist

The Windows migration should verify these in order:

1. Python 3.11 environment installs project dependencies without `cv2` / NumPy
   ABI mismatch.
2. Hik MVS SDK Python bindings import in the selected Windows Python
   environment.
3. Real camera can be enumerated, opened, and read through the Web profile.
4. LU92XX serial port can read current temperature.
5. LU92XX setpoint, output power, and output start commands are confirmed by
   readback / physical device display.
6. `dev_offline_capture` can replay the standard material in the Web UI.
7. `dev_lab` can complete preset, Freeze, rotated ROI, ROI-local A/B, live
   run, manual stop, and data analysis on real hardware.
8. Any Windows-only path differences are kept in ignored local config, not in
   tracked baseline configs.

## Mac Codex To Windows Control Path

The preferred remote-control model is:

```text
Mac Codex -> SSH -> Windows PowerShell -> yyt1771 Web workstation
```

The Windows machine owns all hardware access. Camera SDK calls, LU92XX serial
access, local config files, and Web server startup should run on Windows. The
Mac machine only issues commands, transfers code/material when needed, and
opens the resulting Web page for inspection.

Do not store Windows usernames, passwords, hostnames, fixed IP addresses,
camera IDs, serial ports, or private keys in tracked repository files.

### Windows One-Time Remote Setup

Run these from an elevated Windows PowerShell session on the Windows machine:

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

Confirm the Windows user that Codex should use:

```powershell
whoami
$env:COMPUTERNAME
ipconfig
```

Record the Windows host/IP and username outside the repo, for example in a
private note or local shell variable on the Mac.

### Mac Key Setup

On the Mac, create a dedicated SSH key for this bench:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/yyt1771_windows_codex -C yyt1771-windows-codex
```

Copy the public key text:

```bash
cat ~/.ssh/yyt1771_windows_codex.pub
```

On Windows, append that public key to the target user's authorized keys:

```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.ssh
notepad $env:USERPROFILE\.ssh\authorized_keys
icacls $env:USERPROFILE\.ssh /inheritance:r
icacls $env:USERPROFILE\.ssh /grant "${env:USERNAME}:(OI)(CI)F"
icacls $env:USERPROFILE\.ssh\authorized_keys /inheritance:r
icacls $env:USERPROFILE\.ssh\authorized_keys /grant "${env:USERNAME}:F"
Restart-Service sshd
```

Then test from the Mac:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> "powershell -NoProfile -Command \"whoami; hostname; py --version\""
```

If `py --version` is not available, install Python 3.11 on Windows before
continuing.

### Remote Command Pattern

Use SSH to run Windows commands explicitly through PowerShell:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location 'C:\path\to\yyt1771_starter'; .venv\Scripts\python -m pytest tests\architecture -q\""
```

Prefer a Windows-local repository checkout. If the current Mac worktree has
uncommitted documentation or code that Windows must receive, either commit it
first or transfer a deliberate patch / archive; do not rely on undocumented
manual copying.

### Windows Environment Bootstrap By Remote Codex

Once SSH works, Mac Codex can prepare the Windows Python environment remotely:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location 'C:\path\to\yyt1771_starter'; py -3.11 -m venv .venv; .venv\Scripts\python -m pip install -U pip; .venv\Scripts\python -m pip install -e '.[dev]'\""
```

Then verify the ABI-sensitive imports before running Web or vision flows:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location 'C:\path\to\yyt1771_starter'; .venv\Scripts\python -c 'import numpy, cv2; print(numpy.__version__); print(cv2.__version__)'\""
```

### Remote Web Startup And Browser Access

For offline replay:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location 'C:\path\to\yyt1771_starter'; .venv\Scripts\python -m src.webapp.serve --profile dev_offline_capture\""
```

For real hardware:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex <windows-user>@<windows-host> \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Set-Location 'C:\path\to\yyt1771_starter'; .venv\Scripts\python -m src.webapp.serve --profile dev_lab\""
```

Run the Web server command in one terminal and leave it open. The safest
browser path from Mac is a second SSH session used only for tunneling:

```bash
ssh -i ~/.ssh/yyt1771_windows_codex -L 8002:127.0.0.1:8002 <windows-user>@<windows-host>
```

Then open the Mac browser at:

```text
http://127.0.0.1:8002/
```

If tunneling is not used, the Windows Web profile must bind to a reachable
interface and the Windows firewall must allow the selected port. Keep that
machine-specific network decision in local config, not in tracked baseline
YAML.

### Remote Validation Order For Codex

When a Mac-based Codex session drives Windows remotely, use this order:

1. SSH connectivity: `whoami`, `hostname`, Python version.
2. Repository state: branch, tag, `git status --short`, expected commit.
3. Python environment: install dependencies, then verify `numpy` and `cv2`.
4. Offline Web replay: start `dev_offline_capture`, open the tunneled browser,
   confirm preset / ROI / live run / stop / analysis.
5. Camera SDK: verify Hik MVS import and camera enumeration on Windows.
6. Temperature controller: verify LU92XX serial read, setpoint write, output
   power write, and physical readback/display.
7. Real Web run: start `dev_lab`, complete the full Web flow on hardware.
8. Final report: name the Windows host, profile, Python environment, Web URL,
   hardware state, browser flow tested, and any unverified item.

## Validation Boundary

This document is a direction and migration-state correction. It does not claim
Windows hardware validation has already passed.

Any future claim that Windows is ready must name the exact Windows machine,
profile, Python environment, camera SDK state, temperature-controller state,
and browser URL used for validation.
