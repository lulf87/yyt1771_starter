# Live Run Task Status v1

Updated on 2026-03-24
Status: ACTIVE_WORKTREE_SNAPSHOT

## Purpose

这份文件回答 3 个实际问题：

1. 现在应该把哪份文档当成最新需求
2. 当前 live run 代码实际完成到了哪一步
3. 下一步应该从哪个 task 继续，才不会把已做工作推翻或和并行进程冲突

这是一份“当前工作树快照”，不是最终发布状态。

---

## Authoritative requirement baseline

### 1. Upstream design source

- [office_hours_requirement_baseline_v1.md](../requirements/office_hours_requirement_baseline_v1.md)

说明：

- 这是当前仓库内已经整合好的 `/office-hours` 需求基线
- 它把 3 份外部 design doc 的继承关系和有效结论统一收口到了 repo docs
- live run、LU92XX 和 live setup 交互语义都应以它为当前产品基线解释

### 2. Repo entrypoint

当前仓库内应该优先从 [requirements_overview.md](../requirements/requirements_overview.md) 进入。

对于 live run，实际应按下面顺序阅读：

1. [requirements_overview.md](../requirements/requirements_overview.md)
2. [office_hours_requirement_baseline_v1.md](../requirements/office_hours_requirement_baseline_v1.md)
3. [desktop_workstation_migration_requirement_v1.md](../requirements/desktop_workstation_migration_requirement_v1.md)
4. [live_capture_temporal_sampling_requirement_v1.md](../requirements/live_capture_temporal_sampling_requirement_v1.md)
5. [desktop_workstation_migration_plan_lock_v1.md](./desktop_workstation_migration_plan_lock_v1.md)
6. [desktop_workstation_migration_status_v1.md](./desktop_workstation_migration_status_v1.md)
7. [live_capture_temporal_sampling_plan_lock_v1.md](./live_capture_temporal_sampling_plan_lock_v1.md)
8. [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)
9. [live_run_plan_lock_v1.md](./live_run_plan_lock_v1.md)
10. [live_run_execution_plan_v1.md](./live_run_execution_plan_v1.md)
11. [live_run_implementation_breakdown_v1.md](./live_run_implementation_breakdown_v1.md)
12. [live_run_test_plan_v1.md](./live_run_test_plan_v1.md)
13. [lu92xx_modbus_rtu_requirement_v1.md](../requirements/lu92xx_modbus_rtu_requirement_v1.md)

### 3. Latest locked conclusions

当前 live run 需求基线已经锁定成：

- 最小闭环是 `preview -> measurement definition -> live coordinator -> result/artifacts`
- live run 属于 `Experiment & Analysis Lane` 主链；`precheck/probe` 属于 `Commissioning Lane`
- replay / workspace 继续保留，但定位为离线验证与复盘能力
- 最终交付方向已新增锁定：
  - 保留现有 workflow 语义
  - 不再以 Web 作为最终交付形态
  - 优先在当前仓库内做桌面迁移
  - 首批抽离目标是 `webapp/config.py` 与 `webapp/deps.py` 中的应用层职责
- `workflow` 不直接处理 LU92XX 寄存器与串口细节
- `curve` 负责结果计算
- `target_temperature_celsius` 保持 API 语义
- LU92XX 默认采用 `slave=1`、`19200 / 8N1`
- 温度寄存器默认候选为 `264`，`258` 只允许作为 profile override
- `start_output()` 若依赖功率寄存器，启动功率必须来自 `startup_power_percent`
- live setup 的交互语义按 freeze-first 锁定：
  - `Stop Live Preview` 应保留最后一帧
  - preview stop / restart 不应要求页面刷新
  - ROI / 观测窗口 / A-B 点都应支持图上可视化编辑
- “刷新率”现在被拆成 4 个 requirement-level concept：
  - `camera_resulting_fps`
  - `preview_display_fps`
  - `measurement_sample_hz`
  - `artifact_capture_hz`
- `50 Hz synchronized measurement` 已锁成 baseline gate
- `100 Hz synchronized measurement` 仅是 stretch goal
- 桌面可视预览 `preview_display_fps >= 50` 已被单独锁成 desktop migration gate
- `analysis_roi` / `metric_box` 不能再被当成 camera-side acquisition ROI 的替代品

---

## Verified workspace snapshot

### Verification run

2026-03-23 本地已执行并通过：

