# UI Information Architecture V1

Task-016 freezes the workspace information architecture before richer controls are added.

## Workspace Layout

The workspace page uses a four-part shell:

1. Top status bar
2. Left step navigation
3. Central main workspace
4. Right contextual side panel

This structure is fixed for the current phase even though the inner widgets are still placeholders.

## Top Status Bar

The top bar shows:

- session id
- current state
- current profile
- latest Af95 summary when available

The top bar is informational only in this phase.

## Left Step Navigation

The left rail freezes the six-step flow:

1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

The stepper is presentational in this phase and does not yet control workflow transitions.

## Main Workspace

The main area is reserved for:

- image/curve/detail viewers
- active task context
- operator-facing notes

For Task-016 it only needs placeholder cards and minimal session summary context.

## Side Panel

The right panel is reserved for:

- run summary
- parameter snapshot
- quick links back to session APIs

For Task-016 it remains a lightweight placeholder panel with the current session summary.

## Home Entry Rules

The home page must expose workspace entry points from:

- the latest run result area
- the recent sessions list

This allows users to move from list/detail summary views into the workspace shell without introducing a frontend framework.
