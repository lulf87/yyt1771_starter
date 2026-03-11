# Task-008：Web 交互架构冻结与跨平台运行配置

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目目录树
- 当前项目中的 `src/` 与 `configs/`

## 任务目标

把项目正式切换到“**浏览器 Web 交互 + 后端服务**”路线，并冻结跨平台运行边界：

- Mac：开发、测试、回放、mock 联调
- Windows：最终接真实设备并运行后端服务
- 浏览器：最终交互入口

这轮先做**架构冻结和最小骨架**，不要直接实现复杂页面和实时采集线程。

---

## 背景约束

1. 最终交互形式不是桌面 GUI，而是 Web。
2. 现有代码主链已经有：
   - camera / temp / plc
   - vision / sync / curve
   - workflow / storage / report
3. 需要在不破坏既有模块边界的前提下，引入一个 Web 层。
4. 以后必须同时支持：
   - Mac 上开发调试
   - Windows 上最终使用
5. 不能让 Web 层直接吞掉业务边界。

---

## 本轮要做的事

### 1. 正式批准一个新的 `src/webapp/` 模块

请更新 `docs/architecture_lock.md` 和 `docs/module_map.md`，把 `src/webapp/` 作为批准的新一级模块加入架构。

建议目录：

```text
src/
  webapp/
    __init__.py
    app.py
    deps.py
    schemas.py
    routes/
      __init__.py
      health.py
```

职责边界：
- `webapp` 只负责 HTTP 路由、请求/响应模型、依赖注入
- `webapp` 可以依赖：
  - `core`
  - `workflow`
  - `storage`
  - `report`
- `webapp` 不应直接依赖：
  - `camera`
  - `temp`
  - `plc`
  - `vision`
  - `curve`
  - `sync`

也就是说，设备访问和算法调用仍通过 `workflow` 或后续服务层中转，不要让路由函数直接读 RTSP/Modbus。

### 2. 增加最小 Web 骨架

使用 FastAPI 建一个最小可运行骨架，至少包含：

- `create_app()` 工厂
- `/health` 路由，返回基本健康信息
- 可选：`/api/system/profile` 返回当前配置 profile

不要实现复杂业务 API，不要实现前端框架，不要接入实时流。

### 3. 增加跨平台运行配置

在 `configs/` 下新增三份配置文件：

```text
configs/
  dev_mock.yaml
  dev_lab.yaml
  prod_win.yaml
```

语义约束：

- `dev_mock.yaml`
  - Mac 默认开发模式
  - 全 mock 或离线回放
- `dev_lab.yaml`
  - 真实 RTSP / 真实 Modbus 温度 / PLC 可 mock
  - 用于实验室联调
- `prod_win.yaml`
  - Windows 运行模式
  - 真实相机 / 真实温度 / 真实 PLC / SQLite 路径 / 日志路径

这轮可以只做最小配置内容，不要求全部字段一次到位。

### 4. 增加最小 Web 测试

至少新增：

```text
tests/webapp/test_health.py
```

覆盖：
- app 可创建
- `/health` 返回 200
- 响应中包含最小健康信息，例如 app 名称、mode/profile、status

如你实现了 `/api/system/profile`，请补对应测试。

---

## 允许修改

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `src/webapp/**`
- `configs/dev_mock.yaml`
- `configs/dev_lab.yaml`
- `configs/prod_win.yaml`
- `tests/webapp/**`
- 如确有必要，可少量修改 `pyproject.toml` 或依赖声明文件

## 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要改现有 `camera/temp/plc/vision/curve/sync` 的业务语义
- 不要直接实现复杂业务会话接口
- 不要做前端工程化拆分，不要新增 `frontend/` 顶层目录
- 不要引入 Electron / Qt / 桌面 GUI

---

## 设计要求

1. Web 交互必须保持“浏览器是前端、Python 是后端”。
2. 路由层不要直接操作设备适配器。
3. 继续保持 `src.*` 绝对导入。
4. 继续遵守“先冻结边界，再加功能”。
5. Mac 与 Windows 都应可从源码运行同一套后端代码；最终仅运行配置不同。
6. 尽量让本轮代码在没有真实设备时也能运行测试。

---

## 建议实现方向

- FastAPI app factory：
  - `create_app(profile: str = "dev_mock")`
- `GET /health`：
  - 返回：
    - `status`
    - `app`
    - `profile`
- 如果需要配置解析，可以先做最小版本，不必一次做成完整 settings 系统。

---

## 验收命令

至少运行：

```bash
pytest -q
```

如果实现了 app，可补充：

```bash
python - <<'PY'
from src.webapp.app import create_app
app = create_app()
print(app.title)
PY
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
