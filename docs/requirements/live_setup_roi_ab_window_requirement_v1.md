# Live Setup ROI / A-B / Observation Window Requirement v1

Updated on 2026-03-25
Status: CANONICAL_REQUIREMENT_ADDENDUM
Superseded in operator workflow scope by: `live_setup_freeze_roi_tracking_requirement_v1.md`

## Purpose

这份 requirement 用于冻结 live setup 里 4 个最容易被混淆的视觉语义：

- `analysis_roi`
- `Auto Detect Points`
- `point_a_px / point_b_px`
- `observation_window`

这轮 requirement 的目标不是讨论 UI 样式，而是把下面这件事写成权威结论：

> `ROI` 的作用是限定需要搜索和分析的图像区域；`A-B` 是主几何锚点；`observation_window` 是在 `A-B` 确定之后，为 live run 阶段限制后续形变观测区域而定义的矩形，而不是 Auto Detect Points 的前置条件。

---

## Problem Being Resolved

当前实现和用户真实意图之间存在一个关键偏差：

- 现实现里，auto detect 会直接在 `metric_box / observation_window` 内找前景连通域，然后沿固定轴取两个极值点
- 用户真正需要的是：
  - 先在 `ROI` 内找到目标物体
  - 再在该物体上确定一组主锚点 `A-B`
  - 然后再由 `A-B` 生成或辅助生成后续观测矩形

因此这轮 requirement 的本质，是把：

- `ROI 用于筛选目标区域`
- `A-B 用于确定目标物体的主几何`
- `observation_window 用于限制后续 live run 的观测范围`

这三件事重新拆开并冻结。

---

## Supported Target Families

当前 requirement 明确承认，在 `ROI` 内待检测目标至少存在两类高层视觉形态：

### Family A: guidewire-like

可理解为：

- 黑 - 白 - 黑
- 目标很细
- 可能弯曲
- 大部分背景是空白或弱纹理背景

典型目标：

- 导丝
- 细长弯曲结构

### Family B: balloon-like

可理解为：

- 白 - 黑 - 白
- 目标主体占据画面较大比例
- 两侧背景为空白或弱纹理背景

典型目标：

- 球囊
- 较宽的亮/暗主体结构

这份 requirement 不强行锁定具体实现算法，但明确锁定：

> Auto Detect Points 必须支持这两类 target family，且不能把“只支持某一个固定 polarity 或固定几何方向”当成 requirement 合规实现。

---

## Frozen Workflow

从现在开始，live setup 的权威工作流冻结为：

1. Freeze / fetch preview frame
2. Draw ROI
3. 直接二选一：
   - manual `Point A`
   - manual `Point B`
   - 或 `Auto Detect Points`
4. 在 `A-B` 已经存在后，再执行 `Draw Window`
5. 系统根据 `A-B` 连线方向生成默认 observation window
6. 操作员再人工调节：
   - window 大小
   - window 位置
   - window 角度
7. 操作员选择后续观测方向：
   - `long_axis`
   - `short_axis`
8. Save definition
9. Start live run

这条顺序意味着：

- `Draw Window` 不再是 `Auto Detect Points` 的前置要求
- `Auto Detect Points` 也不应再依赖先画 observation window 才能工作

---

## Frozen Semantics

### R1. ROI is the primary detection search region

`analysis_roi` 的正式语义冻结为：

- 限定 Auto Detect Points 的搜索区域
- 排除与目标无关的背景区域
- 为 manual A/B 放点提供允许范围

`analysis_roi` 不只是“粗粒度分析区域”，它还是：

> auto detect 的第一层搜索边界

因此从 requirement 角度看：

- Auto Detect Points 必须首先受 `ROI` 约束
- 不能要求先定义 `observation_window` 才能开始找 `A-B`

### R2. Auto Detect Points must find an axis-constrained dominant point pair inside ROI

`Auto Detect Points` 的正式目标冻结为：

> 在 `ROI` 内找到目标物体，并返回该物体横向或纵向主跨度对应的两个点。

这里“主跨度对应的两个点”指：

