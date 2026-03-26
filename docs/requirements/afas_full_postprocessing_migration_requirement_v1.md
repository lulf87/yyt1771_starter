# AFAS Full Postprocessing Migration Requirement v1

Updated on 2026-03-25
Status: CANONICAL_REQUIREMENT_ADDENDUM

## Purpose

这份文档用于锁定一个新的需求判断：

- 当前项目已经具备轻量 live `As / Af / AF95` 结果链
- 但它还不等于 `AFAS/` 目录中的完整后处理产品
- 如果产品要求是“把 `AFAS/` 中拿到数据后的全部后处理能力迁入本项目”
- 那么必须把这件事定义成一条独立 requirement，而不是继续把当前轻量实现误写成“已经等同 AFAS”

这份 requirement 解决的不是“还要不要继续算 As/Af”，而是下面 4 个更具体的问题：

1. “AFAS parity” 在当前项目里到底指什么
2. 哪些 `AFAS/` 能力属于必须迁入的后处理范围
3. 当前项目里哪些部分已经有同类能力，哪些仍明显缺失
4. 以后什么情况下才允许说“当前项目已具备 AFAS 全量后处理能力”

---

## Context

当前仓库里已经有一条 live 结果链：

- [afas.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/curve/afas.py)

它已经能做这些事：

- 从 `SyncPoint` 提取温度-单通道形变量曲线
- 计算导数
- 选取最大斜率附近的中间切线
- 拟合低温/高温基线
- 输出 `As`
- 输出 `Af`
- 输出 `AF95`

但 `AFAS/` 目录里对应的成品后处理能力更完整，当前我已经核对到这些模块：

- [preprocessing.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/preprocessing.py)
- [tangent_analysis.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/tangent_analysis.py)
- [analysis_chart.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/analysis_chart.py)
- [overview_chart.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/overview_chart.py)
- [results_panel.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/results_panel.py)
- [report_export.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/report_export.py)

这些文件共同定义的是一条更完整的“拿到数据之后”的分析产品：

- 多通道总览
- 通道选择
- 温度分组
- 异常值处理
- Savitzky-Golay 平滑
- 可调的低温/高温基线区间
- 中间切线偏移
- 完整的切线分析图
- 结果面板
- PNG 300 DPI 导出
- Excel 报告导出

因此，从现在开始，必须明确区分：

- 当前项目中的 **轻量 tangent-style live analysis**
- `AFAS/` 中的 **完整 postprocessing product**

---

## Office-Hours Synthesis

这轮 `/office-hours` 风格梳理后的结论是：

### The real question is not "Can we reuse some formulas?"

真正的问题不是“现有项目已经能不能算出 As/Af”，而是：

> 如果用户要求的是“把 `AFAS/` 中拿到数据后的全部后处理能力迁入当前项目”，那么迁移目标必须是完整分析产品，而不是单一结果公式。

### Full AFAS parity starts after data availability, not before acquisition

这轮需求聚焦的是**拿到数据之后**。

也就是说，迁移范围的起点不是：

- 相机采集
- live setup
- 温控联动

而是：

- 已经有结构化温度-形变量数据
- 已经可以构成 AFAS 输入曲线

然后从这个起点开始，当前项目应继续提供与 `AFAS/` 对齐的完整后处理能力。

### Result parity is not enough without preprocessing parity

当前项目如果只保留：

- 导数
- 最大斜率点
- 三线交点

但没有迁入：

- 温度分组
- 异常值处理
- Savitzky-Golay 平滑
- 可调参数

那么它不能被称为“AFAS 全量后处理迁移完成”。

### Plot parity and export parity are product requirements, not polish

`AFAS/` 不是只有一个算法核，它本身就是一个分析产品。

因此：

- 分析图
- 参数面板
- 结果面板
- PNG/Excel 导出

都属于 requirement 范围，而不是后续可选 polish。

### Current single-channel live contract is not enough for full AFAS parity

当前主项目的轻量结果链主要围绕单个 `metric_raw` 通道展开。

如果最终目标是“包含 AFAS 中所有拿到数据后的功能”，那 requirement 必须明确承认：

- 仅靠当前单通道 summary/result contract，不足以覆盖 `AFAS/` 的多通道总览与通道选择能力
- 因此后续实现允许并需要扩大 artifact/result/postprocessing contract，以承载 AFAS 所需的通道数据

---

## Frozen Requirement

从现在开始，关于 AFAS 全量后处理迁移的 requirement 冻结如下。

### R1. Scope starts once structured analysis data is available

这条 requirement 的作用域起点冻结为：

