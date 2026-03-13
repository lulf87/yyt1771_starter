# WP-A：Adjustment MVP 页面与交互拆解说明 v1

## 目标
在当前已有：
- workspace 工作台
- replay detail
- 曲线与关键帧
- Active Selection
- Adjustment Preview（只读）
- adjustment 后端契约与 API

的基础上，一次性推进到 **Adjustment MVP**：

- 在 workspace 中开放最小可编辑 adjustment UI
- 支持 draft 保存
- 支持 apply 生效
- 展示 automatic result 与 latest result 的差异
- 展示 applied version history
- 保持现有 replay / mock / workspace 能继续工作

---

## 范围边界

### 本轮做
1. 只对 **结果层** 开放最小人工修正能力
2. 当前优先支持 `af95`
3. 使用已有 adjustment API：
   - `GET /api/session/{session_id}/adjustment`
   - `PUT /api/session/{session_id}/adjustment/draft`
   - `POST /api/session/{session_id}/adjustment/apply`
4. workspace 内增加：
   - Draft Editor
   - Latest Result vs Auto Result 展示
   - Version History 展示
5. 调整成功后，workspace 局部刷新，不要求整页重载

### 本轮不做
1. 不做 ROI 手动编辑
2. 不做 threshold / baseline / smoothing 真调参
3. 不做曲线拖拽
4. 不做 As / Af / Af-tan 真编辑
5. 不做 live 采集联动
6. 不做多用户/审批流
7. 不做复杂撤销/恢复系统

---

## 总体界面策略

### 现在的工作台层次
- 左：Workflow Stepper
- 中：Curve + Key Frames + Adjustment Preview
- 右：Workflow Stage / Summary / Active Selection / Detail Snapshot / Quick Actions

### WP-A 后的工作台层次
保留整体结构不变，但让“调整”真正有可用内容：

#### 中央区域
- Curve Panel（保留）
- Key Frame Panel（保留）
- Adjustment Panel（由只读 preview 升级为 MVP）

#### 右侧区域
- Workflow Stage（保留）
- Session Summary（增强）
- Active Selection（保留）
- Adjustment Status（新增）
- Version History（新增或并入 Adjustment Status 下方）
- Quick Actions（保留）

---

## 中央区域：Adjustment Panel 设计

### 1. Automatic Result Card
目的：明确系统自动结果。

字段建议：
- Auto Af95
- Auto source（replay / mock）
- Auto point_count
- Auto basis note

最少 hook：
- `adjustment-auto-af95`
- `adjustment-auto-source`

---

### 2. Latest Result Card
目的：明确“当前最新结果”是什么。

规则：
- 若没有 applied version，则 latest = auto
- 若已经 apply，则 latest 显示人工结果

字段建议：
- Latest Af95
- Latest result source（auto / adjusted）
- Latest version number（若存在）

最少 hook：
- `adjustment-latest-af95`
- `adjustment-latest-source`
- `adjustment-latest-version`

---

### 3. Draft Editor Card
这是 WP-A 的核心。

#### 当前仅开放：
- `af95` 输入框
- `reason` 文本域

#### 行为：
- 页面加载时读取 adjustment state
- 若已有 draft，则回填：
  - af95 草稿值
  - reason
- 用户可修改：
  - draft.af95
  - draft.reason
- 点击 Save Draft：
  - 调 `PUT /api/session/{session_id}/adjustment/draft`
- 点击 Apply Adjustment：
  - 调 `POST /api/session/{session_id}/adjustment/apply`

#### 校验建议：
- `reason` 必填
- `af95` 必须是 number 或空
- 如果 af95 未变、reason 为空，可禁用 apply
- Apply 前必须存在 draft

最少 hook：
- `adjustment-draft-af95`
- `adjustment-draft-reason`
- `adjustment-save-draft-btn`
- `adjustment-apply-btn`
- `adjustment-draft-status`

---

### 4. Adjustment Notes Card
目的：明确当前阶段只开放最小结果修正，不是完整参数编辑。

展示文案示例：
- 当前仅开放 Af95 最小手动修正
- As / Af / Af-tan 预留，暂未开放
- 图像处理与曲线参数调整后续开放

这个卡片可以减少误解。

---

## 右侧区域增强

### A. Adjustment Status
显示：
- 是否存在 draft
- draft 更新时间
- 是否存在 applied versions
- 当前 latest result 是否已被人工覆盖

建议 hook：
- `adjustment-has-draft`
- `adjustment-applied-count`
- `adjustment-is-manual`

---

### B. Version History
展示 applied_versions 列表。

每条至少显示：
- version
- reason
- created_at_ms
- result_before.af95
- result_after.af95

最开始可以做成简洁列表，不需要复杂折叠。

建议 hook：
- `adjustment-version-history`
- `adjustment-version-item`

---

## 交互流程

### 页面加载
并行请求：
- summary
- detail
- adjustment state

然后刷新：
- Curve / Key Frames
- Active Selection
- Automatic Result
- Latest Result
- Draft Editor
- Version History

---

### Save Draft
1. 读取输入框：
   - af95
   - reason
2. 请求：
   - `PUT /api/session/{session_id}/adjustment/draft`
3. 成功后：
   - 更新 draft 状态
   - 更新 Adjustment Status
   - 不改变 latest result

---

### Apply Adjustment
1. 请求：
   - `POST /api/session/{session_id}/adjustment/apply`
2. 成功后：
   - latest result 更新
   - version history 增加
   - draft 清空
   - Session Summary / Adjustment Status 同步刷新

---

## 曲线区最小增强建议
虽然 WP-A 不是“计算视图”主工单，但建议做两个小增强：

1. 当 latest result 与 auto result 不同时，
   - 在曲线区或结果区明确显示：
     - Auto Af95
     - Latest Af95
2. 如果已经 apply，
   - 在 UI 上明显表示当前结果已被 manual override

不要求重新画两套曲线，只做结果提示。

---

## 错误态与空态

### 1. Adjustment state 获取失败
- 页面不崩
- Adjustment Panel 显示错误提示
- 其他 summary/detail 区仍可用

### 2. Draft 保存失败
- 显示最小错误消息
- 不清空用户输入

### 3. Apply 失败
- 显示最小错误消息
- 保留 draft 状态

### 4. applied_versions 为空
- Version History 显示空态说明

---

## 视觉风格
继续沿用当前工业深色风格：
- 深色底
- 卡片式分区
- Auto / Latest 用清晰对比色
- Draft 输入区清楚但不花哨
- Apply 按钮比 Save Draft 更强调
- disabled 的未来项继续保留 Coming soon

---

## 本轮验收重点
完成后应能回答：
1. 当前自动 Af95 是多少？
2. 当前最新 Af95 是多少？
3. 有没有未应用 draft？
4. 有没有历史人工版本？
5. 每次人工应用的原因是否可追溯？
6. UI 是否已经具备最小可用的手动修正入口？
