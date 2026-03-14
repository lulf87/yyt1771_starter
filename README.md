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
