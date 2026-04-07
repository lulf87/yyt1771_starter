# Office-Hours Requirement Baseline v1

Updated on 2026-04-01
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

当前与本项目直接相关的 `/office-hours` 输出共有 7 份：

1. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-140012.md`
   标题：`YY/T 1771 浏览器分析工作台需求收敛 v1`

2. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-141929.md`
   标题：`奥氏体转变全链路测试工作站需求重整 v2`
   `Supersedes: lulingfeng-main-design-20260321-140012.md`

3. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260322-222900.md`
   标题：`Live Setup 交互需求澄清与冻结建议 v1`
   `Supersedes: lulingfeng-main-design-20260321-141929.md`

4. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260327-102500.md`
   标题：`首页 Launch & Control Cockpit 与 Workspace Analysis Studio 信息架构收敛 v1`
   `Follows: lulingfeng-main-design-20260322-222900.md`

5. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260329-095356.md`
   标题：`首页与 Workspace 信息层级、Journey Flow 与工程模式收敛 v1`
   `Follows: lulingfeng-main-design-20260327-102500.md`

6. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260329-175019.md`
   标题：`首页一线工人极简操作面与隐藏调试入口收敛 v1`
   `Follows: lulingfeng-main-design-20260329-095356.md`

7. `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260329-190658.md`
   标题：`Analysis Studio 向 AFAS 内容模型收敛 v1`
   `Follows: lulingfeng-main-design-20260329-175019.md`

因此从 lineage 看：

- 第 1 份不是“当前最新需求”，而是最早的 framing
- 第 2 份覆盖了第 1 份的主产品定义
- 第 3 份不是推翻第 2 份，而是在第 2 份已经确定“要做 full-chain live workstation”的前提下，进一步冻结 live setup 的交互需求
- 第 4 份不是推翻前 3 份，而是在 live setup requirement 已冻结后，把首页和 workspace 的页面职责、信息架构和视觉系统收口成当前产品 shell
- 第 5 份不是再次改 shell 角色，而是在 shell 角色已经确定后，把“默认可见 / 按需展开 / 工程模式”和跨页面 journey flow 冻结成当前页面层级基线
- 第 6 份不是再改一次 shell 角色或 hierarchy 框架，而是把首页进一步收成面向一线工人的极简操作面，并把调试信息整体降到隐藏入口
- 第 7 份不是再改一次首页，而是把 workspace 默认分析界面收成更接近 AFAS 的内容模型，并把研发过程类信息整体后移

需要额外说明的是：

- 2026-03-29 在 office-hours 之后，又补了一轮 `plan-eng-review`
- 那一天的 `plan-eng-review` 没有再新增新的 office-hours 产品方向
- 它只把两个最容易分叉的实现边界补成了 repo requirement addendum：
  - worker-minimal cockpit 的 ready / handoff / save / state-machine 边界
  - AFAS-style workspace 的 trigger / fallback / replay placement / compatibility 边界

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

### Round 4 added

第 4 份文档不是再次改产品目标，也不是再改一次 live setup requirement。

它补的是此前一直没有冻结的浏览器 shell 层问题：

- 首页到底承担什么
- workspace 到底承担什么
- `ROI` 和 `Point A / Point B` 在首页中应如何分层
- `af-analyzer` 应该借什么，不该借什么

这轮真正锁定的是：

- 首页收敛为 `Launch & Control Cockpit`
- workspace 收敛为 `Analysis Studio`
- 首页不再承担完整 replay / AFAS 分析页职责
- workspace 保留三栏分析骨架，但强化中心主工作区和右侧 sticky summary
- `ROI` 是首页主几何，`A-B` 保留但降级为次级层
- `Future Adjustment Controls` 收进折叠区或抽屉，不占默认主视区
- 首页和 workspace 应共享一套 dark glass + Morandi 风格的视觉 token，而不是继续各自一套卡片语义

### Round 5 added

第 5 份文档不是再次改产品目标，也不是再次改 shell 命名。

它补的是第 4 份之后仍然没有冻结的页面层级问题：

