# Live Run Implementation Breakdown v1

Related design doc: [office_hours_requirement_baseline_v1.md](../requirements/office_hours_requirement_baseline_v1.md)
Primary lock doc: [live_run_plan_lock_v1.md](./live_run_plan_lock_v1.md)
Companion temporal-sampling lock doc: [live_capture_temporal_sampling_plan_lock_v1.md](./live_capture_temporal_sampling_plan_lock_v1.md)
Related execution plan: [live_run_execution_plan_v1.md](./live_run_execution_plan_v1.md)
Related test plan: [live_run_test_plan_v1.md](./live_run_test_plan_v1.md)
Status: READY_FOR_TASK_SPLIT_AFTER_OFFICE_HOURS_SYNTHESIS

## Purpose

这份文档把已经锁定的 live run 方案继续收敛成“可以直接开工”的实施拆解。

它回答 5 个问题：

1. 先做什么，后做什么
2. 每一阶段允许改哪些模块
3. 每一阶段必须交付什么契约
4. 每一阶段怎么验收
5. 哪些问题可以后置，哪些问题会阻塞下一阶段

这份 breakdown 不替代 execution plan；它是 execution plan 的施工版。

---

## Global locks

在所有阶段里，都必须保持下面这些锁定不变：

1. `workflow` 不直接写 LU92XX 寄存器，不处理 CRC，不决定具体串口报文。
2. `curve` 负责 AFAS 结果计算，`workflow` 只消费结果。
3. `webapp/routes` 只做 HTTP、schema、依赖注入和状态映射，不直接碰硬件细节。
4. `temp` 的 public semantic 保持：
   - `set_target_temperature(celsius)`
   - `set_output_power_percent(percent)`
   - `start_output()`
   - `stop_output()`
   - `read()`
5. `target_temperature_celsius` 继续是 API 语义，即使底层 LU92XX 的旧系统命名更像“停止温度”。
6. `264` 作为当前温度默认寄存器候选，`258` 作为 profile 可覆盖候选；不允许在代码里分叉两套设备逻辑。
7. `output_power_percent` 属于当前 run 已确认的温控设置包；profile 只能提供默认值，不能覆盖已确认的 runtime 输入。
8. 首版 live run 继续采用单协调循环，不引入 WebSocket、事件总线和多进程采集。
9. `Stop Live Preview` 的产品语义按 freeze-last-frame 锁定，不再允许“停流即清空画面”。
10. `metric_box` 在 UI 语义上视为 `观测窗口 / 测试范围`，并要求与 ROI、A/B 点一起支持图上可视化编辑。
11. `setup preview fluidity` 与 `measurement cadence` 是并行但分离的 workstream，不允许再合并成单一“刷新率”目标。
12. `50 Hz synchronized measurement` 是 cadence workstream 的 baseline gate；`100 Hz` 只作为 stretch gate。
13. `analysis_roi` / `metric_box` 不能代替 measurement-mode 的 camera-side acquisition ROI。

---

## Deliverable shape

最终需要形成 5 层交付物：

1. 契约层
   - state enum
   - data model
   - typed config
   - schema
2. 编排层
   - live run coordinator
   - state transition
   - finalize pipeline
3. 设备层
   - camera adapter reuse
   - LU92XX temp adapter
   - vision extractor
4. 结果层
   - AFAS adapter
   - result summary
   - evidence package
5. 验证层
   - unit tests
   - integration tests
   - API tests
   - bench validation

---

## Temporal sampling follow-up workstream

下面这组任务是对现有 Phase 1-5 的补充，不替代原 phase 编号。

### TS-1. Contract split and rate-report skeleton

目标：

- 把 `camera_resulting_fps`、`preview_display_fps`、`measurement_sample_hz`、`artifact_capture_hz` 正式写进 contract / schema / artifact
- 补 `capture_mode` 读取契约

允许改动：

- `src/core/**`
- `src/webapp/schemas.py`
- `src/webapp/routes/live_run.py`
- `src/storage/**`
- `tests/architecture/**`
- `tests/webapp/**`

验收：

- rate concepts 不再用单一“刷新率”混写
- API 和 artifact 可表达 achieved values

### TS-2. Camera measurement profile plumbing

目标：

- setup preview / measurement 两套相机 profile 进入 typed config 和 adapter
- 支持 camera-side acquisition ROI / reduced readout wiring

允许改动：

- `src/core/config_models.py`
- `src/webapp/config.py`
- `src/camera/**`
- `tests/camera/**`
- `tests/webapp/test_config_loader.py`

验收：

- measurement-mode profile 能被 workflow 请求并应用
- resulting facts 可被回读

### TS-3. Workflow cadence accounting

目标：

- 在 live coordinator 中记录 measurement timestamps、cadence summary 和 achieved-rate reporting

