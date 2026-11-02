<template>
  <div class="common-data-table-container">
    <!-- 统一综合顶栏 (将【信标1】操作区 与 【信标2】检索区 融合在同一紧凑卡片内) -->
    <div v-if="$slots.toolbar || $slots.search || importKey" class="table-unified-header-bar">
      <!-- 左侧区域：业务操作动作 (如“新建供应商”) + 业务搜索过滤项 -->
      <div class="header-bar-left">
        <div v-if="$slots.toolbar" class="toolbar-primary-slot">
          <slot name="toolbar" />
        </div>
        <div v-if="$slots.search" class="toolbar-search-slot">
          <slot name="search" />
        </div>
      </div>

      <!-- 右侧区域：系统级通用工具 (下载模板 / 批量导入 / 刷新 / 列设置) -->
      <div class="header-bar-right">
        <!-- 批量导入与 AI 录入入口 (简洁短标签 + 0.5s tooltip) -->
        <div v-if="importKey" class="import-button-group">
          <el-tooltip content="下载标准 Excel 导入模板" placement="top" :show-after="500">
            <el-button
              circle
              size="small"
              :icon="Download"
              :loading="downloadingTemplate"
              class="tool-btn"
              @click="handleDownloadTemplate"
            />
          </el-tooltip>
          <el-tooltip content="批量导入标准 Excel 数据" placement="top" :show-after="500">
            <el-button
              type="primary"
              size="small"
              :icon="Upload"
              class="tool-btn"
              @click="importDialogVisible = true"
            >
              导入
            </el-button>
          </el-tooltip>
          <el-tooltip content="通过图片截图、文本、表格进行 AI 提取批量录入" placement="top" :show-after="500">
            <el-button
              type="primary"
              plain
              size="small"
              :icon="MagicStick"
              class="tool-btn ai-smart-btn"
              @click="aiImportDialogVisible = true"
            >
              AI 录入
            </el-button>
          </el-tooltip>
        </div>

        <!-- 撤销与重做操作入口 (支持快捷键 Ctrl+Z / Ctrl+Y) -->
        <el-tooltip
          :content="`撤销 (Ctrl+Z)${undoStack.length > 0 ? ` [${undoStack.length}]` : ''}`"
          placement="top"
          :show-after="500"
        >
          <el-button
            circle
            size="small"
            :icon="RefreshLeft"
            :disabled="undoStack.length === 0"
            class="tool-btn"
            @click="undo"
          />
        </el-tooltip>
        <el-tooltip
          :content="`重做 (Ctrl+Y)${redoStack.length > 0 ? ` [${redoStack.length}]` : ''}`"
          placement="top"
          :show-after="500"
        >
          <el-button
            circle
            size="small"
            :icon="RefreshRight"
            :disabled="redoStack.length === 0"
            class="tool-btn"
            @click="redo"
          />
        </el-tooltip>

        <el-tooltip content="刷新数据" placement="top" :show-after="500">
          <el-button
            circle
            size="small"
            :icon="Refresh"
            class="tool-btn"
            @click="onRefresh"
          />
        </el-tooltip>

        <!-- 列设置浮层 (列显隐与上下排布顺序) -->
        <el-popover
          placement="bottom-end"
          :width="220"
          trigger="click"
        >
          <template #reference>
            <el-button
              circle
              size="small"
              :icon="Operation"
              class="tool-btn"
              title="自定义列显示与顺序"
            />
          </template>
          <div class="column-settings-box">
            <div class="settings-head">
              <span class="settings-title">列展示与顺序</span>
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
                <el-checkbox v-model="col.visible" size="small" @change="saveColumnSettings">
                  <span class="col-name" :title="col.label">{{ col.label }}</span>
                </el-checkbox>
                <div class="order-arrows">
                  <el-button
                    link
                    size="small"
                    :icon="Top"
                    :disabled="index === 0"
                    @click="moveColumn(index, -1)"
                  />
                  <el-button
                    link
                    size="small"
                    :icon="Bottom"
                    :disabled="index === managedColumns.length - 1"
                    @click="moveColumn(index, 1)"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <!-- 表格核心主工作区 (撑满剩余高度、紧凑优雅) -->
    <div class="table-main-card">
      <div class="table-body-wrapper">
        <el-table
          ref="tableRef"
          v-loading="loading"
          :data="data"
          height="100%"
          border
          stripe
          class="custom-fit-table"
          :tooltip-options="defaultTooltipOptions"
          @sort-change="handleSortChange"
          @header-dragend="handleHeaderDragend"
          @selection-change="handleSelectionChange"
        >
          <!-- 紧凑多选列 -->
          <el-table-column
            v-if="showSelection"
            type="selection"
            width="40"
            align="center"
            fixed="left"
          />

          <!-- 紧凑序号列 (带分页跨页累计) -->
          <el-table-column
            v-if="showIndex"
            type="index"
            label="#"
            width="48"
            align="center"
            fixed="left"
            :index="calcRowIndex"
          />

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
              <!-- 表头插槽：列名 + 悬停微型齿轮快捷配置字段属性与格式 (信标 7) -->
              <template #header>
                <div class="feishu-header-cell">
                  <span class="feishu-header-title">{{ col.label }}</span>
                  <el-tooltip content="⚙️ 配置字段属性与时间格式" placement="top" :show-after="500">
                    <el-icon
                      v-if="col.editable || isDateColumn(col)"
                      class="feishu-header-config-btn"
                      @click.stop.prevent="openColumnConfig(col)"
                      @mousedown.stop
                    >
                      <Setting />
                    </el-icon>
                  </el-tooltip>
                </div>
              </template>

              <template #default="scope">
                <!-- 1. 若外部父组件明确提供了对应插槽，则优先由外部插槽渲染 -->
                <slot v-if="$slots[col.slotName || col.prop]" :name="col.slotName || col.prop" v-bind="scope" />

                <!-- 2. 飞书多维表格风格行内可编辑单元格引擎 -->
                <template v-else-if="col.editable">
                  <!-- A. 单选彩色胶囊选择器 (editType === 'select') -->
                  <div
                    v-if="col.editType === 'select'"
                    class="feishu-cell-container is-select"
                    :class="{
                      'is-focused': isCellFocused(scope.row, col.prop),
                      'is-autofill-range': isInAutofillRange(scope.$index, col.prop)
                    }"
                    :data-row-idx="scope.$index"
                    @click.stop="focusCell(scope.row, col)"
                  >
                    <el-popover
                      :visible="activeSelectPopoverKey === getCellKey(scope.row, col.prop)"
                      :width="230"
                      placement="bottom-start"
                      :offset="4"
                      popper-class="feishu-select-popper"
                      :show-after="0"
                      :hide-after="0"
                      @show="onSelectPopoverShow(scope.row, col)"
                    >
                      <template #reference>
                        <div
                          class="feishu-pill-display"
                          tabindex="0"
                          @click.stop="toggleSelectPopover(scope.row, col)"
                          @keydown="handleCellKeydown($event, scope.row, col, scope.$index)"
                        >
                          <el-tag
                            v-if="scope.row[col.prop]"
                            :type="getTagColor(scope.row[col.prop], col)"
                            size="small"
                            effect="light"
                            class="feishu-status-pill"
                          >
                            {{ getOptionLabel(scope.row[col.prop], col) }}
                          </el-tag>
                          <span v-else class="feishu-placeholder-text">选择...</span>
                          <span
                            v-if="cellFeedbackMap[`${scope.row.id ?? scope.row.code}_${col.prop}`]"
                            class="cell-status-dot saved"
                            title="已自动保存"
                          />
                        </div>
                      </template>

                      <!-- 飞书风格下拉面板 (含搜索与就地 allowCreate 新建选项) -->
                      <div class="feishu-popover-box" @click.stop>
                        <el-input
                          v-if="getColumnOptions(col).length > 4 || col.allowCreate"
                          v-model="popoverSearchMap[col.prop]"
                          placeholder="搜索或输入新选项..."
                          size="small"
                          clearable
                          :prefix-icon="Search"
                          class="feishu-popover-search"
                          @keyup.enter="handleEnterCreateOption(scope.row, col)"
                        />
                        <div class="feishu-options-list">
                          <div
                            v-for="opt in getFilteredOptions(col)"
                            :key="opt.value"
                            class="feishu-opt-item"
                            :class="{ active: scope.row[col.prop] === opt.value }"
                            @click="selectOptionAndSave(scope.row, col, opt.value)"
                          >
                            <span class="opt-color-dot" :class="`is-${opt.color || getTagColor(opt.value, col)}`"></span>
                            <span class="opt-label">{{ opt.label }}</span>
                            <el-icon v-if="scope.row[col.prop] === opt.value" class="opt-check-icon"><Check /></el-icon>
                          </div>
                          <div v-if="getFilteredOptions(col).length === 0 && !col.allowCreate" class="feishu-no-opt">
                            无匹配选项
                          </div>

                          <!-- 飞书精髓：就地创建新选项 -->
                          <div
                            v-if="col.allowCreate && getPopoverSearch(col.prop).trim() && !hasExactMatch(col, getPopoverSearch(col.prop).trim())"
                            class="feishu-create-btn"
                            @click="createOptionAndSelect(scope.row, col, getPopoverSearch(col.prop).trim())"
                          >
                            <el-icon class="mr-1"><Plus /></el-icon>
                            <span>创建选项 <strong>"{{ getPopoverSearch(col.prop).trim() }}"</strong></span>
                          </div>
                        </div>
                      </div>
                    </el-popover>

                    <!-- 需求 6：单元格右下角拖拽复制填充手柄 (信标 2：鼠标触达或拖拽时收起弹窗) -->
                    <div
                      v-if="isCellFocused(scope.row, col.prop) && !isCellEditing(scope.row, col.prop)"
                      class="feishu-autofill-handle"
                      title="拖拽复制填充（支持向上或向下）"
                      @mouseenter="onHandleHover"
                      @mousedown.stop.prevent="startAutofillDrag($event, scope.row, col, scope.$index)"
                      @click.stop.prevent
                    />
                  </div>

                  <!-- B. 多选彩色胶囊标签组 (editType === 'multi-select') -->
                  <div
                    v-else-if="col.editType === 'multi-select'"
                    class="feishu-cell-container is-multi"
                    :class="{
                      'is-focused': isCellFocused(scope.row, col.prop),
                      'is-autofill-range': isInAutofillRange(scope.$index, col.prop)
                    }"
                    :data-row-idx="scope.$index"
                    @click.stop="focusCell(scope.row, col)"
                  >
                    <el-popover
                      :visible="activeSelectPopoverKey === getCellKey(scope.row, col.prop)"
                      :width="260"
                      placement="bottom-start"
                      :offset="4"
                      popper-class="feishu-select-popper"
                      :show-after="0"
                      :hide-after="0"
                    >
                      <template #reference>
                        <div
                          class="feishu-pill-display multi"
                          tabindex="0"
                          @click.stop="toggleSelectPopover(scope.row, col)"
                          @keydown="handleCellKeydown($event, scope.row, col, scope.$index)"
                        >
                          <template v-if="getMultiValues(scope.row[col.prop]).length > 0">
                            <el-tag
                              v-for="val in getMultiValues(scope.row[col.prop])"
                              :key="val"
                              :type="getTagColor(val, col)"
                              size="small"
                              effect="light"
                              class="feishu-status-pill multi-item"
                            >
                              {{ val }}
                            </el-tag>
                          </template>
                          <span v-else class="feishu-placeholder-text">多选...</span>
                          <span
                            v-if="cellFeedbackMap[`${scope.row.id ?? scope.row.code}_${col.prop}`]"
                            class="cell-status-dot saved"
                            title="已自动保存"
                          />
                        </div>
                      </template>

                      <!-- 飞书风格多选面板 -->
                      <div class="feishu-popover-box" @click.stop>
                        <el-input
                          v-model="popoverSearchMap[col.prop]"
                          placeholder="搜索或输入新增标签..."
                          size="small"
                          clearable
                          :prefix-icon="Search"
                          class="feishu-popover-search"
                          @keyup.enter="handleEnterCreateMultiOption(scope.row, col)"
                        />
                        <div class="feishu-options-list">
                          <div
                            v-for="opt in getFilteredOptions(col)"
                            :key="opt.value"
                            class="feishu-opt-item"
                            :class="{ active: isMultiSelected(scope.row[col.prop], opt.value) }"
                            @click="toggleMultiOption(scope.row, col, opt.value)"
                          >
                            <el-checkbox
                              :model-value="isMultiSelected(scope.row[col.prop], opt.value)"
                              @click.prevent
                              class="opt-checkbox"
                            />
                            <span class="opt-label">{{ opt.label }}</span>
                          </div>

                          <!-- 飞书就地新增多选标签 -->
                          <div
                            v-if="col.allowCreate && getPopoverSearch(col.prop).trim() && !hasExactMatch(col, getPopoverSearch(col.prop).trim())"
                            class="feishu-create-btn"
                            @click="createMultiOptionAndSelect(scope.row, col, getPopoverSearch(col.prop).trim())"
                          >
                            <el-icon class="mr-1"><Plus /></el-icon>
                            <span>创建并选择 <strong>"{{ getPopoverSearch(col.prop).trim() }}"</strong></span>
                          </div>
                        </div>
                      </div>
                    </el-popover>

                    <!-- 需求 6：单元格右下角拖拽复制填充手柄 -->
                    <div
                      v-if="isCellFocused(scope.row, col.prop) && !isCellEditing(scope.row, col.prop)"
                      class="feishu-autofill-handle"
                      title="拖拽复制填充（支持向上或向下）"
                      @mouseenter="onHandleHover"
                      @mousedown.stop.prevent="startAutofillDrag($event, scope.row, col, scope.$index)"
                      @click.stop.prevent
                    />
                  </div>

                  <!-- C. 文本 / 数值行内直接编辑 (单击聚焦蓝框、回车/双击就地打字、Tab 跳转) -->
                  <div
                    v-else
                    class="feishu-cell-container is-text"
                    :class="{
                      'is-focused': isCellFocused(scope.row, col.prop),
                      'is-editing': isCellEditing(scope.row, col.prop),
                      'is-autofill-range': isInAutofillRange(scope.$index, col.prop)
                    }"
                    :data-row-idx="scope.$index"
                    tabindex="0"
                    @click="focusCell(scope.row, col)"
                    @dblclick="startCellEdit(scope.row, col)"
                    @keydown="handleCellKeydown($event, scope.row, col, scope.$index)"
                  >
                    <!-- 编辑态控件 -->
                    <div v-if="isCellEditing(scope.row, col.prop)" class="feishu-input-wrap" @click.stop>
                      <el-input-number
                        v-if="col.editType === 'number'"
                        ref="cellInputRef"
                        v-model="editingCell!.tempValue"
                        size="small"
                        controls-position="right"
                        class="feishu-edit-input"
                        autofocus
                        @keyup.enter="saveCellEdit(scope.row, col, scope.$index)"
                        @blur="saveCellEdit(scope.row, col)"
                      />
                      <el-input
                        v-else
                        ref="cellInputRef"
                        v-model="editingCell!.tempValue"
                        size="small"
                        class="feishu-edit-input"
                        autofocus
                        @keyup.enter="saveCellEdit(scope.row, col, scope.$index)"
                        @blur="saveCellEdit(scope.row, col)"
                      />
                    </div>

                    <!-- 展示态 -->
                    <div v-else class="feishu-text-display">
                      <span class="cell-text-val">{{ formatCellValue(scope.row, col) }}</span>
                      <el-icon class="cell-hover-edit-icon"><Edit /></el-icon>
                      <span
                        v-if="cellFeedbackMap[`${scope.row.id ?? scope.row.code}_${col.prop}`]"
                        class="cell-status-dot saved"
                        title="已自动保存"
                      />
                    </div>

                    <!-- 需求 6：单元格右下角拖拽复制填充手柄 -->
                    <div
                      v-if="isCellFocused(scope.row, col.prop) && !isCellEditing(scope.row, col.prop)"
                      class="feishu-autofill-handle"
                      title="拖拽复制填充（支持向上或向下）"
                      @mouseenter="onHandleHover"
                      @mousedown.stop.prevent="startAutofillDrag($event, scope.row, col, scope.$index)"
                      @click.stop.prevent
                    />
                  </div>
                </template>

                <!-- 3. 普通非编辑列展示态 (支持日期时间0.5s悬浮与格式化) -->
                <template v-else>
                  <el-tooltip
                    v-if="isDateColumn(col) && hasValidDate(scope.row[col.prop])"
                    :content="`完整时间: ${formatFullDateTime(scope.row[col.prop])}`"
                    placement="top"
                    :show-after="500"
                  >
                    <span class="cell-plain-text date-cell-text">{{ formatCellValue(scope.row, col) }}</span>
                  </el-tooltip>
                  <span v-else class="cell-plain-text">{{ formatCellValue(scope.row, col) }}</span>
                </template>
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

          <!-- 表格底部追加行插槽 (如飞书多维表格行底快速加行) -->
          <template v-if="$slots.append" #append>
            <slot name="append" />
          </template>
        </el-table>
      </div>

      <!-- 固定底部分页栏 (支持左侧指标胶囊插槽 footer-left 与右侧扩展 footer-right) -->
      <div v-if="pagination" class="table-pagination-footer">
        <div class="pagination-footer-left">
          <span class="pagination-info">
            共 <strong>{{ pagination.total }}</strong> 条
          </span>
          <slot name="footer-left" />
        </div>
        <div class="pagination-footer-right">
          <slot name="footer-right" />
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
      </div>
    </div>

    <!-- 全局通用 Excel 批量导入与多维校验模态窗 -->
    <ExcelImportDialog
      v-if="importKey"
      v-model="importDialogVisible"
      :biz-key="importKey"
      :title="importTitle"
      @success="handleImportSuccess"
    />

    <!-- 全局通用 AI 智能识别与批量录入模态窗 -->
    <AiSmartImportDialog
      v-if="importKey"
      v-model="aiImportDialogVisible"
      :biz-key="importKey"
      :title="importTitle"
      :columns="columns"
      :unique-key="uniqueKey"
      @success="handleImportSuccess"
    />

    <!-- 表头字段属性可视化配置模态窗 (需求 7) -->
    <ColumnConfigDialog
      v-model="configDialogVisible"
      :column="selectedColForConfig"
      @save="handleColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Refresh, Operation, Top, Bottom, Upload, Download, Edit, Search, Check, Plus, Setting, MagicStick, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { TableColumn, TablePagination, CellChangeEvent, BatchCellChangeEvent, TableOptionItem, HistoryCommand } from './types'