```bash
arch -x86_64 /Users/lulingfeng/miniforge3/envs/yyt1771-mvs-x86/bin/python -m pytest \
  tests/architecture/test_model_contracts.py \
  tests/storage/test_live_run_artifacts.py \
  tests/webapp/test_config_loader.py \
  tests/camera/test_hik_gige_mvs.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_ui_shell.py \
  tests/workflow/test_live_run.py \
  tests/workflow/test_live_run_state_machine.py -q
node --check src/webapp/static/app.js
python3 -m compileall src/webapp/deps.py src/webapp/routes/live_run.py \
  tests/webapp/test_live_run_api.py tests/webapp/test_ui_shell.py
```

结果：

- `73 passed`
- `node --check` 通过
- `compileall` 通过

补充 browser QA：

- 在 `http://127.0.0.1:8002/` 的 `dev_mock` profile 下已验证：
  - `Create Live Run -> Fetch Preview`
  - `Start Live Preview -> Stop Live Preview -> Start Live Preview`
  - stop 后保留冻结帧
  - 同一 run 内无刷新 restart
  - `Preview FPS` 在 stop 后可读出约 `7.4 fps`

2026-03-23 真实相机 temporal bench 已执行，详见：

- [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)

本轮新增已验证事实：

- real camera direct bench：
  - full frame + `50 Hz` target -> `camera_resulting_fps = 14.86`，host cadence 约 `7.19 Hz`
  - `512 x 512` measurement ROI + `50 Hz` target -> host cadence 约 `49.79 Hz`
- real camera coordinator/artifact bench：
  - `512 x 512` measurement ROI + mock temp -> `measurement_sample_hz = 50.13`
  - `camera_resulting_fps = 50.0`
  - `dropped_frame_count = 0`
  - bundle 落盘完整
- control bench：
  - full frame + mock temp -> `measurement_sample_hz = 7.27`
  - `dropped_frame_count = 18`
  - warnings 明确暴露 cadence miss 与 dropped frames

物理约束说明：

- 这轮已经重新连上真实相机，因此不再停留在 mock-only camera 结论
- 但这轮 temporal bench 仍然没有使用真实温控器
- 因此当前能诚实宣称的是：
  - real camera cadence gate 已通过
  - full-chain thermal experiment gate 仍未宣称完成

2026-03-21 此前还执行并通过：

```bash
pytest tests/architecture/test_model_contracts.py \
  tests/vision/test_metric_two_point_distance.py \
  tests/curve/test_af95.py \
  tests/curve/test_afas_adapter.py \
  tests/storage/test_live_run_artifacts.py \
  tests/temp/test_lu92xx_modbus_rtu_controller.py \
  tests/workflow/test_live_run.py \
  tests/workflow/test_live_run_state_machine.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_config_loader.py \
  tests/webapp/test_ui_shell.py \
  tests/webapp/test_workspace_ui.py
```

结果：

- `72 passed`

### Important note

当前仓库是**脏工作树**，并且 live run 相关代码已有大量未提交改动。

因此这份状态只能说明：

- “当前工作树里已经存在并且通过验证的内容”

不能说明：

- “这些改动已经形成稳定提交点”
- “另一个并行进程不会继续改同一批文件”

---

## Phase status board

## Phase 1: Contract skeleton and state freeze

Status: VERIFIED_DONE

已验证完成项：

- live run 独立状态枚举已存在：
  - [enums.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/core/enums.py)
- `MeasurementDefinition` / `RunDraftRecord` 已存在：
  - [models.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/core/models.py)
- `TempControllerPort` 已存在：
  - [contracts.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/core/contracts.py)
- typed live config 已存在：
  - [config_models.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/core/config_models.py)
  - [config.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/config.py)
- route skeleton / in-memory registry 已存在：
  - [live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/routes/live_run.py)
  - [deps.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/deps.py)

对应测试：

- [test_model_contracts.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/architecture/test_model_contracts.py)
- [test_live_run_api.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_live_run_api.py)
- [test_config_loader.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_config_loader.py)

备注：

- 代码里用的是 `RunStatus` 命名，而不是文档中的 `LiveRunState`；这不影响 Phase 1 完成判断

---

## Phase 2: Preview, measurement definition, and run gating

Status: VERIFIED_DONE_FOR_CURRENT_WEB_BASELINE_WITH_ROUTE_NAMING_DEVIATION

已验证完成项：

- preview frame API 已存在并通过测试
- preview stream API 已存在并通过测试
- measurement definition 结构校验已存在并通过测试
- auto detect suggestion 已存在并通过测试
- UI shell 已出现 live setup 入口并通过页面测试
- `Stop Live Preview` 已保留冻结帧，而不是清空画面
- 同一 run 内 stop / restart 已在 browser 中验证成立，无需刷新页面
- ROI / 观测窗口 / A-B 点已支持图上 overlay 编辑，并已在页面中验证可用

