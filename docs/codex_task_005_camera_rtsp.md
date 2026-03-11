# Task-005：海康 RTSP 相机适配器最小实现

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/camera/hik_rtsp_opencv.py`
- 当前项目里的 `src/core/models.py`
- 当前项目里的 `tests/` 目录

## 任务目标

把当前的 `src/camera/hik_rtsp_opencv.py` 从占位实现升级成**最小可测的 RTSP 相机适配器**，但这轮仍然**不要求真实连上海康相机**。

本轮目标是把“真实相机接入”前最关键的工程边界先收住：

1. 有一个稳定的 `HikRtspCamera` 适配器。
2. 能根据海康常见 RTSP 规则生成 URL。
3. 能通过 OpenCV `VideoCapture` 风格接口读取一帧并返回 `FramePacket`。
4. 单元测试不依赖真实相机、不依赖真实网络。
5. 尽量不改 `core` 契约。

这次任务不是 GUI，不是 PLC，不是温控采集，也不是工业相机 SDK。

---

## 范围

### 优先修改文件

- `src/camera/hik_rtsp_opencv.py`
- `tests/camera/test_hik_rtsp_opencv.py`（若不存在则新建）
- `src/camera/__init__.py`（如有必要）

### 尽量不要改动

- `src/core/models.py`
- `src/core/contracts.py`
- `src/vision/*`
- `src/curve/*`
- `src/workflow/*`
- `src/storage/*`

除非你遇到阻塞性问题，否则这轮不要改 `core` 契约。

---

## 功能要求

### 1. RTSP URL 构造函数

请在 `src/camera/hik_rtsp_opencv.py` 提供一个清晰、可测的函数，例如：

```python
def build_hik_rtsp_url(
    host: str,
    username: str,
    password: str,
    channel: int = 1,
    stream: int = 1,
    port: int = 554,
) -> str:
    ...
```

目标格式可按海康常见规则：

```text
rtsp://<username>:<password>@<host>:<port>/Streaming/channels/<channel><stream>
```

要求：

- 参数命名清楚。
- 默认值合理。
- 对 `channel`、`stream`、`port` 做最小输入校验；非法值要抛出明确异常。

### 2. HikRtspCamera 最小适配器

请把占位类升级为最小可用版本。推荐但不强制的接口：

```python
class HikRtspCamera(CameraPort):
    def __init__(
        self,
        rtsp_url: str,
        capture_factory: Callable[[str], Any] | None = None,
        auto_open: bool = False,
        source_name: str = "hik_rtsp_opencv",
    ) -> None:
        ...

    def open(self) -> None:
        ...

    def read_frame(self) -> FramePacket:
        ...

    def close(self) -> None:
        ...
```

要求：

- `capture_factory` 允许测试时注入 fake capture，避免单测依赖真实 `cv2`。
- 若未提供 `capture_factory`，请在 `open()` 内部再尝试导入 `cv2`，不要在模块导入阶段强依赖它。
- `open()` 成功后保存 capture 对象。
- `read_frame()` 读取一帧成功时返回 `FramePacket`：
  - `timestamp_ms` 为当前毫秒时间戳
  - `source` 为稳定来源名
  - `image` 为读取到的 frame
  - `frame_id` 为递增计数
  - `meta` 至少包含 `transport="rtsp"`、`backend="opencv"`
- `close()` 应释放底层 capture，并允许重复调用而不崩。

### 3. 失败行为

请给出清晰、可测的失败行为：

- 无法打开流时抛出明确异常
- `read()` 返回失败时抛出明确异常
- `rtsp_url` 为空时抛出明确异常

这轮不要求你引入新的全局错误体系；如果确实不需要改 `core/errors.py`，就不要改。

### 4. 测试要求

至少覆盖这些场景：

1. `build_hik_rtsp_url(...)` 输出符合预期。
2. 读取两帧时 `frame_id` 单调递增。
3. `read_frame()` 返回的 `FramePacket.image` 等于 fake capture 产出的对象。
4. 打开失败会抛异常。
5. 读帧失败会抛异常。
6. `close()` 会调用底层 `release()`，且重复关闭不会报错。

注意：

- 单元测试不要访问真实网络。
- 单元测试不要要求本机安装真实海康 SDK。
- 单元测试最好也不要要求本机必须安装 `cv2`；优先通过 `capture_factory` 注入 fake capture。

---

## 设计约束

1. 仍然遵守 `docs/architecture_lock.md`。
2. 不新增一级模块。
3. 不创建 `utils/`、`common/`、`shared/`。
4. 导入风格保持 `src.*` 绝对导入。
5. 不把视觉算法塞进 camera 适配器。
6. 不在这轮处理温度、PLC、同步、会话编排。

---

## 可选但推荐

如果你认为合适，可以让 `HikRtspCamera` 支持：

- 显式 `is_opened()`
- 作为上下文管理器使用

但这不是强制项；优先保证主链简单稳定。

---

## 验收命令

至少运行：

```bash
pytest -q
```

如果你为相机适配器单独补了定向测试，也请把命令和结果一并附上。

---

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
