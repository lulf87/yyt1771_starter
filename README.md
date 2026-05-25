# yyt1771_starter

YY/T 1771 visual-analysis workstation baseline with:

- offline mock and replay session flows
- shared workflow / storage / report core reused across delivery shells
- Web workstation kept as the active operator-facing shell
- current `mac-finish` delivery direction centered on the Web workstation
- Windows migration now means Web-on-Windows first, not PySide6 desktop first
- replay detail visualization and workspace analysis views
- full AFAS postprocessing workspace parity with persisted analysis/export artifacts
- adjustment contract and Adjustment MVP state flow

The repository is no longer at the Task-000 scaffold stage. It now reflects the
current migration state:

- canonical requirements and plan docs have moved under `docs/requirements/`
  and `docs/plan_eng_review/`
- the shared application layer is being extracted from `webapp`
- `src.webapp.serve` is the current operator-facing shell
- the older `src/desktop_app/` PySide6 shell remains in the tree as paused
  historical / fallback work, not as the active Windows migration path

For review and current execution truth, prefer the canonical docs rather than
older browser-first wording in historical materials.

## Requirements Entry

Start here:

- [docs/requirements/requirements_overview.md](docs/requirements/requirements_overview.md)
- [docs/plan_eng_review/current_run_modes_20260524.md](docs/plan_eng_review/current_run_modes_20260524.md)
- [docs/plan_eng_review/web_on_windows_migration_status_20260525.md](docs/plan_eng_review/web_on_windows_migration_status_20260525.md)

Use those files as the current entry point for:

- project goals and phase order
- module and directory responsibilities
- current Web workstation run modes
- Windows migration boundaries for the Web workstation
- Mac Codex -> SSH -> Windows PowerShell remote-control setup
- task-by-task implementation references under the canonical docs tree

## 3 分钟跑起来

### 0. 本机 Python 选择

在这台 Mac 上，不要用裸 `python` 直接跑 OpenCV/视觉回归或启动 Web。
当前 shell 的裸 `python` 指向 miniforge base 环境，已确认会触发
`cv2` / NumPy ABI 不匹配。

从 `yyt1771_starter/` 目录运行时，推荐固定使用下面两个解释器：

```bash
# 跑 pytest / compileall / 纯项目回归
.venv/bin/python

# 启动当前 Web 工作站、真实设备、离线素材回放
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11
```

### 1. 环境准备

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\python -m pip install -e ".[dev]"
```

### 2. 启动命令

当前你实际操作的主入口是 Web 工作站：

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_lab
```

安装到虚拟环境后也有对应 console script：

```bash
yyt1771-web --profile dev_lab
```

常用 profile：

- `dev_lab`：真实相机 + 真实温控，本机联机调试用。
- `dev_lab_camera_mock_temp`：真实相机 + 模拟温控。
- `dev_offline_capture`：使用真实相机录制的灰度素材做离线 Web 回放。
- `dev_mock`：纯 mock 开发/回归，不代表真实设备采集链路。

例如离线素材回放：

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_offline_capture
```

### 2.1 Mac 快速切换模拟素材和真实设备

Mac 本机调试时，模拟素材、真实设备、真实相机 + 模拟温控之间通过
profile 切换。切换 profile 需要先停止当前 Web 服务，再用另一个
profile 重启；建议统一用 `8000` 端口，避免不同 profile 默认端口造成混乱。

先进入项目目录：

```bash
cd "/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter"
```

如果不确定旧服务是否还占着 `8000`，先停掉：

```bash
pids=$(lsof -tiTCP:8000 -sTCP:LISTEN)
[ -n "$pids" ] && kill $pids
```

真实相机 + 真实温控：

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 \
  -m src.webapp.serve \
  --profile dev_lab \
  --port 8000 \
  --open-browser
```

模拟素材离线测试：

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 \
  -m src.webapp.serve \
  --profile dev_offline_capture \
  --port 8000 \
  --open-browser
```

真实相机 + 模拟温控：

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 \
  -m src.webapp.serve \
  --profile dev_lab_camera_mock_temp \
  --port 8000 \
  --open-browser
```

也可以在当前终端里临时设置 alias，提高切换速度：

```bash
export YYT_PY="../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11"

alias yyt-stop='pids=$(lsof -tiTCP:8000 -sTCP:LISTEN); [ -n "$pids" ] && kill $pids'
alias yyt-real='yyt-stop; $YYT_PY -m src.webapp.serve --profile dev_lab --port 8000 --open-browser'
alias yyt-offline='yyt-stop; $YYT_PY -m src.webapp.serve --profile dev_offline_capture --port 8000 --open-browser'
alias yyt-real-mock-temp='yyt-stop; $YYT_PY -m src.webapp.serve --profile dev_lab_camera_mock_temp --port 8000 --open-browser'
```

之后直接运行：

```bash
yyt-offline
yyt-real
yyt-real-mock-temp
```

对应关系：

- `yyt-offline`：模拟素材离线测试。
- `yyt-real`：真实相机 + 真实温控。
- `yyt-real-mock-temp`：真实相机 + 模拟温控。

其他入口只在特定场景使用：

