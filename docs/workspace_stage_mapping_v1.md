# Workspace 阶段映射说明 v1（Task-018 对应）

## 目标
把当前 `/workspace/{session_id}` 左侧的 6 步导航，从“静态展示”推进为“会话阶段状态展示”。

这轮不做真正步骤切换，也不做参数调整，只做：
- 当前会话在工作流中的阶段映射
- stepper 的视觉状态表达
- 右侧摘要区的层级整理

---

## 一、当前问题
当前 stepper 已经有 6 个步骤：
1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

但它现在主要还是静态结构，不能清晰表达：
- 当前会话处于哪个阶段
- 哪些步骤已完成
- 哪些步骤尚未开始
- mock / replay 会话在当前阶段应如何投影到 UI

---

## 二、阶段映射原则

### 1. 当前阶段先做“只读映射”
本轮不新增后端复杂状态机字段，不改 `core` 契约。
优先用现有信息推导页面阶段，例如：
- session summary 是否存在
- session state 是否 completed / failed
- 是否有 replay detail
- detail 是否包含 points / key_frames

### 2. replay 会话的默认映射
对当前已有 replay 会话，建议映射为：

- 准备：done
- 采集：done
- 处理：done
- 计算：active
- 调整：todo
- 存储：done（若 summary/detail 已存在）

说明：
- replay 本质上是“已经完成采集”的数据
- 当前工作台第一版主要承载“处理/计算结果查看”
- 因此本轮最合理的高亮阶段仍然是“计算”
- 如果 summary/detail 均已落盘，存储可以显示 done

### 3. mock 会话的默认映射
对 mock 会话，建议映射为：
- 准备：done
- 采集：done
- 处理：done
- 计算：active
- 调整：todo
- 存储：done（如果 summary 已保存）

因为 mock 当前没有 detail 图像资产，显示逻辑可更简化。

---

## 三、建议的步骤状态集合

每一步支持以下最小状态：
- `done`
- `active`
- `todo`
- `error`（可选）

推荐默认：
- 正常 replay/mocks：使用 `done/active/todo`
- 若 session state = failed：把“计算”或当前阶段显示为 `error`

---

## 四、右侧摘要区分层建议

将当前 side panel 拆成更清晰的 4 个卡片：

### A. Workflow Stage
显示：
- 当前阶段名称
- session state
- 当前模式（replay / mock）
- 当前步骤说明

### B. Session Summary
显示：
- session_id
- point_count
- af95
- created / artifact presence（若可得）

### C. Detail Snapshot
显示：
- source
- points 数量
- key_frames 数量
- detail 是否存在

### D. Quick Actions
显示：
- Return Home
- Refresh Workspace
- View Summary JSON（可选）
- View Detail JSON（可选）

---

## 五、页面行为建议

### 页面加载时
除了拉 summary 和 detail 外，还在前端做一次 stage mapping。

### Stepper 呈现
每步卡片显示：
- 步骤编号
- 步骤名称
- 状态标记
- 若是 active，可加一句最小说明

### 右侧摘要联动
stage mapping 的结果同步显示在右侧 `Workflow Stage` 卡片中。

---

## 六、本轮不做的事
- 不做真正步骤切换路由
- 不做参数调整面板
- 不做 ROI 编辑
- 不做手动点位覆写
- 不做 live 采集映射
- 不新增后端复杂状态机字段

---

## 七、验收标准（页面层）
- 用户进入 workspace 后，能明确看出当前会话处在哪一步
- replay 与 mock 至少能显示不同的阶段语义
- 右侧摘要区层次更清晰
- 页面仍然保持当前工作台的结构，不做大改版
