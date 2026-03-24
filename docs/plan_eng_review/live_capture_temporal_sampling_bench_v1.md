# Live Capture Temporal Sampling Bench v1

Updated on 2026-03-23
Status: REAL_CAMERA_BENCH_RECORDED

## Purpose

这份 bench 记录只回答 temporal-sampling workstream 的 3 个问题：

1. 真实海康相机在当前 Mac bench 上，到底能不能到 `50 Hz`
2. 哪些 profile / ROI 组合可以过 gate，哪些不行
3. 这些结论是否已经通过正式 artifact / telemetry 路径落盘

这不是 requirement 文档，也不是 UI QA 文档。

---

## Bench environment

- host: 当前这台 Mac
- camera runtime: Hik MVS official Python binding + patched local dylib runtime
- camera identity:
  - model: `MV-CA060-11GM`
  - serial_number: `00J67378626`
  - ip: `192.168.3.211`
- adapter path:
  - [hik_gige_mvs.py](../../src/camera/hik_gige_mvs.py)
  - [deps.py](../../src/webapp/deps.py)
  - [live_run.py](../../src/workflow/live_run.py)

重要约束：

- 这轮 bench 使用了真实相机
- 这轮 bench 没有使用真实温控器
- coordinator 路径使用的是 `mock` temp controller 和 mock metric source
- 因此这份记录可以证明 camera / workflow / artifact 的 `50 Hz` cadence gate
- 但它**不能**被表述成“真实温升-形变实验链已经完整通过”

---

## Bench cases

### Case A. Direct camera read, full frame, target `50 Hz`

配置：

- measurement target: `50.0 Hz`
- acquisition ROI: full frame

结果：

- `camera_resulting_fps = 14.8619`
- host-side measured cadence: `7.19 Hz`
- frame shape: `3072 x 2048`
- frame id trace:
  - first: `1`
  - last: `50`

结论：

- full-frame measurement mode 在当前 bench 上**不能**达到 `50 Hz`
- adapter 现在会把 `camera_resulting_fps` 和 frame-id evidence 带回上层

### Case B. Direct camera read, `512 x 512` ROI, target `50 Hz`

配置：

- measurement target: `50.0 Hz`
- acquisition ROI: `x=0, y=0, width=512, height=512`

结果：

- `camera_resulting_fps = 50.0`
- host-side mean interval: `20.08 ms`
- host-side measured cadence: `49.79 Hz`
- frame shape: `512 x 512`

结论：

- 当前 bench 上，camera-side measurement ROI 已足以把真实相机拉到 `~50 Hz`
- `50 Hz` baseline 不能依赖 full frame；必须依赖 measurement acquisition profile

### Case C. Coordinator + artifact path, real camera + mock temp, `512 x 512` ROI

配置：

- runtime path: [live_run.py](../../src/workflow/live_run.py) coordinator
- measurement target: `50.0 Hz`
- artifact target: `50.0 Hz`
- acquisition ROI: `x=0, y=0, width=512, height=512`
- temp backend: `mock`
- metric source: mock

artifact/result facts：

- telemetry rows: `20`
- `measurement_sample_hz = 50.1319`
- `camera_resulting_fps = 50.0`
- `artifact_capture_hz = 50.1319`
- `dropped_frame_count = 0`
- warnings: `[]`
- measurement profile:
  - `acquisition_roi = 512 x 512`
  - `decimation = None`
  - `binning = None`
  - `exposure_us = 10000`
- `definition.json / telemetry.csv / detail.json / result.json / keyframes/first.png` 全部落盘成功

结论：

- `50 Hz synchronized measurement` 的 camera/workflow/artifact gate 已经在真实相机上被证明可达
- achieved cadence 已经进入 artifact 和 result contract，而不是停留在 bench 脚本打印

### Case D. Coordinator + artifact path, real camera + mock temp, full frame

配置：

- measurement target: `50.0 Hz`
- acquisition ROI: full frame

artifact/result facts：

- telemetry rows: `20`
- `measurement_sample_hz = 7.2686`
- `camera_resulting_fps = 14.8619`
- `artifact_capture_hz = 7.2686`
- `dropped_frame_count = 18`
- warnings:
  - `measurement cadence below target: achieved 7.27 Hz < target 50.00 Hz`
  - `measurement dropped frames detected: 18`
- measurement profile:
  - `acquisition_roi = None`
  - `decimation = None`
  - `binning = None`
  - `exposure_us = 10000`

结论：

- full-frame path 在真实 coordinator bench 上也明确失败
- current baseline 必须写成：
  - `50 Hz` 依赖 camera-side reduced acquisition profile
  - full frame 仅能作为失败对照，不得再被当成 target profile

---

## Locked conclusions

当前可以锁定的 engineering 结论：

- 海康官方 SDK path 现在已经真正应用了 `AcquisitionFrameRateEnable` / `AcquisitionFrameRate`
- `measurement_target_hz` 已进入正式 run pacing，而不是只作为 warning target
- adapter 现在会把 `camera_resulting_fps` 和 hardware-derived frame evidence 带到 workflow
- 未配置 measurement ROI 时，adapter 会尽力把设备 ROI 复位到 full frame，避免沿用前一次会话的残留 ROI
- `50 Hz` baseline 在当前真实相机上是可达的，但需要 measurement acquisition ROI

当前仍然**不能**锁定的结论：

- 真实 LU92XX 温控链已经达到 `50 Hz`
- 真实位移提取链已经在现场图像上完成动态 tracking bench
- `100 Hz` 已可达

---

## Recommended interpretation

后续如果有人问“TS-5 到底算不算完成”，当前最诚实的说法是：

- 对 camera / workflow / artifact cadence workstream：算完成
- 对真实温控器闭环实验链：不算完成

因此 TS-5 的状态应被解释成：

- real camera cadence gate: passed
- full-chain thermal experiment gate: not yet claimed