- 哪些内容必须默认可见
- 哪些内容只在复核或高级调整时展开
- 哪些内容属于工程模式，不应继续占据 operator 默认视区
- 首页和 workspace 应如何共同表达同一条 operator journey
- AFAS result card 应如何从“技术结果卡”升级为“第一屏答案卡”

这轮真正锁定的是：

- home / workspace 必须显式区分 `default visible / on-demand reveal / engineering mode`
- 首页默认只服务单一 operator path，而不是功能总览
- workspace 第一屏默认以 AFAS 分析和决策为主，replay 只保留轻量上下文角色
- cross-surface journey 冻结为从设备就绪到 AFAS 出点 / 导出的 8 步
- provenance / API / placeholder / coming-soon 内容不得继续与主流程争夺默认焦点

### Round 6 added

第 6 份文档不是再次改页面命名，也不是只提“删掉几段文字”。

它补的是上一轮之后仍然存在的一个落地问题：

- 首页虽然已经不再是完整分析页
- 但默认第一屏仍然太像解释页、联调页，而不够像一线工人的操作面

这轮真正锁定的是：

- 首页默认不再展示 shell 标题、journey 说明、`当前任务` 说明块
- 首页默认不再展示 `系统 / 配置 / 模式` 这类工程状态大卡
- 首页默认首屏必须由 `实时预览 + 操作列` 填满，不允许留下大面积解释性空白
- 首页完成态不再显示摘要卡，而是显示 `保存数据 / 进入分析` 的动作区
- `Save Definition` 退出 operator flow
- `ROI 定义 -> ROI 框选`
- `查看 ROI 几何字段 -> 查看ROI参数`
- `ROI 角度` 进入 `查看ROI参数`
- 手动 `A/B` 校正面板必须保持显式展开，不能在刷新后自动回收

### Round 7 added

第 7 份文档不是推翻 `Analysis Studio` 这个页面角色，而是进一步冻结：

- workspace 默认首屏应该像什么
- 哪些内容应以 AFAS 风格的分析任务为主语
- 哪些研发过程信息必须退出默认首屏

这轮真正锁定的是：

- workspace 默认分析界面向 AFAS 的内容模型收敛
- 默认首屏以 `通道选择 -> 分析参数 -> 总览图 -> 单通道切线分析 -> 分析结果 -> 导出` 为主线
- replay 继续保留，但降级为 session context，而不是默认 hero
- rail、sticky summary、version、adjustment、future controls、API / provenance 等内容整体后移
- workspace 继续跟首页共享视觉 token，但不再默认渲染产品说明型 hero

---

## Why The Old Docs Felt Duplicated

如果只看标题，7 份文档容易显得像 7 套需求。

其实它们分别解决的是 7 个不同层次的问题：

1. 第 1 份：
   先把“这到底是 replay 工具还是设备工作站”的叙事梳理出来

2. 第 2 份：
   把主产品定义正式定成 full-chain live workstation

3. 第 3 份：
   把 live workstation 里最容易返工的一段，也就是 live setup 交互，冻结成可实现规则

4. 第 4 份：
   把首页和 workspace 的页面职责、信息架构与视觉收口冻结下来

5. 第 5 份：
   把首页 / workspace 的默认可见层级、按需展开边界、工程模式边界与跨页面 journey 表达冻结下来

6. 第 6 份：
   把首页进一步收成面向一线工人的极简操作面，并把完成态与调试入口收口到更直接的动作语义

7. 第 7 份：
   把 workspace 默认分析界面进一步收成 AFAS 风格的分析工作面，并把研发过程类信息整体后移

所以真实关系不是“互相冲突”，而是：

- `Round 1` 提供结构视角
- `Round 2` 提供产品主目标
- `Round 3` 提供 live setup 交互冻结
- `Round 4` 提供首页 / workspace 的产品壳层分工与视觉收口
- `Round 5` 提供首页 / workspace 的页面层级、journey flow 与结果语义收口
- `Round 6` 提供首页的一线工人极简操作面、隐藏调试入口与完成态动作区收口

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

### 3A. Screen Architecture

当前推荐的页面职责分工冻结为：

