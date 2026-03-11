# Task-001：离线主链契约冻结（Contract Freeze）

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- 当前项目目录树与现有实现

## 任务目标

在**不做真实业务算法**的前提下，先把离线最小主链用到的核心数据契约冻结下来。

这一步的目标不是“识别成功”，而是让后续视觉算法、同步、曲线模块都围绕**同一套稳定的数据字段**开发。

---

## 本次必须处理的核心问题

当前骨架已经完成了目录冻结，但还存在一个关键问题：

- `FramePacket` 还没有稳定的图像字段约定
- `ShapeMetric` 的字段还没有对齐后续视觉与曲线主链

如果现在直接实现 OpenCV 逻辑，后面会因为 dataclass 语义漂移而返工。

所以本任务要求你先把契约定稳。

另外，如果项目里的 `docs/module_map.md` 或 `docs/master_control_plan.md` 仍是占位版，请先按本轮提供的正式版本覆盖，再继续本任务。

---

## 允许修改的文件

主要范围：

- `src/core/models.py`
- `src/core/contracts.py`
- `src/camera/mock_camera.py`
- `src/vision/metric_end_displacement.py`
- `examples/offline_demo.py`
- `tests/conftest.py`
- `tests/vision/test_vision_end_displacement.py`
- `docs/module_map.md`（若当前是占位版，可按本轮提供的正式内容覆盖）
- `docs/master_control_plan.md`（若当前是占位版，可按本轮提供的正式内容覆盖）
- 可新增少量契约测试（建议放在 `tests/architecture/`）

如果确有必要，可小幅修改：

- `src/__init__.py`
- `src/core/__init__.py`

---

## 不允许做的事

1. 不要实现真实 OpenCV 阈值/轮廓算法。
2. 不要接入真实相机、PLC、温控设备。
3. 不要新增新的一级目录或一级模块。
4. 不要创建 `utils/`、`common/`、`shared/`。
5. 不要把字段变成过度设计的大而全对象。
6. 不要修改模块依赖方向。

---

## 本次要冻结的最小契约

### `FramePacket`

请把它调整为适合视觉算法输入的最小形式：

- `timestamp_ms: int`
- `source: str = "unknown"`
- `image: Any | None = None`
- `frame_id: int | None = None`
- `meta: dict[str, Any]`（可选，默认空字典）

要求：

- 后续视觉算法能够直接读取 `frame.image`
- 不再使用含糊的 `payload` 作为图像主字段

### `ShapeMetric`

请把它调整为适合视觉输出与曲线输入的最小形式：

- `timestamp_ms: int`
- `metric_name: str = "end_displacement"`
- `metric_raw: float | None = None`
- `metric_norm: float | None = None`
- `quality: float = 0.0`
- `roi: tuple[int, int, int, int] | None = None`
- `feature_point_px: tuple[int, int] | None = None`
- `baseline_px: float | None = None`
- `meta: dict[str, Any]`（可选，默认空字典）

说明：

- 当前只冻结最小字段，不要求一次把所有将来可能字段都塞进去。
- `quality` 先约定为 `0.0 ~ 1.0`。
- 当前 extractor 仍可返回占位值。

---

## 占位实现要求

### `src/vision/metric_end_displacement.py`

本次不要上真实算法，但要与新契约对齐。

至少做到：

- 保留 `EndDisplacementMetricExtractor`
- `extract(frame: FramePacket) -> ShapeMetric`
- 如果 `frame.image is None`，返回低质量占位结果
- 返回字段必须使用新的 `ShapeMetric` 契约

### `src/camera/mock_camera.py`

建议输出一个最小可读的 mock 图像：

- 可用 `numpy` 生成一个简单黑底白块图
- 也可以保留极简实现，但必须填充 `FramePacket.image`

目的：

- 让 `examples/offline_demo.py` 和后续 vision 测试围绕真实图像字段工作

---

## 测试要求

至少完成这些测试：

1. `FramePacket` 能以 `image=` 初始化，并且字段存在
2. `ShapeMetric` 暴露新的核心字段：`metric_name / metric_raw / metric_norm / quality`
3. `EndDisplacementMetricExtractor.extract()` 返回的新对象符合新契约
4. `pytest -q` 全通过

建议：

- 在 `tests/architecture/` 新增一个契约测试文件，例如 `test_model_contracts.py`
- 更新现有 `tests/vision/test_vision_end_displacement.py`

---

## 你应该特别注意

1. 这是“契约冻结”任务，不是“算法实现”任务。
2. 字段名一旦冻结，后续任务原则上不再改语义。
3. 所有导入仍必须使用 `src.*` 绝对导入。
4. 变更要尽量小，但要真正消除 `payload` / 旧字段名带来的歧义。

---

## 验收命令

至少运行：

```bash
pytest -q
```

如果你修改了示例脚本，也请补充：

```bash
python -m examples.offline_demo
```

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
