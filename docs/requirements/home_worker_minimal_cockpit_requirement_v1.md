# Home Worker Minimal Cockpit Requirement v1

Updated on 2026-04-01
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `home_workspace_shell_requirement_v1.md`
- `home_workspace_information_hierarchy_requirement_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`

## Purpose

这份 requirement 用于冻结首页在一线工人场景下的极简操作面规则。

它解决的不是新的算法问题，而是下面这些已经在当前 UI 中暴露出来的产品偏差：

1. 首页默认仍然显示过多说明性文本与工程状态
2. 首页默认仍然保留大块非操作性空白
3. 首页默认仍然把调试 / profile / mode / diagnostics 与主操作链放在同一视觉层
4. `Save Definition` 仍然把 setup 流程切成额外一步
5. 完成实时测试后，首页仍然更像摘要页，而不是下一步动作页
6. 首页仍把手动 `A/B` 当成当前主流程的一部分

这份 requirement 的目标是：

> 把首页真正收成面向一线工人的最小操作界面，而不是面向研发或联调的功能总览页。

如果本文件与：

- `home_workspace_information_hierarchy_requirement_v1.md`

冲突，则：

- `home_workspace_information_hierarchy_requirement_v1.md` 继续定义 `default visible / on-demand reveal / engineering mode` 这三个层级框架
- 本文件在首页 worker-facing minimal cockpit 这个更窄的 scope 内，进一步冻结“默认到底显示什么，不显示什么”

如果本文件与：

- `home_workspace_shell_requirement_v1.md`

冲突，则：

- `home_workspace_shell_requirement_v1.md` 继续定义 `Compact Result -> Workspace` 的确定性目标、`A/B` 显性条件、DOM / API / test-anchor guardrails
- 本文件定义首页默认 operator surface 的收敛方式、完成态动作区与调试入口退场规则

如果本文件与：

- `live_setup_freeze_roi_tracking_requirement_v1.md`

冲突，则在 live setup 的 ROI-first 语义、A/B 复算条件和温度确认语义上，仍以 `live_setup_freeze_roi_tracking_requirement_v1.md` 为准。

如果讨论的问题是：

- 首页默认是否还需要一个极简 `ready` 信号
- 完成态只剩 `保存数据 / 进入分析` 后，`进入分析` 到底对应哪个 session
- `保存数据` 在当前 scope 内到底是导出 / 确认，还是新的持久化动作
- 温控设置确认之后若 ROI / sensitivity / A/B 又发生变化，`开始测试` 如何回退

则必须继续联读：

- [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md)

---

## Scope Boundary

这份 requirement 只约束下面这类工作：

- [index.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/index.html)
- [app.css](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.css)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)
- 与首页 handoff 直接相关的 [workspace.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/workspace.html)

它不直接要求：

- 修改 ROI / A-B detection algorithm
- 修改 AFAS analysis contract
- 重做 session schema

但如果现有 home route / schema / config 还无法承载当前 run 的温控设置包：

- 目标温度
- 手动方式
- 温度功率
- confirmed / unconfirmed 状态

则必须做最小 supporting contract extension。

它冻结的是：

> operator-facing minimal cockpit behavior, naming, and completion handoff on home

---

## Primary User

从本 requirement 起，首页默认用户画像冻结为：

- 一线工人 / 操作员
- 目标是完成一次实时 setup 和实时测试
- 不需要默认看到 profile、mode、mock/runtime、API、artifact、FPS/Hz 这类工程信息

因此首页必须优先回答下面 6 个问题：

1. 当前看到的实时画面是什么
2. 是否已经冻结
3. ROI 在哪里
4. `A/B` 是否已经自动定位正常
5. 温度、手动方式和功率是否已经确认
6. 现在能否开始测试 / 测完后能否保存并进入分析

凡是不能直接服务这 6 个问题的内容，都不得继续占据首页默认首屏。

---

## Frozen Decisions

