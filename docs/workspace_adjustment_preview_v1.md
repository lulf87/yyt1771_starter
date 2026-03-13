# Workspace Adjustment Preview 拆解说明 v1（Task-020 对应）

## 目标
在不开放真实手动调整的前提下，把 `/workspace/{session_id}` 的“调整”步骤先落成一个只读预览区。

本轮聚焦：
- 自动分析依据可视化
- 提取与分析上下文可视化
- 未来可调整项的界面占位
- 当前选中点/帧与这些信息联动

不做：
- ROI 真正编辑
- threshold 真正修改
- Af95 真正改写
- 手动结果覆写
- 调整结果保存

---

## 一、为什么先做只读 Adjustment Preview
当前工作台已经有：
- 曲线
- 关键帧
- Af95
- Active Selection
- Workflow Stage
- Session Summary / Detail Snapshot

但还缺一层：
“本次自动分析是基于什么信息算出来的，以及未来哪些项会允许调整”。

所以本轮目标不是“可编辑”，而是先把“自动依据 + 未来调整入口”做成清晰的只读面板。

---

## 二、页面布局建议

### 1. 顶部状态栏
保持不变。

### 2. 左侧 stepper
保持当前 6 步：
1. 准备
2. 采集
3. 处理
4. 计算
5. 调整
6. 存储

本轮建议：
- 当前仍以“计算”为 active
- “调整”显示为 ready/upcoming
- 不做真正步骤切换

### 3. 中央主区
保留现有：
- Curve Panel
- Key Frame Panel

并在 Key Frame Panel 下方新增：

## Adjustment Preview

---

## 三、Adjustment Preview 结构

### A. Automatic Basis
目的：说明当前结果的自动分析依据。

建议字段：
- source
- point_count
- key_frame_count
- af95
- current_stage
- detail available
- 当前 active selection 的 timestamp / metric / feature point
- 一句自动分析说明文本

这是纯只读信息卡。

---

### B. Extraction & Analysis Context
目的：显示当前选中对象对应的提取/分析上下文。

建议字段：
- ROI
- feature_point_px
- baseline_px
- quality
- threshold_value
- component_area
- metric_norm
- 当前 stage

说明：
- 没有的数据可以显示 `N/A`
- 如果字段来自当前 active selection，则明确显示这是“current selection context”

---

### C. Future Adjustment Controls
目的：为后续真正“调整”步骤预留结构。

建议按三组展示：

#### 图像处理参数
- ROI
- threshold
- baseline lock

#### 曲线分析参数
- smoothing
- normalization basis
- Af95 threshold

#### 结果覆写
- As
- Af
- Af95
- reason

本轮全部：
- disabled
- read-only
- coming soon

---

## 四、交互规则

### 页面加载后
继续读取：
- summary
- detail
- active selection

并把这些内容映射到 Adjustment Preview。

### 关键帧 / 点切换时
同步刷新：
- Automatic Basis
- Extraction & Analysis Context

### Future Adjustment Controls
始终为只读，不可编辑。

---

## 五、视觉要求
继续沿用当前工业深色风格：
- 深色背景
- 卡片式分区
- 结果信息高亮
- Adjustment Preview 与现有曲线区风格一致
- 禁用项用柔和灰态表达，不要太抢眼

---

## 六、本轮不做的事
- 真正手动调整
- 参数提交
- 调整记录
- 手动结果与自动结果并排对比
- 保存 adjustment 版本
- 新增后端可编辑接口

---

## 七、验收标准
用户进入 workspace 后，应能看懂：
1. 当前自动结果依据了哪些信息
2. 当前选中点/帧的上下文是什么
3. 将来哪些地方会允许调整
4. 但当前版本仍然不会让用户误以为已经可以修改
