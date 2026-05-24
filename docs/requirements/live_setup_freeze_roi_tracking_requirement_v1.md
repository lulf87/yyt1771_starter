# Live Setup Freeze / ROI / Tracking Requirement v1

Updated on 2026-04-01
Status: CANONICAL_REQUIREMENT_ADDENDUM
Supersedes (where conflicting): `live_setup_roi_ab_window_requirement_v1.md`

## Purpose

这份 requirement 用于冻结当前 live setup 的新操作流和几何语义。

它解决的是下面这件事：

> 相机在项目启动后直接进入实时预览；操作员通过 `Freeze` 取当前静帧；随后只围绕一个可平移、缩放、旋转的 `ROI` 完成起始测试点定义，并在开始测试后持续在该 ROI 内跟踪形变和实时刷新测试点。

这份 requirement 是当前 live setup 的更高优先级 requirement。
如果它与：

- `live_setup_roi_ab_window_requirement_v1.md`
- `office_hours_requirement_baseline_v1.md`

中的旧语义冲突，以本文件为准。

---

## Problem Being Resolved

当前实现仍保留了上一轮 workflow 的痕迹：

- `Create Live Run`
- `Fetch Preview`
- `Start Live Preview`
- `Draw Window`
- `Rotate Window`

以及：

- 先定义 `A-B`
- 再由 `A-B` 生成 `observation_window`

这套心智模型。

用户现在明确要求的不是这条链，而是一条更直接的 operator flow：

1. 启动项目后相机立即进入 live preview
2. 操作员点击 `Freeze` 固定当前帧
3. 操作员只定义一个 ROI
4. 系统在该 ROI 的本地横轴上自动求出起始测试点 `A-B`
5. 后续 tracking 与 live deformation 只发生在该 ROI 内

因此，这轮 requirement 的本质是：

- 去除旧的 preview 按钮式 workflow
- 去除 `Draw Window / Rotate Window` 概念
- 把 `ROI` 升级为 setup 和 tracking 的唯一主几何
- 把 `A-B` 改成 ROI 内局部横轴上的目标边界点

---

## Frozen Operator Workflow

从现在开始，live setup 的权威工作流冻结为：

1. 启动项目
2. 相机自动进入 live preview
3. 操作员点击 `Freeze`
4. 操作员绘制 `ROI`
5. 系统在该 ROI 内自动计算起始 `A-B`
6. 如果当前 frozen frame 不合适，操作员可点击 `解除冻结` 回到 live preview，再重新 `Freeze`
7. 如果需要，操作员可继续调整：
   - ROI 中心点位置
   - ROI 宽高
   - ROI 角度
   - 灵敏度参数
8. 每次重新计算 `A-B` 时，系统都必须重新抓取一帧，并基于这张新帧计算结果
9. 操作员确认温控设置：
   - 目标温度
   - 手动方式
   - 温度功率
10. 点击 `Start Live Run`
11. 进入 live test：
    - 相机恢复实时刷新
    - `A-B` 实时刷新
    - 形变只在该 ROI 内捕捉和更新

这条 workflow 明确意味着：

- 不再要求 `Create Live Run`
- 不再要求 `Fetch Preview`
- 不再要求 `Start Live Preview`
- 不再要求 `Draw Window`
- 不再要求 `Rotate Window`

唯一保留的 preview lifecycle 按钮是：

- `Freeze`
- `解除冻结`

其正式语义是：

- `Freeze`
  - 停止实时预览并保留最后一帧，供 ROI 编辑和起始点重新计算使用
- `解除冻结`
  - 放弃当前 frozen setup frame
  - 返回 live preview
  - 允许操作员重新选择抓帧时机

---

## Frozen UI Actions

### R1. Camera preview starts automatically on app launch

项目启动后，相机必须自动进入实时预览。

因此 UI 上不应再暴露下面 3 个操作按钮：

- `Create Live Run`
- `Fetch Preview`
- `Start Live Preview`

如果系统内部仍保留对应状态或 API，这些都应视为实现细节，而不是 operator-facing workflow。

### R2. `Freeze` and `解除冻结` are the only operator-facing preview lifecycle actions

用户可见的 preview lifecycle 按钮必须冻结为：

- `Freeze`
- `解除冻结`

这意味着：

- 不再保留旧的 `Stop Live Preview`
- 不再保留 `Fetch Preview`
- 不再保留 `Start Live Preview`

其语义分别为：

- `Freeze`
  - 停止当前 live preview
  - 保留最后一帧
  - 进入可编辑 setup 状态
- `解除冻结`
  - 清掉当前 frozen setup frame 的“正在编辑”状态
  - 返回 live preview
  - 等待用户重新 `Freeze`

