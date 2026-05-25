"""Build the Windows Web workstation ZIP from a local PyInstaller app build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import zipfile

REQUIRED_PREREQ_KEYS = {"hik_mvs", "vc_redist_x64", "usb_serial"}
DEFAULT_PACKAGE_NAME = "yyt1771-windows-webstation"
APP_EXE_NAME = "yyt1771-webstation"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the YYT1771 Windows Web workstation ZIP.")
    parser.add_argument("--app-dir", type=Path, default=None, help="Existing PyInstaller one-dir app to copy into app/")
    parser.add_argument("--build-app", action="store_true", help="Run PyInstaller before assembling the ZIP")
    parser.add_argument(
        "--prereq-dir",
        type=Path,
        default=Path("../_local/yyt1771_windows_prereqs"),
        help="Local directory containing prereqs_manifest.json and official installer files",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("dist/windows"), help="Directory for staging and ZIP output")
    parser.add_argument("--package-name", default=DEFAULT_PACKAGE_NAME, help="ZIP base name")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app_dir = args.app_dir
    if args.build_app:
        app_dir = build_pyinstaller_app(output_dir=args.output_dir)
    if app_dir is None:
        raise SystemExit("--app-dir is required unless --build-app is set")
    zip_path = assemble_windows_zip(
        app_dir=app_dir,
        prereq_dir=args.prereq_dir,
        output_dir=args.output_dir,
        package_name=args.package_name,
    )
    print(zip_path)


def build_pyinstaller_app(*, output_dir: Path) -> Path:
    if sys.platform != "win32":
        raise RuntimeError("PyInstaller Windows app builds must run on Windows.")
    build_root = output_dir / "pyinstaller"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name",
        APP_EXE_NAME,
        "--collect-data",
        "src.webapp",
        "--add-data",
        f"configs{';' if sys.platform == 'win32' else ':'}configs",
        "src/webapp/serve.py",
    ]
    subprocess.run(command, check=True, cwd=Path(__file__).resolve().parents[2])
    app_dir = Path("dist") / APP_EXE_NAME
    if not app_dir.is_dir():
        raise RuntimeError(f"PyInstaller did not create expected app dir: {app_dir}")
    build_root.mkdir(parents=True, exist_ok=True)
    target = build_root / APP_EXE_NAME
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(app_dir, target)
    return target


def assemble_windows_zip(
    *,
    app_dir: Path,
    prereq_dir: Path,
    output_dir: Path,
    package_name: str = DEFAULT_PACKAGE_NAME,
) -> Path:
    app_dir = app_dir.resolve()
    prereq_dir = prereq_dir.resolve()
    output_dir = output_dir.resolve()
    if not app_dir.is_dir():
        raise FileNotFoundError(f"app directory not found: {app_dir}")
    prereq_manifest = load_prereq_manifest(prereq_dir)

    package_root = output_dir / package_name
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_dir, package_root / "app")
    copy_baseline_configs(package_root / "app")
    (package_root / "app" / "launcher").mkdir(parents=True, exist_ok=True)
    _write_text(package_root / "install_yyt1771.bat", INSTALL_BAT)
    _write_text(package_root / "start_yyt1771.bat", START_BAT)
    _write_text(package_root / "stop_yyt1771.bat", STOP_BAT)
    _write_text(package_root / "安装与启动说明.md", INSTALL_GUIDE)
    _write_text(package_root / "app" / "launcher" / "install_yyt1771.ps1", INSTALL_PS1)
    _write_text(package_root / "app" / "launcher" / "install_prereqs.ps1", INSTALL_PREREQS_PS1)
    _write_text(package_root / "app" / "launcher" / "start_yyt1771.ps1", START_PS1)
    _write_text(package_root / "app" / "launcher" / "stop_yyt1771.ps1", STOP_PS1)

    prereq_output_dir = package_root / "prereqs"
    prereq_output_dir.mkdir(parents=True, exist_ok=True)
    packaged_entries = []
    for entry in prereq_manifest["entries"]:
        source = prereq_dir / entry["filename"]
        target = prereq_output_dir / entry["filename"]
        shutil.copy2(source, target)
        packaged = dict(entry)
        packaged["sha256"] = sha256_file(target)
        packaged_entries.append(packaged)
    prereq_runtime_manifest = {"entries": packaged_entries}
    _write_json(prereq_output_dir / "manifest.json", prereq_runtime_manifest)

    package_manifest = {
        "name": package_name,
        "profile": "dev_lab",
        "camera_identity_policy": {
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
        },
        "prereqs": [{"key": item["key"], "filename": item["filename"], "sha256": item["sha256"]} for item in packaged_entries],
    }
    _write_json(package_root / "manifest.json", package_manifest)

    zip_path = output_dir / f"{package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_root.parent))
    return zip_path


def copy_baseline_configs(app_root: Path) -> None:
    source_config_dir = Path(__file__).resolve().parents[2] / "configs"
    target_config_dir = app_root / "configs"
    target_config_dir.mkdir(parents=True, exist_ok=True)
    for source in source_config_dir.glob("*.yaml"):
        if source.name.endswith(".local.yaml"):
            continue
        shutil.copy2(source, target_config_dir / source.name)


def load_prereq_manifest(prereq_dir: Path) -> dict[str, Any]:
    manifest_path = prereq_dir / "prereqs_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Prerequisite manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("prereqs_manifest.json must contain an entries list")
    normalized_entries = []
    seen_keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each prerequisite entry must be an object")
        key = str(entry.get("key", "")).strip()
        filename = str(entry.get("filename", "")).strip()
        label = str(entry.get("label", key)).strip() or key
        install_args = entry.get("install_args", [])
        if isinstance(install_args, str):
            install_args = [install_args]
        if not key or not filename:
            raise ValueError("Each prerequisite entry requires key and filename")
        if key in seen_keys:
            raise ValueError(f"Duplicate prerequisite key: {key}")
        if not (prereq_dir / filename).is_file():
            raise FileNotFoundError(f"Prerequisite file listed in manifest was not found: {prereq_dir / filename}")
        seen_keys.add(key)
        normalized_entries.append(
            {
                "key": key,
                "label": label,
                "filename": filename,
                "install_args": [str(item) for item in install_args],
            }
        )
    missing_keys = REQUIRED_PREREQ_KEYS - seen_keys
    if missing_keys:
        raise ValueError(f"Missing required prerequisite entries: {', '.join(sorted(missing_keys))}")
    return {"entries": normalized_entries}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\r\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


INSTALL_BAT = r"""
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\launcher\install_yyt1771.ps1"
if errorlevel 1 pause
"""

START_BAT = r"""
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\launcher\start_yyt1771.ps1"
if errorlevel 1 pause
"""

STOP_BAT = r"""
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\launcher\stop_yyt1771.ps1"
if errorlevel 1 pause
"""

INSTALL_PS1 = r"""
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LocalRoot = Join-Path $env:LOCALAPPDATA "YYT1771"
$ConfigDir = Join-Path $LocalRoot "configs"
$DataDir = Join-Path $LocalRoot "data"
$ArtifactDir = Join-Path $LocalRoot "artifacts"
$LogDir = Join-Path $LocalRoot "logs"
New-Item -ItemType Directory -Force $ConfigDir, $DataDir, $ArtifactDir, $LogDir | Out-Null