- 允许只在横向或纵向中二选一
- 不允许输出任意斜向直径或任意角度的最长弦
- 必须基于 ROI 内实际目标物体，而不是基于预设 observation window
- 横向和纵向二者中，应选择主跨度更显著的一组点

从 requirement 语言看，合规实现至少应满足：

- object-shape-aware
- ROI-bounded
- axis-constrained-to-horizontal-or-vertical

如果算法只能输出：

- 与目标无关的固定模板点
- 或依赖预设 observation window 方向的 axis extremes

则该实现不满足当前 requirement。

### R3. A-B are the primary geometry anchors

`point_a_px / point_b_px` 的正式语义冻结为：

- 表示目标物体上的两端点或两主锚点
- 既可以由人工指定
- 也可以由 auto detect 生成

`A-B` 一旦确定，应视为：

> 后续 observation window 默认生成和 live run 观测方向定义的主几何依据

### R4. Observation window is post-A/B geometry, not pre-A/B search geometry

`metric_box` 的正式用户语义仍应叫：

- `Observation Window`
- 或 `观测窗口`

但其 requirement 语义发生冻结修正：

- 它不是 auto detect 的必要前置条件
- 它不应主导最初的 A/B 搜索
- 它应在 `A-B` 形成之后被创建、生成或调整

它的正式用途是：

> 在后续执行 `Start Live Run` 后，把形变观测限制在该矩形区域内。

因此当前 requirement 明确规定：

- `observation_window` 是 live-run observation aperture
- 不是 ROI 的替代物
- 也不是 auto-detect 的第一搜索几何

### R5. Draw Window should derive its default pose from the A-B segment

当操作员点击 `Draw Window`，系统默认行为应冻结为：

- 先读取已确定的 `A-B`
- 以 `A-B` 连线方向生成默认矩形姿态
- 再允许操作者继续调整大小、位置、角度

这意味着：

- 默认 window angle 应与 `A-B` 连线对齐
- 默认中心、长轴、短轴应围绕 `A-B` 形成合理初值

### R6. Observation direction is constrained to the window's long or short axis

后续 live run 的观测方向，不应允许任意自由角度表达。

当前 requirement 冻结为：

- `observation_axis = long_axis`
- 或 `observation_axis = short_axis`

也就是说：

- 后续位移或形变观测方向
- 必须绑定到 observation window 的长轴或短轴

这条 requirement 的目的，是保证：

- geometry definition 简洁
- 用户心智稳定
- downstream tracking semantics 可解释

### R7. Manual Point A / Point B must be available immediately after ROI

只要 `ROI` 已经存在，系统就必须允许：

- 直接手工设置 `Point A`
- 直接手工设置 `Point B`

不能要求：

- 先画 observation window
- 再允许定义 A/B

### R8. Low-confidence auto detect remains allowed, but must be clearly framed as advisory

如果 auto detect 结果低置信度，系统仍可返回结果，但必须明确提示：

- 这是建议值
- 需要人工核验
- 必要时应直接手工调整 `A-B`

这条 requirement 允许低置信自动结果存在，但不允许把低置信结果伪装成 definitive geometry。

---

## Current Non-Conformance Statement

按当前 requirement，下面这种实现不合规：

- auto detect 先在 `observation_window` 内做搜索
- 再沿 window 的固定 axis 取两个 extremes

因为这会导致：

- `ROI` 失去应有的 primary-search 角色
- `A-B` 变成 window 的附属产物
- 自动点位受 window 预设轴向绑架，而不是先在 ROI 内决定横向或纵向主跨度

因此后续实现与计划都应把当前逻辑视为：

- `requirement-misaligned`
- 需要修正

---

## Outcome

这轮 office-hours 风格收口后的最终 requirement 表达应为：

> Live setup 必须采用 `ROI-first, A-B-second, Window-after` 的几何定义顺序。Auto Detect Points 的任务是在 ROI 内找到目标物体横向或纵向主跨度对应的两个点；它不得依赖预先定义的 observation window，也不得输出任意斜向直径。Observation window 只能在 A-B 确定后生成和调整，其用途是限制后续 live run 的观测区域；后续观测方向仅允许绑定到该矩形的长轴或短轴。