---

## Frozen Geometry Model

### R3. ROI is the only setup geometry primitive

从当前 requirement 起，setup 阶段的主几何原语冻结为：

- `analysis_roi`

`analysis_roi` 同时承担：

- 搜索区域
- tracking 区域
- 形变观测区域

也就是说：

> 后续 live run 期间只允许在该 ROI 内观测和更新形变。

这意味着旧的：

- `metric_box`
- `observation_window`

不再作为当前 operator flow 的必要用户概念。

### R4. ROI must support translation, resize, and rotation

ROI 必须是一个可旋转矩形，而不是只能轴对齐的框。

用户必须能够通过两种方式修改它：

1. 图上直接操作
   - 拖动平移
   - 拖动缩放
   - 拖动顶部中心的旋转手柄改变角度

2. 右侧参数区直接设置
   - ROI center x
   - ROI center y
   - ROI width
   - ROI height
   - ROI angle

因此当前 requirement 明确要求：

- ROI 参数面板必须保留中心点和大小字段
- 同时新增并保留 `angle` 显示与设置功能

### R5. Any A/B recompute requires a newly captured frame

从当前 requirement 起，规则不再只是“某些参数变化时要不要重算”，而是：

> 只要发生一次新的 `A-B` 计算，就必须先抓一张新帧。

系统必须：

1. 重新抓取一帧
2. 用这张新帧替换当前 frozen setup frame
3. 再重新计算起始 `A-B`

会触发这一流程的事件至少包括：

- ROI 中心点变化
- ROI 尺寸变化
- ROI 角度变化
- 灵敏度变化
- 操作员主动要求重新计算
- `解除冻结` 后重新 `Freeze`

这条触发规则的粒度冻结为“提交型事件”，至少包括：

- 图上拖拽 / 缩放 / 旋转结束时
- ROI 数值字段提交或失焦确认时
- `Sensitivity` 滑块释放或显式确认时
- 操作员点击 `重新计算` 时

也就是说：

- 系统可以在连续拖动或连续滑动过程中只更新本地预览态
- 但不得要求在每一个中间采样点都重新抓帧

这条 requirement 的目的，是避免用户看到的 frozen frame、当前几何定义和 `A-B` 结果错位。

---

## Frozen Point Semantics

### R6. Auto-detected points are defined in ROI-local horizontal axis

起始测试点 `A-B` 的新正式定义是：

> 在 ROI 本地坐标系中，沿 ROI 的横轴（即局部 `0°` 方向）寻找目标物体最远的两个边界点。

这里的关键不是整张图的世界坐标横向，而是：

- 以 ROI 自身角度为准
- 在 ROI 局部横轴方向上做检测

如果 ROI 被旋转，则：

- `A-B` 也必须随之在该旋转后的局部横轴上重新定义

### R6.1. A/B are contour boundary points, not projected points

`A-B` 只有一套正式语义：

> `A-B` 点不是投影点，而是 ROI 局部测量方向下，目标物体最大有效跨度对应的两个真实边界点；形变量曲线必须来源于这同一对 `A-B` 点。

这意味着：

- `point_a_px / point_b_px` 必须表示目标物体轮廓或边界上的真实点
- 系统不得把沿 ROI 方向的数学投影点显示、保存或下发为正式 `A-B`
- 如需在算法内部使用方向坐标、排序或跨度比较，只能作为临时计算量，不得形成第二套对外可见的 `source A/B`、`axis A/B` 或 `projected A/B`
- 实时画面、实时曲线、落盘 telemetry、数据分析入口都必须以同一对正式 `A-B` 为来源

### R7. The target inside ROI follows a blank-object-blank model

当前 requirement 锁定的 operator mental model 是：

- ROI 左侧与右侧是空白区域
- 中间是待测物体

在成像上可抽象为：

- `白 - 黑 - 白`

或更一般地：

- `blank - object - blank`

Auto detect 的目标不是任意找两个显著点，而是：

> 在 ROI 的局部横轴上，找出目标物体在该轴向上的左右边界位置。

### R8. A-B are the starting test points and must update during live run

`A-B` 既是 setup 阶段的起始测试点，也是后续 live run 期间实时更新的可视锚点。

点击 `Start Live Run` 后：

- 相机必须恢复实时刷新
- `A-B` 必须实时刷新
- 以便操作员直接看到 ROI 内最大形变位置变化

### R9. Manual A/B is removed from the current operator flow

当前 live setup requirement 明确取消下面这些 operator-facing 能力：

