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