import ExcelImportDialog from '@/components/common/ExcelImportDialog/index.vue'
import AiSmartImportDialog from '@/components/common/AiSmartImportDialog/index.vue'
import ColumnConfigDialog from './components/ColumnConfigDialog.vue'
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
    uniqueKey?: string
    showSelection?: boolean
    showIndex?: boolean
  }>(),
  {
    loading: false,
    storageKey: '',
    actionWidth: 140,
    actionFixed: 'right',
    emptyText: '未检索到符合条件的数据记录',
    importKey: '',
    importTitle: '',
    uniqueKey: '',
    showSelection: true,
    showIndex: true
  }
)

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'page-change', page: number): void
  (e: 'size-change', size: number): void
  (e: 'sort-change', payload: { column: any; prop: string; order: string | null }): void
  (e: 'cell-change', payload: CellChangeEvent): void
  (e: 'batch-cell-change', payload: BatchCellChangeEvent): void
  (e: 'selection-change', selection: any[]): void
}>()

const tableRef = ref<any>(null)
const cellInputRef = ref<any>(null)

// 序号列计算跨页索引
const calcRowIndex = (index: number) => {
  if (props.pagination && props.pagination.page && props.pagination.pageSize) {
    return (props.pagination.page - 1) * props.pagination.pageSize + index + 1
  }
  return index + 1
}

