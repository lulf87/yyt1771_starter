# Task-009：Web 运行配置接入与 Profile API

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的 `src/webapp/`
- 当前项目中的 `configs/dev_mock.yaml`
- 当前项目中的 `configs/dev_lab.yaml`
- 当前项目中的 `configs/prod_win.yaml`

## 任务目标

把 Task-008 中冻结的 Web 骨架，从“只有固定 profile 字符串的最小 app”推进到“**能接入运行 profile 配置**”的状态，但仍然保持范围可控。

这轮重点不是复杂业务接口，而是：

1. 让 `webapp` 能读取 profile 配置
2. 让 API 能返回当前 profile 信息
3. 让后端启动方式同时适合：
   - macOS 开发调试
   - Windows 最终运行

---

## 本轮要做的事

### 1. 增加最小 profile 配置加载能力

建议新增：

```text
src/webapp/
  config.py
```

职责：
- 根据 profile 名称定位 `configs/<profile>.yaml`
- 读取 YAML
- 返回最小结构化结果

建议至少支持这些 profile 名称：
- `dev_mock`
- `dev_lab`
- `prod_win`

最低要求：
- 能拿到 `profile`
- 能拿到 `platform`
- 能拿到 `mode`
- 能拿到 `webapp.host`
- 能拿到 `webapp.port`
- 能拿到 `adapters`

你可以先实现为简单 dataclass / typed dict / pydantic model，任选其一；不要把它做成过重的配置系统。

### 2. 让 `create_app(...)` 真正接入配置

当前 `create_app(profile=...)` 只是把 profile 字符串挂到 `app.state`。

请改成：
- `create_app(profile: str = "dev_mock")`
- 内部加载对应配置
- 至少把以下内容挂到 `app.state`：
  - `profile_name`
  - `runtime_config`

注意：
- 仍然不要去真实连接 RTSP / Modbus / PLC
- 只是接入配置，不启动复杂后台任务

### 3. 增加 Profile 查询 API

建议新增路由：

```text
GET /api/system/profile
```

返回最小信息，例如：
- `profile`
- `platform`
- `mode`
- `webapp`
- `adapters`

不要把敏感信息设计进返回结构。

### 4. 增加最小运行入口

建议新增一个最小运行入口，例如：

```text
src/webapp/serve.py
```

目标：
- 能通过类似方式启动：

```bash
python -m src.webapp.serve --profile dev_mock
```

最低要求：
- 从参数里接收 profile
- 调 `create_app(profile=...)`
- 用 `uvicorn.run(...)` 启动

这样后面：
- Mac 上可以 `--profile dev_mock` / `dev_lab`
- Windows 上可以 `--profile prod_win`

### 5. 增加测试

至少增加：

```text
tests/webapp/test_profile_api.py
tests/webapp/test_config_loader.py
```

覆盖建议：
- `create_app("dev_mock")` 能拿到配置
- `/api/system/profile` 返回 200
- 返回内容与对应 profile 配置一致
- 读取不存在 profile 时，报出清晰异常

如果你实现了 `serve.py` 的参数解析逻辑，也可以补一个最小单测，但不是强制。

---

## 允许修改

- `src/webapp/**`
- `tests/webapp/**`
- 如确有必要，可修改 `pyproject.toml` 或依赖声明
- 如确有必要，可补充 `docs/master_control_plan.md` 中 Web 阶段描述

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要改 `camera/temp/plc/vision/curve/sync` 的业务语义
- 不要直接写真实业务会话 API
- 不要直接让路由函数访问设备适配器
- 不要新增 `frontend/` 顶层目录

---

## 设计要求

1. `src.webapp` 继续只依赖允许的模块边界。
2. 配置加载逻辑尽量轻量。
3. 继续保持 `src.*` 绝对导入。
4. Mac 与 Windows 的差异通过 profile 配置表达，而不是分叉代码。
5. 运行入口不应默认连真实设备。

---

## 验收命令

至少运行：

```bash
pytest -q
```

建议补充：

```bash
python - <<'PY'
from src.webapp.app import create_app
app = create_app("dev_mock")
print(app.state.profile_name)
print(app.state.runtime_config)
PY
```

如实现 `serve.py`，可补充：

```bash
python -m src.webapp.serve --profile dev_mock --help
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