核心文件：

- [live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/routes/live_run.py)
- [metric_two_point_distance.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/vision/metric_two_point_distance.py)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)
- [index.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/index.html)

对应测试：

- [test_live_run_api.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_live_run_api.py)
- [test_metric_two_point_distance.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/vision/test_metric_two_point_distance.py)
- [test_ui_shell.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_ui_shell.py)
- [test_workspace_ui.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_workspace_ui.py)

当前偏差：

- 计划文档早期草稿写的是 `POST /api/runs/{run_id}/definition/auto-detect`
- 当前实现和前端使用的是 `POST /api/runs/{run_id}/definition/auto`
- 这属于 route naming deviation，不影响当前 Phase 2 的 mock/browser 完成判断
- 当前这项完成判断尚未包含单独的真机 operator-side UI 手感复核

补充说明：

- 这里的完成判断只表示当前 Web baseline 已经达到 freeze-first 交互语义
- 它不等于桌面迁移已经完成
- 桌面迁移的交付进度应另看：
  - [desktop_workstation_migration_status_v1.md](./desktop_workstation_migration_status_v1.md)

建议：

- 若后续要做 route naming 统一，应作为单独契约清理任务处理
- 在重新接入真实相机后，再补一次 operator-side 真机 UI smoke test

---

## Temporal sampling workstream status

这部分是 2026-03-23 requirement addendum 新增的工程主线。

Status: CAMERA_CADENCE_GATE_VERIFIED_FULL_THERMAL_CLOSED_LOOP_BLOCKED

### TS-1. Contract split and achieved-rate skeleton

Status: VERIFIED_DONE

说明：

- `capture_mode`、四类 rate concept、`measurement_profile` 已进入 canonical model / API / artifact contract
- `GET /api/runs/{run_id}`、`result.json`、detail/result schema 已能稳定回读这些字段
- 相关回归已覆盖 contract、artifact、API 基线

### TS-2. Camera measurement-profile plumbing

Status: VERIFIED_DONE

说明：

- `setup_preview` / `measurement` 双 acquisition profile 已进入 typed config
- preview path 与 live-run path 已分别请求对应 profile
- `measurement.device_roi` 已下发到 Hik official SDK bridge，并与 analysis ROI 保持分离

### TS-3. Workflow cadence accounting

Status: VERIFIED_DONE

说明：

- coordinator 现在使用 source timestamps 计算 achieved cadence，不再用合成时间戳伪造 sample rate
- `telemetry.csv` 已能回读 `sample_index`、`sample_interval_ms`、source timestamps、`frame_id`
- detail / result / telemetry API 已贯穿 achieved cadence 与 cadence warning
- 低于 target cadence 时会显式暴露 warning，而不是静默当成达标

### TS-4. Setup preview optimization

Status: VERIFIED_DONE_WITH_REAL_CAMERA_PREVIEW_BENCH

说明：

- `preview_target_fps` 默认值已从旧的低频预览提升到 `8.0`
- stream path 已改成更轻的 preview payload：
  - stream downsample 到 `384 x 256` 上限
  - interval 由 `preview_target_fps` 驱动，而不是只靠旧的 `preview_poll_ms`
- `preview_display_fps` 已贯穿到 preview service、run detail API 和页面 facts
- 海康 Mono8 preview path 已进一步减重：
  - official SDK bridge 不再为 setup preview 强制物化完整 Python 二维像素列表
  - web preview route 会优先走 image-native downsample fast path
- motion preview stream 已从逐帧 PNG 切到 MJPEG：
  - multipart part `Content-Type` 现在是 `image/jpeg`
  - setup preview service 改成 latest-frame-wins 语义，采集与发送不再严格串行绑死
- `Fetch Preview` 与 stop 后的冻结帧已拆成两种语义：
  - 手动 `Fetch Preview` 默认抓取新的 still
  - stop 后自动加载 cached frozen frame，保留最后一帧编辑语义
- browser QA 已验证：
  - stop 后保留冻结帧
  - 同一 run 内 restart 成立
  - 页面能显示 `Preview FPS`
- real camera preview smoke 已复测：
  - 在 `dev_lab` 的当前 full-frame setup preview 配置下，真实 bench 先从约 `0.47 fps` 提升到约 `4.82 - 5.07 fps`
  - 继续切到 MJPEG + latest-frame-wins 后，同一条链路进一步提升到约 `8.58 - 8.89 fps`
  - 这轮改善显著降低了 setup preview 的卡顿，但当前 setup preview 仍未达到 measurement ROI bench 的高频水平