- Home = `Launch & Control Cockpit`
- Workspace = `Analysis Studio`

它们不是一页的两个 tab，也不是谁替代谁，而是：

- 首页承接系统状态、live setup、launch / control、diagnostics、最近结果入口
- workspace 承接 replay、AFAS、adjustment、version history 和决策支持

这意味着：

- 首页不再承担完整 replay / AFAS analysis 展示
- workspace 也不再只是“打开看一眼结果”的附属页

当前 baseline 已经倾向保留两个不同入口，但让它们的职责边界更清楚。

同时，从 2026-03-29 起，screen architecture 还必须继续遵守：

- home / workspace 都显式区分 `default visible / on-demand reveal / engineering mode`
- 首页默认只服务单一 operator path
- workspace 默认第一屏以 AFAS 分析和决策为主，replay 只保留轻量上下文角色
- provenance / API / placeholder / coming-soon 内容不得继续占据默认主焦点
- cross-surface operator journey 被固定为从设备就绪到 AFAS 出点 / 导出的 8 步

并且，从 2026-03-29 的最新一轮 office-hours 起，首页 operator-facing surface 还必须继续遵守：

- 首页默认首屏不再渲染 shell 标题、journey 说明和 `当前任务` 说明块
- 首页默认首屏不再渲染 `系统 / 配置 / 模式` 大卡
- 首页默认首屏必须收成 preview-led 的一线工人操作面
- 首页完成态必须优先回答“保存，还是进入分析”，而不是显示迷你结果摘要卡
- `Save Definition` 不再属于当前 operator path
- `ROI 角度` 必须进入 `查看ROI参数`
- 调试信息必须统一退到不抢眼的隐藏入口

并且，从同日的 engineering review addendum 起，首页实现还必须继续遵守：

- 默认首屏仍要保留一个极简 `ready` 信号
- 完成态虽然收成动作区，但 `进入分析` 仍必须显示并指向唯一的 target session
- `保存数据` 在当前 scope 内应被实现成已持久化结果的确认 / 导出动作，而不是新的 persistence contract
- 温控设置确认之后如果目标温度、功率或方式改变，必须清掉 confirmed 状态
- 温控设置确认之后如果 ROI / sensitivity 变化导致 `A/B` 重算，`开始测试` 必须暂时失效，直到新结果重新进入 valid 状态

并且，从同日的 workspace engineering review addendum 起，Analysis Studio 的默认分析界面实现还必须继续遵守：

- `afas_available=1` 时，workspace 应自动加载 active channel 分析，而不是继续把显式 `Run AFAS` 作为默认主步骤
- `通道选择` 与已提交的参数变化应自动刷新分析结果
- `afas_available=0`、single-channel、summary-only / no-detail 这几种状态都必须有明确降级路径，而不是退回旧的研发过程卡堆
- replay 在默认首屏中的落位应固定为 AFAS 主分析区上方的 compact context strip / foldout
- 第一轮 AFAS-style refactor 仍必须保持现有 DOM / JS / test-anchor compatibility

如果讨论的问题是：

- 首页 `Compact Result` 应该把用户带去哪个 workspace
- 首页是否还允许 `observation_window / metric_box` 回到默认 operator path
- `A-B` 在什么状态下必须重新显性供诊断复核
- 首轮 shell refactor 能否重排 DOM 但保持现有 `id` / `data-testid` / API contract 稳定

则必须优先联读：

- [home_workspace_shell_requirement_v1.md](./home_workspace_shell_requirement_v1.md)

如果讨论的问题是：

- 首页哪些内容必须默认可见
- 首页哪些内容只应按需展开
- 哪些内容应视为工程模式
- workspace 第一屏的主焦点到底是什么
- workspace 哪些内容必须进入第二屏或折叠区
- cross-surface journey 应如何表达
- AFAS result card 应承担什么语义

则必须优先联读：

- [home_workspace_information_hierarchy_requirement_v1.md](./home_workspace_information_hierarchy_requirement_v1.md)
- [analysis_studio_afas_alignment_requirement_v1.md](./analysis_studio_afas_alignment_requirement_v1.md)
- [analysis_studio_afas_alignment_state_fallback_requirement_v1.md](./analysis_studio_afas_alignment_state_fallback_requirement_v1.md)
- [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md)
- [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md)

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

