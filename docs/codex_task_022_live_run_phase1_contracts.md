# Task-022：Live Run Phase 1 合同、状态与 API 骨架

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/live_run_execution_plan_v1.md`
- `docs/live_run_test_plan_v1.md`
- `docs/codex_response_contract.md`
- 当前项目中的：
  - `src/core/contracts.py`
  - `src/core/models.py`
  - `src/core/enums.py`
  - `src/core/config_models.py`
  - `src/webapp/config.py`
  - `src/webapp/app.py`
  - `src/webapp/deps.py`
  - `src/webapp/schemas.py`
  - `src/webapp/routes/session.py`
  - `tests/webapp/`
  - `tests/architecture/`

## 任务目标

把 live run 的 **第一阶段骨架** 落到仓库里，但这轮仍然不做真实采集和结果计算。

这轮要解决的是：

- live run 有独立的状态模型
- live run 有独立的 API 命名空间
- 配置契约不再继续堆匿名 dict
- measurement definition 的请求/响应结构先冻结
- 后续 Phase 2/3 能在这个骨架上继续填充，而不是返工接口

换句话说，这轮不是做“能跑完整实验”，而是做“让后续 live run 有一个不会乱掉的骨架”。

## 范围

### 允许修改

- `src/core/contracts.py`
- `src/core/models.py`
- `src/core/enums.py`
- `src/core/config_models.py`
- `src/webapp/config.py`
- `src/webapp/app.py`
- `src/webapp/deps.py`
- `src/webapp/schemas.py`
- `src/webapp/routes/` 下新增或修改文件
- `tests/webapp/**`
- `tests/architecture/**`
- 如确有必要，可少量新增 `tests/core/**`

### 不允许修改

- 不要接真实相机
- 不要接真实串口温控
- 不要引入 `WebSocket`
- 不要做 preview 图像流
- 不要做 `As/Af` 实现
- 不要改现有 replay / adjustment 业务语义
- 不要新增新的一级模块
- 不要在 route 层直接碰 `camera/temp/vision/curve`

## 本轮要做的事

### 1. 冻结 live run 的状态模型

在 `src/core/enums.py` 中补充一个独立于 `SessionState` 的 live run 状态枚举，例如：

- `created`
- `device_ready`
- `preview_ready`
- `definition_editing`
- `run_ready`
- `running`
- `stopping`
- `completed`
- `failed`
- `invalidated`
- `aborted`

要求：

- 现有 `SessionState` 不要被破坏
- replay/session summary 仍继续使用 `SessionState`
- live mutable state 使用新枚举

### 2. 冻结 live run 的核心数据契约

在 `src/core/models.py` 中为 live run 补最小数据模型。

建议新增：

- `RectRegion`
- `MetricBox`
- `PixelPoint`
- `MeasurementDefinition`
- `RunDraftRecord`

要求：

- 命名要按真实语义，不要沿用旧系统可能混乱的 `W/H`
- `MeasurementDefinition` 至少表达：
  - `analysis_roi`
  - `metric_box`
  - `point_a_px`
  - `point_b_px`
  - `foreground_polarity`
  - `threshold_mode`
  - `ignore_internal_texture`
  - `min_target_area_px`
- `RunDraftRecord` 至少表达：
  - `run_id`
  - `status`
  - `profile`
  - `preset`
  - `definition`
  - `created_at_ms`
  - `updated_at_ms`

要求：

- 本轮可以只做 dataclass，不接持久化
- 允许先把 live run draft 存在内存中

### 3. 扩展 boundary-facing contracts

在 `src/core/contracts.py` 中新增最小温控控制接口：

- `TempControllerPort`

建议方法：

- `set_target_temperature(celsius: float) -> None`
- `start_output() -> None`
- `stop_output() -> None`

要求：

- 不要破坏现有 `TempReader`
- 本轮只冻结接口，不实现真实串口

### 4. 冻结 typed config sections

在 `src/core/config_models.py` 和 `src/webapp/config.py` 中，把 live run 第一版要用到的配置从匿名 dict 收口成 typed sections。

至少覆盖：

- `camera`
  - `transport`
  - `sdk`
  - `trigger_mode`
  - `pixel_format`
  - `exposure_us`
  - `gain_db`
  - `timeout_ms`
  - `device_roi`
- `temp`
  - 先允许为空或缺省，但结构要存在
- `vision`
  - `foreground_polarity`
  - `threshold_mode`
  - `edge_threshold`
  - `ignore_internal_texture`
  - `min_target_area_px`
  - `quality_threshold`
- `analysis`
  - `engine`
  - `channel_name`
  - `as_fit_point_count`
  - `af_fit_point_count`
- `run`
  - `preview_poll_ms`
  - `telemetry_poll_ms`
  - `capture_interval_ms`
  - `stop_on_invalid_tracking`

要求：

- YAML loader 继续兼容现有 profile
- 没填的 live run 配置可以走默认值
- 不要求这轮同时把所有已有 `camera/storage/replay/logging` 字段彻底重构
- 但新增 live run 相关字段不能继续裸 dict 下沉到业务层

### 5. 新增 live run route skeleton

建议新增：

- `src/webapp/routes/live_run.py`

并在 `src/webapp/app.py` 中挂载。

这轮至少提供：

- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `PUT /api/runs/{run_id}/definition`

行为要求：

#### `POST /api/runs`

- 创建一个最小 `RunDraftRecord`
- 不连设备
- 返回：
  - `run_id`
  - `status`
  - `profile`
  - `preset`

#### `GET /api/runs/{run_id}`

- 返回当前 in-memory draft
- 找不到返回 404

#### `PUT /api/runs/{run_id}/definition`

- 接收 measurement definition
- 做最小结构校验
- 保存回 draft
- 若定义完整，则状态推进到 `run_ready` 或 `definition_editing`

要求：

- 这轮可以用 app-state 内存 registry
- 不要为了首版骨架引入 SQLite 持久化 live draft
- route 层只做 HTTP/Schema/依赖注入，不做业务细节

### 6. 新增 schemas

在 `src/webapp/schemas.py` 中补齐至少这些模型：

- `RectRegionRequest/Response`
- `MetricBoxRequest/Response`
- `PixelPointRequest/Response`
- `MeasurementDefinitionRequest/Response`
- `RunCreateRequest`
- `RunSummaryResponse`
- `RunDetailResponse`

要求：

- 命名清晰，不要和 replay detail schema 混在一起
- 结构与 `docs/live_run_execution_plan_v1.md` 保持一致
- `definition` 字段要允许 `null`，因为 run draft 初建时还未定义

### 7. 最小依赖注入

在 `src/webapp/deps.py` 中提供 live run registry / service 的最小依赖。

建议：

- 先不要上复杂 service 分层
- 允许这轮用一个很薄的 in-memory registry helper
- 但不要把这个 registry 写在 route 文件里

### 8. 补测试

至少补：

- `tests/webapp/test_live_run_api.py`
- `tests/architecture/test_model_contracts.py` 或新增 `tests/core/test_live_run_models.py`

覆盖：

- `POST /api/runs` 返回 200
- `GET /api/runs/{run_id}` 能拿到 draft
- 找不到 run 返回 404
- `PUT /api/runs/{run_id}/definition` 能保存定义
- definition 缺关键字段时返回 422
- `create_app()` 后 live run router 已挂上
- 现有 `/api/session/*` 回放接口不被破坏

## 设计约束

1. 这轮只做 Phase 1 骨架，不做设备接入。
2. `run draft` 和 `session summary` 是两类资源，不要混成一个对象。
3. 不要让 `webapp` 直接依赖 `camera/temp/vision/curve`。
4. 不要把 UI step 状态反向当作 domain state。
5. typed config 的目标是减少匿名 dict 蔓延，不是把所有历史配置一次性重写。
6. 最小 diff 优先，但不能牺牲后续 Phase 2/3 的接口稳定性。

## 建议实现路径

建议按下面顺序推进：

1. `src/core/enums.py`
   - 补 `RunStatus`
2. `src/core/models.py`
   - 补 live run dataclass
3. `src/core/contracts.py`
   - 补 `TempControllerPort`
4. `src/core/config_models.py`
   - 补 typed config sections
5. `src/webapp/config.py`
   - 把 YAML normalize 到 typed sections
6. `src/webapp/schemas.py`
   - 补 run + definition schema
7. `src/webapp/deps.py`
   - 补 in-memory draft registry
8. `src/webapp/routes/live_run.py`
   - 补 3 个骨架接口
9. `src/webapp/app.py`
   - 挂 router
10. `tests/webapp/test_live_run_api.py`
   - 补 API 契约测试

## 验收命令

至少运行：

```bash
pytest tests/webapp/test_live_run_api.py tests/webapp/test_session_api.py tests/architecture/test_model_contracts.py -q
```

建议补充：

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from src.webapp.app import create_app

client = TestClient(create_app(profile="dev_mock"))
created = client.post("/api/runs", json={"preset": "balloon"})
print(created.status_code)
print(created.json())
run_id = created.json()["run_id"]
detail = client.get(f"/api/runs/{run_id}")
print(detail.status_code)
print(detail.json())
PY
```

## 本轮完成标准

以下条件同时满足，才算完成本工单：

- live run 有独立的状态与 definition contract
- `/api/runs` 命名空间存在且能创建/查询/保存 definition
- typed config sections 已进入加载链
- replay/session 历史接口没有被破坏
- 测试覆盖 live run skeleton 的 happy path 和最小失败路径

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