允许改动：

- `src/workflow/live_run.py`
- `src/sync/**`
- `src/storage/**`
- `src/report/**`
- `tests/workflow/**`
- `tests/storage/**`

验收：

- `telemetry.csv` / `result.json` / detail API 均可读出 achieved measurement cadence

### TS-4. Setup preview optimization

目标：

- 评估并实现更轻的 setup preview 传输路径
- 提升 setup 可操作性，但不把它伪装成 measurement cadence 完成

允许改动：

- `src/webapp/static/**`
- `src/webapp/templates/**`
- `src/webapp/routes/live_run.py`
- `tests/webapp/**`

验收：

- setup preview 操作流明显改善
- UI 对 preview 与 measurement 的表达不混淆

### TS-5. 50 Hz bench validation

目标：

- 真机验证 `>= 50 Hz synchronized measurement`

依赖：

- TS-1
- TS-2
- TS-3

验收：

- 真实 bench evidence 可证明 achieved rate、profile、时间基准和温度同步

### TS-6. 100 Hz stretch review

目标：

- 基于 TS-5 bench 结果决定是否值得冲 `100 Hz`

锁定：

- TS-6 不是当前实现承诺

---

## Phase breakdown

## Phase 1: Contract skeleton and state freeze

### Goal

先把 live run 的“骨架接口”冻结，避免后面一边做功能一边返工 API 和模型。

### Primary output

- 独立的 live run 状态枚举
- live run draft / definition 数据模型
- live run route skeleton
- typed config section skeleton
- in-memory registry / dependency entry

### Target files

- `src/core/enums.py`
- `src/core/models.py`
- `src/core/contracts.py`
- `src/core/config_models.py`
- `src/webapp/config.py`
- `src/webapp/deps.py`
- `src/webapp/schemas.py`
- `src/webapp/routes/live_run.py`
- `src/webapp/app.py`
- `tests/webapp/**`
- `tests/architecture/**`

### Required decisions

1. 新增 `LiveRunState`，不污染现有 `SessionState`
2. 冻结 `MeasurementDefinition`
3. 冻结 `RunDraftRecord`
4. 冻结 `TempControllerPort`
5. 冻结 `POST /api/runs`、`GET /api/runs/{run_id}`、`PUT /api/runs/{run_id}/definition`

### Acceptance criteria

- 可以创建 run draft
- 可以读取 run draft
- 可以写入 measurement definition
- definition 不完整时不会误进入 `run_ready`
- route 层没有直接依赖 `camera/temp/vision/curve`

### Test minimum

- `tests/webapp/test_live_run_api.py`
  - create
  - get detail
  - update definition
  - invalid payload
- `tests/architecture/`
  - import boundary check

### Blocking rules

这一阶段不依赖真实设备，也不依赖 LU92XX 台架。

### Notes

当前阶段的首个任务入口应直接以本文件和
[live_run_execution_plan_v1.md](./live_run_execution_plan_v1.md) 为准。

---

## Phase 2: Preview, measurement definition, and run gating

### Goal

把“创建 run”推进到“可定义测量区域并进入 run_ready”，但仍然不接真实结果计算。

### Primary output

- preview frame 获取路径
- measurement definition 完整校验
- auto-detect suggestion API
- run gating 状态推进

### Target files

- `src/workflow/live_run.py`
- `src/core/models.py`
- `src/webapp/schemas.py`
- `src/webapp/routes/live_run.py`
- `src/webapp/templates/**`
- `src/webapp/static/**`
- `tests/workflow/test_live_run_state_machine.py`
- `tests/webapp/test_live_run_api.py`
- `tests/webapp/test_local_visible_live_setup.py`

### Required decisions

1. `preview_ready -> definition_editing -> run_ready` 的状态推进要稳定
2. `POST /api/runs/{run_id}/preview/frame` 只返回最小预览结果，不扩散成图像流协议
3. `POST /api/runs/{run_id}/definition/auto-detect` 负责给出建议点和建议框，但不锁定最终定义
4. definition 的“自动建议 + 手动微调”必须使用同一套 `MeasurementDefinition` 结构
5. preview stop / freeze / restart 的生命周期必须无刷新可重复使用
6. ROI、观测窗口、A/B 点必须有图上可见的 overlay 语义，而不只是表单输入

### Acceptance criteria

- 预览图可取回
- stop preview 后最后一帧仍保留，可继续做定义
- 同一 run 可完成 `start preview -> freeze -> restart preview`，无需刷新页面
- definition 必填字段有明确校验错误
- auto-detect 返回的建议点位落在 metric box 内
- ROI、观测窗口、A/B 点都可在图上被看见并被操作
- 未完成定义时 `start` 不可用
- 已锁定定义时状态可以推进到 `run_ready`