但从 2026-03-25 起，如果讨论的问题是：

- 当前项目是否已经具备 `AFAS/` 目录中的完整后处理能力
- 是否已经包含 `AFAS/` 中拿到数据后的全部功能
- 是否已经具备与 `AFAS/` 等价的预处理、平滑、切线分析图和导出

则必须优先联读：

- [afas_full_postprocessing_migration_requirement_v1.md](./afas_full_postprocessing_migration_requirement_v1.md)

也就是说：

- 当前 baseline 继续承认 live 结果目标里有 `As / Af / Af95`
- 但“完整 AFAS 后处理产品能力”现在已被定义为一条更高要求的独立 requirement

### 5. Measurement Model

measurement definition 这层现在应视为已冻结到下面 3 个视觉原语：

- `analysis_roi`
- `metric_box`
- `point_a_px / point_b_px`

但从 2026-03-25 开始，这 3 个原语的语义需要联读：

- [live_setup_roi_ab_window_requirement_v1.md](./live_setup_roi_ab_window_requirement_v1.md)

并且要按下面的新用户语义解释：

- `analysis_roi`
  = Auto Detect Points 的主搜索区域
  = 当前 live setup operator flow 中唯一需要用户定义的主几何
- `metric_box`
  = 在 `A-B` 确定之后生成和调整的 `Observation Window`
  = 后续 live run 阶段限制形变观测范围的旋转长方形
  = UI 文案应优先叫 `观测窗口` 或 `测试范围`
- `point_a_px / point_b_px`
  = 目标物体的主几何锚点
  = 当前首页流程中由 auto detect 生成并在 live run 中持续更新
  = 历史数据模型仍可保留点坐标字段，但当前首页流程不再要求手工摆点

但从 2026-03-25 的后续澄清开始，如果讨论的问题是：

- 相机是否在项目启动后自动开始预览
- `Freeze` 是否取代 `Fetch Preview / Start Live Preview / Stop Live Preview`
- ROI 是否成为 setup 与 live tracking 的唯一主几何
- `A-B` 是否按 ROI 的局部横轴求取
- 是否去除 `Draw Window / Rotate Window`
- 是否引入 ROI 旋转手柄、ROI angle 字段、灵敏度、当前温度显示、目标温度确认按钮、以及 live run 期间实时刷新的 `A-B`

则必须优先联读：

- [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md)

也就是说：

- 旧 baseline 继续保留上一轮 `ROI -> A-B -> observation window` 的历史解释价值
- 但当前 operator-facing live setup workflow 现在已经被新的 `Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking` requirement 覆盖

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

7. 在当前首页的信息架构里，`ROI` 必须继续作为主几何出现

8. `A-B` 必须保留可见和可诊断能力，但视觉层级必须低于 `ROI`
   它们更适合作为 detection result、advanced setup 或诊断复核层，而不是与 ROI 并列的一级主操作；当前首页流程不再要求手工摆点

9. `Draw Window` 不是 `Auto Detect Points` 的前置条件

10. 历史上曾存在的顺序是：
   `Draw ROI -> manual A/B or Auto Detect Points -> Draw Window`
   这条只保留旧 baseline 解释价值，不再代表当前首页最高优先级 operator flow

11. Auto Detect Points 必须在 `ROI` 内寻找目标物体横向或纵向主跨度对应的两点，而不是在预定义 observation window 内沿固定轴取极值，也不应输出任意斜向直径

12. observation window 必须在 `A-B` 已确定后，根据 `A-B` 连线方向生成默认姿态

13. 后续观测方向必须绑定到 observation window 的：
   - `long_axis`
   - 或 `short_axis`

但从 2026-03-25 当前轮新的 operator workflow 冻结开始，上面第 9-13 条不再代表当前最高优先级用户流。
只要问题涉及：