- 当前 Web 工作站脚本：`yyt1771-web --profile dev_lab`
- 暂停的旧桌面壳入口：`.venv/bin/python -m src.desktop_app.main --profile dev_mock --smoke-run`
- 离线素材录制工具：`../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.application.capture_camera_frames ...`
- 回归测试：`.venv/bin/python -m pytest tests/vision/test_metric_two_point_distance.py -q`

### 3. 浏览器地址

实际端口由 profile 的 `webapp.port` 决定；当前常用本机 Web 调试地址是：

```text
http://127.0.0.1:8002/
```

若 profile 使用默认端口，则也可能是：

```text
http://127.0.0.1:8000/
```

桌面壳现状：

- `src/desktop_app/` 仍保留第一版 bootstrap 和测试
- 当前 `mac-finish` 方向已暂停 PySide6/Qt 桌面壳，不再把它作为 Windows 迁移默认入口
- 后续 Windows 迁移应优先验证 Web 工作站：`python -m src.webapp.serve --profile dev_lab`

### 4. 最小可见流程

1. 打开首页。
2. 确认能看到 `Health / Profile / Mode / System Precheck`。
3. 点击 `Run Replay Session`。
4. 点击 `Open Workspace`。
5. 在 workspace 中看到 `Replay Curve`、`AFAS Analysis`、`Key Frames`、`Adjustment MVP`、`Version History`。

### 5. AFAS Workspace And Persisted Artifacts

- workspace 里的 `AFAS Analysis` 面板现在已经接通：
  - preprocessing parity
  - parameterized tangent analysis parity
  - overview chart
  - single-channel analysis chart
  - PNG export
  - Excel report export
- 当你调用这些 session 级 AFAS 接口时，结果不再只是瞬时响应，而会落到对应 session artifact 目录：
  - `afas_dataset.json`
  - `afas_analysis.json`
  - `afas_plot.png`
  - `afas_report.xlsx`
- 默认路径形如：
  - `<artifact_dir>/<session_id>/afas_dataset.json`
  - `<artifact_dir>/<session_id>/afas_analysis.json`
  - `<artifact_dir>/<session_id>/afas_plot.png`
  - `<artifact_dir>/<session_id>/afas_report.xlsx`
- 若该 session 已有 `result.json`，AFAS analysis / export 路由也会把这些 artifact refs 回填到 `result.json.artifacts`。

### 6. 当前边界

- 当前最稳定的可见链路仍是 offline mock/replay/workspace。
- live run / real camera / temporal sampling 已有更深实现，但 Windows 硬件端仍需重新验证。
- 这不是“Windows 桌面最终成品”，而是当前 Web 工作站主线的主仓库工作树。
- `configs/prod_win.yaml` 与 `desktop_app` 相关内容是历史生产/桌面迁移参考，不代表当前 `mac-finish` 可直接运行的 Windows 方案。

### 7. Camera Probe（受控单帧）

- 首页现在有 `Probe Camera` 按钮，对应 `POST /api/system/camera/probe`。
- 这个入口只做一次受控单帧探测，不会进入 workspace live。
- 现在支持两种模式：`Protocol Any` 和 `Pinned Device`。
- `Protocol Any` 允许在 `serial_number` / `ip` 为空时按协议优先探测第一台可用设备。
- `Pinned Device` 要求同时给出 `allowed_models` 和 `serial_number` 或 `ip`，用于锁定具体设备。
- 仓库默认的 [prod_win.yaml](configs/prod_win.yaml) 仍然不会提交真实现场 identity；在当前 `mac-finish` 方向下它只应视为未验收的历史生产 profile 骨架。需要真实探测时，请优先用本机 local override 填写，不要把现场身份信息提交回仓库。

### 8. Probe 失败怎么看

- `error_stage` 先告诉你失败落在哪一层，例如 `config_contract`、`sdk_runtime`、`device_discovery`、`frame_read`、`device_validation`。
- `error_code` 再给出稳定分类，例如 `SDK_IMPORT_NOT_READY`、`PINNED_IDENTITY_MISSING`、`FRAME_READ_FAILED`。
- `detail` 保留现场可读说明，但排障时优先看 `error_stage + error_code`，这样比自然语言字符串更稳定。

### 9. Probe 轻量留痕

- 每次 `POST /api/system/camera/probe` 成功或失败，都会追加一条轻量诊断记录。
- 记录只保存摘要字段：时间、profile、probe_mode、matched_by、backend/transport/sdk、命中设备信息、frame 摘要、status、error_code、error_stage、detail。
- 记录不会进入 session/workspace 业务链，也不会保存原始图像。
- 默认文件名是 `probe_diagnostics/camera_probe.jsonl`。若 profile 配了 `logging.dir`，会落在那个目录下；否则会落在本地日志目录。

## Mac 本机联机准备

1. [dev_lab.yaml](configs/dev_lab.yaml) 仍然是仓库跟踪基线，不直接提交本机联机参数。
2. 复制 [dev_lab.local.example.yaml](configs/dev_lab.local.example.yaml) 为 `configs/dev_lab.local.yaml`。
3. 在本机 local 文件里切到 `hik_gige_mvs + protocol_any`，不要把真实 `serial_number` / `ip` 提交回仓库。
4. 即使相机未上电，也可以先看首页 precheck 里的 `camera_sdk_runtime`，确认本机 MVS Python/SDK import readiness 是否就绪。
5. 真的要试一次受控探测时，再在首页点 `Probe Camera`。
