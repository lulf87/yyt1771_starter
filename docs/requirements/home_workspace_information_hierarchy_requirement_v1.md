# Home / Workspace Information Hierarchy Requirement v1

Updated on 2026-04-01
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `home_workspace_shell_requirement_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`
- `afas_full_postprocessing_migration_requirement_v1.md`

## Purpose

这份 requirement 用于冻结 home / workspace 的信息层级与跨页面 journey 表达。

它解决的不是新的算法问题，也不是新的视觉主题问题，而是下面 4 类会直接导致页面继续“看起来内容很多、但用户不知道下一步”的实现歧义：

1. 首页哪些内容必须默认可见，哪些只能按需展开
2. 首页哪些内容属于工程模式，不应继续占据 operator 默认视区
3. workspace 第一屏到底只服务什么，哪些内容必须下沉到第二屏或折叠区
4. 首页和 workspace 应如何共同表达同一条 operator journey

如果本文件与：

- `home_workspace_shell_requirement_v1.md`

冲突，则：

- `home_workspace_shell_requirement_v1.md` 继续负责 shell target、`observation_window` 排除、`A-B` 显性条件、DOM/API/test-anchor guardrails
- 本文件负责 home / workspace 的默认可见层级、按需展开边界、工程模式边界、journey flow 和结果卡语义

如果本文件与：

- `live_setup_freeze_roi_tracking_requirement_v1.md`

冲突，则在 live setup operator flow、ROI-first 语义、A/B 重算与确认条件上，仍以 `live_setup_freeze_roi_tracking_requirement_v1.md` 为准。

如果讨论的问题是：

- 首页是否仍应显示 hero / journey / `当前任务` 说明层
- 首页默认是否还允许 `系统 / 配置 / 模式` 这类大卡并列出现
- 首页是否应改成面向一线工人的极简操作面
- 完成态是否只保留 `保存数据 / 进入分析`
- 首页是否允许大面积解释性空白

则必须继续联读：

- [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md)

如果讨论的问题是：

- workspace 默认界面是否应向 AFAS 项目的信息和操作模型收敛
- workspace 默认首屏到底该保留哪些分析内容
- replay / rail / summary / version / adjustment 哪些应退出默认首屏
- workspace 的导出区、参数区和结果区应如何像 AFAS 一样组织

则必须继续联读：

- [analysis_studio_afas_alignment_requirement_v1.md](./analysis_studio_afas_alignment_requirement_v1.md)

---

## Problem Being Resolved

当前首页与 workspace 的主要问题，不在于视觉 token 不统一，而在于：

- 操作主流程
- 按需复核
- 工程调试

这三类信息仍然容易被放到同一视觉层里。

结果是：

- 页面中每个 section 单独看都合理
- 但用户很难迅速判断当前步骤的主任务
- 首页像“系统能力总览”
- workspace 像“研发试验台”

而现有 canonical requirement 已经明确：

- Home = `Launch & Control Cockpit`
- Workspace = `Analysis Studio`

因此现在需要冻结的不是“再加什么卡片”，而是：

> 哪些信息属于默认主流程，哪些只在需要时出现，哪些应退到工程模式。

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
- 修改 ROI / A-B detection algorithm
- 修改 AFAS analysis contract

它的主语是：

> operator-facing page hierarchy and journey expression for the current cockpit + studio shell

---

## Information Layers

从本 requirement 起，home / workspace 都必须显式区分 3 类信息：

### L1. Default Visible

每次进入页面都应看到，且直接服务当前主任务。

### L2. On-Demand Reveal

只有当用户进入复核、高级调整或补充查看时，才需要展开。

### L3. Engineering Mode

开发、联调、验收或追溯时才需要；不得继续占据默认 operator 视区。

这 3 类信息不能再继续共享同一级视觉语义。

---

## Frozen Decisions

### R1. Home must support one operator path by default

首页默认可见的 operator path 冻结为：

```text
[1] 设备就绪
[2] 预览冻结
[3] ROI 定义
[4] A/B 确认
[5] 目标温度确认
[6] 开始测试
```

其中：

- `auto-live-preview` 仍然属于首页 flow 起点
- `ROI` 仍是 setup 主几何
- `A-B` 仍是 ROI 内锚点，而不是与 ROI 并列的一套主几何
- `Compact Result` 只在完成后承接 `[7] 打开分析`

