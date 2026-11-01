<template>
  <div class="common-data-table-container">
    <!-- 顶部检索与操作区 -->
    <div v-if="$slots.search || $slots.toolbar" class="table-search-area">
      <el-card shadow="never" class="search-card">
        <div class="search-card-layout">
          <!-- 左侧：检索条件插槽 -->
          <div v-if="$slots.search" class="search-form-side">
            <slot name="search" />
          </div>

          <!-- 右侧：业务操作与表格辅助工具 (如 批量导入、新建、刷新、列设置等) -->
          <div class="toolbar-right">
            <!-- 批量导入与模板工具 (当配置 importKey 时自动激活) -->
            <el-button-group v-if="importKey" class="import-button-group">
              <el-button
                type="success"
                plain
                :icon="Upload"
                class="import-main-btn"
                @click="importDialogVisible = true"
              >
                批量导入
              </el-button>
              <el-tooltip content="下载该表的 Excel 标准填报模板" placement="top" :show-after="500">
                <el-button
                  type="success"
                  plain
                  :icon="Download"
                  class="template-quick-btn"
                  :loading="downloadingTemplate"
                  @click="handleDirectDownloadTemplate"
                />
              </el-tooltip>
            </el-button-group>

            <!-- 业务操作按钮插槽 (如 新建供应商) -->
            <slot name="toolbar" />

            <!-- 刷新按钮 -->
            <el-tooltip content="刷新数据" placement="top" :show-after="500">
              <el-button
                circle
                :icon="Refresh"
                class="tool-btn"
                @click="$emit('refresh')"
              />
            </el-tooltip>

            <!-- 列设置浮层 (显隐与列排序) -->
            <el-popover
              placement="bottom-end"
              :width="260"
              trigger="click"
              popper-class="column-settings-popover"
            >
              <template #reference>
                <el-button circle :icon="Operation" class="tool-btn" title="列显示与排序设置" />
              </template>

              <div class="column-settings-box">
                <div class="settings-head">
                  <span class="settings-title">列显示与顺序</span>
                  <el-button link type="primary" size="small" @click="resetColumnSettings">
                    恢复默认
                  </el-button>
                </div>

                <div class="column-list">
                  <div
                    v-for="(col, index) in managedColumns"
                    :key="col.prop"
                    class="column-setting-item"
                  >
                    <el-checkbox v-model="col.visible" size="small">
                      <span class="col-name" :title="col.label">{{ col.label }}</span>
                    </el-checkbox>
                    <div class="order-arrows">
                      <el-button
                        link
                        size="small"
                        :disabled="index === 0"
                        :icon="Top"
                        @click="moveColumn(index, -1)"
                      />
                      <el-button
                        link
                        size="small"
                        :disabled="index === managedColumns.length - 1"
                        :icon="Bottom"
                        @click="moveColumn(index, 1)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </el-popover>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 表格主卡片区 (自适应撑满剩余高度) -->
    <el-card shadow="never" class="table-main-card">
      <!-- 仅在提供了自定义表格标题插槽时才渲染上方栏目，不再显示多余的统计徽章 -->
      <div v-if="$slots['table-title']" class="table-header-toolbar">
        <slot name="table-title" />
      </div>

      <!-- 表格核心区 (100% 撑满 + 内部虚拟滚动) -->
      <div class="table-body-wrapper">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="data"
          height="100%"
          border
          stripe
          class="custom-fit-table"
          @sort-change="handleSortChange"
          @header-dragend="handleHeaderDragend"
        >
          <!-- 动态数据列 -->
          <template v-for="col in visibleColumns" :key="col.prop">
            <el-table-column
              :prop="col.prop"
              :label="col.label"
              :width="col.width"
              :min-width="col.minWidth || 120"
              :align="col.align || 'left'"
              :fixed="col.fixed"
              :sortable="col.sortable ?? true"
              :resizable="col.resizable ?? true"
              :show-overflow-tooltip="col.showOverflowTooltip ?? true"
              :tooltip-options="defaultTooltipOptions"
              :filters="getColumnFilters(col)"
              :filter-method="col.filterMethod || (getColumnFilters(col) ? defaultFilterMethod(col.prop) : undefined)"
            >
              <template #default="scope">
                <slot :name="col.slotName || col.prop" v-bind="scope">
                  <!-- 行内编辑态 -->
                  <div
                    v-if="col.editable && isCellEditing(scope.row, col.prop)"
                    class="inline-edit-wrapper"
                    @click.stop
                  >
                    <el-select
                      v-if="col.editType === 'select'"
                      v-model="editingCell!.tempValue"
                      size="small"
                      autofocus
                      class="inline-edit-control"
                      @change="saveCellEdit(scope.row, col)"
                      @blur="saveCellEdit(scope.row, col)"
                    >
                      <el-option
                        v-for="opt in col.editOptions || []"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                    <el-input-number
                      v-else-if="col.editType === 'number'"
                      v-model="editingCell!.tempValue"
                      size="small"
                      controls-position="right"
                      class="inline-edit-control"
                      @keyup.enter="saveCellEdit(scope.row, col)"
                      @blur="saveCellEdit(scope.row, col)"
                    />
                    <el-input
                      v-else
                      v-model="editingCell!.tempValue"
                      size="small"
                      autofocus
                      class="inline-edit-control"
                      @keyup.enter="saveCellEdit(scope.row, col)"
                      @blur="saveCellEdit(scope.row, col)"
                    />
                  </div>

                  <!-- 默认/只读展示态 (支持双击快编) -->
                  <div
                    v-else
                    :class="['cell-content-box', { 'is-editable': col.editable }]"
                    :title="col.editable ? '双击可快速编辑' : undefined"
                    @dblclick="col.editable && startCellEdit(scope.row, col)"
                  >
                    <span>{{ formatCellValue(scope.row, col) }}</span>
                    <el-icon v-if="col.editable" class="edit-hint-icon"><Edit /></el-icon>
                  </div>
                </slot>
              </template>
            </el-table-column>
          </template>

          <!-- 操作列插槽 -->
          <el-table-column
            v-if="$slots.action"
            label="操作"
            :width="actionWidth || 140"
            :fixed="actionFixed || 'right'"
            align="center"
          >
            <template #default="scope">
              <slot name="action" v-bind="scope" />
            </template>
          </el-table-column>

          <!-- 空状态插槽 -->
          <template #empty>
            <slot name="empty">
              <el-empty :description="emptyText || '未检索到符合条件的数据记录'" />
            </slot>
          </template>
        </el-table>
      </div>

      <!-- 固定底部分页栏 -->
      <div v-if="pagination" class="table-pagination-footer">
        <span class="pagination-info">
          共 <strong>{{ pagination.total }}</strong> 条
        </span>
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="pagination.pageSizes || [10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          :total="pagination.total"
          @update:current-page="onPageChange"
          @update:page-size="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 全局通用 Excel 批量导入与多维校验模态窗 -->
    <ExcelImportDialog
      v-if="importKey"
      v-model="importDialogVisible"
      :biz-key="importKey"
      :title="importTitle"
      @success="handleImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Refresh, Operation, Top, Bottom, Upload, Download, Edit } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { TableColumn, TablePagination, CellChangeEvent } from './types'
