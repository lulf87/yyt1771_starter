# Current Run Modes Freeze - 2026-05-24

This file freezes the two operator-relevant run modes that should be preserved
before any cleanup work. It is an engineering-state document, not a new product
requirement.

## Scope

Primary product repository:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter
```

Workspace root:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771
```

Recommended Python for current Web workstation startup on this Mac:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11
```

The current project should be treated as having only two formal run states for
active debugging:

1. real camera + real temperature controller
2. offline capture material replay

Other profiles and historical folders may remain useful as references, but they
should not be treated as the main operator states unless this file is updated.

## State A - Real Camera And Real Temperature Controller

Purpose:

- connected-device validation
- final hardware behavior checks
- confirming camera acquisition, temperature readback, setpoint write, output
  power write, and live A/B tracking against real hardware

Profile:

```text
configs/dev_lab.yaml
configs/dev_lab.local.yaml
```

Loading rule:

- `src.application.runtime_config.load_runtime_config("dev_lab")` loads
  `configs/dev_lab.yaml`
- if present, `configs/dev_lab.local.yaml` is automatically deep-merged over it
- `configs/*.local.yaml` is ignored by git and is the correct place for
  machine-local hardware details

Current local hardware adapter state:

```text
camera adapter: hik_gige_mvs
temperature adapter: lu92xx_modbus_rtu
plc adapter: mock
```

Current tracked baseline highlights:

```text
profile: dev_lab
mode: lab
web port: 8000
measurement device ROI: x=512, y=342, width=2048, height=1364
preview target fps: 20
measurement target Hz: 20
manual_stop_max_samples: 0
```

Current local temperature-controller highlights:

```text
protocol: modbus_rtu
slave_address: 1
serial port: /dev/cu.usbserial-11110
baudrate: 19200
process_value register: 264, decode_scale=0.1
target_or_stop_value register: 0, encode_scale=10.0
output_power register: 4, encode_scale=256.0
start_output_mode: power_nonzero
startup_power_percent: 100.0
completion_mode: target_reached
```

Current local run override:

```text
stop_on_invalid_tracking: false
```

Startup command:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_lab
```

Expected URL:

```text
http://127.0.0.1:8000/
```

Validation boundary:

- do not report this state as hardware-verified unless the real camera and
  temperature controller were connected during the current validation
- do not commit real site identities, fixed IPs, serial numbers, or credentials
  into tracked baseline config files

## State B - Offline Capture Material Replay

Purpose:

- reproduce A/B detection, ROI rotation, live curve, manual stop, terminal
  result, and analysis-page behavior without connected hardware
- debug the same measurement-resolution frame chain with recorded temperature
  data

Profile:

```text
configs/dev_offline_capture.yaml
```

Current adapter state:

```text
camera adapter: offline_capture
temperature adapter: offline_capture
plc adapter: mock
```

Current standard offline material:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab
```

Material summary from `manifest.json`:

```text
source profile: dev_lab
camera profile: measurement
target fps: 10.0
achieved fps: 9.677583513485446
frame count: 5807
frame format: npy
frame shape: 1364 x 2048
dtype: uint8
duration limit: 600.0 s
elapsed: 600.0464880419895 s
temperature csv: temperature.csv
```

Temperature range previously measured from `temperature.csv`:

```text
min: about 1.2 C
first: 1.4 C
last/max: 15.0 C
```

Current profile highlights:

```text
profile: dev_offline_capture
mode: offline
web port: 8002
measurement device ROI: x=0, y=0, width=2048, height=1364
preview target fps: 10
measurement target Hz: 10
artifact capture Hz: 10
manual_stop_max_samples: 0
stop_on_invalid_tracking: false
```

Startup command:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_offline_capture
```

Expected URL:

```text
http://127.0.0.1:8002/
```

Current observed process state during this freeze:

```text
python process listening on 127.0.0.1:8002
```

Validation boundary:

- this state can validate offline reproduction and UI flow
- it cannot validate real Modbus writes or real camera SDK device-open behavior
- live run throughput in this state is currently processing-bound by A/B
  contour extraction, not by the source material fps

## Preservation Rules

1. Keep these two states usable before doing cleanup.
2. Do not delete the current standard offline material without explicit
   confirmation.
3. Do not move machine-local hardware config into tracked baseline config.
4. If a new material becomes the standard offline replay source, update this
   file and `configs/dev_offline_capture.yaml` together.
5. If the real hardware profile changes from `dev_lab`, update this file before
   changing operator instructions.
