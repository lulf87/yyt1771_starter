# 模块映射（Module Map）

这份文件是 `architecture_lock.md` 的职责展开版。
后续所有新的实现和文档更新，都应以 `docs/requirements/` 与
`docs/plan_eng_review/` 中的权威文件为准，并由本文件和
`architecture_lock.md` 共同约束模块边界。

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
| `src.storage` | 落盘、索引、回放、artifact keyframe 序列化 | `src.core`、`src.vision` | 工作流反向控制、新视觉识别 |
| `src.report` | 结果摘要、图表导出 | `src.core` | 设备访问、流程控制 |
| `src.application` | 共享运行时配置、设备工厂、预览服务、live run 服务、应用容器 | `src.core`、`src.camera`、`src.temp`、`src.plc`、`src.vision`、`src.curve`、`src.workflow`、`src.storage`、`src.report` | GUI 布局、HTTP 路由、桌面控件 |
| `src.webapp` | HTTP 路由、请求响应模型、Web 依赖注入 | `src.application`、`src.core`、`src.desktop_app`、`src.workflow`、`src.storage`、`src.report`、`src.curve`、`src.vision` | 设备适配器直连、继续扩大共享业务逻辑 |
| `src.desktop_app` | 桌面壳、Qt runtime bootstrap、桌面 controller、原生预览控件 | `src.application`、`src.core`、`src.camera`、`src.workflow` | 设备/算法/存储结构反向决策 |

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
- `hik_rtsp_opencv.py`：海康 RTSP 路线适配器
- `hik_gige_mvs.py`：海康 GigE / MVS 路线适配器

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
- `mock_afas_curve_playback.py`：workbook-backed mock AFAS 曲线回放；只消费 runtime-config-like duck type，不反向依赖 `application`

### `src/application/`

- `runtime_config.py`：共享运行时 profile/config 解析
- `container.py`：共享应用容器，集中持有 repo/store/service
- `device_factory.py`：按 runtime profile 构建设备与 mock adapter
- `live_preview_service.py`：共享预览采集服务
- `live_run_registry.py`：live run draft registry
- `live_run_service.py`：live run 应用服务
- `preview_render.py`：共享 preview bitmap/render helper

### `src/workflow/`

- `adjustments.py`：adjustment state 组装、draft 保存、apply 版本推进
- `camera_probe.py`：受控真实相机单帧探测编排与错误归一化
- `session.py`：测试会话上下文
- `state_machine.py`：状态流转
- `precheck.py`：开测前检查

### `src/storage/`

- `probe_diagnostics.py`：camera probe 轻量诊断 JSONL 留痕
- `session_artifacts.py`：replay detail 等 JSON artifact 持久化
- `session_adjustments.py`：adjustment draft / applied version JSON 持久化
- `session_store.py`：会话索引
- `sqlite_repo.py`：SQLite 持久化
- `csv_exporter.py`：曲线导出

### `src/report/`

- `summary.py`：结果摘要
- `plotter.py`：绘图或导出图像

### `src/webapp/`

- `app.py`：FastAPI app factory
- `config.py`：兼容层，委托 `src.application.runtime_config`
- `deps.py`：Web 层依赖注入，委托共享 `ApplicationContainer`
- `schemas.py`：请求/响应模型
- `serve.py`：Web 启动入口
- `routes/health.py`：健康检查路由
- `routes/profile.py`：profile / precheck / camera probe 路由
- `routes/session.py`：session / replay / adjustment API 路由
- `routes/ui.py`：页面路由与 workspace 页面入口

### `src/desktop_app/`

- `controller.py`：桌面壳 controller，复用共享 application layer
- `main.py`：桌面入口、smoke 和 benchmark CLI
- `qt_runtime.py`：Qt / MVS runtime bootstrap 辅助
- `window.py`：最小桌面主窗口
- `preview_canvas.py`：桌面预览画布
- `overlay_math.py`：桌面 overlay 几何辅助

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
MockCamera / HikRtspCamera / HikGigeMvsCamera
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

Web 交互入口冻结为：

```text
Browser
   ↓
src.webapp
   ↓
src.application
   ↓
workflow / storage / report
```

桌面交互入口冻结为：

```text
Desktop shell
   ↓
src.desktop_app
   ↓
src.application
   ↓
workflow / storage / report
```

说明：

- 真正的设备控制命令后置，先把离线主链打通。
- GUI 不决定算法结构；Web 和桌面壳都通过共享 application layer 进入主链。
- `workflow` 只负责编排，不替代 `vision` 或 `curve`。
- `workflow.camera_probe` 只负责编排受控单帧探测，不替代 `camera` 层 SDK 访问实现。
- `webapp` 负责 HTTP / HTML 交互壳和 Web 依赖注入，不直接连接相机、温度、PLC。
- `desktop_app` 负责桌面壳和原生预览控件，不复制共享应用服务。

## 6. 约束提醒

- 不新增 `utils/`、`common/`、`shared/`。
- 不把视觉算法塞进 `camera`。
- 不把结果计算塞进 `workflow`。
- 不在 `storage` 中调用 `workflow`。
- 不让 `report` 直接读取相机、温度或 PLC。
- 不让 `webapp` 或 `desktop_app` 重新成为共享业务逻辑的事实来源。