import ExcelImportDialog from '@/components/common/ExcelImportDialog/index.vue'
import { formatDate } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    columns: TableColumn[]
    data: any[]
    loading?: boolean
    pagination?: TablePagination
    storageKey?: string
    actionWidth?: number | string
    actionFixed?: boolean | 'left' | 'right'
    emptyText?: string
    importKey?: string
    importTitle?: string
  }>(),
  {
    loading: false,
    storageKey: '',
    actionWidth: 140,
    actionFixed: 'right',
    emptyText: '未检索到符合条件的数据记录',
    importKey: '',
    importTitle: ''
  }
)

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'page-change', page: number): void
  (e: 'size-change', size: number): void
  (e: 'sort-change', payload: { column: any; prop: string; order: string | null }): void
  (e: 'cell-change', payload: CellChangeEvent): void
}>()

const tableRef = ref<any>(null)

// 批量导入与模板下载状态
const importDialogVisible = ref(false)
const downloadingTemplate = ref(false)

const handleImportSuccess = () => {
  emit('refresh')
}

const handleDirectDownloadTemplate = async () => {
  if (!props.importKey) return
  downloadingTemplate.value = true
  try {
    const res = await axios.get(`/api/excel/template/${props.importKey}`, {
      responseType: 'blob'
    })
    let filename = `SQM_${props.importTitle || '数据'}_导入模板.xlsx`
    const disposition = res.headers['content-disposition']
    if (disposition && disposition.includes("filename*=UTF-8''")) {
      const parts = disposition.split("filename*=UTF-8''")
      if (parts[1]) filename = decodeURIComponent(parts[1])
    }
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载就绪')
  } catch (err: any) {
    ElMessage.error(`下载模板失败: ${err.message || '网络连接异常'}`)
  } finally {
    downloadingTemplate.value = false
  }
}

// 管理列状态（支持显隐、拖拽宽度与自定义顺序）
const managedColumns = ref<TableColumn[]>([])

