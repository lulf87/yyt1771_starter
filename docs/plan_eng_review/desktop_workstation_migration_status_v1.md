# Desktop Workstation Migration Status v1

Updated on 2026-03-24
Status: PAUSED_LEGACY_REFERENCE_AFTER_MAC_FINISH

## 2026-05-25 `mac-finish` Supersession Note

This status board is retained only as historical / fallback desktop context.

It must not be used as the default Windows migration state for `mac-finish`.
The active direction is now Web-on-Windows:

```text
src.webapp.serve -> application -> workflow / storage / report
```

Read these first for current work:

- [current_run_modes_20260524.md](./current_run_modes_20260524.md)
- [web_on_windows_migration_status_20260525.md](./web_on_windows_migration_status_20260525.md)

Do not add new `desktop_app` work unless the user explicitly reactivates the
desktop track.

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

## Current locked truths after `mac-finish`

当前已经锁定且不应再被反复重开的问题：

- current active shell is Web workstation
- Windows migration means Web-on-Windows first
- desktop migration is paused historical / fallback material, not an active
  default path
- 当前仓库继续作为唯一实现主线
- 若用户未来明确重新启用桌面路线，历史默认桌面技术路线仍是
  `PySide6 / Qt`
- 已抽离的 application layer 继续服务于 Web 工作站与未来可能的交付壳
- `50 Hz synchronized measurement` 已作为 camera/workflow cadence gate 站住
- “桌面可视预览 >50 Hz” 仅保留为历史 desktop preview gate

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
- 最小窗口现在也已经包含第一版 preview panel：
  - 可显示当前 preview frame
  - start preview 后会定时拉取最新 cached frame
  - stop / freeze 后会保留最后一帧
- 桌面 preview panel 现在已接入第一版原生 overlay 编辑：
  - `Draw ROI`
  - `Draw Window`
  - `Rotate Window`
  - `Point A`
  - `Point B`
  - overlay 改动会同步回 definition 表单
- 已新增不依赖 Qt 的 headless desktop smoke mode：
  - `python -m src.desktop_app.main --profile dev_mock --smoke-run`
  - 可在未安装 `PySide6` 的环境里验证最小桌面 workflow 主链
- 已补桌面运行时 bootstrap：
  - 会显式设置 Qt plugin 搜索路径
  - 当前可避免“路径未注入”这类入口级错误
- 已在本机验证一套可工作的桌面 Qt 运行时：
  - 本地 conda 环境 `.conda-desktop`
  - `python 3.11`
  - `conda-forge pyside6 6.10.2`
  - 该环境下已通过真实 `QApplication` 初始化、窗口 preview smoke、desktop main / window 测试
- 当前窗口仍是 bootstrap 形态：
  - 主要用于验证桌面壳可以直接消费共享 controller
  - 虽然已经有第一版图上编辑，但桌面壳仍未进入最终交付级 UI 完成态
  - 也还没有最终的高 FPS native preview rendering 实现
  - 本机原先的 pip venv `.venv-desktop-qt` 仍存在独立的 QPA plugin 初始化问题：
    - `QApplication` 创建时报 `Could not find the Qt platform plugin "cocoa/offscreen"`
    - plugin 文件本身存在，但该环境当前不应再视为桌面验证基线

已验证：

- `desktop_app` controller 回归通过
- shared preview render helper 回归通过
- desktop main 的 headless smoke 回归通过
- overlay geometry helper 回归通过
- `.conda-desktop` 环境下的真实桌面窗口 smoke 已通过：
  - create run
  - start preview
  - stop / freeze
  - preview bitmap retained
- 在未安装 `PySide6` 的环境里，桌面入口会给出明确缺依赖提示，而不是静默崩溃

### D6. Desktop preview optimization

Status: PARTIAL_IN_CODE

计划内显式交付：

- 用 desktop preview path 替代当前 Web MJPEG 最终显示路径
- 在 Windows bench profile 下完成 `preview_display_fps >= 50` 验收

当前已存在但只应视为输入条件的事实：

- real camera + `512 x 512` measurement ROI 已验证 `measurement_sample_hz = 50.13`
- 当前 Web preview 经过减重后大约在 `8.58 - 8.89 fps`
- 这些结果证明“相机 / workflow cadence”与“Web preview display”不是同一个 gate

当前已经进入代码的部分：

