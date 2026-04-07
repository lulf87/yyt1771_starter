# Analysis Studio AFAS Alignment Requirement v1

Updated on 2026-03-29
Status: CANONICAL_REQUIREMENT_ADDENDUM
Clarifies implementation scope of:
- `home_workspace_information_hierarchy_requirement_v1.md`
- `home_workspace_shell_requirement_v1.md`
- `afas_full_postprocessing_migration_requirement_v1.md`

## Purpose

这份 requirement 用于把 workspace 的默认分析界面，冻结成与 AFAS 项目内容模型基本一致的 Analysis Studio。

它解决的不是新的算法问题，而是下面这些已经在当前 workspace UI 中暴露出来的产品偏差：

1. 默认首屏仍然带着明显的研发过程面板气质
2. rail、summary、version、adjustment、future controls 等过程型信息仍然占据过高视觉层级
3. AFAS 分析相关内容虽然已经存在，但还没有成为默认主屏唯一主角
4. 页面上的操作按钮和分组方式仍然更像内部模块暴露，而不像成熟分析工具

这份 requirement 的目标是：

> 把 Analysis Studio 的默认首屏收成 AFAS 风格的分析工作面，而不是研发试验台。

如果本文件与：

- `home_workspace_information_hierarchy_requirement_v1.md`

冲突，则：

- `home_workspace_information_hierarchy_requirement_v1.md` 继续定义 home / workspace 的 `default visible / on-demand reveal / engineering mode` 三层框架
- 本文件在 workspace 默认分析界面的更窄 scope 内，进一步冻结“默认到底应像 AFAS 的哪一部分”

如果本文件与：

- `home_workspace_shell_requirement_v1.md`

冲突，则：

- `home_workspace_shell_requirement_v1.md` 继续定义 Home / Workspace 的 surface 分工、session target、DOM / API / test-anchor guardrails
- 本文件定义 workspace 默认首屏的 AFAS-style content model

如果本文件与：

- `afas_full_postprocessing_migration_requirement_v1.md`

冲突，则：

- `afas_full_postprocessing_migration_requirement_v1.md` 继续定义算法、图表、结果面板、导出与 artifact 层面的 capability parity
- 本文件只定义这些能力在 Analysis Studio 默认界面上应如何出现

---

## Scope Boundary

这份 requirement 只约束下面这类工作：

- [workspace.html](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/templates/workspace.html)
- [app.css](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.css)
- [app.js](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/static/app.js)
- 必要时的 [ui.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/webapp/routes/ui.py)

它不直接要求：

- 修改 AFAS analysis contract
- 修改 replay / session backend contract
- 新增 backend API
- 修改 artifact schema

它冻结的是：

> the default operator-facing analysis surface inside the existing session-scoped workspace

工程实现上如果涉及：

- 参数改动后的分析触发语义
- `afas_available=0` / single-channel / summary-only 的默认降级路径
- replay 在默认首屏中的固定落位
- first-pass refactor 中的 DOM / JS / test-anchor 兼容边界

则必须继续联读：

- [analysis_studio_afas_alignment_state_fallback_requirement_v1.md](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/docs/requirements/analysis_studio_afas_alignment_state_fallback_requirement_v1.md)

---

## Primary User

从本 requirement 起，workspace 默认用户画像冻结为：

- 需要对一条已完成 session 做结果判读的人
- 主要目标是：
  - 选择通道
  - 查看总览趋势
  - 查看单通道切线分析
  - 读取 `As / Af-tan / ΔT`
  - 必要时调参数
  - 导出分析图和报告

默认用户不是：

- 在这里阅读开发过程信息的人
- 需要默认看到 API / provenance / placeholder / future controls 的人
- 需要默认进入 adjustment / version / quick actions 的人

因此 workspace 默认首屏必须优先回答下面 6 个问题：

1. 当前分析的是哪个 session / 哪个通道
2. 多通道总览是什么
3. 当前通道的切线分析图是什么
4. `As / Af-tan / ΔT` 结果是什么
5. 这些结果由什么参数得到
6. 现在是继续微调，还是导出

---

## Frozen Decisions

### R1. Analysis Studio must borrow AFAS content model, not its Streamlit skeleton

workspace 默认首屏应向 AFAS 借用下面这套内容模型：

```text
通道选择
-> 分析参数
-> 总览图
-> 单通道切线分析
-> 分析结果
-> 导出
```