const initColumns = () => {
  // 从 localStorage 恢复自定义配置
  if (props.storageKey) {
    try {
      const saved = localStorage.getItem(`sqm_table_cols_${props.storageKey}`)
      if (saved) {
        const parsed: { prop: string; visible: boolean; width?: number | string }[] = JSON.parse(saved)
        // 按照保存的顺序重排，并注入新的属性
        const colMap = new Map(props.columns.map(c => [c.prop, c]))
        const ordered: TableColumn[] = []
        parsed.forEach(p => {
          const original = colMap.get(p.prop)
          if (original) {
            ordered.push({
              ...original,
              visible: p.visible ?? true,
              width: p.width || original.width
            })
            colMap.delete(p.prop)
          }
        })
        // 补充新加但未被存储的列
        colMap.forEach(col => {
          ordered.push({ ...col, visible: col.visible ?? true })
        })
        managedColumns.value = ordered
        return
      }
    } catch {
      // 容错降级
    }
  }

  // 默认从 props 继承
  managedColumns.value = props.columns.map(c => ({
    ...c,
    visible: c.visible ?? true
  }))
}

// 可见的排序列
const visibleColumns = computed(() => {
  return managedColumns.value.filter(c => c.visible !== false)
})

// 保存列配置到 localStorage
const saveColumnSettings = () => {
  if (!props.storageKey) return
  try {
    const serialized = managedColumns.value.map(c => ({
      prop: c.prop,
      visible: c.visible,
      width: c.width
    }))
    localStorage.setItem(`sqm_table_cols_${props.storageKey}`, JSON.stringify(serialized))
  } catch {
    // 忽略
  }
}

// 移动列顺序
const moveColumn = (index: number, delta: number) => {
  const target = index + delta
  if (target < 0 || target >= managedColumns.value.length) return
  const item = managedColumns.value.splice(index, 1)[0]
  managedColumns.value.splice(target, 0, item)
  saveColumnSettings()
}

// 恢复默认列设置
const resetColumnSettings = () => {
  if (props.storageKey) {
    localStorage.removeItem(`sqm_table_cols_${props.storageKey}`)
  }
  managedColumns.value = props.columns.map(c => ({
    ...c,
    visible: c.visible ?? true
  }))
}

// 列宽拖拽结束自动持久化
const handleHeaderDragend = (newWidth: number, _oldWidth: number, column: any) => {
  const targetCol = managedColumns.value.find(c => c.prop === column.property)
  if (targetCol) {
    targetCol.width = newWidth
    saveColumnSettings()
  }
}

// 排序事件
const handleSortChange = (payload: { column: any; prop: string; order: string | null }) => {
  emit('sort-change', payload)
}

// 默认 Tooltip 延迟 0.5 秒 (500ms) 防频繁闪烁
const defaultTooltipOptions = {
  enterable: true,
  placement: 'top',
  showAfter: 500
}

// 动态获取列筛选配置 (支持 autoFilter 自动从数据中去重提取)
const getColumnFilters = (col: TableColumn) => {
  if (col.filters && col.filters.length > 0) return col.filters
  if (col.autoFilter && props.data && props.data.length > 0) {
    const rawValues = props.data.map(item => item[col.prop]).filter(v => v !== null && v !== undefined && v !== '')
    const uniqueValues = Array.from(new Set(rawValues))
    return uniqueValues.map(v => ({ text: String(v), value: v }))
  }
  return undefined
}

// 默认列过滤方法
const defaultFilterMethod = (prop: string) => {
  return (value: any, row: any) => {
    return row[prop] === value
  }
}

// 单元格数据智能格式化 (支持 date/datetime 自动转换)
const formatCellValue = (row: any, col: TableColumn) => {
  const val = row[col.prop]
  if (val === null || val === undefined || val === '') return '-'

  if (col.dataType === 'date') {
    return formatDate(val, 'YYYY-MM-DD')
  }
  if (col.dataType === 'datetime') {
    return formatDate(val, 'YYYY-MM-DD HH:mm:ss')
  }

  // 智能识别 _at / _date 字段中的 ISO 时间串
  if (typeof val === 'string' && (col.prop.endsWith('_at') || col.prop.endsWith('_date'))) {
    if (val.includes('T') || val.includes('-')) {
      return formatDate(val, 'YYYY-MM-DD')
    }
  }

  return val
}

// 行内快捷编辑状态管理
const editingCell = ref<{ rowId: any; prop: string; tempValue: any } | null>(null)

