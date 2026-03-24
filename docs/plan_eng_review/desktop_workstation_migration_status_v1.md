# Desktop Workstation Migration Status v1

Updated on 2026-03-24
Status: ACTIVE_DESKTOP_TRANSITION_SNAPSHOT

## Purpose

这份文件单独追踪桌面迁移计划 `D1-D7` 的当前状态。

它回答的是：

1. 桌面迁移本身已经推进到哪一步
2. 哪些结论已经锁定
3. 哪些工作仍然只是输入条件，还没有进入桌面实现

这份文件不是 live run 全量状态板的替代品，而是桌面迁移程序的专用状态板。

---

## Authoritative baseline

桌面迁移工作应按下面顺序阅读：

1. [requirements_overview.md](../requirements/requirements_overview.md)
2. [desktop_workstation_migration_requirement_v1.md](../requirements/desktop_workstation_migration_requirement_v1.md)
3. [desktop_workstation_migration_plan_lock_v1.md](./desktop_workstation_migration_plan_lock_v1.md)
4. [live_run_task_status_v1.md](./live_run_task_status_v1.md)
5. [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)

---

## Current locked truths

当前已经锁定且不应再被反复重开的问题：

- 最终交付方向是 Windows 桌面工作站，而不是浏览器
- 当前仓库继续作为唯一实现主线
- 若继续使用 Python，默认桌面技术路线是 `PySide6 / Qt`
- 必须先抽 `src/webapp/config.py` 与 `src/webapp/deps.py` 中的应用层职责
- `webapp` 后续应退化为 thin adapter，而不是继续承担共享应用层
- `50 Hz synchronized measurement` 已作为 camera/workflow cadence gate 站住
- “桌面可视预览 >50 Hz” 现在也已被独立锁定为 desktop preview gate

当前仍未被宣布完成的部分：

- `desktop_app` 已有代码骨架，但还没有进入已验收的桌面运行时状态
- Windows 打包与最终现场验收尚未开始
- 真实温控闭环实验链尚未宣称完成

---

## D1-D7 status board

### D1. Documentation lock

Status: VERIFIED_DONE

已完成：

- desktop migration requirement 已落地
- desktop migration plan lock 已落地
- canonical entry docs 已接入桌面迁移主线
- 桌面预览 `>50 Hz` gate 已进入 requirement / plan 文档

### D2. Shared config extraction

Status: VERIFIED_DONE

计划内显式交付：

- 把 `src/webapp/config.py` 抽成共享 runtime/config 层
- 保留 `setup_preview` / `measurement` profile split
- 把 MVS 固化成桌面迁移主路径的默认相机基线
- 修正 temp backend naming mismatch

已完成：

- 共享 `runtime_config` 已从 `src/webapp/config.py` 抽到 `src/application/runtime_config.py`
- `src/webapp/config.py` 已退化为兼容层
- `webapp` 关键入口已改为依赖共享 config 模块
- `dev_lab` 默认相机基线已切到 `hik_gige_mvs`
- temp backend resolution 已优先读取 `live.temp.backend`
- `dev_lab.local.example.yaml` 已显式把 temp adapter 切到 `lu92xx_modbus_rtu`

已验证：

- runtime config loader 回归通过
- `dev_lab` / `prod_win` profile API 回归通过
- precheck / UI shell / live run 相关回归通过

### D3. Application-service extraction

Status: VERIFIED_DONE

计划内显式交付：

- 抽离 `LivePreviewService`
- 抽离 `LiveRunService`
- 抽离 `LiveRunDraftRegistry`
- 抽离 device build logic
- 建立共享 application layer

已完成：

- `LivePreviewService` 已抽到 `src/application/live_preview_service.py`
- `LiveRunService` 已抽到 `src/application/live_run_service.py`
- `LiveRunDraftRegistry` 已抽到 `src/application/live_run_registry.py`
- device build logic 已抽到 `src/application/device_factory.py`

已验证：