& (Join-Path $PSScriptRoot "install_prereqs.ps1")

$ConfigPath = Join-Path $ConfigDir "dev_lab.local.yaml"
if (-not (Test-Path $ConfigPath)) {
@"
platform: windows
adapters:
  camera: hik_gige_mvs
  temp: lu92xx_modbus_rtu
  plc: mock
camera:
  transport: gige_vision
  sdk: hik_mvs
  probe_mode: protocol_any
  allowed_models: []
  serial_number: ""
  ip: ""
temp:
  backend: lu92xx_modbus_rtu
  serial:
    port: ""
storage:
  sqlite_path: $($DataDir.Replace('\','/'))/dev_lab.sqlite3
  artifact_dir: $($ArtifactDir.Replace('\','/'))
logging:
  dir: $($LogDir.Replace('\','/'))
"@ | Set-Content -Encoding UTF8 $ConfigPath
}

Write-Host "YYT1771 installation prepared."
Write-Host "Local config: $ConfigPath"
"""

INSTALL_PREREQS_PS1 = r"""
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PrereqDir = Join-Path $PackageRoot "prereqs"
$ManifestPath = Join-Path $PrereqDir "manifest.json"
if (-not (Test-Path $ManifestPath)) {
  throw "Missing prerequisite manifest: $ManifestPath"
}
$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

function Test-MvsInstalled {
  $candidates = @(
    "${env:ProgramFiles(x86)}\MVS\Development\Samples\Python\MvImport\MvCameraControl_class.py",
    "$env:ProgramFiles\MVS\Development\Samples\Python\MvImport\MvCameraControl_class.py"
  )
  return [bool]($candidates | Where-Object { Test-Path $_ } | Select-Object -First 1)
}

function Test-VcRedistInstalled {
  $paths = @(
    "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
  )
  foreach ($path in $paths) {
    if (Test-Path $path) {
      $item = Get-ItemProperty $path
      if ($item.Installed -eq 1) { return $true }
    }
  }
  return $false
}

function Test-UsbSerialReady {
  try {
    $ports = Get-PnpDevice -Class Ports -Status OK -ErrorAction Stop
    return [bool]($ports | Where-Object { $_.FriendlyName -match "USB|Serial|COM" } | Select-Object -First 1)
  } catch {
    return $false
  }
}

function Invoke-PrereqInstaller($Entry) {
  $installer = Join-Path $PrereqDir $Entry.filename
  if (-not (Test-Path $installer)) { throw "Missing prerequisite installer: $installer" }
  if ($Entry.sha256) {
    $actualHash = (Get-FileHash -Algorithm SHA256 -Path $installer).Hash.ToLowerInvariant()
    if ($actualHash -ne $Entry.sha256.ToLowerInvariant()) {
      throw "SHA256 mismatch for $($Entry.filename). Expected $($Entry.sha256), got $actualHash."
    }
  }
  $args = @()
  if ($Entry.install_args) { $args = @($Entry.install_args) }
  Write-Host "Installing prerequisite: $($Entry.label)"
  Start-Process -FilePath $installer -ArgumentList $args -Wait
}

foreach ($entry in $Manifest.entries) {
  $needed = $false
  switch ($entry.key) {
    "hik_mvs" { $needed = -not (Test-MvsInstalled) }
    "vc_redist_x64" { $needed = -not (Test-VcRedistInstalled) }
    "usb_serial" { $needed = -not (Test-UsbSerialReady) }
    default { $needed = $true }
  }
  if ($needed) {
    Invoke-PrereqInstaller $entry
  } else {
    Write-Host "Prerequisite already present: $($entry.label)"
  }
}
"""

START_PS1 = r"""
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$AppRoot = Join-Path $PackageRoot "app"
$LocalRoot = Join-Path $env:LOCALAPPDATA "YYT1771"
$ConfigDir = Join-Path $LocalRoot "configs"
$LogDir = Join-Path $LocalRoot "logs"
$PidPath = Join-Path $LocalRoot "yyt1771-web.pid"
$StdoutLogPath = Join-Path $LogDir "yyt1771-web.out.log"
$StderrLogPath = Join-Path $LogDir "yyt1771-web.err.log"
$Port = 8000
$Url = "http://127.0.0.1:$Port/"
$HealthUrl = "http://127.0.0.1:$Port/health"
New-Item -ItemType Directory -Force $ConfigDir, $LogDir | Out-Null

function Test-Health {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 2
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

if (Test-Health) {
  Start-Process $Url
  exit 0
}

$exe = Get-ChildItem -Path $AppRoot -Filter "yyt1771-webstation.exe" -Recurse -File | Select-Object -First 1
if ($exe) {
  $command = $exe.FullName
  $arguments = @("--profile", "dev_lab", "--host", "127.0.0.1", "--port", "$Port")
} else {
  $python = Join-Path $AppRoot ".venv\Scripts\python.exe"
  if (-not (Test-Path $python)) { throw "Cannot find yyt1771-webstation.exe or app\.venv\Scripts\python.exe" }
  $command = $python
  $arguments = @("-m", "src.webapp.serve", "--profile", "dev_lab", "--host", "127.0.0.1", "--port", "$Port")
}

$env:YYT1771_PROJECT_ROOT = $AppRoot
$env:YYT1771_USER_CONFIG_DIR = $ConfigDir
$process = Start-Process -FilePath $command -ArgumentList $arguments -WorkingDirectory $AppRoot -WindowStyle Minimized -RedirectStandardOutput $StdoutLogPath -RedirectStandardError $StderrLogPath -PassThru
Set-Content -Encoding ASCII -Path $PidPath -Value $process.Id

for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Milliseconds 500
  if (Test-Health) {
    Start-Process $Url
    exit 0
  }
}

throw "YYT1771 Web server did not become healthy. See logs: $StdoutLogPath and $StderrLogPath"
"""

STOP_PS1 = r"""
$ErrorActionPreference = "Stop"
$LocalRoot = Join-Path $env:LOCALAPPDATA "YYT1771"
$PidPath = Join-Path $LocalRoot "yyt1771-web.pid"
if (-not (Test-Path $PidPath)) {
  Write-Host "YYT1771 Web server PID file was not found."
  exit 0
}
$pidValue = Get-Content $PidPath -Raw
if ($pidValue -match "^\s*(\d+)\s*$") {
  $process = Get-Process -Id ([int]$Matches[1]) -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $process.Id -Force
    Write-Host "Stopped YYT1771 Web server process $($process.Id)."
  }
}
Remove-Item $PidPath -Force -ErrorAction SilentlyContinue
"""

INSTALL_GUIDE = r"""
# YYT1771 Windows Web 工作站安装与启动说明

## 1. 解压

请把整个 ZIP 解压到本机固定目录，例如：

```text
C:\YYT1771
```

不要只拖出其中某一个文件运行。

## 2. 安装依赖

双击：

```text
install_yyt1771.bat
```

安装脚本会按需检查并安装 `prereqs/` 内的官方安装器：

- Hik MVS SDK / 驱动
- Microsoft Visual C++ x64 Runtime
- USB 转串口驱动

如果某个官方安装器弹出自己的安装界面，请按默认推荐步骤完成。

## 3. 启动

双击：

```text
start_yyt1771.bat
```

脚本会启动 Web 工作站并自动打开浏览器。用户不需要打开终端，也不需要手动输入网址。

## 4. 选择温控串口

进入页面后，在温度设置区域刷新串口，选择 LU92XX 对应 COM 口，点击“使用并读取”。
读取成功后，COM 口会保存到本机用户配置：

```text
%LOCALAPPDATA%\YYT1771\configs\dev_lab.local.yaml
```

## 5. 停止

双击：

```text
stop_yyt1771.bat
```

日志位于：

```text
%LOCALAPPDATA%\YYT1771\logs
```
"""


if __name__ == "__main__":
    main()
