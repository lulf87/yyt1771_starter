# Task-002：最小可用视觉形变量提取器

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目中的 `src/core/models.py`
- 当前项目中的 `src/vision/metric_end_displacement.py`

## 任务目标

在**不接真实硬件、不引入流程层逻辑**的前提下，实现一个真正可工作的最小视觉提取器：

`FramePacket.image -> ShapeMetric(metric_name="end_displacement")`

本轮目标不是做完整工业算法，而是把**最小单元**做成可验证、可重复、可继续扩展的版本。

---

## 本轮只允许碰这些文件

优先只修改：

- `src/vision/metric_end_displacement.py`
- `tests/vision/test_vision_end_displacement.py`
- `examples/offline_demo.py`

如有必要，可少量新增/修改：

- `tests/conftest.py`
- `src/vision/quality.py`

除非绝对必要，**不要修改**：

- `src/core/models.py`
- `src/core/contracts.py`
- `src/sync/hub.py`
- `src/camera/mock_camera.py`

如果你认为必须改这些文件，请在输出中先说明原因。

---

## 功能要求

请实现 `EndDisplacementMetricExtractor` 的最小可用版本，要求如下。

### 1. 输入图像

至少支持以下输入：

- `list[list[int]]` 的二维灰度图
- `tuple[tuple[int, ...], ...]` 的二维灰度图

如果你愿意兼容 `numpy.ndarray` 也可以，但**不要把本任务绑定到必须安装 OpenCV 才能运行**。

### 2. ROI

支持可选 ROI：

```python
roi: tuple[int, int, int, int] | None  # (x, y, w, h)
```

如果设置了 ROI，则只在 ROI 内找目标；
返回的 `feature_point_px` 必须是**整幅图的全局坐标**，不是 ROI 内局部坐标。

### 3. 二值判定

本轮至少支持固定阈值法：

- 像素值 `>= threshold_value` 视为前景

可选支持：

- `threshold_method="otsu"`

如果你实现 Otsu，请确保测试仍然稳定；
如果不实现 Otsu，也不要为了凑功能写空壳分支。

### 4. 目标选择

请不要直接取“所有前景像素里最右边的点”。

要求：

- 找出所有前景连通域
- 过滤掉面积小于 `min_area_px` 的连通域
- 取面积最大的有效连通域作为目标
- 取该目标最右端像素的 x 坐标作为自由端位置

### 5. baseline 与 metric_raw

要求支持：

- 构造函数可传入 `baseline_px`
- 若 `baseline_px is None` 且 `auto_lock_baseline=True`，第一次检测到有效目标时自动锁定 baseline
- 返回：

```python
metric_raw = feature_x - baseline_px
```

所以通常第一次成功检测后，`metric_raw` 应接近 `0.0`。

### 6. 输出字段

返回的 `ShapeMetric` 至少要正确填写：

- `timestamp_ms`
- `metric_name="end_displacement"`
- `metric_raw`
- `metric_norm=None`（本轮先不做归一化）
- `quality`
- `roi`
- `feature_point_px`
- `baseline_px`
- `meta`

### 7. 质量评分

请把 `quality` 约束在 `0.0 ~ 1.0`。

最小规则：

- 没有图像：`quality == 0.0`
- 没找到有效目标：低质量，建议 `<= 0.2`
- 找到有效目标：中高质量，建议 `>= 0.7`

`meta` 中至少补充：

- `reason`（失败时）
- `component_area`
- `threshold_value`
- `source`

---

## 建议实现方式

为了让后续接 OpenCV 时不推翻本轮结构，建议类签名接近下面这样：

```python
class EndDisplacementMetricExtractor(VisionMetricExtractor):
    def __init__(
        self,
        roi: tuple[int, int, int, int] | None = None,
        threshold_value: int = 127,
        min_area_px: int = 4,
        baseline_px: float | None = None,
        auto_lock_baseline: bool = True,
    ) -> None:
        ...

    def extract(self, frame: FramePacket) -> ShapeMetric:
        ...
```

你可以在同文件里增加私有辅助函数，例如：

- `_normalize_image(...)`
- `_crop_roi(...)`
- `_find_connected_components(...)`
- `_pick_target_component(...)`
- `_rightmost_point(...)`

本轮先追求**稳定和可测**，不是追求炫技。

---

## 测试要求

请至少写 4 个 pytest。

### test 1
合成图中白色目标整体向右移动，`metric_raw` 单调增加。

### test 2
ROI 外添加噪声，提取结果不变或基本不变。

### test 3
没有有效前景时，返回低质量结果，并在 `meta["reason"]` 中说明原因。

### test 4
首次成功检测后自动锁定 `baseline_px`，第二帧若目标右移，则 `metric_raw > 0`。

可选再加：

- 小面积噪声低于 `min_area_px` 时不应被当作目标
- `feature_point_px` 必须返回全局坐标

---

## 示例脚本要求

更新 `examples/offline_demo.py`，让它打印出：

- 是否检测到图像
- `feature_point_px`
- `baseline_px`
- `metric_raw`
- `quality`

但不要引入 GUI，不要接真实设备。

---

## 约束

1. 不允许访问相机、PLC、温控真实设备。
2. 不允许把算法逻辑塞进 `camera/`。
3. 不允许修改一级模块结构。
4. 不允许新增 `utils/`、`common/`、`shared/`。
5. 不要大规模重构无关文件。
6. 保持所有导入为 `src.*` 绝对导入。

---

## 验收命令

至少运行：

```bash
pytest -q
python -m examples.offline_demo
```

如果你增加了额外检查命令，也请附上原始输出。

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