- shared preview interval 已不再被 `50ms` floor 硬锁
- interval 现在可由 `preview_target_fps` 直接驱动到 `20ms` 级别
- desktop shell 已开始把“真正显示到界面上的帧”回写到 `preview_display_fps`
- desktop `QTimer` 已改成按 preview target 驱动，而不是固定 `120ms`
- 已新增 headless desktop preview benchmark 入口：
  - `python -m src.desktop_app.main --profile dev_mock --preview-benchmark --duration-s 1.5`
  - 可输出 `presented_frames`、`measured_presented_fps`、`preview_display_fps`
  - 这条 bench path 设计为后续切到真实相机 / Windows 时继续复用
- 已新增 Qt-driven desktop preview benchmark 入口：
  - `python -m src.desktop_app.main --profile dev_mock --qt-preview-benchmark --duration-s 1.5`
  - 会通过真实 `DesktopMainWindow` 和 Qt 事件循环驱动 preview
  - 可输出窗口级 `stream_presented_frames`、`measured_presented_fps`、`preview_display_fps`
- 两条 benchmark 入口都已支持运行时 override：
  - `--target-preview-fps`
  - `--preview-poll-ms`
  - `--setup-preview-roi-x/y/width/height`
  - 便于直接对同一 profile 做高 FPS bench，而不必先改 profile 文件
- desktop runtime bootstrap 现在会自动恢复本机 Hik MVS patched runtime 所需的 `/tmp/mvs` sidecar symlink：
  - `libMVGigEVisionSDK.dylib`
  - `libMVU3VisionSDK.dylib`
  - `libMediaProcess.dylib`
- preview bitmap 构建已补 image-native fast path：
  - `HikGigeMvsCamera` 的 `_Mono8ImageView` 现在可直接提供 downsampled bitmap payload
  - desktop preview 不再必须先构造嵌套 Python `list[list[int]]` 再 flatten
- desktop preview canvas 已切到 `FastTransformation`
  - 以优先保证高 FPS preview，而不是优先保证最平滑缩放
- 当前已有第一份本机 mock benchmark 基线：
  - `dev_mock`
  - `target_preview_fps = 50`
  - `preview_poll_ms = 20`
  - headless benchmark 约 `31 fps`
  - Qt-driven benchmark 约 `30 fps`
  - 这说明 benchmark 路径已可用，但 desktop preview `>50 Hz` gate 仍未达成
- 当前真实相机 desktop benchmark 已经真正进入出帧阶段：
  - `dev_lab + x86_64 headless benchmark`
  - MVS SDK import / patched dylib / sidecar symlink 已自动 bootstrap
  - full-frame baseline 约 `13.09 fps`
  - `512 x 512` setup-preview ROI 下约 `42.64 fps`
  - 这说明 desktop preview 的真实相机 blocker 已从“设备枚举失败”切换成“显示链性能”
- `dev_lab + x86_64 Qt-driven benchmark` 现在也已能真实出帧：
  - 本地 `.conda-desktop-x86` 环境已验证可创建 `x86_64` `QApplication`
  - full-frame baseline 约 `1.35 fps`
  - `512 x 512` setup-preview ROI 下约 `25.57 fps`
  - `384 x 384` + `target_preview_fps=50` + `preview_poll_ms=20` 下约 `49.91 fps`
  - `384 x 384` + `target_preview_fps=60` + `preview_poll_ms=16` 下：
    - `preview_display_fps = 57.496`
    - `measured_presented_fps = 57.496`
  - 这说明桌面 preview `>50 Hz` gate 已在本机 Mac 代理 bench 条件下被真实击穿
- `dev_lab + arm64 Qt-driven benchmark` 仍然不是可用基线：
  - arm64 `PySide6` 进程无法加载 x86_64 的 patched Hik MVS dylib
  - 当前不应用它作为真实相机桌面 bench 环境

当前仍未完成的部分：

- 还没有在 Windows bench profile 上验证 `preview_display_fps >= 50`
- 还没有把当前 Mac 代理 bench 条件固化成正式 bench profile / env script
- 还没有在 Windows 最终运行时上复现同一组 preview gate
- 因为 requirement 明确把 desktop preview gate 锁在 Windows bench profile 上，所以 D6 还不能诚实地标为完成

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

1. 先按 [web_preview_18fps_plan_lock_v1.md](./web_preview_18fps_plan_lock_v1.md) 跑完 Web viability gate
2. 如果 Web gate 失败，再继续把这组 Mac 代理 bench 条件固化成正式 desktop preview bench profile / script
3. 准备 Windows bench 环境，复现 `384 x 384 / target 60 / poll 16` 这组 gate 条件
4. 在 Windows 上完成 `preview_display_fps >= 50` 的正式收口