### Test minimum

- API:
  - preview frame
  - definition auto-detect
  - definition validation
  - run gating
- Browser:
  - preview visible
  - preview freeze / restart visible
  - ROI / metric box / A-B overlays visible
  - invalid definition cannot submit

### Blocking rules

可以使用 fake camera / fake vision，不要求真实设备。

---

## Phase 3: AFAS adapter and result contract first

### Goal

先把结果链路固定下来，避免硬件接入后才发现 `SyncPoint -> AFAS -> result` 契约不对。

### Primary output

- `SyncPoint` 到 AFAS 输入的适配层
- `As/Af` 结果结构
- result summary / artifact contract
- result unavailable 的失败语义

### Target files

- `src/curve/**`
- `src/core/models.py`
- `src/storage/**`
- `src/report/**`
- `src/webapp/schemas.py`
- `tests/curve/test_afas_adapter.py`
- `tests/storage/test_live_run_artifacts.py`

### Required decisions

1. `workflow` 只传入时序数据，不实现 AFAS 细节
2. 结果为空、点数不足、温度缺失都要变成显式失败语义
3. `result.json`、`definition.json`、`telemetry.csv`、`events.jsonl` 的 artifact 结构先冻结

### Acceptance criteria

- 给定确定性的 `SyncPoint` 序列，可以稳定产出 `As/Af`
- 数据不足时返回明确失败原因，而不是空值静默成功
- artifact contract 在测试中可读、可校验

### Test minimum

- AFAS success
- insufficient points
- missing temperature
- invalid metric
- artifact write/readback assertions

### Blocking rules

这一阶段不依赖 LU92XX 真机，可以完全使用 fake telemetry。

---

## Phase 4: Live run coordinator with mock temp first

### Goal

用 fake temp / fake camera / fake vision 把单循环 live run 编排打通，先验证状态流和 finalize，而不是先上真硬件。

### Primary output

- `workflow.live_run` 单协调循环
- 状态迁移与 stop / abort / fail 语义
- telemetry 聚合
- finalize result + artifact write

### Target files

- `src/workflow/live_run.py`
- `src/sync/**`
- `src/storage/**`
- `src/webapp/routes/live_run.py`
- `tests/workflow/test_live_run.py`
- `tests/workflow/test_live_run_state_machine.py`
- `tests/webapp/test_live_run_api.py`

### Required decisions

1. tick 内执行顺序固定为：
   - `camera.read_frame()`
   - `temp.read()`
   - `vision.extract()`
   - `sync.aggregate()`
2. `aborted` 只用于用户停止或 guard stop
3. `failed` 用于基础设施、协议、存储和 finalize 错误
4. `invalidated` 用于测量链路质量失效

### Acceptance criteria

- completed run 可走完全链
- user stop 走 `running -> stopping -> aborted`
- tracking invalidation 语义可见
- finalize failure 不会伪装成 completed

### Test minimum

- completed run
- temp read failure during running
- tracking invalidation during running
- finalize failure
- user stop path

### Blocking rules

不依赖真实硬件，但需要 Phase 1-3 契约已经冻结。

---

## Phase 5: LU92XX temp adapter with profile-driven defaults

### Goal

在不破坏上层契约的前提下，把真实温控设备接入 `temp` 边界。

### Primary output

- `LU92XXModbusRtuController`
- profile-driven register map
- serial config loader
- temp adapter unit tests

### Target files

- `src/temp/lu92xx_modbus_rtu_controller.py`
- `src/temp/modbus_temp.py`
- `src/core/config_models.py`
- `src/webapp/config.py`
- `configs/**`
- `tests/temp/test_lu92xx_modbus_rtu_controller.py`

### Locked config defaults

- `backend: lu92xx_modbus_rtu`
- `protocol: modbus_rtu`
- `slave_address: 1`
- `serial.baudrate: 19200`
- `serial.data_bits: 8`
- `serial.parity: N`
- `serial.stop_bits: 1`
- `register_map.target_or_stop_value.start_address: 0`
- `register_map.target_or_stop_value.encode_scale: 10.0`
- `register_map.output_power.start_address: 4`
- `register_map.output_power.encode_scale: 256.0`
- `register_map.process_value.start_address: 264`
- `register_map.process_value.decode_scale: 0.1`
- `control.start_output_mode: power_nonzero`
- `control.default_control_mode: manual`
- `control.default_power_percent: 100.0`

### Required decisions

1. `258` 只能作为 profile override，不进入 adapter 分支逻辑
2. `set_target_temperature()` 始终接收摄氏度 float，不暴露寄存器语义
3. `set_output_power_percent()` 必须接收 operator 已确认的当前 run 功率值，而不是隐藏的 profile-only 启动默认值
4. `stop_output()` 必须是显式零功率或设备定义的停止语义，不允许“什么也不做”

