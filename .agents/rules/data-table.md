# Tars 工业级多维数据表格（DataTable）设计与交互规约

本规范为 SQM 系统的统一表格交互标准，融合“飞书多维表格 / Notion Database”的高效数据流转心智，确保全系统所有业务表格（供应商、零件、项目、CTQ、质量问题、协同任务）拥有**高度一致、无缝就地快编、零冗余弹窗**的现代化操作体验。

---

## 一、 核心设计理念

1. **就地可触达（Direct Manipulation）**：
   - 常见属性（如准入状态、负责人、配合度、城市、联系电话）直接在单元格内完成查阅与修改，严禁迫使用户为了修改一个状态而打开冗长复杂的模态弹窗。
2. **纯配置驱动（Config-Driven UI）**：
   - 统一由 `columns: TableColumn[]` 声明列属性与控件类型，严禁在业务视图组件中书写大量重复的 `<template #status>` 标签样板代码。
3. **沉浸式键盘流（Keyboard-First Experience）**：
   - 完整支持飞书多维表格的键盘习惯：单击选中（蓝框）、Enter 开启/提交、Tab 跳格、方向键移格、Esc 撤回。
4. **低摩擦字典扩展（Zero-Friction Taxonomy）**：
   - 允许用户在单元格下拉中直接检索；若不存在，支持 `allowCreate: true` 一键就地创建新标签，无需跳出页面。

---

## 二、 列定义 Schema 统一规范 (`TableColumn`)

所有业务表格在声明列时，统一遵循以下字段规范：

```typescript
export interface TableOptionItem {
  label: string
  value: any
  color?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | string // 语义色徽标
  description?: string
}

export interface TableColumn {
  prop: string
  label: string
  width?: number | string
  minWidth?: number | string
  align?: 'left' | 'center' | 'right'
  fixed?: boolean | 'left' | 'right'
  sortable?: boolean | 'custom'

  // ========== 多维表格与编辑控制 ==========
  editable?: boolean                                    // 是否开启就地快编（默认 false）
  editType?: 'input' | 'number' | 'select' | 'multi-select' | 'date' // 控件类型（默认 input）
  dictKey?: string                                      // 关联动态字典标识（如 SUPPLIER_TIER）
  options?: TableOptionItem[]                           // 静态选项列表（与 dictKey 互为备用/兜底）
  allowCreate?: boolean                                 // 是否支持就地输入新建选项（飞书风格）
  colorMap?: Record<string, string>                     // 选项值与语义色彩映射表
  dataType?: 'text' | 'date' | 'datetime' | 'number'    // 数据展示格式化
}
```

---

## 三、 单元格交互与视觉规范

### 1. 单元格三态模型
- **展示态（Idle）**：
  - 纯文本或彩色胶囊展示，悬停时右侧隐式显示浅灰微型编辑图标（✎），提示用户可直接编辑。
- **聚焦态（Focused）**：
  - 单击单元格时激活，呈现 **2px 飞书品牌蓝（#2563eb）高亮外框**，此时单元格捕获键盘事件。
- **编辑态（Editing）**：
  - 呈现轻量级输入框或无缝 Popover 气泡菜单，光标自动对焦。

### 2. 键盘事件流转规约
- `Enter`（回车键）：
  - 聚焦态下：开启编辑态；
  - 编辑态下：保存修改并自动将焦点下移至同列下一行单元格。
- `Tab` / `Shift + Tab`：
  - 保存当前修改，并将焦点横向移动至右侧/左侧下一个可编辑单元格；行尾自动折行。
- `Escape`（退出键）：
  - 放弃当前未保存的修改，退出编辑态并保留焦点。
- `Arrow Keys`（↑ ↓ ← →）：
  - 在聚焦态下快速在网格之间移动选框。

### 3. 彩色状态胶囊（Tag）与下拉气泡
- **单选（`editType: 'select'`）**：
  - 单击直接呼出下浮极简气泡，包含选项圆点、选项名；点击任一项后即刻变色更新并关闭气泡。
- **多选（`editType: 'multi-select'`）**：
  - 单元格内以紧凑微型胶囊组排列（如：`IATF16949` `ISO9001`），单击弹出复选勾选浮层；支持全选与模糊搜索。
- **就地新增（`allowCreate: true`）**：
  - 下拉气泡内置搜索条，若输入词不存在，列表底部弹出 `➕ 创建新选项 "{keyword}"`；点击后自动分配协调色并触发保存。

---

## 四、 持久化与反馈规范

1. **静默防抖持久化**：
   - 单元格失焦或确认时，统一派发 `@cell-change` 事件：
     ```typescript
     emit('cell-change', { row, prop, value, oldValue })
     ```
   - 页面调用后端 `PUT` 局部更新接口（如 `PUT /api/maindata/suppliers/{id}`），不刷新整表。
2. **轻量反馈指示器**：
   - 保存中：单元格右上角闪烁蓝色脉冲微点；
   - 保存成功：微点闪过绿色已生效动画（2秒后隐去），**严禁频繁弹出全局黑色/彩色的大吐司弹窗遮挡视线**；
   - 保存失败：恢复旧值（`oldValue`），并通过 `ElMessage.error` 提示失败原因。

---

## 五、 行底快速加行连续录入规范

在业务数据表底端，统一集成飞书多维表格风格的行底录入带：
1. 表格最后一行常驻 `+ 添加新记录` 条目；
2. 点击或按 Enter 激活行内紧凑录入行，各个输入框对齐对应列；
3. 回车即刻提交并生成下一行，光标自动落在新一行的首个必填字段，支持无需鼠标的极速连续批量记账。
