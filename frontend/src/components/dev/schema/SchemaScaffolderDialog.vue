<template>
  <el-dialog
    v-model="dialogVisible"
    title="🛠️ 数据字典与 UI 页面脚手架 (Schema Scaffolder)"
    width="1060px"
    draggable
    append-to-body
    :close-on-click-modal="false"
    class="schema-scaffolder-dialog"
  >
    <div class="scaffolder-container" v-loading="loadingTables">
      <!-- 左栏：数据表选择与字典字段列表 (【信标 1】增强版) -->
      <div class="scaffolder-left-pane">
        <!-- 1. 表选择与元数据卡片 -->
        <div class="table-select-card">
          <div class="section-title">
            <span class="title-icon">🗄️</span>
            <span>选择数据库实体表：</span>
          </div>

          <el-select
            v-model="selectedTableName"
            filterable
            placeholder="搜索或选择数据表..."
            class="table-selector-input"
            @change="handleTableChange"
          >
            <el-option
              v-for="t in tableList"
              :key="t.name"
              :label="`${t.name} ${t.comment ? '(' + t.comment + ')' : ''}`"
              :value="t.name"
            >
              <div class="table-option-row">
                <span class="table-opt-name">{{ t.name }}</span>
                <span class="table-opt-comment" v-if="t.comment">{{ t.comment }}</span>
                <el-tag size="small" type="info" effect="plain" class="table-opt-tag">
                  {{ t.row_count }} 行
                </el-tag>
              </div>
            </el-option>
          </el-select>

          <div class="table-meta-summary" v-if="currentTableInfo">
            <span class="meta-item">
              <span class="meta-label">注释：</span>
              <span class="meta-val">{{ currentTableInfo.comment || '未注明业务含义' }}</span>
            </span>
            <span class="meta-item">
              <span class="meta-label">行数：</span>
              <span class="meta-val">{{ currentTableInfo.row_count }} 条</span>
            </span>
          </div>
        </div>

        <!-- 2. 字段字典选择工具栏 -->
        <div class="columns-toolbar">
          <div class="toolbar-left">
            <span class="columns-title">
              📋 字段字典清单 ({{ columns.length }})
            </span>
          </div>
          <div class="toolbar-right">
            <el-button link type="primary" size="small" @click="selectAllColumns">全选</el-button>
            <el-button link type="primary" size="small" @click="selectBusinessOnly">仅业务字段</el-button>
            <el-button link type="info" size="small" @click="clearSelection">清空</el-button>
          </div>
        </div>

        <!-- 3. 字段字典表格 (【信标 1】复选与智能推断增强) -->
        <div class="columns-table-wrap" v-loading="loadingColumns">
          <el-table
            ref="columnsTableRef"
            :data="columns"
            row-key="name"
            stripe
            size="small"
            class="columns-pick-table"
            height="420"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="38" align="center" />

            <el-table-column prop="name" label="字段物理名" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="field-name-wrap">
                  <span class="key-badge" v-if="row.is_primary" title="物理自增主键">🔑</span>
                  <span class="req-star" v-else-if="!row.is_nullable && row.default === null" title="数据库非空必填">*</span>
                  <span class="field-name-text">{{ row.name }}</span>
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="comment" label="业务注释" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="field-comment-text">{{ row.comment || '-' }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="type" label="类型" width="90" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag size="small" type="info" effect="plain" class="type-tag">
                  {{ row.type }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="推断控件" width="90" align="center">
              <template #default="{ row }">
                <span class="inferred-badge" :class="`badge-${row.inferred?.controlType || 'input'}`">
                  {{ getControlName(row.inferred?.controlType) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="left-pane-footer">
          <span class="selection-count-pill">
            已勾选 <strong>{{ selectedFields.length }}</strong> / {{ columns.length }} 个字段
          </span>
        </div>
      </div>

      <!-- 右栏：多场景代码生成与交互原型 (所见即所得) -->
      <div class="scaffolder-right-pane">
        <el-tabs v-model="activeScenarioTab" class="scaffolder-tabs">
          <!-- 场景 1: 数据展示表格 -->
          <el-tab-pane label="📊 展示表格" name="table">
            <div class="scenario-content">
              <div class="scenario-actions-bar">
                <div class="scenario-desc">
                  <span>自动生成 SQM 标准数据列表骨架与自定义插槽</span>
                </div>
                <div class="scenario-btns">
                  <el-button type="primary" size="small" @click="copyCode(tableCodeSnippet)">
                    <el-icon><CopyDocument /></el-icon> 复制表格代码
                  </el-button>
                </div>
              </div>

              <!-- 实时原型预览 -->
              <div class="preview-box">
                <div class="preview-header">
                  <span class="preview-tag">交互原型实时预览</span>
                  <span class="preview-hint">({{ selectedFields.length }} 列已就绪)</span>
                </div>
                <div class="preview-viewport">
                  <el-table :data="mockTableData" stripe border size="small" style="width: 100%" max-height="160">
                    <el-table-column
                      v-for="f in selectedFields"
                      :key="f.prop"
                      :prop="f.prop"
                      :label="f.label"
                      min-width="110"
                      show-overflow-tooltip
                    >
                      <template #default="{ row }">
                        <template v-if="f.controlType === 'switch'">
                          <el-tag :type="row[f.prop] ? 'success' : 'info'" size="small">
                            {{ row[f.prop] ? '是' : '否' }}
                          </el-tag>
                        </template>
                        <template v-else-if="f.controlType === 'select'">
                          <el-tag size="small">{{ row[f.prop] || '有效' }}</el-tag>
                        </template>
                        <template v-else>
                          {{ row[f.prop] || '-' }}
                        </template>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="100" fixed="right" align="center">
                      <template #default>
                        <el-button link type="primary" size="small">编辑</el-button>
                        <el-button link type="danger" size="small">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>

              <!-- 代码高亮查看器 -->
              <div class="code-view-box">
                <div class="code-header">
                  <span>生成的 Vue 3 模板代码</span>
                  <button class="copy-tiny-btn" @click="copyCode(tableCodeSnippet)">一键复制</button>
                </div>
                <pre class="code-pre"><code>{{ tableCodeSnippet }}</code></pre>
              </div>
            </div>
          </el-tab-pane>

          <!-- 场景 2: 新增/编辑弹窗表单 -->
          <el-tab-pane label="📝 业务表单" name="form">
            <div class="scenario-content">
              <div class="scenario-actions-bar">
                <div class="scenario-desc">
                  <span>自动推断 Input/Select/Number 控件并生成 rules 校验</span>
                </div>
                <div class="scenario-btns">
                  <el-button type="primary" size="small" @click="copyCode(formTemplateCode)">
                    <el-icon><CopyDocument /></el-icon> 复制表单 Template
                  </el-button>
                  <el-button size="small" @click="copyCode(formScriptCode)">
                    复制 Script 规则
                  </el-button>
                </div>
              </div>

              <!-- 实时表单预览 -->
              <div class="preview-box">
                <div class="preview-header">
                  <span class="preview-tag">表单原型实时试用</span>
                  <span class="preview-hint">(含输入框与必填标识)</span>
                </div>
                <div class="preview-viewport form-viewport">
                  <el-form :model="mockFormData" label-width="110px" size="small" label-position="right">
                    <el-row :gutter="12">
                      <el-col
                        v-for="f in editableFields"
                        :key="f.prop"
                        :span="f.controlType === 'textarea' ? 24 : 12"
                      >
                        <el-form-item :label="f.label" :required="f.required">
                          <template v-if="f.controlType === 'switch'">
                            <el-switch v-model="mockFormData[f.prop]" active-text="是" inactive-text="否" />
                          </template>
                          <template v-else-if="f.controlType === 'select'">
                            <el-select v-model="mockFormData[f.prop]" placeholder="请选择" style="width: 100%">
                              <el-option label="合格 / 生效" value="ACTIVE" />
                              <el-option label="待评定" value="PENDING" />
                            </el-select>
                          </template>
                          <template v-else-if="f.controlType === 'input-number'">
                            <el-input-number v-model="mockFormData[f.prop]" :step="1" controls-position="right" style="width: 100%" />
                          </template>
                          <template v-else-if="f.controlType === 'date-picker'">
                            <el-date-picker v-model="mockFormData[f.prop]" type="date" placeholder="选择日期" style="width: 100%" />
                          </template>
                          <template v-else-if="f.controlType === 'textarea'">
                            <el-input v-model="mockFormData[f.prop]" type="textarea" :rows="2" placeholder="请输入说明" />
                          </template>
                          <template v-else>
                            <el-input v-model="mockFormData[f.prop]" :placeholder="`请输入${f.label}`" />
                          </template>
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </el-form>
                </div>
              </div>

              <!-- 代码高亮查看器 -->
              <div class="code-view-box">
                <div class="code-header">
                  <span>生成的 el-form 模板与响应式校验代码</span>
                  <button class="copy-tiny-btn" @click="copyCode(formTemplateCode + '\n\n' + formScriptCode)">复制全部</button>
                </div>
                <pre class="code-pre"><code>{{ formTemplateCode }}

{{ formScriptCode }}</code></pre>
              </div>
            </div>
          </el-tab-pane>

          <!-- 场景 3: 列表搜索筛选栏 -->
          <el-tab-pane label="🔍 筛选栏" name="filter">
            <div class="scenario-content">
              <div class="scenario-actions-bar">
                <div class="scenario-desc">
                  <span>提取高频筛选维度，生成页面顶部查询表单</span>
                </div>
                <div class="scenario-btns">
                  <el-button type="primary" size="small" @click="copyCode(filterBarCodeSnippet)">
                    <el-icon><CopyDocument /></el-icon> 复制筛选栏代码
                  </el-button>
                </div>
              </div>

              <!-- 搜索栏实时预览 -->
              <div class="preview-box">
                <div class="preview-header">
                  <span class="preview-tag">顶部查询栏原型预览</span>
                </div>
                <div class="preview-viewport filter-viewport">
                  <div class="demo-filter-row">
                    <el-input placeholder="搜索核心关键字..." size="small" style="width: 180px;" clearable />
                    <el-select placeholder="状态分类" size="small" style="width: 130px;" clearable>
                      <el-option label="全部状态" value="" />
                      <el-option label="已生效" value="ACTIVE" />
                    </el-select>
                    <el-button type="primary" size="small">查询</el-button>
                    <el-button size="small">重置</el-button>
                  </div>
                </div>
              </div>

              <!-- 代码查看器 -->
              <div class="code-view-box">
                <div class="code-header">
                  <span>生成的筛选栏代码</span>
                  <button class="copy-tiny-btn" @click="copyCode(filterBarCodeSnippet)">一键复制</button>
                </div>
                <pre class="code-pre"><code>{{ filterBarCodeSnippet }}</code></pre>
              </div>
            </div>
          </el-tab-pane>

          <!-- 场景 4: TypeScript 契约与 CTQ 规程表 -->
          <el-tab-pane label="📑 契约 & 规程表" name="ts">
            <div class="scenario-content">
              <div class="scenario-actions-bar">
                <div class="scenario-desc">
                  <span>导出 TS 接口契约，或生成质量规程 CTQ 公差表格 HTML</span>
                </div>
                <div class="scenario-btns">
                  <el-button type="primary" size="small" @click="copyCode(typeScriptCodeSnippet)">
                    <el-icon><CopyDocument /></el-icon> 复制 TS 接口
                  </el-button>
                  <el-button size="small" @click="copyCode(ctqHtmlSnippet)">
                    复制 CTQ 规程表
                  </el-button>
                </div>
              </div>

              <!-- 代码查看器 1: TS 实体 -->
              <div class="code-view-box" style="margin-bottom: 10px;">
                <div class="code-header">
                  <span>TypeScript 实体契约 Interface</span>
                  <button class="copy-tiny-btn" @click="copyCode(typeScriptCodeSnippet)">复制 TS</button>
                </div>
                <pre class="code-pre"><code>{{ typeScriptCodeSnippet }}</code></pre>
              </div>

              <!-- 代码查看器 2: CTQ HTML -->
              <div class="code-view-box">
                <div class="code-header">
                  <span>规程编辑器标准 CTQ 表格 HTML 片段</span>
                  <button class="copy-tiny-btn" @click="copyCode(ctqHtmlSnippet)">复制 HTML</button>
                </div>
                <pre class="code-pre"><code>{{ ctqHtmlSnippet }}</code></pre>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { CopyDocument } from '@element-plus/icons-vue'
import { ElMessage, type TableInstance } from 'element-plus'
import {
  type ColumnMeta,
  type InferredField,
  inferField,
  generateTableCode,
  generateFormCode,
  generateTypeScriptCode,
  generateFilterBarCode,
  generateCtqHtmlTable
} from './useSchemaGenerator'

interface TableSummary {
  name: string
  comment: string
  row_count: number
  engine: string
}

interface ColumnWithInferred extends ColumnMeta {
  inferred?: InferredField
}

const dialogVisible = ref(false)
const loadingTables = ref(false)
const loadingColumns = ref(false)

const tableList = ref<TableSummary[]>([])
const selectedTableName = ref<string>(localStorage.getItem('sqm_scaffolder_last_table') || 'sqm_supplier')
const columns = ref<ColumnWithInferred[]>([])
const selectedFields = ref<InferredField[]>([])

const activeScenarioTab = ref<'table' | 'form' | 'filter' | 'ts'>('table')
const columnsTableRef = ref<TableInstance | null>(null)

const currentTableInfo = computed(() => {
  return tableList.value.find(t => t.name === selectedTableName.value)
})

const editableFields = computed(() => {
  return selectedFields.value.filter(f => f.prop !== 'id' && f.prop !== 'created_at' && f.prop !== 'updated_at')
})

const mockFormData = ref<Record<string, any>>({})

const mockTableData = computed(() => {
  const row1: Record<string, any> = {}
  const row2: Record<string, any> = {}
  selectedFields.value.forEach(f => {
    if (f.controlType === 'input-number') {
      row1[f.prop] = 85.5
      row2[f.prop] = 92.0
    } else if (f.controlType === 'switch') {
      row1[f.prop] = true
      row2[f.prop] = false
    } else if (f.controlType === 'date-picker') {
      row1[f.prop] = '2026-10-31'
      row2[f.prop] = '2026-11-05'
    } else if (f.controlType === 'select') {
      row1[f.prop] = '合格'
      row2[f.prop] = '良好'
    } else {
      row1[f.prop] = `${f.label}-示例A`
      row2[f.prop] = `${f.label}-示例B`
    }
  })
  return [row1, row2]
})

// 生成的代码片段
const tableCodeSnippet = computed(() => {
  return generateTableCode(selectedTableName.value || 'data_table', selectedFields.value)
})

const formDataGenerated = computed(() => {
  return generateFormCode(selectedTableName.value || 'data_form', selectedFields.value)
})

const formTemplateCode = computed(() => formDataGenerated.value.template)
const formScriptCode = computed(() => formDataGenerated.value.script)

const typeScriptCodeSnippet = computed(() => {
  return generateTypeScriptCode(selectedTableName.value || 'data_item', selectedFields.value)
})

const filterBarCodeSnippet = computed(() => {
  return generateFilterBarCode(selectedFields.value)
})

const ctqHtmlSnippet = computed(() => {
  return generateCtqHtmlTable(selectedFields.value)
})

const getControlName = (type?: string) => {
  switch (type) {
    case 'input-number': return '数字步进'
    case 'select': return '下拉枚举'
    case 'date-picker': return '日期选择'
    case 'textarea': return '多行文本'
    case 'switch': return '布尔开关'
    default: return '单行文本'
  }
}

// 1. 获取所有表清单
const fetchTables = async () => {
  loadingTables.value = true
  try {
    const res = await fetch('/api/dev/db/tables')
    if (res.ok) {
      const rawData = await res.json()
      tableList.value = rawData.map((t: any) => ({
        name: t.name || t.table_name,
        comment: t.comment || '',
        row_count: t.real_count ?? t.row_count ?? t.table_rows ?? 0,
        engine: t.engine || 'InnoDB'
      }))

      if (tableList.value.length > 0) {
        if (!tableList.value.some(t => t.name === selectedTableName.value)) {
          selectedTableName.value = tableList.value[0].name
        }
        await fetchColumns(selectedTableName.value)
      }
    }
  } catch (err: any) {
    ElMessage.error(`获取数据表失败: ${err.message}`)
  } finally {
    loadingTables.value = false
  }
}

// 2. 获取指定表的字段清单
const fetchColumns = async (tableName: string) => {
  if (!tableName) return
  loadingColumns.value = true
  try {
    const res = await fetch(`/api/dev/db/tables/${tableName}/columns`)
    if (res.ok) {
      const rawCols = await res.json()
      const cols: ColumnMeta[] = rawCols.map((c: any) => ({
        name: c.name || c.column_name,
        type: c.column_type || c.data_type || c.type || 'varchar',
        is_nullable: c.is_nullable ?? true,
        default: c.column_default ?? c.default_val ?? c.default,
        is_primary: !!c.is_primary,
        comment: c.column_comment || c.comment || ''
      }))
      columns.value = cols.map(c => ({
        ...c,
        inferred: inferField(c)
      }))

      // 默认全选或仅选中业务字段
      await nextTick()
      selectBusinessOnly()
    }
  } catch (err: any) {
    ElMessage.error(`获取字段失败: ${err.message}`)
  } finally {
    loadingColumns.value = false
  }
}

const handleTableChange = (val: string) => {
  selectedTableName.value = val
  try {
    localStorage.setItem('sqm_scaffolder_last_table', val)
  } catch {}
  fetchColumns(val)
}

const handleSelectionChange = (selection: ColumnWithInferred[]) => {
  selectedFields.value = selection.map(c => c.inferred || inferField(c))
  const newMockForm: Record<string, any> = {}
  selectedFields.value.forEach(f => {
    newMockForm[f.prop] = f.defaultValue
  })
  mockFormData.value = newMockForm
}

const selectAllColumns = () => {
  columnsTableRef.value?.toggleAllSelection()
}

const selectBusinessOnly = () => {
  if (!columnsTableRef.value) return
  columnsTableRef.value.clearSelection()
  columns.value.forEach(row => {
    // 排除自增主键和创建时间戳等基础字段
    if (row.name !== 'id' && row.name !== 'created_at' && row.name !== 'updated_at') {
      columnsTableRef.value?.toggleRowSelection(row, true)
    }
  })
}

const clearSelection = () => {
  columnsTableRef.value?.clearSelection()
}

// 一键复制代码
const copyCode = async (text: string) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板！可直接粘贴至前端代码中')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板！可直接粘贴至前端代码中')
  }
}

const toggleDialog = (tableName?: string) => {
  if (dialogVisible.value) {
    dialogVisible.value = false
  } else {
    openDialogWithTable(tableName)
  }
}

const openDialogWithTable = async (tableName?: string) => {
  dialogVisible.value = true
  if (tableList.value.length === 0) {
    await fetchTables()
  }
  if (tableName && tableName !== selectedTableName.value) {
    selectedTableName.value = tableName
    await fetchColumns(tableName)
  } else if (columns.value.length === 0 && selectedTableName.value) {
    await fetchColumns(selectedTableName.value)
  }
}

// 全局快捷键 Alt+S
const handleKeydown = (e: KeyboardEvent) => {
  if (e.altKey && (e.key === 's' || e.key === 'S')) {
    e.preventDefault()
    toggleDialog()
  }
}

const handleCustomEvent = (e: Event) => {
  const custom = e as CustomEvent<{ tableName?: string }>
  openDialogWithTable(custom?.detail?.tableName)
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('sqm:toggle-schema-scaffolder', handleCustomEvent)
  fetchTables()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('sqm:toggle-schema-scaffolder', handleCustomEvent)
})