### Acceptance criteria

- adapter 可以按默认 profile 构造
- `read()` 能把寄存器值正确缩放为摄氏度
- `set_target_temperature()` 正确编码 reg `0`
- `set_output_power_percent()` 正确编码 reg `4`
- `start_output()` 只使用当前 run 已确认的设置
- `stop_output()` 正确写零
- `258` override 可通过配置生效

### Test minimum

- reg `0` x10 encode
- reg `4` x256 encode
- reg `264` x10 decode
- `258` override
- bad CRC / timeout / exception code path
- already-stopped edge case

### Blocking rules

这一阶段可以在无真机条件下完成大部分实现，但不能宣布“真机 ready”。

---

## Phase 6: Bench validation and profile lock

### Goal

用真实 LU92XX 台架裁决剩余设备语义冲突，把 profile 从“高置信默认”升级成“已验证配置”。

### Primary output

- `264` vs `258` 裁决结论
- reg `0` 的业务命名结论
- reg `4` 启停语义确认
- 现场串口参数与从站地址确认
- 已验证 profile 样例

### Validation checklist

1. 读取当前温度，确认 `264` 或 `258`
2. 写入目标温度，确认 reg `0` 的缩放与设备行为
3. 执行启动，确认是否依赖 reg `4` 非零功率
4. 执行停止，确认 reg `4 = 0` 是否足够
5. 验证 `19200 / 8N1 / slave 1` 是否与现场一致

### Acceptance criteria

- 至少一个 bench profile 完整跑通
- 不再把 `264/258` 作为代码层 open question
- 温控 adapter 默认值和现场 profile 的关系清晰记录

### Test minimum

- bench log
- profile snapshot
- result artifact sample

### Blocking rules

这一阶段阻塞“真机可用”声明，但不阻塞前面 mock 链路完成。

---

## Phase 7: Result package and workspace integration

### Goal

把 live run 的结果真正接进历史与工作台，而不是只停留在 API 可用。

### Primary output

- workspace 中的 live run result view
- 历史记录可见 live run
- result / evidence package 可追溯

### Target files

- `src/webapp/routes/**`
- `src/webapp/templates/**`
- `src/webapp/static/**`
- `src/storage/sqlite_repo.py`
- `tests/webapp/**`

### Required decisions

1. live run 与 replay 在 workspace 中共享哪些组件
2. result view 优先展示哪些字段
3. artifact 链接如何暴露但不泄露内部实现细节

### Acceptance criteria

- live run 完成后能在历史中找到
- workspace 可查看结果与证据引用
- result not ready / result failed 的 UI 语义清晰

### Test minimum

- API result retrieval
- history listing
- browser visible result panel

### Blocking rules

依赖前面阶段已能产出稳定 artifact 和 summary。

---

## Cross-phase dependency map

```text
Phase 1 -> Phase 2 -> Phase 4 -> Phase 7
     \        \        /
      \        -> Phase 3
       \
        -> Phase 5 -> Phase 6
```

解释：

- Phase 1 是所有后续阶段的基础。
- Phase 2 和 Phase 3 可以并行推进，但都要建立在 Phase 1 契约冻结之后。
- Phase 4 需要消费 Phase 2 的 definition/gating 和 Phase 3 的 result contract。
- Phase 5 可以在 Phase 1 之后启动，但真机闭环要等 Phase 6。
- Phase 7 只应在 Phase 4 和结果契约稳定后进入。

---

## Suggested task split

如果后续还需要继续拆分执行单元，推荐按下面的粒度切：

1. Task-A: live run Phase 1 contracts and route skeleton
2. Task-B: preview frame + definition validation + auto-detect
3. Task-C: AFAS adapter + result contract + artifact schema
4. Task-D: live coordinator + stop/abort/fail state flow
5. Task-E: LU92XX Modbus RTU adapter + profile defaults
6. Task-F: bench validation and profile lock record
7. Task-G: workspace/history/result integration

每个 task 都应包含：

- 必读文档
- 允许修改范围
- 禁止修改范围
- required tests
- done criteria

---

## Done definition

只有当下面这些条件同时满足时，才可以认为 live run implementation plan 已经真正进入可执行状态：

1. Phase 1-5 都有清晰的代码落点和测试落点
2. Phase 6 的 bench 验证清单已经单独记录
3. Phase 7 没有提前把 UI 需求和硬件接入混在一起
4. 所有 open questions 都明确落到了某一阶段，而不是停留在“以后再看”

当前结论：

- 这份 breakdown 可以直接作为后续 task 拆分基线
- `LU92XX` 相关剩余风险已经被收敛到 Phase 6
- live run 的主链实施顺序已经足够稳定，不需要再做一次架构层重排
