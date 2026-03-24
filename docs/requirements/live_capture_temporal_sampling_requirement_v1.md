# Live Capture Temporal Sampling Requirement v1

Updated on 2026-03-23
Status: CANONICAL_REQUIREMENT_ADDENDUM

## Purpose

这份文档用于把“相机刷新率需要提升”收敛成可执行的正式需求。

它要解决的不是一个单点抱怨，而是 4 个经常被混在一起的概念：

1. 相机真实出帧率
2. 浏览器预览刷新率
3. 位移/形变量测量采样率
4. telemetry / artifact 落盘间隔

如果这 4 个量不拆开，后续实现很容易出现两类误判：

- 只把浏览器画面刷快了，但测量曲线仍然采样不足
- 只把相机拉到更高帧率，却没有保证温度与位移的同步时间基准

---

## Context

当前现场反馈很明确：

- 相机预览刷新率偏低
- 这会影响操作者判断温升与形变量之间曲线关系的可信度
- 需求方向不是“把页面动画做得更顺”，而是要提升对真实实验过程的时域分辨率

因此，这次 requirement 的主语不是单纯的 UI preview，而是：

`live capture + synchronized measurement`

---

## Current Reality On This Bench

截至 2026-03-23，这台 Mac + 当前相机链路的已知事实是：

- 当前相机型号：
  - `MV-CA060-11GM`
- 当前相机桥运行日志显示：
  - `ResultingFrameRate[14.86]`
  - `ExposureTime[10000.00]`
  - `PayloadSize[6291456]`
  - `GevLinkSpeed[1000]`

本机证据：

- [CamCtrl_00.log](../../MvSdkLog/CamCtrl_00.log)

这说明当前 bench 上的真实限制不是只有浏览器显示慢，而是：

- 当前相机在当前 full-frame / exposure / GigE 配置下，本身就只有约 `14.86 fps`
- 当前 web preview 实现还在此基础上继续做了额外节流和 PNG 编码

因此，“提升刷新率”必须拆成：

- 提升 setup preview 的操作流畅度
- 提升 measurement path 的实际采样频率

而不是把两者继续当成同一件事。

---

## External Evidence

以下在线资料用于支撑这次 requirement，不用于替代本机 bench 结果。

### 1. ROI / image size directly affects max frame rate

Basler 官方文档指出：

- Image ROI 只传 ROI 内的像素
- 在多数相机上，缩小 image ROI，尤其是缩小高度，会显著提高最大帧率

Source:

- [Basler Image ROI](https://docs.baslerweb.com/image-roi)

### 2. Exposure time and frame rate are coupled

Basler 官方文档指出：

- Exposure Time 决定图像传感器暴露时长
- 有效曝光时间会受到传感器和 frame rate 影响

这意味着更高采样频率通常会要求：

- 更短曝光
- 更稳定照明
- 或者更低分辨率/更小采集区域

Source:

- [Basler Exposure Time](https://docs.baslerweb.com/exposure-time)

### 3. Acquisition frame rate is a distinct controllable limit

Basler 官方文档指出：

- `AcquisitionFrameRate` 只是给相机帧率设置上限
- 实际帧率仍受其他限制因素影响
- 应使用 resulting frame rate 类参数看真实结果

这和本项目的需求高度一致：不能只看“想设多少 Hz”，而必须看“真实达到了多少 Hz”。

Source:

- [Basler Acquisition Frame Rate](https://docs.baslerweb.com/acquisition-frame-rate)

### 4. Reducing payload / bandwidth pressure can raise frame rate

Basler 官方文档指出：

- 压缩图像数据可降低带宽占用
- 也可能提升帧率

虽然当前项目未必采用相机端压缩，但这个资料强化了一个工程事实：

- 带宽和 payload 不是旁枝问题，而是帧率预算的一部分

Source:

- [Basler Compression Beyond](https://docs.baslerweb.com/compression-beyond)

### 5. Binning / decimation are valid frame-rate levers

Basler 官方文档指出：

- binning 可以减少传输数据量，并可能提高帧率
- decimation 通过减少发送的行/列来减少数据量，并可能提高帧率

这为当前项目提供了明确方向：

- 如果目标是 50 Hz 或 100 Hz 的测量采样，必须允许把“相机侧采集模式”从 full frame 切到更激进的 measurement mode

Sources:

- [Basler Binning](https://docs.baslerweb.com/binning)
- [Basler Decimation](https://docs.baslerweb.com/decimation)

---

## Office-Hours Synthesis

这轮 `/office-hours` 风格梳理后的核心结论是：

### The real requirement is not "higher preview FPS"

真实需求应表述为：

> 系统必须提供足够的时域采样能力，使温度上升过程中的形变量变化能够被可信地同步观察、记录与回放。

这句话比“页面更流畅”更接近项目目标。

### The requirement must separate operator preview from measurement sampling

操作者需要的是：

- setup 阶段能看清画面变化
- freeze / draw ROI / place A/B 时交互不卡顿

算法与实验需要的是：

- 温度与位移数据有足够高的同步采样频率
- 结果曲线不会因为采样过稀而失真

因此这两个目标必须拆开锁定。

### 50 Hz should be the locked baseline; 100 Hz is a stretch target

基于当前 bench 现实、1 GigE 带宽、当前相机日志、以及实现复杂度，当前推荐冻结为：

- `50 Hz synchronized measurement` 作为锁定目标
- `100 Hz synchronized measurement` 作为 stretch goal

这里的“measurement”不是指浏览器里全分辨率图像 50/100 fps。
它指的是：

- 相机采样
- 位移测量
- 温度同步
- 时间戳对齐

共同组成的 measurement path。

这是根据现场约束和外部资料做出的工程判断，不是来自某一份单独文档的原话。

---

## Frozen Requirement

从现在开始，关于刷新率/采样率的 requirement 冻结如下。

### R1. Separate four rate concepts explicitly

系统必须在 requirement、plan、config、UI 和测试中明确区分：

- `camera_resulting_fps`
- `preview_display_fps`
- `measurement_sample_hz`
- `artifact_capture_hz`

任何后续文档或实现，如果继续用一个模糊的“刷新率”覆盖这四者，应视为 requirement drift。

### R2. Full-frame browser preview at 50/100 Hz is not the baseline requirement

系统当前不要求：

- 在浏览器里以 full-frame 图像实现 `50 Hz` 或 `100 Hz` 的实时显示

原因是：

- 这与项目真正要解决的“曲线采样是否足够”不是同一问题
- 在当前 1 GigE 和当前相机 full-frame 现实下，也不应被当成基线承诺

### R3. Setup preview must become meaningfully more fluid than today

系统必须显著优于当前的低频 setup preview 体验。

冻结要求：

- setup preview 的目标是“让操作员能稳定观察画面变化并完成设置”
- 它应作为独立目标被优化
- 但它不等于 measurement mode 的采样目标

当前不在 requirement 中硬锁一个单一 preview fps 数字，因为真正上限仍取决于：

- 预览传输格式
- downsample/encode 开销
- 浏览器显示路径

### R4. Measurement mode must target synchronized 50 Hz as the minimum locked goal

系统必须提供一个 measurement-oriented live mode，其目标是：

- 温度采样与位移测量同步更新
- 实际 measurement sample rate `>= 50 Hz`
- 时间戳可追踪
- curve generation 以该同步时间基准为基础

这里的 requirement 落点是：

- `shape metric / displacement samples`
- `temperature samples`
- `shared time base`

而不是“图像显示帧率”本身。

### R5. 100 Hz is a stretch goal, not a baseline promise

系统应保留走向 `100 Hz synchronized measurement` 的架构空间，但它当前不应被写成已锁定的 bench 承诺。

要进入 `100 Hz`，至少允许并评估以下工程手段：

- camera-side ROI (`Width / Height / OffsetX / OffsetY`)
- decimation
- binning
- 更短 exposure
- 更强照明
- 更轻的 preview transport
- 预览与 measurement path 分离

### R6. Measurement mode may use a different camera acquisition profile from setup preview mode

系统必须允许至少两种不同的 live profile：

- `setup_preview_mode`
- `measurement_mode`

两者可以在以下维度不同：

- resolution / ROI
- exposure
- gain
- transport strategy
- preview encoding
- persisted frame density

换句话说：

- setup 阶段可以偏可视化
- measurement 阶段必须偏采样充分

### R7. Camera-side ROI is now a requirement-level concern

页面里的 `analysis_roi` 和 `metric_box` 只是分析定义，不足以保证更高的 measurement rate。

因此 requirement 正式新增：

- measurement mode 需要支持 camera-side acquisition ROI / reduced readout strategy

如果系统只有 analysis ROI，而没有 camera-side ROI / readout reduction capability，则不能声称已经完成高频 measurement requirement。

### R8. The system must expose actual achieved rates, not just desired rates

系统必须在 API、日志或 UI 中至少暴露以下真实值中的一部分：

- camera resulting frame rate
- preview delivered frame rate
- measurement sample rate
- dropped / skipped frame indicators if available

原因是：

- 设定值不等于达成值
- requirement 验证必须基于 achieved rate

### R9. Requirement validation must happen on the real bench

`50 Hz` 和 `100 Hz` 的 requirement 不能只用 mock 或理论推导验收。

必须在真实 bench 条件下验证：

- 实机相机
- 实际照明
- 实际 exposure
- 实际 ROI / measurement mode
- 实际温控过程

---

## Acceptance Criteria

下面的验收标准从现在开始作为后续计划和实现的 requirement gate。

### A. Setup Preview Gate

系统必须证明：

- 操作者可在 live setup 中稳定完成：
  - start preview
  - freeze
  - restart
  - ROI / observation window / A-B placement
- setup preview 不再停留在“明显低频到影响操作”的状态

### B. Measurement 50 Hz Gate

系统必须证明：

- 在 measurement mode 下，实际同步测量频率达到或超过 `50 Hz`
- 温度与位移数据的时间基准可追溯
- 导出的 telemetry / result artifact 能说明实际 sample cadence

### C. 100 Hz Stretch Gate

只有在以下条件同时满足时，才可宣称支持 `100 Hz`：

- 实际 achieved measurement sample rate `>= 100 Hz`
- 数据没有不可接受的丢帧/跳点
- 图像质量仍足以支撑 measurement extraction
- 温度同步链没有被降级成虚假的高频插值

### D. Non-cheating Gate

以下行为不能被视为 requirement 完成：

- 只把前端轮询刷快
- 只把 preview fps 刷快，但 measurement 仍低频
- 只写目标值，不展示 achieved value
- 只在 mock 环境声称 50/100 Hz

---

## Implications For Follow-up Planning

这份 requirement 对后续 plan 的直接影响是：

1. plan 必须把 `preview performance` 和 `measurement cadence` 分成两个 workstream
2. 相机适配层需要评估 camera-side ROI / decimation / binning capability
3. preview transport 需要评估比当前 PNG multipart 更轻的方案
4. telemetry / result contract 需要纳入 actual achieved sample-rate reporting
5. `50 Hz` bench validation 必须进入后续 test/bench plan

---

## Explicit Non-Goals

当前这份 requirement 不锁定以下内容：

- 浏览器 full-frame `100 fps` 视频显示
- 当前相机在 full-frame 条件下必须达到 `100 fps`
- 在未做 camera-side ROI / readout reduction 的情况下承诺高频 measurement

---

## Source Notes

### Repo-internal evidence

- [Current camera runtime log](../../MvSdkLog/CamCtrl_00.log)

### Online sources used

- [Basler Image ROI](https://docs.baslerweb.com/image-roi)
- [Basler Exposure Time](https://docs.baslerweb.com/exposure-time)
- [Basler Acquisition Frame Rate](https://docs.baslerweb.com/acquisition-frame-rate)
- [Basler Compression Beyond](https://docs.baslerweb.com/compression-beyond)
- [Basler Binning](https://docs.baslerweb.com/binning)
- [Basler Decimation](https://docs.baslerweb.com/decimation)

---

## Status

This document is now the canonical requirement addendum for all future work
related to:

- live preview performance
- synchronized measurement cadence
- 50 Hz / 100 Hz target discussions
- camera-side acquisition reduction strategy