- 手动放置 `Point A`
- 手动放置 `Point B`
- 手动 `A/B` 校正面板
- 把手动 `A/B` 作为默认 setup 链路的一环

当前合法语义是：

> setup 阶段的 `A-B` 只允许来自自动检测。

---

## Frozen Sensitivity Requirement

### R10. Sensitivity is a first-class setup parameter

系统必须新增一个 operator-facing 参数：

- `sensitivity`

它的正式用途是：

- 区分哪些位置属于物体
- 区分哪些位置属于空白
- 在网格状或多孔结构目标上，允许把网格整体视为同一个连续物体
- 更稳定地确定物体边界

这意味着 sensitivity 不是调试隐藏参数，而是：

> 当前 live setup requirement 的正式组成部分。

### R11. Sensitivity must have a directional meaning

当前 requirement 明确冻结 sensitivity 的 operator-facing 含义：

- sensitivity 调大：
  - 更容易把弱对比、细网格、局部孔洞或小断裂视为同一连续目标
  - 检测结果更宽松、更容易连成一体
- sensitivity 调小：
  - 更严格地区分目标与空白
  - 检测结果更保守、更容易收缩或分裂

UI 或帮助文案至少必须把“大 / 小”的方向意义表达清楚。

### R12. Sensitivity participates in point recomputation

只要 sensitivity 被修改，系统就必须：

- 重新抓取一帧
- 重新计算 `A-B`

---

## Frozen Temperature UI Requirement

### R13. Current temperature display is required

界面上必须新增并显示：

- `Current Temperature`

其数据来源应是当前温控链实时读数。

### R14. Temperature settings require explicit bundled confirmation

界面上必须保留并新增下面这些温控设置项：

- `Target Temperature`
- `Control Mode = Manual`
- `Temperature Power`

并新增一个显式确认动作，例如：

- `Confirm Temperature Settings`

或语义等价的确认按钮。

当前 requirement 明确要求：

- 修改目标温度输入值
- 修改功率值
- 改变温控方式

都不应等价于已经确认下发。

必须有一次显式确认动作，把：

- 目标温度
- 手动方式
- 温度功率

作为一个设置包整体确认。

这 3 个字段的 ownership 当前冻结为：

- 它们属于当前 run 的 operator-confirmed temperature settings bundle
- profile 可以提供默认值，但不能替代界面当前显示值与本次确认值
- route / schema / workflow state 必须能携带：
  - target temperature
  - control mode = manual
  - power
  - confirmed / unconfirmed state
- 具体寄存器写入时机与设备启停细节，仍由 `temp` adapter 决定

---

## Frozen Live Run Behavior

### R15. Live run uses ROI as the deformation capture region

点击 `Start Live Run` 后，后续形变计算和 tracking 必须只发生在当前 ROI 内。

当前 requirement 不再接受旧的解释：

- 先由 `observation_window` 决定后续 tracking 区域

对当前主流程来说，合规语义是：

> ROI = setup search region = live deformation capture region

### R16. Live run preview must remain visually live

进入测试后，操作员不能失去图像反馈。

因此在 `Start Live Run` 后：

- 相机显示必须继续实时刷新
- `A-B` 位置必须叠加在实时画面上更新

---

## Explicit Non-Conformance Statement

按当前 requirement，下面这些旧行为都已不再合规：

- 启动项目后仍要求用户点击 `Create Live Run`
- 仍要求用户点击 `Fetch Preview`
- 仍要求用户点击 `Start Live Preview`
- 没有 `解除冻结`，只能单向 `Freeze`
- 使用 `Draw Window` / `Rotate Window` 作为主设置流程
- 先定义 window，再由 window 驱动 auto detect
- 在整张图世界坐标系里固定按水平/垂直找 `A-B`
- 任何一次 `A-B` 重算仍复用旧 frozen frame
- ROI 改动后不重新抓帧、不重算点位
- 保留手动 `A/B` 作为当前 operator 主流程能力
- 温控确认仍只确认目标温度，而不同时确认手动方式与功率
- 开始测试后不继续实时刷新 `A-B`

---

## Relationship To Older Requirement

`live_setup_roi_ab_window_requirement_v1.md` 仍保留历史价值，但从现在开始：

- 它只适合作为“上一轮 geometry split 的过渡 requirement”阅读
- 只要涉及当前 operator workflow、ROI 旋转、ROI-local point detection、window removal、sensitivity、live A/B refresh，就必须以本文件为准

换句话说：

> 当前 live setup 的权威 requirement 已从
> `ROI -> A-B -> observation window`
> 迁移为
> `Freeze -> rotated ROI -> ROI-local A-B -> live tracking in ROI`