### R1. Canonical shell names remain, but they must leave the default operator viewport

文档层继续保留：

- Home = `Launch & Control Cockpit`
- Workspace = `Analysis Studio`

但首页默认 UI 不再强制渲染下面这些说明型壳层内容：

1. 产品编号型角标，如 `YYT1771`
2. 大标题型 shell 名称，如 `启动与控制驾驶舱`
3. 说明型副标题 / 引导段落
4. `当前任务` 这类解释型标题和长说明
5. journey 大卡中的说明型 copy

也就是说：

> shell name 仍然是 requirement 和实现中的 canonical 名称，但不再占据一线工人的默认视觉焦点。

### R2. Home default-visible content is reduced to the minimum live operator chain

首页默认可见内容冻结为：

1. 语言切换
2. 小型当前温度显示
3. 大尺寸实时预览
4. `Freeze / 解除冻结`
5. `ROI 框选`
6. 默认可见的检测主控制：
   - `Sensitivity`
7. `A/B` 状态摘要
8. 温控设置：
   - 目标温度
   - 手动方式
   - 温度功率
9. `Confirm Temperature Settings`
10. `开始测试`
11. 完成后：
   - `保存数据`
   - `进入分析`

下列内容不得继续留在首页默认首屏：

- `系统`
- `配置`
- `模式`
- `Launch & Control Cockpit` hero 文案
- `当前任务` 说明块
- 预览尺寸说明型提示文案
- `Compact Result` 的摘要说明文本

### R3. Layout must be preview-led and must not leave explanation-only whitespace

首页第一屏布局冻结为：

```text
主区：实时预览
辅区：操作列
完成后：动作区
调试：弱入口
```

对布局语义的强约束是：

1. 宽屏下不得保留独立 hero 区
2. 宽屏下不得保留独立 journey 大卡
3. 宽屏下不得保留仅承载说明文字的大空白面板
4. 如果有多余空间，应优先用于：
   - 放大预览
   - 提高 ROI / A/B 可读性
   - 承载操作列
   - 承载完成态动作区

不允许再出现：

- 左侧大块空白 + 右侧解释卡
- 右侧大块状态卡 + 左侧说明卡

### R4. Engineering and diagnostics content must move behind an inconspicuous entry

下列内容统一归入 `Engineering Mode / Diagnostics` 隐藏入口：

1. `系统 / 配置 / 模式`
2. `Preview FPS / Measurement Hz`
3. profile / backend / mock-runtime 说明
4. raw precheck / raw probe
5. device protocol / serial / IP / allowed models
6. `Run Mock Session`
7. `Run Replay Session`
8. recent sessions 全列表
9. API / payload / artifact 入口

允许的实现形式包括：

- 顶部弱视觉按钮
- gear / more 入口
- footer 轻量链接
- drawer / popover / collapsed diagnostics sheet

但不允许继续把这些内容作为首页默认主视区的平级模块。

### R5. Post-run home must become an action dock, not a summary card

实时测试完成后，首页不再显示大块 `Compact Result` 摘要卡。

首页完成态冻结为一个轻量 completion dock，只服务当前完成结果的动作与显式重置动作：

1. `保存数据`
2. `进入分析`
3. `新测试`

其中 `进入分析` 必须在视觉上与同一区域的动作按钮保持一致，不得退化成普通文本链接；`新测试` 必须带二次确认，避免 operator 误触后清空当前完成态。

允许保留极轻的一行上下文，例如：

- session id
- 已完成 / 已保存

但不得继续展示：

- 三列 `session / state / AF95` 大卡
- replay snapshot
- “这里保持单一 workspace 入口” 之类说明文本

首页在完成后要回答的问题是：

> 现在是保存、进入分析，还是明确开始一次新测试。

而不是要求用户再读一次首页摘要。

完成后的当前测试结果必须在首页与数据分析页之间保持稳定。除非用户点击 `新测试`，首页不得因为重新进入、刷新、或从数据分析页返回而自动创建新的 live setup run 或清空当前完成结果。