### TS-5. 50 Hz bench validation

Status: VERIFIED_DONE_WITH_REAL_CAMERA_AND_MOCK_TEMP_BENCH

说明：

- 真实海康相机 bench 已重新执行并记录在：
  - [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)
- 当前已验证：
  - real camera + `512 x 512` measurement ROI -> coordinator/artifact path 达到 `50.13 Hz`
  - achieved cadence、`camera_resulting_fps`、`dropped_frame_count`、measurement profile 已贯穿到 artifact/result
  - full-frame 对照 bench 会明确失败，并暴露 cadence warning + dropped-frame warning
- 当前 bench 仍使用 mock temp controller / mock metric source
- 因此这项完成判断只覆盖：
  - camera / workflow / artifact cadence gate
- 不覆盖：
  - 真实温控器闭环实验链

补充说明：

- `TS-5` 已经不再是“完全 blocked”
- 当前真正 blocked 的是：
  - full thermal closed-loop bench
  - desktop preview `>50 Hz` Windows gate
- 这两个问题分别由：
  - Phase 6 / LU92XX 现场 bench
  - [desktop_workstation_migration_status_v1.md](./desktop_workstation_migration_status_v1.md)
 继续跟踪

### TS-6. 100 Hz stretch review

Status: OUT_OF_SCOPE_UNTIL_DESKTOP_PREVIEW_AND_WINDOWS_ACCEPTANCE_REVIEW

---

## Phase 3: AFAS adapter and result contract first

Status: VERIFIED_DONE

已验证完成项：

- AFAS adapter 已独立落到 [afas.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/curve/afas.py)
- live result 已不再只有 `af95`
  - `as_value / af_value`
  - `result_status / result_reason / result_detail`
  - keyframe artifact refs
- `definition.json / telemetry.csv / events.jsonl / detail.json / result.json` 已落地并通过测试
- API 返回结构已同步扩展到 result/detail/artifact refs

核心文件：

- [afas.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/curve/afas.py)
- [summary.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/report/summary.py)
- [session_artifacts.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/storage/session_artifacts.py)
- [live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/workflow/live_run.py)

对应测试：

- [test_afas_adapter.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/curve/test_afas_adapter.py)
- [test_live_run_artifacts.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/storage/test_live_run_artifacts.py)
- [test_live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/workflow/test_live_run.py)
- [test_live_run_api.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_live_run_api.py)

备注：

- 当前实现是“轻量 tangent-style AFAS 分析”，不是外部专有分析引擎
- `af95` 仍然复用 [af95.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/curve/af95.py) 的估计逻辑，这不影响本阶段“adapter + contract”完成判断

---

## Phase 4: Live run coordinator with mock temp first

Status: VERIFIED_DONE

已验证完成项：

- `LiveRunCoordinator` 已具备可观察生命周期：
  - `running`
  - `stopping`
  - `aborted`
  - `failed`
  - `invalidated`
- `start` 已改为后台线程执行，不再是同步立即完成
- operator stop / tracking invalidation / finalize failure / temp read failure 已全部进入测试矩阵
- active run telemetry、events、result 已可在运行中和结束后通过 service / API 读回
- UI 已出现 stop 控件，并按 run 状态禁用 setup 动作

核心文件：

- [live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/workflow/live_run.py)
- [deps.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/deps.py)
- [live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/routes/live_run.py)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)

对应测试：

- [test_live_run.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/workflow/test_live_run.py)
- [test_live_run_state_machine.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/workflow/test_live_run_state_machine.py)
- [test_live_run_api.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_live_run_api.py)
- [test_ui_shell.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/webapp/test_ui_shell.py)

---

## Phase 5: LU92XX temp adapter with profile-driven defaults

Status: VERIFIED_DONE_WITHOUT_BENCH

依据：

- [lu92xx_modbus_rtu_controller.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/temp/lu92xx_modbus_rtu_controller.py) 已存在
- `TempRuntimeConfig` 已扩展 LU92XX 专属 typed config：
  - [config_models.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/core/config_models.py)
  - [config.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/config.py)
- `prod_win` profile 已切到 device-bound backend：
  - [prod_win.yaml](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/configs/prod_win.yaml)
- LU92XX 单元测试已存在：
  - [test_lu92xx_modbus_rtu_controller.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/tests/temp/test_lu92xx_modbus_rtu_controller.py)

已完成项：

- LU92XX adapter 实现
- `264` 默认 / `258` override 的 profile 化
- `startup_power_percent` 配置落地
- LU92XX 单元测试

仍未完成项：

- 真机串口 bench
- 真实设备 profile 样例回填