- 取消 `Draw Window / Rotate Window`
- ROI 成为唯一 tracking geometry
- ROI-local horizontal point detection
- ROI 旋转后重新取点
- 开始测试后实时刷新 `A-B`

都必须优先以：

- [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md)

为准。

### 7. Product Shell Direction

如果要把当前产品壳层方向收成一句话，当前推荐的是：

`Home = Launch & Control Cockpit；Workspace = Analysis Studio`

首页只保留 4 个一级区块：

1. `Hero / Status`
   - `System / Profile / Mode / Current Temp`

2. `Main Stage`
   - `Live Preview + Freeze + Start/Stop`
   - `Setup Definition`
     - `ROI`
     - `Detection`
     - `Temperature`

3. `Ops & Diagnostics`
   - `System Precheck / Probe Camera`
   - `Session Launcher / Recent Sessions`

4. `Compact Result`
   - 最新一次 session 摘要
   - `Open Workspace`

这条方向的意思不是删掉首页已有能力，而是：

- 让首页重新聚焦 live setup 和控制
- 把深度 replay / AFAS analysis 收回 workspace

### 8. Workspace Direction

workspace 不需要推翻重来，当前推荐继续保留三栏逻辑，但把信息层级收紧：

- Topbar
  - `Session / State / 快速状态`

- Grid
  - 左：更细、更轻的 sticky `Flow Rail`
  - 中：`Replay + AFAS + Adjustment` 主工作区
  - 右：sticky `Summary / Version / Quick Actions`

更具体地说：

- 中间第一屏优先显示 `Replay Curve + AFAS KPI strip + AFAS Analysis`
- `AFAS Analysis` 主面板继续分成：
  - `Overview`
  - `Selected Channel`
  - `Results & Parameters`
- 导出按钮保留在右上
- `Key Frames` 和 `Adjustment MVP` 下沉到第二屏
- 右侧 summary 只保留：
  - `Current Stage`
  - `Session Summary`
  - `Active Selection`
  - `Adjustment Status`
  - `Version History`
  - `Quick Actions`
- 当前只读占位的 `Future Adjustment Controls` 不应继续占据默认可视区，应收进折叠区或抽屉

### 9. Visual System Direction

`af-analyzer` 当前最值得借的是视觉语言，而不是页面结构。

当前 baseline 推荐：

- 首页与 workspace 共用一套 theme token
- 采用 dark glass + Morandi accent 的视觉方向
- 收敛 `.panel`、`.workspace-summary-card`、`.workspace-adjustment-card`、`.live-preview-panel`、`.live-definition-panel`
  到同一套 glass-card 规则

也就是说：

- 借皮肤
- 不借骨架

### 10. Hardware / Runtime Direction

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

### 11. Temporal Sampling Follow-up

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

把 4 份 `/office-hours` 合并后，当前可以正式冻结的结论如下。

### Product-level frozen conclusions

- 主产品是 full-chain browser workstation
- 浏览器是最终交互入口
- replay/workspace 是离线验证和复盘链，不再是主产品替代品
- commissioning 与 experiment/analysis 是两个并列 lane，但后者是主线
- 首页现在应明确承担 `Launch & Control Cockpit` 角色
- workspace 现在应明确承担 `Analysis Studio` 角色

### Workflow-level frozen conclusions

- 主分析链继续保持：
  `Frame -> ShapeMetric -> SyncPoint -> Curve -> Result`
- 主交互链至少应包含：
  `precheck/probe -> live preview -> measurement definition -> live run -> result/evidence`
- 首页默认只保留最新结果摘要与 workspace 入口，不再承担完整 replay / AFAS analysis

### Live-setup-level frozen conclusions

- ROI、观测窗口、A/B 点是 measurement definition 的 3 个核心视觉原语
- 但顺序不是“先画 observation window 再找点”，而是：
  `ROI -> A/B -> observation window`
- `metric_box` 的用户语言应改成 `观测窗口` 或 `测试范围`
- `analysis_roi` 是 auto detect 的主搜索边界
- auto detect 的目标是在 ROI 内找到目标物体横向或纵向主跨度对应的两点
- observation window 的作用是限制 live run 阶段的后续观测区域
- `Stop Live Preview` 实际应表现为 freeze，而不是 clear
- live setup 必须支持无刷新 restart
- measurement definition 必须支持图上可视化编辑，而不只是表单输入
- 在当前首页里，`ROI` 必须是主几何，`A-B` 必须保留但退到次级层