### R6. `Save Definition` is removed from the operator flow

`Save Definition` 从当前首页 operator path 中删除。

原因冻结为：

1. 它是工程中间态按钮，不是一线工人的业务动作
2. 它会把连续 setup 流程切成额外一步
3. 它会误导用户以为“还没保存就不能继续”

从本 requirement 起，首页 operator path 应为：

```text
Freeze
-> ROI 框选
-> 自动 A/B
-> 温控设置确认
-> 直接开始测试
```

也就是说：

- 不再要求单独点击 `保存定义`
- `Confirm Temperature Settings` 是 setup 完成态的最后一个显式确认动作
- 在 ROI 有效、最新自动 `A/B` 有效、温控设置包已确认的前提下，页面必须直接进入可开始测试状态

### R7. `ROI 定义` and `查看 ROI 几何字段` are renamed for operator language

当前 operator-facing 命名冻结为：

- `ROI 定义` -> `ROI 框选`
- `查看 ROI 几何字段` -> `查看ROI参数`

这条 requirement 的重点不是机械换词，而是把控件语义收成：

- 一个是动作：
  - 框选 ROI
- 一个是参数查看：
  - 查看 ROI 参数

而不是继续让控件听起来像内部数据结构编辑器。

### R8. ROI angle moves into the ROI-parameter reveal

`ROI 角度` 保留可调能力，但退出默认首屏主视区。

从本 requirement 起：

- `ROI 角度` 与 `Center / Width / Height` 同层
- 统一进入 `查看ROI参数`
- 首页默认主视区只保留 ROI 的直接框选与视觉反馈

不再允许 `ROI 角度` 继续单独占据首页一级操作位。

### R9. Manual A/B is removed from the current home operator flow

从本 requirement 起，首页默认 setup 流程不再保留：

- 手动 `A/B` 校正入口
- 手动 `Point A / Point B` 摆放
- 手动 `A/B` 面板的显隐状态管理

首页当前对 `A/B` 的合法表达应收敛为：

- 当前自动结果是什么
- 当前结果是否有效
- 如果无效，是否需要先重新抓帧并重算

也就是说：

> 当前首页要解决的是“如何得到可靠的自动 A/B”，而不是“如何长期维护一套手动摆点子流程”。

### R10. `进入分析` remains the handoff to workspace, but home no longer previews the workspace for the user

首页完成态中的 `进入分析` 继续承担进入 workspace 的动作。

但首页不再承担：

- 迷你 workspace 摘要
- 迷你 AFAS 摘要
- 迷你 replay 摘要

Home 与 Workspace 的语义边界在这一轮进一步冻结为：

- Home：完成测试、保存、交接
- Workspace：真正的分析、复核、导出

### R11. `保存数据` is an operator-facing persistence action, not a pre-run setup save

首页完成态新增的 `保存数据`，语义冻结为：

- 保存 / 固化当前测试产物
- 或在系统已自动持久化时，提供面向操作员的显式保存确认 / 导出入口

它不是：

- `Save Definition` 的替代名字
- pre-run 的 setup save

因此 `保存数据` 只能出现在完成态，不得重新回流到 setup 阶段。

### R12. Default operator copy should stay Chinese-first

默认 operator surface 的文案应以中文为主。

允许：

- 保留 `中文 / EN` 切换

但不允许：

- 在首页默认首屏大面积混排中英文说明
- 让英文说明卡再次占据操作空间

---

## Practical Consequence

这一轮 requirement 锁定后的首页，应更接近：

- 工位操作界面
- 设备操作台

而不再接近：

- 产品说明页
- 工程联调页
- 研发试验台

如果后续实现仍然出现：

- 大标题 hero
- 大块 journey 说明
- 配置 / 模式 / 系统大卡
- 结果摘要大卡
- 大片空白

则应视为与当前 canonical requirement 不一致。
