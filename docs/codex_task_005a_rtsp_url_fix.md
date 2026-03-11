# Task-005A：修正 Hikvision RTSP URL 生成规则

请先阅读：

- `docs/architecture_lock.md`
- `docs/module_map.md`
- `docs/master_control_plan.md`
- `docs/codex_response_contract.md`
- 当前项目里的 `src/camera/hik_rtsp_opencv.py`
- 当前项目里的 `tests/camera/test_hik_rtsp_opencv.py`

## 任务目标

修正 `build_hik_rtsp_url(...)` 的海康 RTSP 路径生成规则，使其更贴近真实 Hikvision 设备常见格式，避免后续接真机时因为 URL 路径错误无法打开流。

这轮是一个**小型热修正工单**，不要扩大范围。

## 问题说明

当前实现把 RTSP 路径生成为：

`/Streaming/channels/<channel><stream>`

例如 `channel=2, stream=1` 会生成：

`/Streaming/channels/21`

这在真实 Hikvision 场景里通常不对。

请把规则修正为：

`/Streaming/channels/<channel><stream:02d>`

也就是：
- `channel=1, stream=1` -> `.../Streaming/channels/101`
- `channel=1, stream=2` -> `.../Streaming/channels/102`
- `channel=17, stream=1` -> `.../Streaming/channels/1701`

## 范围

允许修改：
- `src/camera/hik_rtsp_opencv.py`
- `tests/camera/test_hik_rtsp_opencv.py`

不允许修改：
- `src/core/models.py`
- `src/core/contracts.py`
- `vision / curve / workflow / storage`
- 不新增一级模块
- 不改任务无关代码

## 功能要求

1. 修正 URL 生成：
`build_hik_rtsp_url(host="192.168.1.10", username="admin", password="secret", channel=2, stream=1, port=8554)`
应返回：
`rtsp://admin:secret@192.168.1.10:8554/Streaming/channels/201`

2. 保持现有适配器行为不退化：
- `capture_factory` 注入测试桩
- `open()` 延迟导入 `cv2`
- `read_frame()` 返回 `FramePacket`
- `frame_id` 递增
- `close()` 可重复调用

3. 测试更新：
- `channel=2, stream=1` 期望 `.../channels/201`
- `channel=1, stream=2` 期望 `.../channels/102`
- 建议补一个多位 channel 例子，如 `17, 1 -> 1701`

## 验收命令

至少运行：
`pytest -q`

可选补充：
`pytest -q tests/camera/test_hik_rtsp_opencv.py`

## 输出格式

请严格按照 `docs/codex_response_contract.md` 输出。
