# Office-Hours Requirement Baseline v1

Updated on 2026-03-22
Status: CANONICAL_SYNTHESIS_OF_OFFICE_HOURS_OUTPUTS

## Purpose

这份文档用于把多次 `/office-hours` 产生的需求文件整合成一份当前可执行的基线。

它回答 4 个问题：

1. 哪几份 `/office-hours` 文档是当前需求来源
2. 它们之间哪些结论是继承关系，哪些已经被后文覆盖
3. 当前项目真正应该把哪套产品定义当成主线
4. 以后继续做需求、计划和实现时，应该优先引用哪份结论

这份文档不是新的 brainstorming。
它是对已有 `/office-hours` 结果的合并、去重、收口。

---

## Source Lineage

当前与本项目直接相关的 `/office-hours` 输出共有 3 份：

1. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-140012.md`
   标题：`YY/T 1771 浏览器分析工作台需求收敛 v1`

2. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-141929.md`
   标题：`奥氏体转变全链路测试工作站需求重整 v2`
   `Supersedes: lulingfeng-main-design-20260321-140012.md`

3. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260322-222900.md`
   标题：`Live Setup 交互需求澄清与冻结建议 v1`
   `Supersedes: lulingfeng-main-design-20260321-141929.md`

因此从 lineage 看：

- 第 1 份不是“当前最新需求”，而是最早的 framing
- 第 2 份覆盖了第 1 份的主产品定义
- 第 3 份不是推翻第 2 份，而是在第 2 份已经确定“要做 full-chain live workstation”的前提下，进一步冻结 live setup 的交互需求

---

## What Each Round Actually Added

### Round 1 added

第 1 份文档的核心贡献不是最终产品定义，而是两个重要 framing：

- 浏览器仍然是主入口
- 产品里天然存在两条不同心智模型：
  - `Commissioning Lane`
  - `Analysis Lane`

其中最有价值的结论是：

- `precheck/probe` 和 `session/workspace` 不应继续被混成同一类任务
- replay/workspace/adjustment 这一条链本身是一条独立价值链

### Round 2 added

第 2 份文档对项目目标做了实质性升格，把主产品定义从：

- “浏览器中的 replay 结果复核工具”

改成：

- “奥氏体转变全链路测试工作站”

这轮真正锁定的是：

- 相机采集
- 温控联动
- ROI / 点位 / 观测策略确认
- live 同步采样
- `As/Af` 结果输出
- 证据包留存

同时它也明确了：

- replay/workspace/adjustment 仍然保留
- 但它们不再主导产品叙事
- 它们应降级为离线验证、复盘、算法验证和结果查看能力

### Round 3 added

第 3 份文档不是又换了一次产品目标，而是把第 2 份里“live setup”这一步真正落到可操作的需求上。

它补清了此前一直模糊的东西：

- `Stop Live Preview` 的语义
- preview stop/restart 的生命周期
- ROI 如何被操作员定义
- A/B 点必须如何可视化
- `metric_box` 在用户语言里应该如何理解

它把“measurement definition”从后端字段，推进成了真实 UI 工作流。

---

## Why The Old Docs Felt Duplicated

如果只看标题，3 份文档容易显得像 3 套需求。

其实它们分别解决的是 3 个不同层次的问题：

1. 第 1 份：
   先把“这到底是 replay 工具还是设备工作站”的叙事梳理出来

2. 第 2 份：
   把主产品定义正式定成 full-chain live workstation

3. 第 3 份：
   把 live workstation 里最容易返工的一段，也就是 live setup 交互，冻结成可实现规则

所以真实关系不是“互相冲突”，而是：

- `Round 1` 提供结构视角
- `Round 2` 提供产品主目标
- `Round 3` 提供 live setup 交互冻结

---

## Canonical Baseline

从现在开始，和本项目相关的 `/office-hours` 结论，应统一按下面这份综合基线理解。

### 1. Product Definition

本项目当前的正式产品定义应为：

一个以浏览器为主入口的奥氏体转变测试工作站，完成从设备就绪检查、实时预览、观测定义、同步采样、曲线生成，到最终 `As/Af` 结果输出与证据留存的完整链路。

这意味着：

- 它不是单纯 replay 复核工具
- 它不是单纯设备 bring-up 工具
- 它也不是桌面 GUI 方向

### 2. Product Lanes

虽然主产品目标已经升级为 full-chain workstation，但第 1 份文档里提出的“两条 lane”仍然应该保留，因为它解释了现有产品结构。

当前推荐的产品心智模型是：

- `Commissioning Lane`
  - `precheck`
  - `probe`
  - SDK / 设备 / profile readiness

- `Experiment & Analysis Lane`
  - live preview
  - measurement definition
  - live run
  - telemetry / result
  - replay / workspace / result review

两条 lane 都存在，但主产品主线应是第二条。

### 3. Replay / Workspace Positioning

replay、workspace、adjustment 仍然重要，但定位已经变化：

- 它们不是主产品的替代品
- 它们是 full-chain live 路线的离线验证和复盘能力

因此后续文档和实现中，不应再把 replay/workspace 写成“项目真正目标”。

### 4. Result Scope

结果目标已经不是只有 `Af95`。

当前正式结果目标应为：

- `As`
- `Af`
- 必要时保留 `Af95`
- 证据包
  - telemetry
  - key frames
  - definition
  - result
  - event trace

### 5. Measurement Model

measurement definition 这层现在应视为已冻结到下面 3 个视觉原语：

- `analysis_roi`
- `metric_box`
- `point_a_px / point_b_px`

并且要按下面的用户语义解释：

- `analysis_roi`
  = 粗粒度分析区域
- `metric_box`
  = 真正参与 A/B 搜索和位移观测的旋转长方形
  = UI 文案应优先叫 `观测窗口` 或 `测试范围`
- `point_a_px / point_b_px`
  = 锁定的两点

### 6. Live Setup Interaction Contract

这部分以第 3 份文档为准，应视为当前必须遵守的交互冻结规则：

1. `Stop Live Preview`
   的产品语义应为：
   `停止流 + 保留最后一帧可编辑`

2. 同一 run 上必须支持：
   - start preview
   - freeze
   - restart preview
   并且不要求用户刷新页面

3. 新建 run 后必须正确重置旧的 preview/editor 状态

4. ROI、观测窗口、A/B 点都必须支持图上可视化编辑

5. A/B 点必须可见，不能只停留在数值输入框

6. auto-detect 的建议结果应以 overlay 呈现，而不是只改表单数值

### 7. Live Setup UX Direction

如果要把交互方案收成一句话，当前推荐的是：

`Freeze-first 实验设置向导`

建议的操作顺序是：

1. Start Live Preview
2. Freeze Current Frame
3. Draw ROI
4. Define Observation Window
5. Place / adjust A and B
6. Save Definition
7. Optional Resume Preview

这不是一个“设计偏好”问题，而是当前最能解释真实操作反馈的一条主线。

### 8. Hardware / Runtime Direction

第 2 份文档锁定的硬件方向继续有效：

- camera:
  `MV-CA060-11GM`
- temperature controller:
  `LU92XX + RS485 + Modbus RTU`
- current high-confidence defaults:
  - `slave=1`
  - `19200 / 8N1`
  - `reg 0 / x10`
  - `reg 4 / x256`
  - `reg 264 / x10`

但这些仍然受 bench 约束：

- `264 vs 258`
- `reg 0` 的正式业务命名
- `reg 4` 的启停语义

在 bench 之前，不应把这些写成“真机已确认事实”。

### 9. Temporal Sampling Follow-up

在 2026-03-23 的后续 requirement 收口里，新增了一条正式 follow-up：

- [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md)

这份 follow-up requirement 的作用是把此前口语化的“刷新率太低”拆成：

- camera resulting fps
- preview display fps
- measurement sample hz
- artifact capture hz

并正式冻结：

- `50 Hz synchronized measurement` 为当前 locked baseline
- `100 Hz synchronized measurement` 为 stretch goal
- full-frame browser preview `50/100 Hz` 不是当前 baseline requirement

因此从现在开始，凡是涉及：

- 预览刷新率
- 50 Hz / 100 Hz 目标
- 温升与形变量曲线的时域分辨率

都不应只引用本文件，而应联读那份 temporal sampling requirement。

---

## Frozen Conclusions

把 3 份 `/office-hours` 合并后，当前可以正式冻结的结论如下。

### Product-level frozen conclusions

- 主产品是 full-chain browser workstation
- 浏览器是最终交互入口
- replay/workspace 是离线验证和复盘链，不再是主产品替代品
- commissioning 与 experiment/analysis 是两个并列 lane，但后者是主线

### Workflow-level frozen conclusions

- 主分析链继续保持：
  `Frame -> ShapeMetric -> SyncPoint -> Curve -> Result`
- 主交互链至少应包含：
  `precheck/probe -> live preview -> measurement definition -> live run -> result/evidence`

### Live-setup-level frozen conclusions

- ROI、观测窗口、A/B 点是 measurement definition 的 3 个核心视觉原语
- `metric_box` 的用户语言应改成 `观测窗口` 或 `测试范围`
- `Stop Live Preview` 实际应表现为 freeze，而不是 clear
- live setup 必须支持无刷新 restart
- measurement definition 必须支持图上可视化编辑，而不只是表单输入

### Temporal-sampling-level frozen conclusions

- “刷新率”必须拆分，不得再用单一词汇覆盖多个速率概念
- 真正服务于曲线可信度的 requirement 主语是 synchronized measurement cadence
- `50 Hz` 是当前 locked baseline
- `100 Hz` 是 stretch goal
- preview 流畅度重要，但不能替代 measurement cadence requirement

---

## Still Open

即使整合后，下面这些问题仍然没有被 `/office-hours` 文档彻底解决，后续应继续显式跟踪。

### Product questions

1. 第一优先用户更偏：
   - 实验操作员
   - 测试/算法工程师
   - 现场联调工程师

2. replay/live 是否最终进入同一个 analysis workspace，还是保留两个不同入口

### Result questions

1. `Af95` 在最终结果体系里的位置到底是：
   - 主结果之一
   - 兼容性输出
   - 仅辅助结果

2. `latest result` 对导出/报告的正式语义仍需继续冻结

### Live setup questions

1. UI 上 `Stop Live Preview` 是否直接改名为 `Freeze Frame`
2. 是否保留独立 `Fetch Preview`
3. ROI 改变时，观测窗口和 A/B 点的 reset/clamp 规则是什么
4. auto-detect 是否同时建议观测窗口
5. 观测窗口 angle 是拖拽主导还是数字输入主导

### Hardware questions

1. `264 vs 258`
2. `reg 0` 正式命名
3. `reg 4` 启停语义
4. LU92XX 现场 bench profile 是否与当前高置信默认值一致

---

## How To Use This Baseline

以后继续推进项目时，推荐按下面规则使用文档：

1. 如果你只想知道“当前 office-hours 的综合结论是什么”
   先看本文件

2. 如果你要看全链路 live run 的工程拆解
   再看：
   - [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
   - [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
   - [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)

3. 如果你要看 live setup 交互为什么要这么设计
   回看：
   `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260322-222900.md`

4. 如果你要追溯“为什么 replay/workspace 还在产品里”
   回看：
   `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-140012.md`

---

## One-Line Summary

当前 `/office-hours` 的综合结论已经不是“继续在 replay 工作台上补功能”，而是：把项目正式当成 full-chain browser workstation 来推进，同时保留 commissioning lane 与 replay/workspace 作为辅助链，并优先冻结 live setup 的交互语义。