defineExpose({
  open: openDialogWithTable,
  toggle: toggleDialog
})
</script>

<style scoped>
.scaffolder-container {
  display: flex;
  gap: 16px;
  min-height: 540px;
  height: 580px;
}

/* 左侧栏 */
.scaffolder-left-pane {
  flex: 0 0 450px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-right: 1px solid #f1f5f9;
  padding-right: 14px;
}

.table-select-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.title-icon {
  font-size: 14px;
}

.table-selector-input {
  width: 100%;
}

.table-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.table-opt-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 12.5px;
}

.table-opt-comment {
  font-size: 11.5px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.table-opt-tag {
  font-size: 10.5px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
}

.table-meta-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11.5px;
  color: #64748b;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}

.meta-label {
  color: #94a3b8;
}

.meta-val {
  color: #334155;
  font-weight: 500;
}

/* 字段选择工具条 */
.columns-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 2px;
}

.columns-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
}

.columns-table-wrap {
  flex: 1;
  min-height: 0;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.columns-pick-table {
  font-size: 12px;
}

.field-name-wrap {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-weight: 600;
  color: #1e293b;
}

.key-badge {
  font-size: 11px;
}

.req-star {
  color: #ef4444;
  font-weight: bold;
}

.field-comment-text {
  color: #475569;
  font-size: 11.5px;
}

.type-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
  color: #475569;
}

