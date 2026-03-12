# Task-010：最小会话 API 与结果查询接口

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的 `src/webapp/`
- 当前项目中的 `src/workflow/session.py`
- 当前项目中的 `src/storage/sqlite_repo.py`

## 任务目标

在不碰真实设备的前提下，把现有的离线能力挂到 Web 层，形成第一条最小业务闭环：

- 浏览器/HTTP 可以触发一次 **mock/offline session**
- 后端通过既有 `workflow` 执行离线 session
- 结果可通过 HTTP 查询

这轮仍然不做实时采集、不做视频流、不做前端页面，只做最小 API。

## 范围

### 允许修改

- `src/webapp/app.py`
- `src/webapp/schemas.py`
- `src/webapp/deps.py`
- `src/webapp/routes/` 下新增或修改文件
- `src/workflow/session.py`（仅限为 Web 调用补最小可复用接口，不改既有业务语义）
- `tests/webapp/**`
- 如确有必要，可少量调整 `tests/workflow/**`

### 不允许修改

- 不要改 `src/core/models.py`
- 不要改 `src/core/contracts.py`
- 不要让 `webapp` 直接依赖 `camera/temp/plc/vision/curve/sync`
- 不要引入真实 RTSP/Modbus 调用
- 不要新增新的一级模块
- 不要做前端工程化

## 本轮要做的事

### 1. 新增最小会话触发 API

建议新增路由：

- `POST /api/session/run-mock`

行为要求：

- 接口内部不要直接调设备适配器
- 使用现有 `workflow` 离线能力执行一次最小 session
- 允许你在 `workflow` 内补一个很薄的 helper，用于生成一组 mock `SyncPoint`
- 返回最小结果：
  - `session_id`
  - `state`
  - `point_count`
  - `af95`

### 2. 新增结果查询 API

建议新增路由：

- `GET /api/session/{session_id}`

行为要求：

- 从现有 `SqliteSessionRepo` 查询 summary
- 查到返回 200
- 查不到返回 404

### 3. 配置与依赖注入

- 继续通过 `app.state.runtime_config` 读取 profile
- SQLite 路径从 profile 配置里读，不要在路由里写死路径
- repo 构造可以放进 `webapp/deps.py`

### 4. schema 补齐

请在 `src/webapp/schemas.py` 中补齐：

- session summary response model
- error response model（可选，最小即可）

## 设计约束

1. `webapp` 只负责 HTTP/依赖注入/response model。
2. 业务执行仍经 `workflow`，持久化仍经 `storage`。
3. 不引入真实设备。
4. 尽量让接口在 `dev_mock` profile 下可直接跑通。
5. 继续保持 Mac 开发、Windows 使用、Web 交互这条路线不变。

## 建议实现方向

可以采用下面的最小路径：

1. 在 `workflow.session` 增加一个很薄的 mock 数据 helper，例如：
   - 生成一组 `SyncPoint(temp.metric_raw)` 数据
   - 交给现有 runner 计算 Af95
2. 在 `webapp/deps.py` 中根据 runtime config 创建 `SqliteSessionRepo`
3. `POST /api/session/run-mock`：
   - 生成 session_id
   - 调 workflow runner
   - 返回 summary
4. `GET /api/session/{session_id}`：
   - repo 查 summary
   - 找不到则 404

## 验收命令

至少运行：

```bash
pytest -q
```

如果你实现了最小 API，请补充：

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from src.webapp.app import create_app
client = TestClient(create_app(profile="dev_mock"))
resp = client.post("/api/session/run-mock")
print(resp.status_code)
print(resp.json())
PY
```

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
