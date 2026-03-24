# Desktop Workstation Migration Requirement v1

Updated on 2026-03-24
Status: CANONICAL_REQUIREMENT_ADDENDUM

## Purpose

这份文档用于锁定一个新的产品与交付方向：

- 保留当前项目已经验证过的工作流与业务语义
- 不再把浏览器 Web 工作站作为最终交付形态
- 在原仓库内继续演进，而不是立刻另开一个新的 Python 项目
- 最终交付方向切换为 Windows 桌面工作站

这份 requirement 解决的不是“要不要重写所有东西”，而是下面 4 个更关键的问题：

1. 哪些现有工作流必须原样保留
2. 哪些现有模块应被视为可复用核心
3. 哪些 `webapp` 代码其实已经是待抽离的应用层
4. 新的桌面迁移应在原仓库内如何开始

---

## Context

当前项目已经证明：

- `precheck -> probe -> preview -> measurement definition -> live run -> result/artifacts`
  这条工作流是对的
- 相机、温控、workflow、artifact、curve/result 这些核心能力并不天然依赖浏览器
- 浏览器更像当前的交付壳，而不是唯一合理的产品边界
- 对“真正可用的 50 Hz 可视预览”的诉求，已经开始逼近浏览器路径的舒适区边界

同时，当前项目的真实部署约束已经非常清楚：

- 日常开发主要发生在 Mac
- 最终用户在 Windows
- 最终打包与现场验收必须在 Windows 完成

因此，新的 requirement 不是“推翻已有工作”，而是：

> 保留已验证的 workflow 与业务核心，把最终交付外壳从 Web 迁移到桌面端。

---

## What Must Be Preserved

从现在开始，下面这些内容应被视为新方向下必须保留的产品语义，而不是可以随意重设计的部分。

### R1. Commissioning and experiment workflows remain intact

必须保留当前已经冻结的两条 lane：

- `Commissioning Lane`
  - `precheck`
  - `probe`
  - profile / runtime readiness

- `Experiment & Analysis Lane`
  - preview
  - freeze
  - ROI / 观测窗口 / A-B 点定义
  - live run
  - telemetry / result / artifact review

新的桌面端交付不应改变这两条 lane 的核心动作，只应改变用户界面载体。

### R2. Freeze-first setup semantics remain intact

当前已经锁定的 live setup 交互语义必须完整保留：

1. `Stop Live Preview` 的语义仍然是：
   - 停止流
   - 保留最后一帧
   - 允许继续编辑

2. 同一 run 内必须支持：
   - `Start Live Preview`
   - `Stop Live Preview`
   - `Restart Live Preview`
   - 且不需要刷新整个应用

3. ROI、观测窗口、A/B 点都必须支持可视化编辑。

桌面化迁移不能以牺牲这些交互冻结规则为代价。

### R3. Measurement/result semantics remain intact

以下结果语义必须保留：

- `As`
- `Af`
- 必要时保留 `Af95`
- evidence package
  - definition
  - telemetry
  - keyframes
  - result
  - event trace

桌面迁移只改变 UI 壳和运行形态，不改变结果合同。

### R4. Temporal-sampling language remains intact

下面 4 个 rate concept 必须继续保留，不得因为桌面迁移重新混淆成一个“刷新率”：

- `camera_resulting_fps`
- `preview_display_fps`
- `measurement_sample_hz`
- `artifact_capture_hz`

同时继续保留：

- `50 Hz synchronized measurement` 为 baseline
- `100 Hz synchronized measurement` 为 stretch goal

桌面端可以改变“可视预览”的实现方式，但不能抹掉 measurement cadence 的 requirement 语言。

---

## Product Direction Change

### R5. Browser is no longer the final delivery baseline

从现在开始，浏览器工作站不再是最终交付基线。

新的正式产品方向应表述为：

> 一个保留当前 YY/T 1771 工作流语义、但最终以 Windows 桌面工作站形式交付的系统。

这意味着：

- `webapp` 不再自动等于“最终产品”
- 浏览器层可以继续保留为：
  - 过渡适配层
  - 调试入口
  - 内部工具
- 但它不再是桌面迁移后的唯一目标壳

### R6. The new work should stay in the current repository

当前 requirement 锁定为：

- 若桌面迁移仍采用 Python 技术栈，则必须优先在现有仓库内演进
- 不应在当前阶段另开一个新的 Python 项目来复制已有核心逻辑