### Workspace-level frozen conclusions

- workspace 保留三栏分析骨架，不推翻重来
- 左侧 flow 应收成更轻的 sticky rail
- 中间第一屏优先承载 replay curve、AFAS KPI 和 AFAS 主分析区
- `Key Frames` 与 `Adjustment MVP` 下沉到第二屏
- 右侧 sticky summary 只保留决策信息
- `Future Adjustment Controls` 收进折叠区或抽屉，不占默认主视区

### Visual-system-level frozen conclusions

- 首页与 workspace 应共用一套主题 token 和 glass-card 语义
- `af-analyzer` 只作为视觉语言参考，不作为页面结构模板

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

### Result questions

1. `Af95` 在最终结果体系里的位置到底是：
   - 主结果之一
   - 兼容性输出
   - 仅辅助结果

2. `latest result` 对导出/报告的正式语义仍需继续冻结

### Live setup questions

1. auto-detect 在不同目标族上如何稳定定义 ROI-local 的起始 / 实时锚点

### Workspace questions

1. 第一屏的 `AFAS KPI strip` 具体包含哪些指标最合适
2. `Future Adjustment Controls` 在未来真实可交互之前，更适合折叠卡片还是抽屉承载
3. workspace topbar 是否需要额外显示当前温度或 profile 信息

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

4. 如果你要看首页 / workspace 为什么要分成 `Launch & Control Cockpit` 和 `Analysis Studio`
   回看：
   `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260327-102500.md`

5. 如果你要看首页 / workspace 为什么必须把主流程、按需复核和工程模式分层，以及为什么需要跨页面 journey
   回看：
   `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260329-095356.md`

6. 如果你要看 repo 内当前 shell 实施边界，包括 `Compact Result` 路由、首页 A/B 显性规则和 DOM/API guardrails
   优先看：
   [home_workspace_shell_requirement_v1.md](./home_workspace_shell_requirement_v1.md)

7. 如果你要看 repo 内当前默认可见 / 按需展开 / 工程模式边界，以及 journey / AFAS result-card 语义
   优先看：
   [home_workspace_information_hierarchy_requirement_v1.md](./home_workspace_information_hierarchy_requirement_v1.md)

8. 如果你要看首页为什么必须去掉 hero / journey / `当前任务`、隐藏 `系统 / 配置 / 模式`，并把完成态收成 `保存数据 / 进入分析`
   优先看：
   [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md)

9. 如果你要看首页在极简完成态下，为什么还必须保留 tiny ready cue、明确的 session handoff 和 post-confirm state machine
   优先看：
   [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md)

10. 如果你要看 workspace 为什么必须进一步收成 AFAS-style 分析工作面，以及为什么参数触发、fallback、replay 落位和兼容护栏都要继续锁死
   优先看：
   [analysis_studio_afas_alignment_requirement_v1.md](./analysis_studio_afas_alignment_requirement_v1.md)
   [analysis_studio_afas_alignment_state_fallback_requirement_v1.md](./analysis_studio_afas_alignment_state_fallback_requirement_v1.md)

11. 如果你要追溯“为什么 replay/workspace 还在产品里”
   回看：
   `/Users/lulingfeng/.gstack/projects/yyt1771_starter/lulingfeng-main-design-20260321-140012.md`

---

## One-Line Summary

当前 `/office-hours` 的综合结论已经不是“继续在 replay 工作台上补功能”，而是：把项目正式当成 full-chain browser workstation 来推进，把首页收敛成 `Launch & Control Cockpit`，把 workspace 收敛成 `Analysis Studio`，并进一步把首页收成面向一线工人的极简操作面、把调试信息退到隐藏入口、把完成态收成 `保存数据 / 进入分析` 的动作区，同时把 workspace 默认分析界面进一步收成 AFAS 风格的分析工作面。
