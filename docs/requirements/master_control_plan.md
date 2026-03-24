# 主控开发总规划（Master Control Plan）

这份文件定义项目的固定推进顺序。
从现在开始，Codex 的每个工单都必须服从这里的阶段划分，不得跳步。

## 1. 总体目标

围绕 YY/T 1771 的视觉法上位机，先打通离线最小主链，再逐步接入真实设备。

正式交互路线冻结为：

```text
Browser -> Web API -> Workflow/Storage/Report
```

其中：

- Mac：开发、测试、mock 联调
- Windows：最终真实设备运行环境
- 浏览器：最终用户交互入口

项目固定主链：

```text
Frame -> ShapeMetric -> SyncPoint -> Curve -> Result
```

其中：

- `Frame` 来自相机层
- `ShapeMetric` 来自视觉层
- `SyncPoint` 来自同步层
- `Curve/Result` 来自曲线层

## 2. 阶段顺序

### Phase 0：结构冻结

目标：冻结目录、模块边界、测试布局。

结果：

- 顶层目录固定
- `src` 一级模块固定
- `tests` 镜像布局固定
- 初始导入守卫存在

状态：**已开始，当前已通过首轮骨架冻结。**

### Phase 1：契约冻结

目标：冻结离线主链所需的最小数据契约。

必须先稳定：

- `FramePacket`
- `ShapeMetric`
- `SyncPoint`
- `VisionMetricExtractor`

输出标准：

- 视觉任务不再依赖临时字段名
- 测试与示例都使用统一字段
- 后续任务不再随意改 dataclass 语义

### Phase 2：vision 最小单元

目标：实现第一个真正可用的形变量提取器。

范围：

- `src/vision/metric_end_displacement.py`
- 合成图单元测试

要求：

- ROI 裁剪
- 灰度/彩色兼容
- 二值化
- 最大轮廓
- 自由端位置提取
- baseline 锁定
- 质量评分

### Phase 3：curve 最小单元

目标：把视觉结果组织成可用于求点的曲线。

范围：

- `src/curve/buffer.py`
- `src/vision/normalizer.py`
- `src/curve/af95.py`

要求：

- 曲线缓存
- metric 归一化
- Af95 初版计算

### Phase 4：workflow + storage

目标：把脚本式调用升级为“测试会话”。

范围：

- `src/workflow/session.py`
- `src/workflow/state_machine.py`
- `src/storage/sqlite_repo.py`
- `src/storage/session_store.py`

要求：

- session_id
- 开始/停止/失败状态
- 曲线点落盘
- 结果可追溯

### Phase 5：真实设备接入

目标：在不破坏主链的前提下接入真实设备。

顺序固定为：

1. `camera`
2. `temp`
3. `plc`

要求：

- 先 RTSP + OpenCV 跑通海康网络流
- 再接温度
- 最后接 PLC
- 不允许三路同时首接

### Phase 6：Web 交互冻结与扩展

目标：以 Web API 和浏览器交互替代桌面 GUI 路线。

范围：

- `src/webapp/`
- 运行 profile 配置
- 后续浏览器页面与接口扩展

## 3. 当前阶段禁止项

在 Phase 1/2 期间，禁止：

- 先上 GUI
- 先上数据库 schema 大设计
- 先做复杂 PLC 控制逻辑
- 先做多阶段相变高级算法
- 先写大量“通用工具”目录

在 Web 路线冻结后，继续禁止：

- 新增桌面 GUI 主路线
- 让路由层直接操作设备适配器

## 4. 每轮工单的固定格式

每一轮都遵循：

1. 我给出任务边界
2. 你把任务发给 Codex
3. Codex 返回 diff + 测试输出
4. 你把结果贴回给我
5. 我验收后再发下一轮工单

## 5. 当前下一步

当前路线补充说明：

- 最终交互不是桌面 GUI，而是 Web。
- 同一套 Python 后端代码需要支持 Mac 开发和 Windows 生产，差异通过配置文件控制。

原因：

- 当前骨架已经有了，但 `FramePacket` / `ShapeMetric` 的字段语义还没有为真实视觉算法固定下来。
- 如果现在直接写算法，后面很可能因为字段名和数据结构不稳定而反复返工。
