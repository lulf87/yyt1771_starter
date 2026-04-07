# Live Run Bench Validation v1

Updated on 2026-04-01
Status: BLOCKED_ON_PHYSICAL_LU92XX_BENCH

## Purpose

这份记录用于收口 Task-F / Phase 6 的现实状态：

1. 当前默认 profile 已经锁到了哪一级
2. 哪些 bench 事实已经确认
3. 哪些结论还**不能**宣称为真机已验证

这不是代码设计文档，而是一份 bench 现场记录。

补充事实：

- 2026-04-01 用户明确说明当前没有接任何外设
- 因此当前 bench 记录不只意味着“LU92XX 串口 bench 阻塞”，也意味着真实相机 / 温控器 / 外部采集链路均未接入

---

## Current locked profile snapshot

当前仓库中的 LU92XX profile 默认值已经锁定为：

- backend: `lu92xx_modbus_rtu`
- protocol: `modbus_rtu`
- slave_address: `1`
- serial: `19200 / 8N1 / timeout 500 ms`
- `process_value.start_address = 264`
- `process_value.decode_scale = 0.1`
- `target_or_stop_value.start_address = 0`
- `target_or_stop_value.encode_scale = 10.0`
- `output_power.start_address = 4`
- `output_power.encode_scale = 256.0`
- `start_output_mode = power_nonzero`
- `startup_power_percent = 100.0`

代码层面已经支持：

- `258` 作为 `process_value.start_address` 的 profile override
- `read()` 的 x10 decode
- `set_target_temperature()` 的 reg `0` x10 encode
- `start_output()` / `stop_output()` 的 reg `4` 写入
- Modbus exception / no response / bad CRC 的显式错误语义

这些结论来自仓库代码与单元测试，不来自真机 bench。

---

## Bench environment check

2026-03-21 的本机检查里，实际看到的串口设备只有：

- `/dev/cu.Bluetooth-Incoming-Port`
- `/dev/cu.debug-console`

没有发现任何明显的 USB 转串口 / RS485 设备节点，例如：

- `/dev/cu.usbserial-*`
- `/dev/cu.usbmodem*`
- `/dev/cu.SLAB_USBtoUART`
- `/dev/cu.wchusbserial*`

因此当前无法对 LU92XX 做真实串口 bench。

结合 2026-04-01 的用户说明，当前可进一步锁定：

- 没有接入真实相机外设
- 没有接入真实温控外设
- 没有接入可用于 Phase 6 的外部硬件链路

因此当前所有与真机相关的结论都必须继续保持：

- blocked on physical hardware
- mock / fake 验证可继续推进
- 不宣称任何真实外设 ready

---

## What was verified

已验证：

- `prod_win.yaml` 已切到 `lu92xx_modbus_rtu` backend，并带默认寄存器映射
- `dev_lab.local.example.yaml` 已提供 LU92XX 本地覆盖样例
- `tests/temp/test_lu92xx_modbus_rtu_controller.py` 覆盖了：
  - reg `264` x10 decode
  - reg `0` x10 encode
  - reg `4` x256 encode
  - `258` override
  - bad CRC
  - no response
  - exception response
  - repeated close / stop path
- `tests/webapp/test_config_loader.py` 覆盖了 typed temp config 与 override

未验证：

- `264` 是否真的是现场 LU92XX 的当前温度寄存器
- `258` 是否才是现场实际寄存器
- reg `0` 的业务语义是否应理解为 target 还是 stop
- reg `4 = 0` 是否足以真实停输出
- `19200 / 8N1 / slave=1` 是否与现场设备一致

---

## Task-F conclusion

当前 Task-F 只能完成到：

- profile lock record 已建立
- bench 阻塞原因已记录
- 真机前必须检查的 checklist 已明确

当前**不能**完成到：

- LU92XX 真机 ready 声明
- `264 vs 258` 的现场裁决
- 已验证 profile 样例
- 真实 result artifact sample

结论：

- Phase 5 代码与配置层已经 ready
- Phase 6 bench validation 仍 blocked，需要物理 LU92XX 串口链路出现后继续
- 当前若继续推进首页 / setup 新需求，应默认在无外设环境下完成 UI、状态流和契约层工作