.inferred-badge {
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 500;
}

.badge-input { background: #f1f5f9; color: #475569; }
.badge-select { background: #eff6ff; color: #2563eb; }
.badge-input-number { background: #f0fdf4; color: #16a34a; }
.badge-date-picker { background: #fef3c7; color: #d97706; }
.badge-switch { background: #f3e8ff; color: #9333ea; }
.badge-textarea { background: #f1f5f9; color: #0284c7; }

.left-pane-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selection-count-pill {
  font-size: 11.5px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 3px 8px;
  border-radius: 4px;
}

.selection-count-pill strong {
  color: #2563eb;
}

/* 右侧栏 */
.scaffolder-right-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.scaffolder-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

:deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 8px 0 0 0;
}

:deep(.el-tab-pane) {
  height: 100%;
}

.scenario-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 10px;
}

.scenario-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.scenario-desc {
  font-size: 12px;
  color: #64748b;
}

.scenario-btns {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 预览区 */
.preview-box {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fafbfc;
  border-bottom: 1px solid #f1f5f9;
}

.preview-tag {
  font-size: 11.5px;
  font-weight: 600;
  color: #059669;
}

.preview-hint {
  font-size: 11px;
  color: #94a3b8;
}

.preview-viewport {
  padding: 8px 10px;
}

.form-viewport {
  max-height: 180px;
  overflow-y: auto;
}

.demo-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
}

/* 代码查看器 */
.code-view-box {
  flex: 1;
  min-height: 0;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #1e293b;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #0f172a;
  color: #94a3b8;
  font-size: 11px;
  border-bottom: 1px solid #334155;
}

.copy-tiny-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #e2e8f0;
  font-size: 10.5px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.copy-tiny-btn:hover {
  background: #3b82f6;
  color: #ffffff;
}

.code-pre {
  margin: 0;
  padding: 10px 12px;
  overflow: auto;
  flex: 1;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 11.5px;
  line-height: 1.5;
  color: #e2e8f0;
}

.code-pre::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.code-pre::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 3px;
}
</style>

<style>
.schema-scaffolder-dialog {
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 20px 48px -12px rgba(15, 23, 42, 0.25) !important;
}

.schema-scaffolder-dialog .el-dialog__header {
  padding: 12px 18px 10px 18px !important;
  margin-right: 0 !important;
  border-bottom: 1px solid #f1f5f9 !important;
  background: #fafbfc !important;
  user-select: none !important;
}

.schema-scaffolder-dialog .el-dialog__title {
  font-size: 14.5px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

.schema-scaffolder-dialog .el-dialog__body {
  padding: 14px 18px 16px 18px !important;
}
</style>