- 已经拿到温度-形变量数据
- 已经能构成 AFAS 分析输入

它不要求在本 requirement 中重新定义：

- 相机采集链
- live setup 几何定义
- 温控控制流程

这些仍由各自 requirement 负责。

### R2. Full AFAS parity requires preprocessing parity

当前项目若要宣称“已迁移 AFAS 完整后处理能力”，必须至少具备与 `AFAS/` 对齐的预处理能力：

- 按温度分组
- 异常值检测与修复
- Savitzky-Golay 平滑

参考源：

- [preprocessing.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/preprocessing.py)

仅靠原始曲线直接求导，不再允许被表述为“AFAS parity”。

### R3. Full AFAS parity requires parameterized tangent analysis

后处理分析必须支持并保留下面这些可调分析参数：

- 平滑窗口长度
- 平滑多项式阶数
- 低温基准线区间
- 高温基准线区间
- 中间切线偏移

并输出与 `AFAS/` 对齐的核心结果：

- `As`
- `Af-tan`
- 最大斜率点温度
- 低温基线
- 高温基线
- 中间切线
- 异常值数量

参考源：

- [tangent_analysis.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/tangent_analysis.py)

### R4. Full AFAS parity includes channel-level analysis UX, not just backend math

若数据源中存在多个通道，则系统必须支持：

- 多通道总览
- 通道选择
- 选中通道高亮分析

参考源：

- [overview_chart.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/overview_chart.py)

因此后续实现不得把 AFAS parity 简化成“始终只有一个固定通道的计算函数”。

### R5. Full AFAS parity includes visual analysis primitives

后处理界面必须具备与 `AFAS/` 同等级的分析图核心元素：

- 平滑后的温度-形变量主曲线
- 低温基准线
- 高温基准线
- 中间切线
- `As` 标记与标注
- `Af-tan` 标记与标注

参考源：

- [analysis_chart.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/analysis_chart.py)

当前项目里仅显示简化 SVG 曲线和少量 marker，不再允许被写成“等同 AFAS 绘图效果”。

### R6. Full AFAS parity includes result-panel semantics

后处理界面必须提供结果面板级信息，而不仅是 API summary 字段。

至少包括：

- `As`
- `Af-tan`
- 转变区间 `ΔT`
- 最大斜率点信息
- 当前分析参数摘要
- 对缺失结果的明确提示

参考源：

- [results_panel.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/ui/results_panel.py)

### R7. Full AFAS parity includes export parity

完整迁移必须覆盖导出能力：

- 高清分析图导出（PNG 300 DPI）
- 结构化分析报告导出（Excel）

参考源：

- [report_export.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS/core/report_export.py)

当前主项目中的：

- [csv_exporter.py](/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter/src/storage/csv_exporter.py)

仍是 placeholder，因此当前状态不得被表述成“导出能力已具备 AFAS parity”。

### R8. Current lightweight AFAS implementation remains valid but incomplete

当前主项目中的轻量 `afas.py` 仍然是合法的 live result path，
但 requirement 语言必须冻结为：

- 它是 **lightweight tangent-style live analysis**
- 它不是 **full AFAS postprocessing parity**

也就是说：

- 轻量 live 分析可继续存在
- 但不得再被写成“已经包含 AFAS 中所有拿到数据后的功能”

### R9. Postprocessing migration may expand current artifact/result contracts

如果要实现完整 AFAS parity，允许并要求后续实现扩大当前 contract，包括但不限于：

- 多通道曲线数据
- 预处理后曲线
- 导数
- 异常值标记
- 分析参数快照
- 导出产物引用

仅保留当前简单 `summary/result/detail` 字段，不足以承载完整迁移目标。

### R10. Acceptance must be framed as AFAS-equivalent capability, not name reuse

最终验收标准必须围绕“能力是否等价”，而不是“名字是否都叫 AFAS”。

也就是说，只有当当前项目具备：

- 预处理等价
- 参数化分析等价
- 图表表达等价
- 导出能力等价

才允许对外说：

> 当前项目已经具备 `AFAS/` 拿到数据后的全量后处理能力。

---

## Outcome

这轮 requirement 的最终冻结表达应是：

> 当前项目现有的轻量 live AFAS 分析，只能被视为完整 AFAS 后处理产品的一部分。若产品目标是迁移 `AFAS/` 中“拿到数据之后”的全部能力，那么迁移范围必须同时覆盖预处理、参数化切线分析、多通道总览、完整分析图、结果面板与 PNG/Excel 导出；仅仅保留 `As / Af / AF95` 结果计算，不再足以被描述为 AFAS parity。

这就是当前锁定的 requirement baseline。
