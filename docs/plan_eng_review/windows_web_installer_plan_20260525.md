# Windows Web Installer Plan - 2026-05-25

Status: ACTIVE_IMPLEMENTATION_PLAN

## Purpose

This file locks the implementation direction for packaging the current Web
workstation for Windows operators.

The implementation starts from:

```text
branch: main
tag: mac-finish-serial-port
commit: 1e39a70
feature branch: feat/windows-web-installer
```

## Product Direction

The Windows deliverable remains the Web workstation:

```text
src.webapp.serve -> src.application -> workflow / storage / report / vision / temp / camera
```

Do not revive the paused PySide6 / Qt desktop track for this work.

Windows v1 packaging targets the real-device `dev_lab` path only:

```text
profile: dev_lab
camera: Hik GigE / MVS, protocol_any, no fixed serial/IP
temperature controller: LU92XX Modbus RTU
delivery shell: Web
```

`dev_offline_capture` remains available for Mac/development replay and browser
regression, but Windows v1 packaging must not create
`configs/dev_offline_capture.local.yaml` or make offline replay the installer
mainline.

## Config And Device Identity

The camera identity policy follows the current Mac state:

```yaml
probe_mode: protocol_any
allowed_models: []
serial_number: ""
ip: ""
```

Real camera serial numbers, fixed IPs, Windows host names, Windows user names,
COM ports, credentials, private keys, SDK payloads, and third-party installers
must not be committed to tracked config.

The Windows installed app may use a private per-user override:

```text
%LOCALAPPDATA%\YYT1771\configs\dev_lab.local.yaml
```

That file may contain Windows-local runtime paths, the selected LU92XX COM
port after Web confirmation, and other machine-local settings.

## Runtime Interfaces

`src.webapp.serve` remains the canonical entry point and gains optional
operator-launch conveniences:

```text
--profile dev_lab
--host <host>
--port <port>
--open-browser
```

`--host` and `--port` override only the current process. They must not mutate
tracked config.

The Web serial-port selection flow remains the operator path. After a LU92XX
COM port is selected and the current temperature can be read, the selected
port should be persisted to the per-user `dev_lab.local.yaml` override.

## Windows ZIP Deliverable

The final deliverable is a single ZIP archive with this shape:

```text
app/
prereqs/
install_yyt1771.bat
start_yyt1771.bat
stop_yyt1771.bat
安装与启动说明.md
manifest.json
```

The ZIP must include user-provided official prerequisite installers in
`prereqs/`:

- Hik MVS SDK / driver installer
- Microsoft Visual C++ x64 runtime installer, if required by Hik/OpenCV
- USB-to-serial driver installer after the real Windows adapter chipset is
  identified

The repository stores scripts and manifests for packaging, not the third-party
binary installers. A release build must fail if required prerequisite files are
missing from the local staging directory.

## Startup Experience

The operator should not type terminal commands or manually enter a URL.

`install_yyt1771.bat` should run the PowerShell installer, install missing
prerequisites, create the user-local YYT1771 directories, initialize
`dev_lab.local.yaml`, and verify the app can start.

`start_yyt1771.bat` should start the Web server, wait for the health endpoint,
and open the default browser automatically.

Logs should live under:

```text
%LOCALAPPDATA%\YYT1771\logs
```

## Validation Gates

Mac validation may cover source checks, Web API tests, and browser-visible Web
flows. It cannot prove Windows hardware readiness.

Windows source validation must prove:

1. Python 3.11 / packaged runtime works.
2. `numpy` and `cv2` import without ABI mismatch.
3. Hik MVS Python binding imports.
4. `dev_lab --open-browser` starts the Web workstation.
5. Camera probe reads one frame via `protocol_any`.
6. LU92XX COM selection reads current temperature.
7. Temperature target and output power write/readback match the physical
   controller.
8. Full Web flow completes: preset, Freeze, rotated ROI, ROI-local A/B, live
   run, manual stop, analysis.

Windows ZIP validation must prove:

1. A clean Windows user can unzip the archive.
2. `install_yyt1771.bat` installs or reports required prerequisites.
3. `start_yyt1771.bat` launches without typed commands and opens the browser.
4. The selected COM port persists after restart in the user-local config.
5. `stop_yyt1771.bat` stops the Web server.

## Commit And Tag Strategy

Use small commits on `feat/windows-web-installer`:

1. `docs: lock windows web installer plan`
2. `feat: add user-local windows profile overrides`
3. `feat: add windows web auto launcher`
4. `feat: package windows prerequisites`
5. `test: validate windows hardware web flow`
6. `feat: produce windows installer zip rc`

Tags are only allowed after their validation evidence exists:

```text
win-web-source-startup
win-web-local-config
win-web-launcher
win-web-prereqs
win-web-hardware-validated
win-web-installer-rc1
```