const handleSelectionChange = (selection: any[]) => {
  emit('selection-change', selection)
}

// ========================================================
// 飞书多维表格风格：撤销 (Ctrl+Z) 与重做 (Ctrl+Y) 历史命令栈
// ========================================================
const undoStack = ref<HistoryCommand[]>([])
const redoStack = ref<HistoryCommand[]>([])
const MAX_HISTORY_STEPS = 50

const recordHistory = (cmd: HistoryCommand) => {
  undoStack.value.push(cmd)
  if (undoStack.value.length > MAX_HISTORY_STEPS) {
    undoStack.value.shift()
  }
  redoStack.value = [] // 发生新编辑动作时清空重做栈
}

const undo = () => {
  if (undoStack.value.length === 0) return
  const cmd = undoStack.value.pop()!

  // 将每一个变更项回滚为 oldValue
  cmd.items.forEach(item => {
    item.row[item.prop] = item.oldValue
    emit('cell-change', {
      row: item.row,
      prop: item.prop,
      value: item.oldValue,
      oldValue: item.newValue
    })
    const rowKey = item.row.id ?? item.row.code
    const key = `${rowKey}_${item.prop}`
    cellFeedbackMap.value[key] = 'saved'
  })

  redoStack.value.push(cmd)
  ElMessage.info(`已撤销: ${cmd.label}`)

  setTimeout(() => {
    cmd.items.forEach(item => {
      const rowKey = item.row.id ?? item.row.code
      delete cellFeedbackMap.value[`${rowKey}_${item.prop}`]
    })
  }, 1800)
}