这里借的是：

- 信息组织
- 参数分组
- 结果语义
- 导出动作层级

不借的是：

- Streamlit 的页面壳层
- 独立上传器结构
- 与当前 session-scoped workspace 相冲突的导航方式

### R2. Workspace default-visible content is reduced to AFAS-style analysis essentials

workspace 默认可见内容冻结为：

1. 轻量 session strip：
   - session id
   - session state
   - 语言切换
   - 必要的轻量刷新 / 返回动作

2. `通道选择`

3. `分析参数`
   - `数据预处理`
   - `切线调整`

4. `总览图`

5. `单通道切线分析`

6. `分析结果`
   - `As`
   - `Af-tan`
   - `ΔT`
   - 最大斜率点 / 最大斜率温度
   - 参数摘要
   - 缺失结果提示

7. `导出`
   - `导出分析图 (PNG)`
   - `导出分析报告 (Excel)`

### R3. Analysis parameters must be grouped by AFAS semantics

workspace 参数区当前冻结为两组：

1. `数据预处理`
   - Savitzky-Golay 窗口
   - 多项式阶数

2. `切线调整`
   - 低温基准线区间
   - 高温基准线区间
   - 中间切线偏移

参数区默认应服务“结果微调”，而不是暴露内部模块层次或研发阶段。

### R4. Process-heavy and engineering-heavy information must leave the default first screen

下列内容不再属于 workspace 默认主分析界面：

1. `路径导轨 / 流程 rail`
2. `Current Stage`
3. `Sticky Summary` 卡堆
4. `Session Summary` 大卡
5. `Active Selection`
6. `Adjustment Status`
7. `Version History`
8. `Quick Actions`
9. `第二屏` 说明性标题
10. `Adjustment MVP`
11. `Key Frames`
12. `Future Adjustment Controls`
13. `Open Summary API / Open Detail API`
14. provenance 型字段：
    - `feature_point_px`
    - `metric_norm`
    - `threshold_value`
    - `component_area`
    - `baseline_px`

这些能力允许保留，但必须进入：

- secondary screen
- traceability drawer
- advanced foldout
- explicit engineering reveal

不得继续与 `总览图 / 单通道切线分析 / 分析结果 / 导出` 争夺默认首屏。

### R5. Replay stays as session context, but no longer occupies the default hero position

当前项目仍然是 session-scoped product，因此 replay 不会消失。

但 replay 在默认界面中的角色冻结为：

- 数据来源上下文
- 在需要时支持回看

更合适的表达包括：

- compact replay strip
- replay foldout
- context tab

不再要求默认第一屏把 replay 曲线作为整个页面主角。

### R6. Results panel must behave like AFAS’s answer surface

结果面板必须像 AFAS 的 `分析结果` 一样，直接回答：

- `As` 是多少
- `Af-tan` 是多少
- `ΔT` 是多少
- 结果是否完整
- 当前参数是什么
- 现在如何导出

因此结果面板必须同时包含：

1. 主结果指标
2. 缺失或异常结果提示
3. 参数摘要
4. 简短分析说明
5. 导出动作

如果结果不完整，默认提示语应明确指向：

> 请尝试调整切线参数。

### R7. Export buttons should follow AFAS wording and hierarchy

导出应成为结果面板的一部分，而不是额外的过程型工具区。

推荐 operator-facing 文案冻结为：

- `导出分析图 (PNG)`
- `导出分析报告 (Excel)`

允许底层继续复用现有 export contract，但默认交互层级应向 AFAS 看齐。

### R8. Workspace visual theme stays aligned with home, but explanatory hero chrome leaves the default viewport

workspace 继续与首页共享：

- 深色底
- glass card
- Morandi-like accent palette
- Inter / mono typography token

但默认首屏不再强制渲染：

- `YYT1771`
- `分析工作台` 大标题
- 说明型副标题

默认首屏更重要的是：

> 现在怎么看结果、怎么调、怎么导出。

### R9. This addendum changes interface hierarchy, not capability scope

本文件不要求：

- 放弃 session 上下文
- 放弃 replay artifact
- 放弃 adjustment / version 能力
- 把 workspace 改成独立 AFAS 上传器
- 修改 AFAS 核心算法或导出 contract

它只要求：

> 把 Analysis Studio 的默认界面，从“研发过程面板”收成“AFAS 风格的分析工作面”。
