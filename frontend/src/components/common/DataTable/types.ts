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
  visible?: boolean
  slotName?: string
}

export interface TablePagination {
  page: number
  pageSize: number
  total: number
  pageSizes?: number[]
}
