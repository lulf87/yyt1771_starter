# Web Preview 18 FPS Viability Requirement v1

Updated on 2026-03-24
Status: SUPERSEDED_BY_MAC_FINISH_WEB_DIRECTION

## 2026-05-25 `mac-finish` Outcome Note

This requirement introduced the decision gate that allowed Web to remain a
delivery candidate. The current product direction has now been refrozen around
the Web workstation.

Use this file for the original Web-preview gate rationale. For current Windows
migration work, use:

- [requirements_overview.md](./requirements_overview.md)
- [web_on_windows_migration_status_20260525.md](../plan_eng_review/web_on_windows_migration_status_20260525.md)

## Purpose

这份文档用于锁定一个新的、更窄但更务实的产品问题：

- 如果最终用户对“真正可用的可视预览”的目标不是 `50 Hz`，而是约 `18 fps`
- 并且仍然希望保留现有 Web 工作流与浏览器交付方式
- 那么项目是否还需要把桌面端当成唯一正确路线

这份 requirement 要解决的不是“Web 好不好”，而是下面 4 个更具体的问题：

1. 当预览目标从 `>50 Hz` 收窄到 `18 fps` 时，Web 是否仍可作为最终交付候选
2. `18 fps` 应如何被定义成一个可验收的 operator preview gate
3. 为达到这个 gate，允许哪些 camera/profile/display 调整
4. 在什么条件下桌面迁移仍然必须继续作为主路径

---

## Context

当前已知事实已经比较清楚：

- 当前相机型号是 `MV-CA060-11GM`
- 该型号在 full-frame `3072 x 2048` 下的标称帧率量级约为 `17 fps`
- 当前 Web preview 在真实相机链路下，经过一轮减重后，已知量级仍大约是 `8.58 - 8.89 fps`
- 当前桌面迁移 requirement 与 plan 是围绕“桌面端可视预览 `preview_display_fps >= 50`”建立的

这意味着：

- 如果产品目标继续坚持“桌面端 >50 Hz 可视预览”，桌面迁移方向仍然成立
- 但如果产品目标实际收窄为“Web 继续保留，只要做到约 `18 fps`、显示更大、亮度可用”，那么原先“桌面端必须成为最终交付”的判断就需要被重新冻结

因此这轮 office-hours 风格整理的核心，不是继续争论 Web 和 desktop 谁更先进，而是：

> 把“18 fps Web preview 是否足够成为最终交付基线”写成一个可执行的 requirement gate。

---

## Office-Hours Synthesis

这轮 `/office-hours` 风格梳理后的核心结论是：

### The real question is not "Is desktop better?"

更准确的问题是：

> 如果最终用户接受的 operator preview 目标是约 `18 fps`，并且现有 workflow 必须保持不变，那么项目是否还能继续以 Web 作为最终交付壳。

这和“desktop 是否在理论上更强”不是同一个问题。

### Workflow continuity matters more than shell ideology

用户当前真正不想放弃的是：

- `precheck -> probe -> preview -> freeze -> ROI / A-B / 观测窗口 -> live run -> result`

这条 workflow 的语义稳定性。

如果 Web 能在这个 workflow 下满足：

- 可接受的预览帧率
- 更大的显示面积
- 足够亮的 setup preview

那么“必须切桌面”就不再是产品层的硬约束，而更像是一个性能优化选项。

### 18 fps preview is a different requirement from 50 Hz measurement

这轮 requirement 必须明确保留一个前提：

- `18 fps` 指的是 operator-visible preview gate
- 它不等于 `50 Hz synchronized measurement`

因此后续讨论必须继续分开：

- `preview_display_fps`
- `measurement_sample_hz`

不能因为 preview gate 收窄到了 `18 fps`，就顺手把 measurement cadence requirement 一起降掉。

### A narrowed Web gate is valid if it is explicit

如果 Web 要继续作为最终交付候选，它不能靠“主观觉得差不多能用”成立。
它必须有一条明确 gate：

- 指定 profile
- 指定 ROI
- 指定 preview 显示尺寸
- 指定曝光/增益策略
- 指定验收指标

只有在这条 gate 通过后，才可以把桌面端从“必选项”降级为“可选优化项”。

---

## Frozen Requirement

本节记录原始“18 fps Web preview 是否足够” gate。`mac-finish` 后，
Web 工作站已成为当前 active shell，因此下面内容应理解为历史 gate
定义，而不是仍待决策的路线选择。

### R1. Existing workflow semantics remain intact

无论最终交付壳是否仍为 Web，下面这些 workflow 语义必须保持不变：

- `precheck`
- `probe`
- `create run`
- `start / stop live preview`
- `freeze last frame`
- `ROI / 观测窗口 / A-B` 定义
- `start live run`
- `telemetry / result / artifact`

这份 requirement 不改变 workflow，只改变对最终 delivery shell 的判断条件。

