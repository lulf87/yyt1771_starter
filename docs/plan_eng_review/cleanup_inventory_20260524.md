# Cleanup Inventory - 2026-05-24

This file classifies the current workspace before cleanup. It is deliberately
conservative: classification first, deletion later.

## Primary Product Repository

Treat this as the current main project:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter
```

The product repository should keep its top-level shape limited to:

```text
configs/
docs/
examples/
src/
tests/
```

Plus normal project files such as:

```text
README.md
pyproject.toml
.gitignore
uv.lock
```

## Product Source And Tests

These are product assets and should not be cleaned as generated files:

```text
configs/*.yaml
docs/requirements/
docs/plan_eng_review/
src/
tests/
README.md
pyproject.toml
.gitignore
uv.lock
```

Important current untracked source files that appear to be part of the active
worktree成果:

```text
configs/dev_offline_capture.yaml
src/application/capture_camera_frames.py
src/camera/camera_frame_capture.py
src/camera/offline_capture_camera.py
src/temp/offline_capture_temp.py
src/vision/contour_direction.py
src/webapp/routes/debug.py
tests/application/test_capture_camera_frames.py
tests/application/test_container.py
tests/camera/test_camera_frame_capture.py
tests/camera/test_offline_capture_camera.py
tests/temp/test_offline_capture_temp.py
tests/vision/test_contour_direction.py
```

These should be reviewed and either committed, intentionally kept local, or
explicitly retired later. Do not delete them as "runtime clutter."

## Machine-Local Config

These are intentionally local and should not be committed as tracked baseline
configuration:

```text
configs/*.local.yaml
configs/*.local.yaml.disabled
```

Current important local file:

```text
configs/dev_lab.local.yaml
```

It currently preserves the real camera + LU92XX Modbus RTU local state.

## Current Standard Offline Material

Preserve this until explicitly replaced:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab
```

Reason:

- it is the current standard offline reproduction source
- it contains real-camera measurement-profile grayscale frames
- `configs/dev_offline_capture.yaml` points to it
- it includes temperature data needed for replay and analysis

Files that are part of this material:

```text
manifest.json
temperature.csv
frames/frame_*.npy
first_frame_raw.png
first_frame_preview.png
```

Do not delete this material during cleanup unless a new standard material has
been selected and the user explicitly confirms removal.

## Generated Runtime Data

These are runtime/generated categories. They can be cleaned later after explicit
confirmation and after preserving any needed evidence:

```text
examples/runtime/artifacts/
examples/runtime/diagnostics/
examples/runtime/*.sqlite3
examples/runtime/*server.log
MvSdkLog/
.playwright-mcp/
tmp/
output/
```

Current generated files/directories can still contain useful bug evidence, so
classification as generated does not mean safe to delete immediately.

## Workspace-Local Support Data

This is outside the product tree and should be treated as machine-local support
state:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local
```

Current checkpoint location:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/checkpoints/yyt1771_starter-20260524-112416
```

This can help recover the current state if future cleanup or refactoring goes
wrong.

## Historical Reference Material

Treat these as read-only historical references unless a task explicitly targets
them:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/archive
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/archive/Orgincoding
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/archive/温控
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/archive/AFAS
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/归档
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/AFAS
```

Use them for reference only. Do not move code from these directories into the
product tree without a specific migration plan.

## Cleanup Order

Recommended cleanup sequence:

1. Keep the current local checkpoint.
2. Make sure the two formal run states still start.
3. Decide which untracked source files should become tracked product work.
4. Decide which generated runtime artifacts are no longer useful.
5. Only then delete old generated artifacts or superseded materials, with
   explicit user confirmation.

## Stop Conditions

Stop cleanup and ask before:

- deleting files or directories
- renaming high-level directories
- moving raw/offline material
- changing `configs/dev_lab.local.yaml`
- changing the standard offline material path
- reverting or overwriting dirty worktree changes