理由：

- 当前核心模块大多已是 headless Python
- 业务价值主要在 workflow / contracts / adapters / artifacts
- 立刻新开仓库会复制文档、配置、测试与技术债，而不是减少风险

这条 requirement 仅在下面情况才允许被推翻：

- 决定改用非 Python 主技术栈
- 明确接受跨语言桥接或重写成本

### R7. Python desktop is the default migration path

如果继续沿用 Python 作为主技术栈，当前推荐冻结为：

- 首选桌面 UI 路线：`PySide6 / Qt`

这不是“永远不能改”，而是：

- 在没有新的 office-hours / plan-review 推翻前
- 当前 requirement 的默认路线就是 Python 桌面 UI

### R8. Desktop delivery must not reuse the web MJPEG preview route as the final preview path

当前 `/preview/stream` 路由及其 MJPEG 预览链不应被当成桌面端的最终预览路径。

桌面端应复用的是：

- preview state semantics
- camera profile selection
- live run coordination
- result/artifact logic

而不是：

- `StreamingResponse`
- `multipart/x-mixed-replace`
- `<img>` 预览链

---

## Boundary Lock

### R9. Shared core stays shared

下面这些模块应被视为桌面迁移中的共享核心：

- `src/core`
- `src/workflow`
- `src/storage`
- `src/report`
- `src/curve`
- `src/camera`
- `src/temp`

其中相机层允许继续做性能优化，但不应因为桌面迁移而先被重写。

### R10. `src/webapp/deps.py` is not just web glue anymore

当前 requirement 明确承认：

- `src/webapp/deps.py`
- `src/webapp/config.py`

已经不是单纯的 Web glue 文件，而是包含了应用层职责。

因此它们必须进入桌面迁移的首批抽离名单。

### R11. New shared application layer is required

桌面迁移必须引入一个共享的应用层，用于承载当前散落在 `webapp` 中、但本质上并不属于浏览器框架的能力。

最小职责包括：

- runtime config loading
- preview service
- live run service
- run draft registry
- camera / temp controller build logic
- run-time ephemeral state container

### R12. Desktop UI should depend on application services, not on FastAPI state

新的桌面 UI 不得直接依赖：

- `FastAPI.app.state`
- route function
- `StreamingResponse`

桌面 UI 应只依赖共享的 application service 层。

---

## Validation Lock

### R13. Mac remains the primary development and most-verification platform

Mac 上应继续承担：

- 核心逻辑开发
- workflow 调试
- contract / artifact / result 验证
- 大部分 integration 测试
- 桌面 UI 的早期开发

### R14. Windows remains the final runtime, packaging, and acceptance platform

Windows 上必须承担：

- 桌面运行时验证
- MVS 运行时验证
- 最终相机预览性能验收
- 串口 / 温控现场链路验收
- 打包与交付产物验证

### R15. Desktop preview display has its own explicit acceptance gate

如果产品目标包含“真正可用的桌面实时预览”，则该目标必须作为独立 requirement gate 存在，
而不能再被隐含进 `50 Hz synchronized measurement`。

从现在开始，桌面预览性能验收至少需要显式记录：

- 平台：Windows 最终验收环境
- 路径：desktop preview path，而不是 Web MJPEG path
- 相机 profile：device ROI / pixel format / exposure / gain / target fps
- 指标：`preview_display_fps >= 50`

若未记录这些前提，就不得宣称“桌面预览 >50 Hz 已完成”。

### R16. Desktop preview gate stays separate from measurement cadence gate

下面两件事必须被视为不同的 requirement：

- `preview_display_fps >= 50` 的桌面可视预览 gate
- `50 Hz synchronized measurement` 的采样/同步 gate

它们可以共享相机与 profile 基础设施，但通过条件和验收记录必须分开。

若后续要补充：

- latency 上限
- dropped-frame 容忍度
- CPU 占用上限

这些值也必须写入 requirement 或 bench 验收记录后，才能作为正式 gate 使用。

---

## Migration Outcome

从现在开始，新的迁移目标应明确表述为：

> 在不改变当前 YY/T 1771 工作流与结果语义的前提下，把项目从 Web 最终交付路线迁移到 Windows 桌面工作站路线，并优先在原仓库内完成这次迁移。

这就是当前锁定的 requirement baseline。
