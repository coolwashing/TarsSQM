export interface TableColumnFilter {
  text: string
  value: string | number | boolean
}

export interface TableOptionItem {
  label: string
  value: any
  color?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | string // 标签语义色彩
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
  resizable?: boolean
  showOverflowTooltip?: boolean
  filters?: TableColumnFilter[]
  filterMethod?: (value: any, row: any, column: any) => boolean
  autoFilter?: boolean // 智能自动表头筛选 (根据当前数据自动去重提取枚举)
  visible?: boolean
  slotName?: string
  dataType?: 'text' | 'code' | 'badge' | 'date' | 'datetime' | 'number' // 自动格式化数据类型

  // ========== 飞书多维表格行内编辑拓展 ==========
  editable?: boolean // 是否支持单元格行内快编
  editType?: 'input' | 'number' | 'select' | 'multi-select' | 'date' // 编辑器类型
  dateFormat?: string // 日期时间显示格式：'YYYY-MM-DD' | 'YYYY-MM-DD HH:mm:ss' | 'YYYY-MM-DD HH:mm' | 'MM-DD' | 'relative'
  options?: (TableOptionItem | string)[] // 静态枚举选项
  editOptions?: (TableOptionItem | string)[] // 兼容别名
  dictKey?: string // 关联动态字典标识（如 SUPPLIER_TIER）
  allowCreate?: boolean // 是否允许在下拉菜单中就地创建新选项（飞书多维表格精髓）
  colorMap?: Record<string, string> // 选项值与语义色彩映射
  quickAddDisabled?: boolean // 在行底快速加行时该列是否禁用/只读
}

export interface QuickAddEvent {
  row: Record<string, any>
  done: () => void
}

export interface TablePagination {
  page: number
  pageSize: number
  total: number
  pageSizes?: number[]
}

export interface CellChangeEvent {
  row: any
  prop: string
  value: any
  oldValue: any
}

export interface BatchCellChangeItem {
  row: any
  prop: string
  value: any
  oldValue: any
}

export interface BatchCellChangeEvent {
  prop: string
  value: any
  items: BatchCellChangeItem[]
}

export interface ActiveCellCoordinate {
  rowKey: string | number
  prop: string
}

export interface HistoryCommandItem {
  row: any
  prop: string
  oldValue: any
  newValue: any
}

export interface HistoryCommand {
  type: 'cell-edit' | 'batch-fill'
  label: string
  items: HistoryCommandItem[]
}