const redo = () => {
  if (redoStack.value.length === 0) return
  const cmd = redoStack.value.pop()!

  // 将每一个变更项重新应用为 newValue
  cmd.items.forEach(item => {
    item.row[item.prop] = item.newValue
    emit('cell-change', {
      row: item.row,
      prop: item.prop,
      value: item.newValue,
      oldValue: item.oldValue
    })
    const rowKey = item.row.id ?? item.row.code
    const key = `${rowKey}_${item.prop}`
    cellFeedbackMap.value[key] = 'saved'
  })

  undoStack.value.push(cmd)
  ElMessage.info(`已重做: ${cmd.label}`)

  setTimeout(() => {
    cmd.items.forEach(item => {
      const rowKey = item.row.id ?? item.row.code
      delete cellFeedbackMap.value[`${rowKey}_${item.prop}`]
    })
  }, 1800)
}

const handleTableUndoRedoKeydown = (e: KeyboardEvent) => {
  // 如果用户正在原生输入框打字编辑中，由浏览器原生 input 处理
  const targetTag = (e.target as HTMLElement)?.tagName
  if (targetTag === 'INPUT' || targetTag === 'TEXTAREA') {
    return
  }

  const isCtrlOrMeta = e.ctrlKey || e.metaKey
  if (!isCtrlOrMeta) return

  if (e.key === 'z' || e.key === 'Z') {
    if (e.shiftKey) {
      e.preventDefault()
      redo()
    } else {
      e.preventDefault()
      undo()
    }
  } else if (e.key === 'y' || e.key === 'Y') {
    e.preventDefault()
    redo()
  }
}

// 批量导入与 AI 导入状态
const importDialogVisible = ref(false)
const aiImportDialogVisible = ref(false)
const downloadingTemplate = ref(false)

const handleImportSuccess = () => {
  emit('refresh')
}

