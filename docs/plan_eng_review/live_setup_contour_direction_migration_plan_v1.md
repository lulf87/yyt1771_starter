# Live Setup Contour Direction Migration Plan v1

Status: IMPLEMENTATION_IN_PROGRESS
Updated on 2026-04-24

## Purpose

本计划用于把当前 live setup 中的相机采集、ROI 绘制和 A/B 点计算，逐步迁移到参考仓库 `https://github.com/h-lu/niti-bfr-standard` 的轮廓采集与方向法语义。

迁移目标不是替换整个实时测试系统，而是替换 live setup 的几何与视觉测量核心：

- 保留本项目已有的相机适配、温度控制、run registry、live run coordinator、报告链路。
- 替换 operator-facing 的窗口/方向/A-B 定义方式。
- 用 ROI 内主目标轮廓或主掩膜作为 A/B 与 tracking 的唯一图像依据。

## Target Contract

新的 live setup 几何契约应收敛为：

- `analysis_roi`
  操作员绘制的目标搜索与 tracking 区域。
- `direction_angle_deg`
  操作员确认的方向线角度，方向定义与参考仓库一致：按二维图像坐标中的投影方向计算跨度。
- `point_a_px` / `point_b_px`
  由 ROI 内主目标轮廓或掩膜沿 `direction_angle_deg` 投影得到的两端点。
- `foreground_polarity` / `threshold_mode` / `sensitivity`
  只影响 ROI 内主目标分割和轮廓连接，不改变几何定义。

旧字段处理：

- `metric_box` 仅作为过渡兼容字段，不能再作为 operator-facing 的主窗口概念。
- `observation_axis` 仅作为旧 API 兼容，不能再决定新方向法的 A/B 语义。
- `observation_window` 不进入新 home cockpit 操作流。

## Reference Mapping

参考仓库中可迁移的核心做法：

- `src/niti_bfr/extract.py`
  wire-like 对象：ROI 内阈值分割，取主连通域和主轮廓，再由轮廓/骨架提取端点与中心线。
- `src/niti_bfr/extract_braided.py`
  braided-like 对象：ROI 内提取主体掩膜、主体轴线、body contour，并按轴向/方向计算几何量。
- `src/niti_bfr/pipeline.py`
  方向法：使用 `direction_angle_deg` 对中心线、轮廓或掩膜点集做投影跨度计算。
- `src/niti_bfr/process_debug_video.py`
  方向法绘制：绘制方向参考线，并把点集投影到该方向线上显示跨度端点。
- `web/templates/index.html`
  前端交互：先选择固定 ROI，再确认方向角。

## Implementation Phases

### Phase 1. Vision API

Status: implemented in `src/vision/contour_direction.py`; covered by `tests/vision/test_contour_direction.py`.

新增独立 vision API：

- 输入：`FramePacket`、`analysis_roi`、`direction_angle_deg`、阈值/灵敏度参数。
- 输出：`ShapeMetric`，包含 `point_a_px`、`point_b_px`、方向跨度、主轮廓/主掩膜调试信息。
- 失败时输出明确 `meta.reason`，例如 `roi_outside_image`、`target_component_not_found`。

该阶段不改前端、不改相机、不改 live run 主流程。

### Phase 2. Backend Auto Detect

Status: implemented for requests carrying `direction_angle_deg`; legacy `metric_box` auto-detect remains for compatibility.

将 `/api/runs/{run_id}/definition/auto` 从 `metric_box` 依赖切换到新 vision API。

关键要求：

- 每次 A/B 重算仍必须基于新抓取帧。
- ROI 内只选择主目标轮廓/掩膜。
- A/B 由方向投影决定，不由世界坐标最大外接框或 `metric_box` 边界决定。

### Phase 3. Frontend Setup

Status: partially implemented. The existing ROI controls now send `direction_angle_deg`, keep `metric_box` as an axis-aligned compatibility container, and display the ROI angle as a direction line.

把前端操作收敛为：

- Freeze 后绘制 ROI。
- 在 ROI 上确认方向线。
- 由后端返回 A/B。
- 前端只负责显示 ROI、方向线、A/B 和分割/轮廓调试覆盖层。

`Draw Window`、`Rotate Window`、手动 A/B 等旧心智模型不再作为用户可见路径。

### Phase 4. Live Tracking

Status: implemented at extractor-selection level. Saved definitions now persist `direction_angle_deg`; `LockedDefinitionMetricSource` uses `DirectionalContourMetricExtractor` when the direction angle is present. True camera validation is still pending.

运行期每帧在 ROI 内重新分割主目标，并沿确认方向刷新 A/B 与 metric。

如果需要动态 ROI：

- 只能作为内部 tracking ROI。
- 不能改变 operator-confirmed `analysis_roi` 与方向语义。

## Done Criteria

- ROI 和方向角是 live setup 的主几何输入。
- A/B 由 ROI 内主轮廓或主掩膜方向投影生成。
- 前端显示的方向线、A/B 和后端计算使用同一 `direction_angle_deg`。
- 旧 `metric_box` 不再决定 A/B 计算。
- 自动检测、live tracking、测试和调试输出都能解释所用轮廓/掩膜、方向和端点。

## Risks

- 当前工作树已有多处未提交修改，迁移必须分阶段做，避免把既有 camera/live-run 改动混入视觉算法提交。
- 参考仓库的视频读取逻辑不能直接替换本项目的工业相机层，只能借鉴帧内目标提取与方向投影方法。
- 新 API 与旧 `MeasurementDefinition.is_complete()` 的兼容需要单独处理，否则前端和 run start 校验会继续要求 `metric_box`。