const isCellEditing = (row: any, prop: string) => {
  if (!editingCell.value) return false
  const rowKey = row.id ?? row.code
  return editingCell.value.rowId === rowKey && editingCell.value.prop === prop
}

const startCellEdit = (row: any, col: TableColumn) => {
  if (!col.editable) return
  const rowKey = row.id ?? row.code
  editingCell.value = {
    rowId: rowKey,
    prop: col.prop,
    tempValue: row[col.prop]
  }
}

const saveCellEdit = (row: any, col: TableColumn) => {
  if (!editingCell.value) return
  const oldValue = row[col.prop]
  const newValue = editingCell.value.tempValue
  if (newValue !== oldValue) {
    row[col.prop] = newValue
    emit('cell-change', {
      row,
      prop: col.prop,
      value: newValue,
      oldValue
    })
    ElMessage.success({ message: '修改已更新', duration: 1500 })
  }
  editingCell.value = null
}

// 分页变化与每页条数持久化缓存
const PAGE_SIZE_KEY = computed(() => {
  return props.storageKey ? `sqm_table_pagesize_${props.storageKey}` : `sqm_table_pagesize_default`
})

const initPageSize = () => {
  if (props.pagination) {
    const saved = localStorage.getItem(PAGE_SIZE_KEY.value)
    if (saved) {
      const size = parseInt(saved, 10)
      if (size && !isNaN(size) && size !== props.pagination.pageSize) {
        emit('size-change', size)
      }
    }
  }
}

const onPageChange = (p: number) => {
  emit('page-change', p)
}

const onPageSizeChange = (s: number) => {
  localStorage.setItem(PAGE_SIZE_KEY.value, s.toString())
  emit('size-change', s)
}

watch(
  () => props.columns,
  () => {
    initColumns()
  },
  { deep: true }
)

watch(
  managedColumns,
  () => {
    saveColumnSettings()
  },
  { deep: true }
)

onMounted(() => {
  initColumns()
  initPageSize()
})

defineExpose({
  tableRef,
  resetColumnSettings
})
</script>

<style scoped>
.common-data-table-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  box-sizing: border-box;
}

/* 顶部搜索与操作区 */
.table-search-area {
  flex-shrink: 0;
}

.search-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.search-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.search-card-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: nowrap;
}

.search-form-side {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.search-form-side :deep(.search-toolbar) {
  display: flex;
  align-items: center;
  width: auto;
}

.search-form-side :deep(.filter-inputs) {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-left: auto;
}

.tool-btn {
  color: #64748b;
  border-color: #cbd5e1;
}
.tool-btn:hover {
  color: #4f46e5;
  border-color: #c7d2fe;
}

/* 表格主卡片容器 (弹性撑满剩余视窗高度) */
.table-main-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.table-main-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow: hidden;
}

/* 表格可选标题栏 */
.table-header-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

/* 表格主体容器 */
.table-body-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.custom-fit-table {
  width: 100%;
  border-radius: 6px;
}

/* 确保单元格长文本不换行、显示省略号 */
.custom-fit-table :deep(.el-table__cell) {
  white-space: nowrap;
}

.custom-fit-table :deep(.cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 12px;
}

/* 表头美化 */
.custom-fit-table :deep(th.el-table__cell) {
  background-color: #f8fafc;
  color: #334155;
  font-weight: 600;
  font-size: 13px;
  height: 44px;
}

/* 底部分页栏 (固定在底部) */
.table-pagination-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
}
.pagination-info strong {
  color: #334155;
}

/* 列设置 Popover */
.column-settings-box {
  padding: 4px;
}

.settings-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 8px;
}

.settings-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
}

.column-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.column-setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px;
  border-radius: 4px;
}
.column-setting-item:hover {
  background-color: #f8fafc;
}

.col-name {
  font-size: 12px;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
}

.order-arrows {
  display: flex;
  align-items: center;
}

.import-button-group {
  margin-right: 2px;
}

/* 单元格行内编辑与高亮微交互 */
.cell-content-box {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 24px;
  width: 100%;
}

.cell-content-box.is-editable {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.15s ease-in-out;
}

.cell-content-box.is-editable:hover {
  background-color: #f1f5f9;
  color: #0284c7;
}

.edit-hint-icon {
  font-size: 12px;
  color: #94a3b8;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.cell-content-box.is-editable:hover .edit-hint-icon {
  opacity: 1;
}

.inline-edit-wrapper {
  width: 100%;
}

.inline-edit-control {
  width: 100% !important;
}

:deep(.el-empty__description) {
  white-space: nowrap !important;
}
:deep(.el-empty__description p) {
  white-space: nowrap !important;
  font-size: 13px;
  color: #64748b;
}
</style>
