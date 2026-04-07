# Home / Workspace Shell Requirement v1

Updated on 2026-04-01
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `office_hours_requirement_baseline_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`

## Purpose

这份 requirement 用于把首页与 workspace 的壳层职责，冻结成可直接实施的规则。

它解决的不是新的算法问题，而是下面 4 个会直接导致前端返工的实现歧义：

1. 首页 `Compact Result -> Open Workspace` 到底应该打开哪个 session
2. `observation_window / metric_box` 是否还属于当前首页 cockpit 的 operator-facing UI
3. `Point A / Point B` 虽然被降级，但在什么状态下必须重新显性并进入诊断复核
4. 首页 / workspace 在第一轮重排时，哪些 DOM / API / test anchor 必须保持稳定

如果这份 requirement 与：

- `office_hours_requirement_baseline_v1.md`

中更宽泛的首页 / workspace 壳层描述冲突，则在 home / workspace shell scope 内，以本文件为准。

如果这份 requirement 与：

- `live_setup_freeze_roi_tracking_requirement_v1.md`

中的 live setup 几何与 operator flow 冲突，则仍以 `live_setup_freeze_roi_tracking_requirement_v1.md` 为准。

如果讨论的问题是：

- 首页 / workspace 哪些内容必须默认可见
- 哪些内容只应按需展开
- 哪些内容应退到 engineering mode
- cross-surface journey 应如何表达
- AFAS result card 在第一屏应承担什么语义

则必须继续联读：

- [home_workspace_information_hierarchy_requirement_v1.md](./home_workspace_information_hierarchy_requirement_v1.md)

如果讨论的问题是：

- 首页是否还应显示 shell 标题、journey 文案、`当前任务` 说明
- 首页是否应隐藏 `系统 / 配置 / 模式` 和其他调试信息
- 首页完成后是否只保留 `保存数据 / 进入分析`
- `Save Definition` 是否应退出 operator flow
- `A/B` 诊断展开层是否应保持锁定展开

则必须继续联读：

- [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md)
- [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md)

---

## Problem Being Resolved

当前 baseline 已经把方向收成：

- Home = `Launch & Control Cockpit`
- Workspace = `Analysis Studio`

但对于实现团队来说，仍有 4 个“方向对了也可能做岔”的点：

### 1. `Compact Result` 的 session 选择规则不明确

如果首页只说“显示最新一次 session 摘要 + Open Workspace”，但没有定义最新到底指什么，那么实现者很容易各写各的：

- 最新创建
- 最新运行中
- 最新完成
- 最新有 detail artifact

最终会造成首页入口不稳定。

### 2. `observation_window` 的历史语义仍容易回流进首页

旧 requirement 里 `ROI -> A-B -> observation_window` 仍有历史解释价值，但更高优先级的 live setup requirement 已经把当前 operator flow 收敛成：

`auto-live-preview -> Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking`

如果不再单独冻结一次，首页改版时很容易把旧的 `Draw Window / Rotate Window / metric_box` 语义又带回来。

### 3. `A-B` 被降级后，显性规则还不够清楚

当前已经明确：

- `ROI` 是主几何
- `A-B` 不能删除
- `A-B` 必须保留可见和可诊断能力

但如果没有写清“什么时候必须重新显性”，工程实现就容易把它做成永远缩在次级层里，导致低置信检测、最新帧无效或重算后仍然不够可诊断。

### 4. 第一轮 shell refactor 的实现边界还没有进 repo canonical requirement

当前较具体的 guardrails 主要还在 office-hours 产出里，尚未成为 repo 内的独立 canonical requirement。

这会带来一个实际风险：

实现者如果只看 `docs/requirements/`，可能会做出：

- 视觉上看起来更对
- 但打断现有 `id`
- 打断 `data-testid`
- 打断 `app.js` 绑定
- 或顺手改了 API contract

这种“看起来是优化，实际上 blast radius 很大”的改动。

---

## Scope Boundary

这份 requirement 只约束下面这类工作：

- [index.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/index.html)
- [workspace.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/workspace.html)
- [app.css](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.css)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)

它不直接要求：

- 新增 backend API
- 修改 API response contract
- 修改 session schema
- 修改 ROI / A-B detection algorithm
- 修改 AFAS analysis contract

这份 requirement 的主语是：

> operator-facing home / workspace shell behavior for the first-pass cockpit + studio refactor

---

## Frozen Decisions

### R1. Home and workspace remain separate surfaces

当前 shell 必须继续保持两个不同页面语义：

- Home = `Launch & Control Cockpit`
- Workspace = `Analysis Studio`

因此第一轮改版：

- 不应把两者合并成单页
- 不应把 workspace 主分析区塞回首页
- 不应让首页重新承担完整 replay / AFAS analysis

Home 的职责是：

- launch
- control
- diagnostics
- latest-result entry

Workspace 的职责是：

- replay review
- AFAS analysis
- adjustment
- version / decision support

### R2. `Compact Result` must use deterministic workspace targeting

首页 `Compact Result` 只服务一个被选中的 session target。

这个 target 的选择顺序冻结为：

1. 最新一个能够打开 detail-backed workspace 的 session
2. 如果没有，则退到最新一个能够打开 summary-only workspace 的 session
3. 如果两者都没有，则 `Open Workspace` 必须保持 disabled 或 hidden，并显示 empty state

这里的 requirement 重点不是一定要依赖某个具体 artifact 名称，而是：

- 首页入口必须有确定性
- 不允许“有时打开空 workspace，有时打开旧 session，有时打开 404”

因此 `Compact Result` 必须同时显示：