- live run / preview / profile / precheck 目标回归通过
- 抽离后保留了现有 service seam，可继续 monkeypatch 和测试
- `webapp/deps.py` 已不再承载这些核心实现

### D4. Web thin-adapter refit

Status: VERIFIED_DONE

计划内显式交付：

- 让 `src/webapp/` 改为调用共享 application layer
- 保持现有 Web 路径可运行
- 不再让 Web 成为共享应用层事实来源

已完成：

- `src/webapp/config.py` 已降级为兼容层
- `src/webapp/deps.py` 已降级为薄依赖注入壳，并改为从共享 `ApplicationContainer` 取 repo / store / service
- `create_app()` 已以共享 container 初始化 Web shell，再保留兼容性 state alias
- live-run / preview / profile / session / adjustment / probe / workspace 相关 Web route 已统一走 container-backed dependency helpers

已验证：

- Web API 目标回归通过：
  - health
  - profile
  - session
  - adjustment
  - camera probe
  - live run
- `compileall` 覆盖 `src/application` 与 `src/webapp` 通过

### D5. Desktop shell bootstrap

Status: PARTIAL_IN_CODE

计划内显式交付：

- 新增 `desktop_app`
- 接通最小工作流主链：
  - precheck
  - probe
  - create run
  - preview start / stop / freeze
  - ROI / 观测窗口 / A-B 编辑
  - start live run
  - result / telemetry readback

当前状态说明：

- `src/desktop_app/` 已新增第一版目录骨架
- 已新增纯 Python 的 `DesktopWorkbenchController`
- controller 已直接复用共享 application layer，接通：
  - precheck
  - probe
  - create run
  - preview start / stop / freeze
  - save definition
  - start live run
  - result / detail / telemetry readback
- 已新增 Qt 启动入口与最小 `DesktopMainWindow` 壳
- 最小窗口已包含 definition 表单：
  - analysis ROI
  - metric box
  - point A / point B
  - target temperature
- 当前窗口仍是 bootstrap 形态：
  - 主要用于验证桌面壳可以直接消费共享 controller
  - 还没有最终的图上 ROI / A-B / 观测窗口原生编辑体验
  - 也还没有最终的 native preview rendering 实现

已验证：

- `desktop_app` controller 回归通过
- 在未安装 `PySide6` 的环境里，桌面入口会给出明确缺依赖提示，而不是静默崩溃

### D6. Desktop preview optimization

Status: NOT_STARTED_IN_CODE

计划内显式交付：

- 用 desktop preview path 替代当前 Web MJPEG 最终显示路径
- 在 Windows bench profile 下完成 `preview_display_fps >= 50` 验收

当前已存在但只应视为输入条件的事实：

- real camera + `512 x 512` measurement ROI 已验证 `measurement_sample_hz = 50.13`
- 当前 Web preview 经过减重后大约在 `8.58 - 8.89 fps`
- 这些结果证明“相机 / workflow cadence”与“Web preview display”不是同一个 gate

### D7. Windows packaging and field gate

Status: NOT_STARTED_ON_WINDOWS

计划内显式交付：

- Windows runtime validation
- packaged-product validation
- desktop preview gate 收口
- 串口 / 温控现场链路收口
- 最终 acceptance

---

## Relationship to other status docs

- [live_run_task_status_v1.md](./live_run_task_status_v1.md)
  负责 live run、temporal sampling、LU92XX、workspace/result 集成的组件状态
- 本文件
  负责桌面迁移 `D1-D7` 的程序级状态

如果两者出现冲突，应先修正文档，而不是让桌面迁移继续带着矛盾往前走。

---

## Recommended immediate next step

当前桌面迁移最稳的下一步是：

1. 继续把 D5 从 bootstrap 推进到可运行的 Qt 工作台
2. 补第一轮桌面端 runtime smoke
3. 在桌面壳能稳定驱动最小工作流后，再进入 D6

也就是说，当前最优执行顺序仍然是：

`shared config -> application services -> web thin adapter -> desktop shell`
