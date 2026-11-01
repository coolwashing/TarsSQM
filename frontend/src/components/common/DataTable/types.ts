export interface TableColumnFilter {
  text: string
  value: string | number | boolean
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
  dataType?: 'text' | 'date' | 'datetime' | 'number' // 自动格式化数据类型
  editable?: boolean // 是否支持双击单元格行内快编
  editType?: 'input' | 'select' | 'number' // 编辑器类型
  editOptions?: { label: string; value: any }[] // 下拉选择器配置项
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