结论：

- Phase 5 可以视为代码与配置层完成
- 但不能把它解释成“真机 ready”

---

## Phase 6: Bench validation and profile lock

Status: BLOCKED_ON_PHYSICAL_BENCH

未开始项：

- `264` vs `258` 台架裁决
- reg `0` 业务语义确认
- reg `4` 启停语义确认
- 现场串口参数与从站地址确认
- 已验证 profile 样例

现场阻塞事实：

- 2026-03-21 这台 Mac 上未发现可用的 LU92XX 串口设备节点
- `/dev/cu.*` 仅见蓝牙与 debug 口，未见 USB 转串口 / RS485 设备

记录文件：

- [live_run_bench_validation_v1.md](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/docs/plan_eng_review/live_run_bench_validation_v1.md)

---

## Phase 7: Result package and workspace/history integration

Status: PARTIAL

已完成部分：

- start 后的 live run 结果已经可以通过 session API 侧读回
- result bundle 已能落盘，说明历史/详情的底层数据基础开始具备

未完成部分：

- 没有明确证据表明 workspace 已完整接入 live run result view
- 历史列表与 workspace 的 live run 展示还没有被单独验收为一个阶段完成项
- 仍缺专门的“result/history integration”任务文档或测试分组

结论：

- 数据基础部分已出现，但 UI/历史集成不应算完成

---

## Current task list

按当前代码实际状态，live run 后续 task 清单应更新为：

1. Task-022
   Status: VERIFIED_DONE
   Scope: Phase 1 合同、状态、schema、route skeleton

2. Task-B
   Status: VERIFIED_DONE_FOR_CURRENT_WEB_BASELINE_WITH_ROUTE_NAMING_DEVIATION
   Scope: preview、definition validation、auto detect、run gating
   Follow-up:
   若要继续做契约清理，可统一 `auto` vs `auto-detect` 路径；若要继续推进最终交付，应转入桌面迁移 D5-D7，而不是再把当前 Web baseline 误报成未完成

3. Task-C
   Status: VERIFIED_DONE
   Scope: AFAS adapter、result contract、artifact schema
   Note: 当前 AFAS 是轻量 tangent-style 实现，`af95` 仍复用现有估计逻辑

4. Task-D
   Status: VERIFIED_DONE
   Scope: live coordinator、stop/abort/fail/invalidation 状态流

5. Task-E
   Status: VERIFIED_DONE_WITHOUT_BENCH
   Scope: LU92XX Modbus RTU adapter、profile defaults、config contract

6. Task-F
   Status: BLOCKED_ON_PHYSICAL_BENCH
   Scope: bench validation、profile lock、现场寄存器裁决

7. Task-G
   Status: NOT_STARTED_AT_UI_LEVEL
   Scope: workspace/history/result integration

---

## Recommended next step

如果你要“顺利往下继续”，推荐先明确自己是在推进哪条主线：

- 若继续补 live run 组件完成度：按下面 bench / integration 顺序走
- 若开始桌面迁移：改看 [desktop_workstation_migration_status_v1.md](./desktop_workstation_migration_status_v1.md) 并从 D5 开始

若当前目标仍是 live run 组件收口，推荐按照下面顺序进行，而不是重新猜需求：

1. 把当前并行进程的 live run 代码先形成一个提交点
2. 在这个提交点上，把 [live_run_task_status_v1.md](./live_run_task_status_v1.md) 当成当前状态板
3. 下一步优先做 Phase 6 bench continuation
   - 前提：物理 LU92XX 串口链路出现在本机或 Windows bench 环境
4. bench 到位后先裁决 `264 vs 258`
   - 再确认 reg `0` / reg `4` 的现场业务语义
5. 在 bench 未到位前，不要把“代码 ready”误报成“真机 ready”

### Safest immediate continuation

如果你现在和另一个进程并行协作，最稳的分工是：

- 一个进程负责 Phase 6 bench continuation 和 profile 样例回填
- 另一个进程负责 Task-G 的 workspace/history/result integration

如果没有明确 ownership，就先不要并行修改 `configs/prod_win.yaml`、`src/webapp/deps.py` 和 live result 相关 schema。

---

## One-line summary

当前最新需求基线已经由 repo 内的 requirement / migration 文档统一收口；当前代码已经完成并验证了 Phase 1、Phase 2、Phase 3、Phase 4、Phase 5，以及 real-camera cadence gate 下的 TS-5；桌面迁移 D1-D4 已经完成，但真实 LU92XX 现场 bench 仍 blocked，Task-G 仍未完成，桌面迁移 D5-D7 也尚未开始代码实施。