因此首页不能继续被表达成“并列大区块集合”，而必须被表达成：

- 当前状态下最该做的下一步

### R2. Home default-visible content is strictly limited

首页默认可见内容冻结为：

1. 压缩状态条：
   - `Health`
   - `Profile`
   - `Mode`
   - `Current Temp`

2. 大尺寸 `Live Preview`

3. 一级主动作：
   - `Freeze`

4. `ROI` 可视定义与必要的视觉调整入口

5. 一个默认可见的检测主控制：
   - `Sensitivity`

6. `A/B` 状态摘要与必要时的重新抓帧 / 重算提示

7. `温度设置（Target Temp / Manual Mode / Power） + Confirm Settings`

8. `Start Live Run`

9. `Compact Result`，仅保留：
   - target session id
   - target session state
   - `Af95`
   - `Open Workspace`

### R3. Home on-demand content must not occupy the default operator viewport

首页下列内容必须进入按需展开层，不得继续在默认视区摊开：

1. ROI 数值字段：
   - `Center X`
   - `Center Y`
   - `Width`
   - `Height`
   - `Angle`

2. Detection 高级项：
   - `Foreground`
   - `Threshold Mode`
   - `Min Area`
   - `Ignore Texture`

3. `A/B` 当前坐标只读值、置信度与最近一次自动检测诊断详情

4. Precheck 的完整条目列表

5. 最近 session 列表

6. `Compact Result` 中的 replay snapshot / artifact peek

### R4. Home engineering-mode content must be hidden behind a diagnostic drawer or equivalent reveal

首页下列内容属于工程模式：

1. `Preview FPS`
2. `Measurement Hz`
3. `Protocol Any / Pinned Device / Allowed Models / Serial / IP`
4. raw precheck 输出
5. raw probe 输出
6. local bring-up hint
7. `Run Mock Session`
8. `Run Replay Session`
9. 完整 recent sessions 历史
10. 非 operator 主流程的保存型按钮，如 `Save Definition`

这些内容可以保留，但不得继续占据默认 operator 主视区。

允许的实现形式包括：

- drawer
- collapsible diagnostics panel
- explicit engineering-mode reveal

但不允许继续与首页主流程并列抢第一屏。

### R5. Home layout must be state-driven rather than feature-gallery-driven

首页布局应表达为：

```text
Top: Journey Ribbon (steps 1-6)
Main Left: Live Preview
Main Right: Current Task Card
Lower Area: Diagnostics Drawer
Completion Entry: Compact Result
```

这里冻结的不是像素布局，而是页面语义：

- 首页应像“当前步骤任务页”
- 而不是“所有能力平铺页”

`Current Task Card` 在不同状态下应只突出当前一步所需的最少动作。

### R6. Workspace default first screen only serves replay, AFAS, and decision

workspace 默认第一屏冻结为只服务下面这些内容：

1. 顶部 `session / state / current stage`
2. `Replay Curve`
3. `Run AFAS Analysis`
4. `Channel selector`
5. AFAS result card
6. `Overview` chart
7. `Selected Channel` chart
8. 压缩版 `Adjustment Status`
9. `Export PNG / Export Excel`

workspace 第一屏的主问题必须是：

> 这条曲线分析出了什么结果，是否需要继续调整或导出

### R7. Workspace second-screen or on-demand content must move behind the main decision flow

workspace 下列内容必须进入第二屏、折叠区或明确的次级层：

1. `Key Frames`
2. AFAS 完整参数编辑器
3. `Draft Editor` 完整表单
4. `Version History` 全列表
5. `Active Selection` 全量字段
6. `Automatic Basis`
7. `Extraction & Analysis Context`
8. `Future Adjustment Controls`

这条 requirement 的重点不是删除这些能力，而是：

- 它们不能继续抢占第一屏主决策位置

### R8. Workspace engineering/provenance content must not compete with the operator answer surface

workspace 下列内容属于工程 / provenance / traceability 层：

1. `Open Summary API`
2. `Open Detail API`
3. 过于技术化的 provenance 字段，如：
   - `feature_point_px`
   - `metric_norm`
   - `threshold_value`
   - `component_area`
   - `baseline_px`
4. “coming soon / read-only” 说明型卡片

这些内容可以保留在：

- engineering drawer
- provenance panel
- explicit traceability reveal