- 目标 session id
- 目标 session state
- 该摘要到底对应哪一个被选中的 session

### R3. `observation_window` is not part of the current home cockpit flow

在当前首页 cockpit 的 operator-facing flow 中，下列概念不得重新回到默认可视区：

- `Draw Window`
- `Rotate Window`
- `metric_box`
- `observation_window`

原因不是这些概念永远不存在，而是：

- 当前更高优先级 requirement 已经把首页 live setup 收敛为 ROI-first
- `observation_window` 只保留历史 requirement 解释价值与其他上下文价值

因此第一轮首页改版必须遵守：

- 首页默认 UI 不展示 `observation_window` 的 primary control
- 首页默认 UI 不展示 `observation_window` 的 secondary control
- 首页默认 UI 不要求用户通过 window 相关步骤才能完成 current operator flow

如果后续某个非首页上下文仍需要保留 `observation_window` 语义，那也必须明确属于：

- 历史 requirement 解释
- replay / offline context
- future phase

而不是当前首页 cockpit 的默认 operator path

### R4. `Point A / Point B` stay secondary, but must escalate for diagnostic review

`Point A / Point B` 在首页中不得再与 `ROI` 抢一级主操作位。

当前冻结为：

- `ROI` 是 setup 主几何
- `A-B` 是 ROI 内起始 / 实时锚点
- `A-B` 可以进入次级区域，如：
  - detection result
  - advanced setup
  - diagnostic reveal

但只要出现下面任一状态，`A-B` 的可见和诊断能力就必须被重新显性抬高：

1. auto detect 返回 advisory / low-confidence 结果
2. ROI 或 sensitivity 变化后系统重新计算了 `A-B`
3. 最新抓帧上没有得到有效 `A-B`

在这些状态下，首页必须满足：

- `A-B` overlay 可见
- 用户能够直接看到当前自动结果与诊断状态
- 页面上有明确状态提示，说明当前 `A-B` 需要诊断复核、重新抓帧或重新计算

这条 requirement 不强制具体 widget 必须是：

- inline card
- accordion
- drawer
- modal

但强制要求：

> 当 `A-B` 需要 operator diagnosis 时，不能继续把它埋在默认不可见的次级层里；这不等于恢复首页手动摆点流程。

### R5. First-pass shell refactor must preserve current integration anchors

第一轮首页 / workspace 壳层改版必须遵守下面的工程边界：

1. 现有功能等价节点的 `id` 必须保留
2. 现有测试锚点的 `data-testid` 必须保留
3. 可以新增 wrapper、section、layout container
4. 不得因为页面重排而修改当前 backend API contract
5. 不得因为页面重排而修改当前路由 contract
6. 不得因为页面重排而修改当前 schema contract

对 [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js) 的第一轮改动边界冻结为：

- 允许新增状态 class
- 允许适配新增 wrapper
- 允许在不改变现有 ID contract 的前提下重排 DOM 查询位置
- 不允许顺手重写核心交互绑定关系

这条 requirement 的目的，是控制 blast radius：

- 先完成 shell 收口
- 再决定是否需要下一轮行为重构

### R6. Workspace placeholders must not occupy the first-screen default focus

workspace 中明确属于 future-phase、read-only、coming-soon 的占位信息，不得继续占据默认第一屏的主注意力区。

当前明确包括：

- `Future Adjustment Controls`

第一轮 workspace 改版必须把它处理成下面两类之一：

1. collapsed by default
2. hidden behind explicit reveal action

它不必在第一轮就拥有真实行为，但必须：

- 不抢默认主工作区
- 不压过 `Replay Curve`
- 不压过 `AFAS Analysis`
- 不压过右侧 sticky summary

---

## Acceptance Checks

实现合规的最小验收应至少覆盖下面这些点：

### A. Home routing and empty-state checks

1. 当存在 detail-backed workspace target 时，首页 `Open Workspace` 打开该 target
2. 当 detail 缺失但 summary-only workspace 可用时，首页 `Open Workspace` 打开该 target
3. 当两者都不可用时，首页展示 empty state，且 CTA 不可触发错误导航

### B. Home setup-surface checks

1. 首页默认 UI 不出现 `Draw Window / Rotate Window / metric_box / observation_window` 操作位
2. `ROI` 仍是首页 setup 主几何
3. `A-B` 不与 ROI 抢一级主操作位
4. 低置信 / 重算 / 最新帧无效状态下，`A-B` 会重新显性并进入诊断复核

### C. Workspace hierarchy checks

1. 第一屏主视觉优先级仍然是 replay / AFAS / summary
2. `Future Adjustment Controls` 不在默认第一屏主区占位

### D. Integration-anchor checks

1. 现有 `id` 未被无故替换
2. 现有 `data-testid` 未被无故替换
3. 现有 API contract 未发生变化
4. 现有 workspace summary-only fallback 未被破坏

---

## Current Non-Conformance Risk

如果不增加这份 requirement，当前最可能出现的 requirement drift 有：

1. 首页 `Compact Result` 指向不稳定，导致 workspace 入口行为不可预测
2. 首页改版时把 `observation_window` 历史语义重新带回 operator path
3. `A-B` 被“形式上保留、实际上埋没”，低置信或重算后仍然缺少清晰复核入口
4. 视觉重排带来隐性回归，破坏现有 `app.js` 绑定、测试锚点或 API 假设

因此从本 requirement 起，凡是涉及：

- 首页 / workspace 页面职责
- `Compact Result` target 选择
- 首页 `A-B` 次级化与显性条件
- 首轮 shell refactor 的 DOM / API guardrails

都必须优先联读本文件。
