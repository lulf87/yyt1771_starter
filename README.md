# yyt1771_starter

YY/T 1771 visual-analysis workstation baseline with:

- offline mock and replay session flows
- Web API and browser workspace as the primary interaction route
- replay detail visualization and workspace analysis views
- adjustment contract and Adjustment MVP state flow

The repository is no longer at the Task-000 scaffold stage. It now reflects the
current Web / workspace / replay / adjustment MVP baseline while keeping live
hardware orchestration and deeper algorithm expansion out of scope for now.

## Requirements Entry

Use [docs/requirements_overview.md](docs/requirements_overview.md) as the single
entry point for:

- project goals and phase order
- module and directory responsibilities
- workspace / web UI requirement documents
- task-by-task implementation references

## 3 分钟跑起来

### 1. 环境准备

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .[dev]
```

### 2. 启动命令

```bash
python -m src.webapp.serve --profile dev_mock
```

### 3. 浏览器地址

```text
http://127.0.0.1:8000/
```

### 4. 最小可见流程

1. 打开首页。
2. 确认能看到 `Health / Profile / Mode / System Precheck`。
3. 点击 `Run Replay Session`。
4. 点击 `Open Workspace`。
5. 在 workspace 中看到 `Replay Curve`、`Key Frames`、`Adjustment MVP`、`Version History`。

### 5. 当前边界

- 当前可见的是 offline mock/replay/workspace 最小链路。
- 当前不包含 live camera / live temp / live plc orchestration。
- 这不是“真机全流程”，而是当前 scope 内的最小浏览器闭环。

### 6. Camera Probe（受控单帧）

- 首页现在有 `Probe Camera` 按钮，对应 `POST /api/system/camera/probe`。
- 这个入口只做一次受控单帧探测，不会进入 workspace live。
- 现在支持两种模式：`Protocol Any` 和 `Pinned Device`。
- `Protocol Any` 允许在 `serial_number` / `ip` 为空时按协议优先探测第一台可用设备。
- `Pinned Device` 要求同时给出 `allowed_models` 和 `serial_number` 或 `ip`，用于锁定具体设备。
- 仓库默认的 [prod_win.yaml](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/configs/prod_win.yaml) 仍然不会提交真实现场 identity；需要真实探测时，请只在本机本地填写，不要把现场身份信息提交回仓库。

### 7. Probe 失败怎么看

- `error_stage` 先告诉你失败落在哪一层，例如 `config_contract`、`sdk_runtime`、`device_discovery`、`frame_read`、`device_validation`。
- `error_code` 再给出稳定分类，例如 `SDK_IMPORT_NOT_READY`、`PINNED_IDENTITY_MISSING`、`FRAME_READ_FAILED`。
- `detail` 保留现场可读说明，但排障时优先看 `error_stage + error_code`，这样比自然语言字符串更稳定。

### 8. Probe 轻量留痕

- 每次 `POST /api/system/camera/probe` 成功或失败，都会追加一条轻量诊断记录。
- 记录只保存摘要字段：时间、profile、probe_mode、matched_by、backend/transport/sdk、命中设备信息、frame 摘要、status、error_code、error_stage、detail。
- 记录不会进入 session/workspace 业务链，也不会保存原始图像。
- 默认文件名是 `probe_diagnostics/camera_probe.jsonl`。若 profile 配了 `logging.dir`，会落在那个目录下；否则会落在本地日志目录。

## Mac 本机联机准备

1. [dev_lab.yaml](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/configs/dev_lab.yaml) 仍然是仓库跟踪基线，不直接提交本机联机参数。
2. 复制 [dev_lab.local.example.yaml](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/configs/dev_lab.local.example.yaml) 为 `configs/dev_lab.local.yaml`。
3. 在本机 local 文件里切到 `hik_gige_mvs + protocol_any`，不要把真实 `serial_number` / `ip` 提交回仓库。
4. 即使相机未上电，也可以先看首页 precheck 里的 `camera_sdk_runtime`，确认本机 MVS Python/SDK import readiness 是否就绪。
5. 真的要试一次受控探测时，再在首页点 `Probe Camera`。