### R2. Web remains an allowed final-delivery candidate if it passes the narrowed gate

原始 gate 锁定后，Web 不应再被自动视为“只剩过渡价值”的壳。

新的冻结规则是：

- 若 Web 在锁定条件下通过 `18 fps` operator preview gate
- 则 Web 仍然可以作为最终交付候选

这条 requirement 会削弱“桌面端必定是最终交付基线”的绝对性，但不会自动否定桌面迁移工作本身的工程价值。

### R3. The narrowed Web preview gate is `preview_display_fps >= 18`

对于当前这轮需求，Web preview 的 operator gate 冻结为：

- 指标：`preview_display_fps >= 18`

注意：

- 这是 preview gate
- 不是 `measurement_sample_hz`
- 也不是相机 full-frame 标称帧率

### R4. The Web preview gate does not require full-frame acquisition

当前 requirement 明确允许：

- `setup_preview` 使用 camera-side ROI
- `measurement` 在第一阶段与 `setup_preview` 共享同一 acquisition ROI

也就是说：

- Web 若要达到 `18 fps`
- 不需要坚持 `3072 x 2048` full-frame

相反，适度裁 ROI 被视为 requirement 允许范围内的正当工程手段。

### R5. The first candidate acquisition profile is intentionally moderate

第一轮推荐候选 profile 可冻结为如下方向：

- `preview_target_fps: 18`
- `setup_preview.device_roi = measurement.device_roi = 2304 x 1536 @ (384, 256)`
- `pixel_format = mono8`
- `exposure_us = 12000`
- `gain_db = 3.0`

这组值当前应被视为：

- requirement-aligned candidate baseline
- 不是已经验证通过的最终 bench 结果

也就是说，它定义的是“优先尝试的产品方向”，不是“已证明达标的现场数据”。

### R6. Web preview should become larger, not just slightly faster

这轮需求不是只要求“fps 高一点”，还要求 operator 可用性提高。

因此当前 requirement 冻结为：

- Web preview stream 的显示尺寸必须显著大于当前 `384 x 256` 级别
- 第一轮目标可按 `768 x 512` 级别理解

这里的 requirement 关注的是 operator-visible size，而不是内部 acquisition resolution 本身。

### R7. Brightness usability is part of the requirement

当前 requirement 明确承认：

- 当前 `10000 us / 0 dB` 的 setup preview 偏暗
- 预览“看得清”本身就是 operator requirement 的一部分

因此系统必须允许并优先采用：

1. 先增加 exposure
2. 再小幅增加 gain

在当前候选配置中：

- `exposure_us = 12000`
- `gain_db = 3.0`

可作为第一轮 requirement-aligned baseline。

### R8. This requirement does not repeal the synchronized-measurement requirement

这份 requirement 不会自动推翻：

- `50 Hz synchronized measurement` baseline
- `100 Hz synchronized measurement` stretch goal

因此必须继续明确区分：

- `preview_display_fps >= 18` 的 Web operator preview gate
- `measurement_sample_hz >= 50` 的 measurement gate

如果后续要修改 measurement baseline，必须单独新增 requirement 或修订已有 temporal-sampling requirement。

### R9. Desktop migration becomes conditional, not automatically cancelled

当前 requirement 不会说“桌面端没必要了”，而是冻结为条件判断：

- 如果 Web 在目标 profile 和目标环境下通过 `preview_display_fps >= 18` gate
  - 桌面端可降级为可选优化路线
  - 不再是最终交付的必选项
- 如果 Web 当时过不了这条 gate
  - 桌面迁移会继续作为当时的主路径
- `mac-finish` 后当前结论
  - Web 工作站已作为 active shell 继续推进
  - 桌面迁移只保留为暂停的历史 / fallback reference

### R10. Final acceptance still belongs to Windows

即使这份 requirement 允许 Web 继续作为最终交付候选，最终验收平台仍冻结为：

- Windows

Mac 上的验证可以继续作为：

- 开发验证
- proxy bench
- 参数探索

但“Web 最终是否足够”仍应在 Windows 环境下给出最后结论。

---

## Outcome

这轮 requirement 的历史冻结表达是：

> 如果项目的 operator preview 目标收窄为约 `18 fps`，并且 workflow 语义保持不变，那么 Web 仍然可以作为最终交付候选；桌面端不再被默认视为唯一正确路线，但只有在 Web 通过明确的 `preview_display_fps >= 18`、更大显示尺寸、可用亮度这组验收条件后，才允许把 desktop 从必选项降级为可选优化项。

2026-05-25 后，这条 gate 的 outcome 已经落到当前 baseline：

```text
src.webapp.serve -> application -> workflow / storage / report
```

当前 Windows 迁移方向见
[web_on_windows_migration_status_20260525.md](../plan_eng_review/web_on_windows_migration_status_20260525.md)。