但不应继续与 AFAS 结果卡争夺第一屏注意力。

### R9. Canonical cross-surface journey is frozen to 8 steps

home / workspace 的 canonical operator journey 冻结为：

```text
[1] 设备就绪
[2] 预览冻结
[3] ROI 定义
[4] A/B 确认
[5] 目标温度确认
[6] 开始测试
[7] 打开分析
[8] AFAS 出点 / 导出
```

其中：

- 首页主要承接 `[1]` 到 `[6]`
- workspace 主要承接 `[7]` 到 `[8]`

允许：

- 首页 ribbon 只显示 1~6
- workspace ribbon / rail 显示 1~8，并将前 6 步标记为已完成

但不允许再让两个页面看起来像两份彼此无关的内容清单。

### R10. Workspace main workline order is frozen

workspace 主工作线顺序冻结为：

1. `Replay Review`
2. `Run AFAS`
3. `AFAS Result Card`
4. `Overview + Selected Channel Charts`
5. `Adjustment / Export`

这意味着：

- `Automatic Basis`
- `Context`
- `Version History`
- `Future Adjustment Controls`
- `API links`

都不应再出现在结果卡之前的默认主工作线位置。

### R11. AFAS result card must act as the first-screen answer card

AFAS result card 至少必须承载：

1. `Result Status`
2. `As`
3. `Af-tan`
4. `ΔT`
5. `Max Slope`
6. 当前参数摘要
7. 缺失结果提示

它的语义应是：

- 当前分析是否已经得出可读结论
- 当前结论是什么
- 这一结论是基于什么参数摘要得出的

而不是继续只做“技术结果列表”。

### R12. Existing shell guardrails remain active

本 requirement 不替换下列既有冻结规则：

1. `Compact Result -> Open Workspace` 的 deterministic targeting
2. `observation_window` 不回流首页默认 operator path
3. `A-B` 在低置信 / 重算 / 最新帧无效时必须显性抬高用于诊断复核
4. 首轮 shell refactor 必须保留 `id` / `data-testid` / route / API / schema contract

也就是说：

- 这份 requirement 负责“内容该在第几层”
- 旧 shell requirement 继续负责“什么不能被打断”

---

## Acceptance Checks

### A. Home default-visible checks

1. 首页默认可见内容能清晰串成 `设备就绪 -> Freeze -> ROI -> A/B -> Target Temp -> Start Live Run`
2. 默认第一屏里不存在与该主流程并列的大量工程诊断字段
3. `Compact Result` 默认只保留目标 session 摘要与 workspace 入口

### B. Home on-demand / engineering separation checks

1. ROI 数值字段、Detection 高级项、A/B 数值编辑器不在默认第一屏平铺
2. `Preview FPS / Measurement Hz` 不在默认 operator 视区
3. probe 参数与 raw 输出进入 diagnostics / engineering reveal
4. mock / replay launcher 不作为首页主流程一级 CTA

### C. Workspace first-screen checks

1. 第一屏主视觉优先级是 replay / AFAS / result / summary
2. `Key Frames` 不在第一屏主工作线抢焦点
3. `Future Adjustment Controls` 不在第一屏默认展开
4. provenance / API / coming-soon 内容不压过 AFAS result card

### D. Journey checks

1. 首页和 workspace 能被理解为同一条 8 步旅程的两个 surface
2. workspace 的第一屏自然接续首页 `Open Workspace` 之后的分析动作

### E. Result-card checks

1. AFAS result card 能回答“当前结果是什么”
2. AFAS result card 能回答“当前状态是否可读”
3. 缺失 AFAS 数据时显示 neutral empty state，而不是把错误噪音当作默认控制流

---

## Current Non-Conformance Risk

如果不增加这份 requirement，当前最可能继续出现的 requirement drift 有：

1. 首页继续把 operator flow、复核入口、工程调试混在同一层
2. workspace 第一屏继续同时展开决策信息、traceability 信息和 future-phase 占位
3. flow rail 继续只表达系统阶段，不表达用户旅程
4. AFAS result card 继续像“技术结果卡”，而不是“页面答案卡”

因此从本 requirement 起，凡是涉及：

- 首页 / workspace 默认可见内容
- 首页 / workspace 的按需展开边界
- 工程模式内容的默认可视区边界
- cross-surface journey expression
- AFAS result card 语义

都必须优先联读本文件。
