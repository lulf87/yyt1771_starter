# 模块映射（Module Map）

这份文件是 `docs/architecture_lock.md` 的职责展开版。
后续所有工单都以本文件和 `architecture_lock.md` 共同约束模块边界。

## 1. 模块总览

| 模块 | 唯一职责 | 允许直接依赖 | 禁止关注点 |
| --- | --- | --- | --- |
| `src.core` | 数据模型、协议接口、枚举、错误码、配置模型 | 无 | OpenCV、PLC 通讯、工作流状态机 |
| `src.camera` | 相机帧采集，产出 `FramePacket` | `src.core` | 视觉识别、曲线计算、流程判断 |
| `src.temp` | 温度采集，产出 `TempReading` | `src.core` | 曲线计算、流程判断 |
| `src.plc` | PLC 点位读写，产出 `PlcSnapshot` | `src.core` | 视觉识别、结果计算 |
| `src.vision` | 图像转 `ShapeMetric` | `src.core` | PLC 控制、工作流、Af95/As/Af |
| `src.sync` | 多源时间对齐为 `SyncPoint` | `src.core` | 视觉算法、设备控制 |
| `src.curve` | 曲线缓存、归一化、结果计算 | `src.core` | 相机/PLC/温控直接访问 |
| `src.workflow` | 会话、状态机、预检查、调度 | `src.core`、`src.camera`、`src.temp`、`src.plc`、`src.vision`、`src.sync`、`src.curve`、`src.storage`、`src.report` | 具体视觉实现细节 |
| `src.storage` | 落盘、索引、回放 | `src.core` | 工作流反向控制 |
| `src.report` | 结果摘要、图表导出 | `src.core` | 设备访问、流程控制 |

## 2. 公共数据契约归属

这些类型只能定义在 `src.core.models`，其他模块只消费，不重复定义：

- `FramePacket`
- `TempReading`
- `PlcSnapshot`
- `ShapeMetric`
- `SyncPoint`
- `CurvePoint`
- `SessionRecord`

这些协议只能定义在 `src.core.contracts`：

- `CameraPort`
- `TempReader`
- `PlcPort`
- `VisionMetricExtractor`

## 3. 文件级归属建议

### `src/core/`

- `models.py`：跨模块 dataclass
- `contracts.py`：Protocol / Port
- `enums.py`：状态枚举
- `errors.py`：项目级异常
- `config_models.py`：配置 dataclass

### `src/camera/`

- `mock_camera.py`：离线/测试输入
- `hik_rtsp_opencv.py`：海康 RTSP 适配器

### `src/temp/`

- `mock_temp.py`：离线/测试温度输入
- `modbus_temp.py`：温度采集适配器

### `src/plc/`

- `mock_plc.py`：离线/测试 PLC 输入
- `modbus_tcp.py`：PLC 适配器

### `src/vision/`

- `metric_end_displacement.py`：自由端位移提取
- `normalizer.py`：形变量归一化
- `quality.py`：质量评分
- `roi.py`：ROI 辅助逻辑

### `src/sync/`

- `hub.py`：多源样本聚合与时间对齐

### `src/curve/`

- `buffer.py`：曲线缓存
- `af95.py`：Af95 或其他点位估计

### `src/workflow/`

- `session.py`：测试会话上下文
- `state_machine.py`：状态流转
- `precheck.py`：开测前检查

### `src/storage/`

- `session_store.py`：会话索引
- `sqlite_repo.py`：SQLite 持久化
- `csv_exporter.py`：曲线导出

### `src/report/`

- `summary.py`：结果摘要
- `plotter.py`：绘图或导出图像

## 4. 导入规则

统一使用 `src.*` 绝对导入。

示例：

```python
from src.core.models import FramePacket, ShapeMetric
from src.sync.hub import SyncHub
```

不允许：

```python
from ..core.models import FramePacket
from src.vision.metric_end_displacement import ...  # 在 camera/temp/plc 中引用视觉逻辑
```

## 5. 当前阶段的数据流

当前按离线最小主链推进：

```text
MockCamera / HikRtspCamera
        ↓
    FramePacket
        ↓
EndDisplacementMetricExtractor
        ↓
    ShapeMetric
        ↓
      SyncHub
        ↓
    SyncPoint
        ↓
    CurveBuffer
        ↓
  Normalizer / Af95
```

说明：

- 真正的设备控制命令后置，先把离线主链打通。
- GUI 不是当前主链的一部分。
- `workflow` 只负责编排，不替代 `vision` 或 `curve`。

## 6. 约束提醒

- 不新增 `utils/`、`common/`、`shared/`。
- 不把视觉算法塞进 `camera`。
- 不把结果计算塞进 `workflow`。
- 不在 `storage` 中调用 `workflow`。
- 不让 `report` 直接读取相机、温度或 PLC。