// 模板下载
const handleDownloadTemplate = async () => {
  if (!props.importKey) return
  downloadingTemplate.value = true
  try {
    const res = await axios.get(`/api/excel/template/${props.importKey}`, {
      responseType: 'blob'
    })
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = `${props.importTitle || props.importKey}_导入模板.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
    ElMessage.success('模板下载已就绪')
  } catch {
    ElMessage.error('下载模板失败，请检查后端网络')
  } finally {
    downloadingTemplate.value = false
  }
}

// 刷新通知
const onRefresh = () => {
  emit('refresh')
}

// 列持久化配置
interface ManagedColumn extends TableColumn {
  visible?: boolean
}

const managedColumns = ref<ManagedColumn[]>([])

const initColumns = () => {
  if (props.storageKey) {
    try {
      const saved = localStorage.getItem(`sqm_table_cols_${props.storageKey}`)
      if (saved) {
        const parsed = JSON.parse(saved) as any[]
        const savedMap = new Map(parsed.map(p => [p.prop, p]))
        const orderedCols: ManagedColumn[] = []

        parsed.forEach(p => {
          const original = props.columns.find(c => c.prop === p.prop)
          if (original) {
            orderedCols.push({
              ...original,
              ...p,
              visible: p.visible ?? true,
              width: p.width ?? original.width,
              dateFormat: p.dateFormat ?? original.dateFormat
            })
          }
        })

        props.columns.forEach(c => {
          if (!savedMap.has(c.prop)) {
            orderedCols.push({ ...c, visible: c.visible ?? true })
          }
        })

        managedColumns.value = orderedCols
        return
      }
    } catch {
      // 容错回退
    }
  }

  managedColumns.value = props.columns.map(c => ({
    ...c,
    visible: c.visible ?? true
  }))
}

const visibleColumns = computed(() => {
  return managedColumns.value.filter(c => c.visible !== false)
})

const saveColumnSettings = () => {
  if (!props.storageKey) return
  try {
    const serialized = managedColumns.value.map(c => ({
      prop: c.prop,
      visible: c.visible,
      width: c.width,
      label: c.label,
      editType: c.editType,
      dateFormat: c.dateFormat,
      options: c.options,
      colorMap: c.colorMap,
      allowCreate: c.allowCreate
    }))
    localStorage.setItem(`sqm_table_cols_${props.storageKey}`, JSON.stringify(serialized))
  } catch {
    // 忽略
  }
}

const moveColumn = (index: number, delta: number) => {
  const target = index + delta
  if (target < 0 || target >= managedColumns.value.length) return
  const item = managedColumns.value.splice(index, 1)[0]
  managedColumns.value.splice(target, 0, item)
  saveColumnSettings()
}

const resetColumnSettings = () => {
  if (props.storageKey) {
    localStorage.removeItem(`sqm_table_cols_${props.storageKey}`)
  }
  managedColumns.value = props.columns.map(c => ({
    ...c,
    visible: c.visible ?? true
  }))
}

const handleHeaderDragend = (newWidth: number, _oldWidth: number, column: any) => {
  const targetCol = managedColumns.value.find(c => c.prop === column.property)
  if (targetCol) {
    targetCol.width = newWidth
    saveColumnSettings()
  }
}

const handleSortChange = (payload: { column: any; prop: string; order: string | null }) => {
  emit('sort-change', payload)
}

const defaultTooltipOptions = {
  enterable: true,
  placement: 'top',
  showAfter: 500
}

const isDateColumn = (col: TableColumn) => {
  if (col.dataType === 'date' || col.dataType === 'datetime' || col.editType === 'date') return true
  if (col.prop.endsWith('_at') || col.prop.endsWith('_date') || col.prop === 'sop_date') return true
  return false
}

const hasValidDate = (val: any) => {
  if (!val || val === '-') return false
  const d = new Date(val)
  return !isNaN(d.getTime())
}

const formatFullDateTime = (val: any) => {
  return formatDate(val, 'YYYY-MM-DD HH:mm:ss')
}

const getColumnFilters = (col: TableColumn) => {
  if (col.filters && col.filters.length > 0) return col.filters
  if (col.autoFilter && props.data && props.data.length > 0) {
    const rawValues = props.data.map(item => item[col.prop]).filter(v => v !== null && v !== undefined && v !== '')
    const uniqueValues = Array.from(new Set(rawValues))
    return uniqueValues.map(v => ({ text: String(v), value: v }))
  }
  return undefined
}

const defaultFilterMethod = (prop: string) => {
  return (value: any, row: any) => {
    return row[prop] === value
  }
}

const formatCellValue = (row: any, col: TableColumn) => {
  const val = row[col.prop]
  if (val === null || val === undefined || val === '') return '-'

  // 日期/时间列：优先使用用户配置的 dateFormat，未配置时默认仅显示日期 YYYY-MM-DD (信标 6)
  if (isDateColumn(col)) {
    const pattern = col.dateFormat || 'YYYY-MM-DD'
    return formatDate(val, pattern)
  }

  return val
}

// ========================================================
// 飞书多维表格风格行内编辑引擎核心状态与函数
// ========================================================

// 聚焦的单元格坐标 (飞书 2px 蓝框选区)
const focusedCell = ref<{ rowId: any; prop: string } | null>(null)

// 处于激活输入态的单元格
const editingCell = ref<{ rowId: any; prop: string; tempValue: any } | null>(null)

// 当前激活展开的下拉浮层 Key（控制唯一下拉展开，避免多开与拖拽阻挡）
const activeSelectPopoverKey = ref<string | null>(null)

const getCellKey = (row: any, prop: string) => {
  return `${row.id ?? row.code}_${prop}`
}

const toggleSelectPopover = (row: any, col: TableColumn) => {
  focusCell(row, col)
  const key = getCellKey(row, col.prop)
  activeSelectPopoverKey.value = activeSelectPopoverKey.value === key ? null : key
}

const onHandleHover = () => {
  // 当鼠标悬浮在拖拽手柄上，准备拖拽时，立即收起下拉框以避免阻挡下方行
  activeSelectPopoverKey.value = null
}

const handleGlobalClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (!target) return
  if (!target.closest('.feishu-select-popper') && !target.closest('.feishu-cell-container')) {
    activeSelectPopoverKey.value = null
  }
}

// 单元格反馈状态 (保存成功微绿点提示)
const cellFeedbackMap = ref<Record<string, 'saved'>>({})

// 运行时用户通过 allowCreate 就地动态创建的选项 Map: { [prop]: TableOptionItem[] }
const dynamicOptionsMap = ref<Record<string, TableOptionItem[]>>({})

// 下拉弹窗内部搜索关键字 Map: { [prop]: string }
const popoverSearchMap = ref<Record<string, string>>({})

const getPopoverSearch = (prop: string) => {
  return popoverSearchMap.value[prop] || ''
}

// 标签色彩推导
const getTagColor = (val: any, col: TableColumn): any => {
  if (val === null || val === undefined || val === '') return 'info'
  const str = String(val).trim()
  if (col.colorMap && col.colorMap[str]) {
    return col.colorMap[str]
  }
  // 工业业务关键词语义映射
  if (['合格', '1供', '高', '已闭环', 'DONE', '通过', '有效', 'A'].includes(str)) return 'success'
  if (['考察', '2供开发中', '中', '进行中', 'IN_PROGRESS', '警告', 'B'].includes(str)) return 'warning'
  if (['冻结', '紧急', 'URGENT', '不合格', '已阻塞', 'BLOCKED', '失效', 'C'].includes(str)) return 'danger'
  if (['潜在', '在开发', '低', '待办', 'TODO', '待排期', 'D'].includes(str)) return 'info'
  return 'primary'
}

// 选项规范化
const getColumnOptions = (col: TableColumn): TableOptionItem[] => {
  const raw = col.options || col.editOptions || []
  const normalized: TableOptionItem[] = raw.map(it => {
    if (typeof it === 'string') {
      return { label: it, value: it, color: getTagColor(it, col) }
    }
    return { ...it, color: it.color || getTagColor(it.value, col) }
  })

  // 融合运行时就地创建的新选项
  const extra = dynamicOptionsMap.value[col.prop] || []
  const existValues = new Set(normalized.map(o => String(o.value)))
  for (const it of extra) {
    if (!existValues.has(String(it.value))) {
      normalized.push(it)
    }
  }

  return normalized
}

const getOptionLabel = (val: any, col: TableColumn): string => {
  if (val === null || val === undefined || val === '') return '-'
  const opts = getColumnOptions(col)
  const match = opts.find(o => String(o.value) === String(val))
  return match ? match.label : String(val)
}

const getFilteredOptions = (col: TableColumn): TableOptionItem[] => {
  const all = getColumnOptions(col)
  const q = (popoverSearchMap.value[col.prop] || '').trim().toLowerCase()
  if (!q) return all
  return all.filter(o => o.label.toLowerCase().includes(q) || String(o.value).toLowerCase().includes(q))
}

const hasExactMatch = (col: TableColumn, keyword: string): boolean => {
  const all = getColumnOptions(col)
  return all.some(o => o.label.trim().toLowerCase() === keyword.trim().toLowerCase())
}

// 解析多选
const getMultiValues = (val: any): string[] => {
  if (!val) return []
  if (Array.isArray(val)) return val.map(String)
  if (typeof val === 'string') {
    return val.split(/[,;；，/]/).map(s => s.trim()).filter(Boolean)
  }
  return [String(val)]
}

const isMultiSelected = (currentVal: any, optVal: any): boolean => {
  const list = getMultiValues(currentVal)
  return list.includes(String(optVal))
}

// 聚焦与编辑态判断
const isCellFocused = (row: any, prop: string) => {
  if (!focusedCell.value) return false
  const rowKey = row.id ?? row.code
  return focusedCell.value.rowId === rowKey && focusedCell.value.prop === prop
}

const isCellEditing = (row: any, prop: string) => {
  if (!editingCell.value) return false
  const rowKey = row.id ?? row.code
  return editingCell.value.rowId === rowKey && editingCell.value.prop === prop
}

const focusCell = (row: any, col: TableColumn) => {
  const rowKey = row.id ?? row.code
  focusedCell.value = { rowId: rowKey, prop: col.prop }
}

const startCellEdit = (row: any, col: TableColumn) => {
  if (!col.editable) return
  const rowKey = row.id ?? row.code
  focusedCell.value = { rowId: rowKey, prop: col.prop }
  editingCell.value = {
    rowId: rowKey,
    prop: col.prop,
    tempValue: row[col.prop]
  }
  nextTick(() => {
    cellInputRef.value?.focus?.()
  })
}

// 触发自动保存事件与右上角微点反馈
const emitCellChange = (row: any, prop: string, value: any, oldValue: any, record = true) => {
  emit('cell-change', { row, prop, value, oldValue })
  if (record) {
    recordHistory({
      type: 'cell-edit',
      label: '修改单元格',
      items: [{ row, prop, oldValue, newValue: value }]
    })
  }
  const rowKey = row.id ?? row.code
  const key = `${rowKey}_${prop}`
  cellFeedbackMap.value[key] = 'saved'
  setTimeout(() => {
    delete cellFeedbackMap.value[key]
  }, 1800)
}

const saveCellEdit = (row: any, col: TableColumn, rowIdx?: number) => {
  if (!editingCell.value) return
  const oldValue = row[col.prop]
  const newValue = editingCell.value.tempValue
  if (newValue !== oldValue) {
    row[col.prop] = newValue
    emitCellChange(row, col.prop, newValue, oldValue)
  }
  editingCell.value = null
  if (rowIdx !== undefined) {
    focusNextRow(rowIdx, col.prop)
  }
}

// 单选气泡选择
const onSelectPopoverShow = (row: any, col: TableColumn) => {
  focusCell(row, col)
  popoverSearchMap.value[col.prop] = ''
}

const selectOptionAndSave = (row: any, col: TableColumn, val: any) => {
  const oldVal = row[col.prop]
  if (oldVal !== val) {
    row[col.prop] = val
    emitCellChange(row, col.prop, val, oldVal)
  }
  popoverSearchMap.value[col.prop] = ''
  activeSelectPopoverKey.value = null
}

// 飞书式：就地创建新单选选项
const createOptionAndSelect = (row: any, col: TableColumn, text: string) => {
  const clean = text.trim()
  if (!clean) return
  if (!dynamicOptionsMap.value[col.prop]) {
    dynamicOptionsMap.value[col.prop] = []
  }
  const newOpt: TableOptionItem = {
    label: clean,
    value: clean,
    color: getTagColor(clean, col)
  }
  dynamicOptionsMap.value[col.prop].push(newOpt)
  selectOptionAndSave(row, col, clean)
  ElMessage.success(`已新建并应用选项【${clean}】`)
}

const handleEnterCreateOption = (row: any, col: TableColumn) => {
  const text = getPopoverSearch(col.prop).trim()
  if (text) {
    createOptionAndSelect(row, col, text)
  }
}

// 多选气泡操作
const toggleMultiOption = (row: any, col: TableColumn, optVal: any) => {
  const current = getMultiValues(row[col.prop])
  const strVal = String(optVal)
  let updated: string[] = []
  if (current.includes(strVal)) {
    updated = current.filter(x => x !== strVal)
  } else {
    updated = [...current, strVal]
  }

  const oldVal = row[col.prop]
  const newVal = Array.isArray(oldVal) ? updated : updated.join(', ')
  row[col.prop] = newVal
  emitCellChange(row, col.prop, newVal, oldVal)
}

const createMultiOptionAndSelect = (row: any, col: TableColumn, text: string) => {
  const clean = text.trim()
  if (!clean) return
  if (!dynamicOptionsMap.value[col.prop]) {
    dynamicOptionsMap.value[col.prop] = []
  }
  const newOpt: TableOptionItem = {
    label: clean,
    value: clean,
    color: getTagColor(clean, col)
  }
  dynamicOptionsMap.value[col.prop].push(newOpt)
  toggleMultiOption(row, col, clean)
  popoverSearchMap.value[col.prop] = ''
  ElMessage.success(`已新建多选标签【${clean}】`)
}

const handleEnterCreateMultiOption = (row: any, col: TableColumn) => {
  const text = getPopoverSearch(col.prop).trim()
  if (text) {
    createMultiOptionAndSelect(row, col, text)
  }
}

// 键盘流导航定位
const focusNextCol = (rowIdx: number, currentProp: string) => {
  const editCols = visibleColumns.value.filter(c => c.editable)
  const colIdx = editCols.findIndex(c => c.prop === currentProp)
  if (colIdx >= 0 && colIdx < editCols.length - 1) {
    const nextCol = editCols[colIdx + 1]
    const row = props.data[rowIdx]
    if (row) focusCell(row, nextCol)
  } else if (rowIdx < props.data.length - 1 && editCols.length > 0) {
    const firstCol = editCols[0]
    const nextRow = props.data[rowIdx + 1]
    if (nextRow) focusCell(nextRow, firstCol)
  }
}

const focusPrevCol = (rowIdx: number, currentProp: string) => {
  const editCols = visibleColumns.value.filter(c => c.editable)
  const colIdx = editCols.findIndex(c => c.prop === currentProp)
  if (colIdx > 0) {
    const prevCol = editCols[colIdx - 1]
    const row = props.data[rowIdx]
    if (row) focusCell(row, prevCol)
  } else if (rowIdx > 0 && editCols.length > 0) {
    const lastCol = editCols[editCols.length - 1]
    const prevRow = props.data[rowIdx - 1]
    if (prevRow) focusCell(prevRow, lastCol)
  }
}

const focusNextRow = (rowIdx: number, prop: string) => {
  if (rowIdx < props.data.length - 1) {
    const nextRow = props.data[rowIdx + 1]
    const col = visibleColumns.value.find(c => c.prop === prop)
    if (nextRow && col) focusCell(nextRow, col)
  }
}

const handleCellKeydown = (e: KeyboardEvent, row: any, col: TableColumn, rowIdx: number) => {
  if (e.key === 'Tab') {
    e.preventDefault()
    if (isCellEditing(row, col.prop)) {
      saveCellEdit(row, col)
    }
    if (e.shiftKey) {
      focusPrevCol(rowIdx, col.prop)
    } else {
      focusNextCol(rowIdx, col.prop)
    }
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (!isCellEditing(row, col.prop)) {
      startCellEdit(row, col)
    } else {
      saveCellEdit(row, col, rowIdx)
    }
  } else if (e.key === 'Escape') {
    if (isCellEditing(row, col.prop)) {
      editingCell.value = null
    }
  }
}

// ========================================================
// 需求 6：拖拽复制填充状态机 (Autofill Handle)
// ========================================================
interface AutofillState {
  isDragging: boolean
  startRowIdx: number
  endRowIdx: number
  col: TableColumn | null
  sourceValue: any
}

const autofillState = reactive<AutofillState>({
  isDragging: false,
  startRowIdx: -1,
  endRowIdx: -1,
  col: null,
  sourceValue: null
})

const isInAutofillRange = (rowIdx: number, prop: string) => {
  if (!autofillState.isDragging || !autofillState.col) return false
  if (autofillState.col.prop !== prop) return false
  const min = Math.min(autofillState.startRowIdx, autofillState.endRowIdx)
  const max = Math.max(autofillState.startRowIdx, autofillState.endRowIdx)
  return rowIdx >= min && rowIdx <= max
}

const startAutofillDrag = (e: MouseEvent, row: any, col: TableColumn, rowIdx: number) => {
  activeSelectPopoverKey.value = null // 关键：拖拽开始瞬间收起所有下拉浮窗，杜绝阻挡
  autofillState.isDragging = true
  autofillState.startRowIdx = rowIdx
  autofillState.endRowIdx = rowIdx
  autofillState.col = col
  autofillState.sourceValue = row[col.prop]

  document.body.classList.add('is-table-autofilling')

  window.addEventListener('mousemove', onAutofillMouseMove)
  window.addEventListener('mouseup', onAutofillMouseUp)
}

const getRowIdxFromPoint = (clientX: number, clientY: number): number => {
  const targetEl = document.elementFromPoint(clientX, clientY)
  if (!targetEl) return -1
  // 1. 优先尝试从带 data-row-idx 的单元格容器中获取
  const cellEl = targetEl.closest('[data-row-idx]') as HTMLElement | null
  if (cellEl && cellEl.dataset.rowIdx !== undefined) {
    const idx = parseInt(cellEl.dataset.rowIdx, 10)
    if (!isNaN(idx)) return idx
  }
  // 2. 兜底尝试从表格行 tr.el-table__row 索引中解析
  const trEl = targetEl.closest('tr.el-table__row')
  if (trEl && trEl.parentElement) {
    const rows = Array.from(trEl.parentElement.querySelectorAll('tr.el-table__row'))
    const idx = rows.indexOf(trEl)
    if (idx !== -1) return idx
  }
  return -1
}

const onAutofillMouseMove = (e: MouseEvent) => {
  if (!autofillState.isDragging) return
  const targetIdx = getRowIdxFromPoint(e.clientX, e.clientY)
  if (targetIdx !== -1 && targetIdx >= 0 && targetIdx < props.data.length) {
    autofillState.endRowIdx = targetIdx
  }
}

const onAutofillMouseUp = () => {
  if (!autofillState.isDragging) return
  window.removeEventListener('mousemove', onAutofillMouseMove)
  window.removeEventListener('mouseup', onAutofillMouseUp)
  document.body.classList.remove('is-table-autofilling')

  const { startRowIdx, endRowIdx, col, sourceValue } = autofillState
  autofillState.isDragging = false

  // 只要目标行与起始行不同（无论是向上拖拽还是向下拖拽），均执行批量覆盖
  if (col && startRowIdx !== -1 && endRowIdx !== -1 && startRowIdx !== endRowIdx) {
    const min = Math.min(startRowIdx, endRowIdx)
    const max = Math.max(startRowIdx, endRowIdx)
    const batchItems: { row: any; prop: string; value: any; oldValue: any }[] = []

    for (let i = min; i <= max; i++) {
      if (i === startRowIdx) continue // 源单元格本身保持原样
      const targetRow = props.data[i]
      if (targetRow) {
        const oldValue = targetRow[col.prop]
        if (oldValue !== sourceValue) {
          targetRow[col.prop] = sourceValue
          batchItems.push({
            row: targetRow,
            prop: col.prop,
            value: sourceValue,
            oldValue
          })
          const rowKey = targetRow.id ?? targetRow.code
          const key = `${rowKey}_${col.prop}`
          cellFeedbackMap.value[key] = 'saved'
        }
      }
    }

    if (batchItems.length > 0) {
      const directionText = endRowIdx > startRowIdx ? '向下' : '向上'

      // 记录批量填充历史命令
      recordHistory({
        type: 'batch-fill',
        label: `${directionText}复制填充 ${batchItems.length} 行`,
        items: batchItems.map(b => ({
          row: b.row,
          prop: b.prop,
          oldValue: b.oldValue,
          newValue: b.value
        }))
      })

      // 触发批量更新事件
      emit('batch-cell-change', {
        prop: col.prop,
        value: sourceValue,
        items: batchItems
      })
      // 同时按序触发单个 cell-change，保持向下兼容
      batchItems.forEach(item => {
        emit('cell-change', item)
      })

      ElMessage.success(`已${directionText}复制填充 ${batchItems.length} 行数据`)

      setTimeout(() => {
        batchItems.forEach(item => {
          const rowKey = item.row.id ?? item.row.code
          delete cellFeedbackMap.value[`${rowKey}_${col.prop}`]
        })
      }, 1800)
    }
  }

  autofillState.startRowIdx = -1
  autofillState.endRowIdx = -1
  autofillState.col = null
  autofillState.sourceValue = null
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onAutofillMouseMove)
  window.removeEventListener('mouseup', onAutofillMouseUp)
  window.removeEventListener('keydown', handleTableUndoRedoKeydown)
  window.removeEventListener('click', handleGlobalClick, true)
  document.body.classList.remove('is-table-autofilling')
})

// ========================================================
// 需求 7：表头可视化编辑字段属性 (ColumnConfigDialog)
// ========================================================
const configDialogVisible = ref(false)
const selectedColForConfig = ref<TableColumn | null>(null)

const openColumnConfig = (col: TableColumn) => {
  selectedColForConfig.value = col
  configDialogVisible.value = true
}

const handleColumnConfigSave = (payload: { prop: string; changes: Partial<TableColumn> }) => {
  const target = managedColumns.value.find(c => c.prop === payload.prop)
  if (target) {
    Object.assign(target, payload.changes)
    saveColumnSettings()
  }
}

// 分页控制 (记住用户每页条数偏好)
const PAGE_SIZE_KEY = computed(() => {
  return props.storageKey ? `sqm_table_pagesize_${props.storageKey}` : `sqm_table_pagesize_default`
})

const initPageSize = () => {
  if (!props.pagination) return
  try {
    const saved = localStorage.getItem(PAGE_SIZE_KEY.value)
    if (saved) {
      const s = parseInt(saved, 10)
      if (!isNaN(s) && s > 0 && s !== props.pagination.pageSize) {
        props.pagination.pageSize = s
        emit('size-change', s)
      }
    }
  } catch {}
}

const onPageChange = (p: number) => {
  emit('page-change', p)
}

const onPageSizeChange = (s: number) => {
  try {
    localStorage.setItem(PAGE_SIZE_KEY.value, s.toString())
  } catch {}
  if (props.pagination) {
    props.pagination.pageSize = s
  }
  emit('size-change', s)
}

watch(
  () => props.columns,
  () => {
    initColumns()
  },
  { deep: true }
)

onMounted(() => {
  initColumns()
  initPageSize()
  window.addEventListener('keydown', handleTableUndoRedoKeydown)
  window.addEventListener('click', handleGlobalClick, true)
})
</script>

<style scoped>
.common-data-table-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

/* 统一紧凑顶部栏 (整合信标1操作区与信标2检索区) */
.table-unified-header-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 10px;
  margin-bottom: 6px;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-sizing: border-box;
  gap: 8px;
  overflow: hidden;
}

.header-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.header-bar-left::-webkit-scrollbar {
  display: none;
}

.toolbar-primary-slot {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.toolbar-search-slot {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.header-bar-right {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  flex-shrink: 0;
}

.import-button-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai-smart-btn {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(147, 51, 234, 0.08)) !important;
  border-color: rgba(147, 51, 234, 0.35) !important;
  color: #7c3aed !important;
  font-weight: 500;
}

.ai-smart-btn:hover {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(147, 51, 234, 0.16)) !important;
  border-color: #7c3aed !important;
  color: #6d28d9 !important;
}

.tool-btn {
  font-size: 12.5px;
}

/* 表格核心主卡片区 (舒适内边距呼吸感、精致内嵌式网格) */
.table-main-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  box-sizing: border-box;
  overflow: hidden;
}

.table-body-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.custom-fit-table {
  width: 100%;
}

.custom-fit-table :deep(th.el-table__cell) {
  padding: 6px 0 !important;
  background-color: #f8fafc !important;
  font-weight: 600;
  font-size: 13px;
  color: #334155;
}

.custom-fit-table :deep(td.el-table__cell) {
  padding: 3px 0 !important;
}

.custom-fit-table :deep(.el-table__body-wrapper .cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 6px;
}

.custom-fit-table :deep(.el-table__header-wrapper .cell) {
  white-space: nowrap;
  overflow: visible !important;
  text-overflow: clip !important;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
}

/* ========================================================
   飞书多维表格风格单元格样式
   ======================================================== */
.feishu-cell-container {
  position: relative;
  min-height: 28px;
  width: 100%;
  display: flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 4px;
  box-sizing: border-box;
  transition: all 0.12s ease;
  outline: none;
  cursor: pointer;
}

.feishu-cell-container:hover {
  background-color: #f1f5f9;
}

/* 飞书标志性单元格聚焦选中外框 (2px 品牌蓝) */
.feishu-cell-container.is-focused {
  background-color: #eff6ff;
  box-shadow: 0 0 0 2px #2563eb !important;
  z-index: 2;
}

.feishu-pill-display {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  width: 100%;
  min-height: 24px;
  outline: none;
}

.feishu-status-pill {
  font-weight: 500;
  font-size: 12px;
  border-radius: 12px;
  padding: 0 8px;
  height: 22px;
  line-height: 20px;
}

.feishu-status-pill.multi-item {
  font-size: 11px;
  padding: 0 6px;
  height: 20px;
  line-height: 18px;
}

.feishu-placeholder-text {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}

.feishu-text-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 24px;
}

.cell-text-val {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-hover-edit-icon {
  font-size: 11px;
  color: #94a3b8;
  opacity: 0;
  transition: opacity 0.15s;
}

.feishu-cell-container:hover .cell-hover-edit-icon {
  opacity: 1;
}

.feishu-input-wrap {
  width: 100%;
}

.feishu-edit-input {
  width: 100% !important;
}

/* 单元格右上角保存生效绿色脉冲点 */
.cell-status-dot {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  pointer-events: none;
}

.cell-status-dot.saved {
  background-color: #10b981;
  box-shadow: 0 0 5px #10b981;
  animation: pulse-save 1.8s ease-out forwards;
}

@keyframes pulse-save {
  0% { transform: scale(1); opacity: 1; }
  60% { transform: scale(1.8); opacity: 0.8; }
  100% { transform: scale(1); opacity: 0; }
}

.cell-plain-text {
  font-size: 13px;
  color: #334155;
}

/* 分页栏 */
.table-pagination-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px 0 4px;
  margin-top: 6px;
  border-top: 1px solid #f1f5f9;
  background-color: #ffffff;
  box-sizing: border-box;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
  flex-shrink: 0;
}

.pagination-info strong {
  color: #334155;
}

.pagination-footer-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  white-space: nowrap;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.pagination-footer-left::-webkit-scrollbar {
  display: none;
}

.pagination-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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
}

.order-arrows {
  display: flex;
  align-items: center;
}

.import-button-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>

<!-- 飞书式 Popover 浮层全局样式 (不加 scoped 以渗透至 teleport 弹出层) -->
<style>
.feishu-select-popper {
  padding: 6px !important;
  border-radius: 8px !important;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
}

.feishu-popover-box {
  display: flex;
  flex-direction: column;
}

.feishu-popover-search {
  margin-bottom: 6px;
}

.feishu-options-list {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feishu-opt-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #334155;
  transition: background-color 0.12s;
}

.feishu-opt-item:hover {
  background-color: #f1f5f9;
}

.feishu-opt-item.active {
  background-color: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}

.opt-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.opt-color-dot.is-success { background-color: #10b981; }
.opt-color-dot.is-warning { background-color: #f59e0b; }
.opt-color-dot.is-danger { background-color: #ef4444; }
.opt-color-dot.is-primary { background-color: #3b82f6; }
.opt-color-dot.is-info { background-color: #06b6d4; }

.opt-check-icon {
  margin-left: auto;
  font-size: 13px;
  color: #2563eb;
}

.feishu-no-opt {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  padding: 12px 0;
}

.feishu-create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  margin-top: 4px;
  border-top: 1px dashed #e2e8f0;
  color: #2563eb;
  font-size: 12.5px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.12s;
}

.feishu-create-btn:hover {
  background-color: #eff6ff;
}

/* ========================================================
   需求 6：单元格右下角拖拽填充手柄 (Autofill Handle)
   ======================================================== */
.feishu-autofill-handle {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 7px;
  height: 7px;
  background-color: #2563eb;
  border: 1.5px solid #ffffff;
  border-radius: 1px;
  cursor: crosshair;
  z-index: 20;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.3);
  transition: transform 0.1s ease;
}

/* 扩大可交互点击拖拽感应区域 (Hitbox)，避免用户很难点中 7px 小点 */
.feishu-autofill-handle::before {
  content: '';
  position: absolute;
  top: -5px;
  left: -5px;
  right: -5px;
  bottom: -5px;
  cursor: crosshair;
}

.feishu-autofill-handle:hover {
  transform: scale(1.4);
}

.feishu-cell-container.is-autofill-range {
  background-color: rgba(37, 99, 235, 0.08) !important;
  box-shadow: inset 0 0 0 1.5px #2563eb !important;
  transition: none !important;
}

:global(body.is-table-autofilling) {
  user-select: none !important;
  cursor: crosshair !important;
}

:global(body.is-table-autofilling *) {
  user-select: none !important;
  cursor: crosshair !important;
}

:global(body.is-table-autofilling .el-popper),
:global(body.is-table-autofilling .feishu-select-popper) {
  display: none !important;
  pointer-events: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

.date-cell-text {
  cursor: help;
}

.custom-fit-table :deep(.el-table__header-wrapper .cell) {
  overflow: visible !important;
  text-overflow: clip !important;
  display: flex !important;
  align-items: center !important;
}

/* ========================================================
   需求 7：表头字段可视化配置悬停按钮
   ======================================================== */
.feishu-header-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  vertical-align: middle;
  overflow: visible;
  flex: 1;
  min-width: 0;
}

.feishu-header-title {
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feishu-header-config-btn {
  font-size: 13px;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  opacity: 0.6;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

:deep(.el-table__header) th:hover .feishu-header-config-btn {
  opacity: 1;
}

.feishu-header-config-btn:hover {
  color: #2563eb;
  background-color: #eff6ff;
  transform: rotate(45deg);
}
</style>
