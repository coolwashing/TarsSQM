<template>
  <el-dialog
    v-model="visible"
    title="编辑字段属性"
    width="480px"
    destroy-on-close
    append-to-body
    class="column-config-dialog"
  >
    <div v-if="editingCol" class="dialog-body">
      <!-- 基础属性 -->
      <div class="form-section">
        <label class="form-label">字段显示名称</label>
        <el-input v-model="form.label" placeholder="输入字段名称" maxlength="30" show-word-limit />
      </div>

      <div class="form-section">
        <label class="form-label">字段类型</label>
        <el-select v-model="form.editType" style="width: 100%" placeholder="选择类型">
          <el-option label="单选标签" value="select" />
          <el-option label="多选标签" value="multi-select" />
          <el-option label="单行文本" value="input" />
          <el-option label="数值" value="number" />
          <el-option label="日期/时间" value="date" />
        </el-select>
      </div>

      <!-- 日期/时间格式配置 -->
      <div v-if="isDateColumn" class="form-section">
        <div class="form-head-with-tip">
          <label class="form-label">日期时间显示格式</label>
          <span class="preview-badge">效果: {{ getFormatPreview(form.dateFormat) }}</span>
        </div>
        <el-select v-model="form.dateFormat" style="width: 100%" placeholder="选择时间显示格式">
          <el-option label="仅日期: YYYY-MM-DD (例如 2026-11-03) [默认推荐]" value="YYYY-MM-DD" />
          <el-option label="完整时间: YYYY-MM-DD HH:mm:ss (例如 2026-11-03 06:55:28)" value="YYYY-MM-DD HH:mm:ss" />
          <el-option label="年月日时分: YYYY-MM-DD HH:mm (例如 2026-11-03 06:55)" value="YYYY-MM-DD HH:mm" />
          <el-option label="简短日期: MM-DD (例如 11-03)" value="MM-DD" />
          <el-option label="相对时间: (如 刚刚 / 2小时前 / 昨天)" value="relative" />
        </el-select>
      </div>

      <!-- 单选/多选专用选项列表配置 -->
      <div v-if="form.editType === 'select' || form.editType === 'multi-select'" class="options-section">
        <div class="options-head">
          <label class="form-label">选项列表</label>
          <el-button type="primary" link size="small" :icon="Plus" @click="addOption">
            添加选项
          </el-button>
        </div>

        <div class="options-list">
          <div
            v-for="(opt, idx) in form.options"
            :key="idx"
            class="option-row"
          >
            <!-- 颜色圆点选择器 -->
            <el-popover placement="bottom" :width="160" trigger="click">
              <template #reference>
                <div
                  class="color-dot-trigger"
                  :style="{ backgroundColor: getOptionColorHex(opt.color) }"
                  title="切换颜色"
                />
              </template>
              <div class="palette-grid">
                <div
                  v-for="c in feishuPalette"
                  :key="c.name"
                  class="palette-item"
                  :style="{ backgroundColor: c.hex }"
                  :title="c.label"
                  @click="opt.color = c.name"
                >
                  <el-icon v-if="opt.color === c.name || (!opt.color && c.name === 'primary')" class="palette-check">
                    <Check />
                  </el-icon>
                </div>
              </div>
            </el-popover>

            <!-- 选项名称输入框 -->
            <el-input
              v-model="opt.label"
              size="small"
              placeholder="选项名称"
              class="opt-name-input"
              @input="onOptionLabelChange(opt)"
            />

            <!-- 操作动作：上下移动与删除 -->
            <div class="opt-actions">
              <el-button
                link
                size="small"
                :icon="Top"
                :disabled="idx === 0"
                @click="moveOption(idx, -1)"
              />
              <el-button
                link
                size="small"
                :icon="Bottom"
                :disabled="idx === form.options.length - 1"
                @click="moveOption(idx, 1)"
              />
              <el-button
                link
                type="danger"
                size="small"
                :icon="Delete"
                @click="removeOption(idx)"
              />
            </div>
          </div>

          <div v-if="form.options.length === 0" class="empty-options-hint">
            暂无选项，点击右上角【添加选项】
          </div>
        </div>

        <!-- 自由新增选项开关 (简洁无废话) -->
        <div class="allow-create-box">
          <el-switch v-model="form.allowCreate" />
          <span class="ac-title">允许在表格中直接输入新增选项</span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存并应用</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { Plus, Check, Top, Bottom, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { TableColumn, TableOptionItem } from '../types'

const props = defineProps<{
  modelValue: boolean
  column: TableColumn | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'save', payload: { prop: string; changes: Partial<TableColumn> }): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const editingCol = computed(() => props.column)

// 8 种高识别度精选色彩
const feishuPalette = [
  { name: 'primary', hex: '#2563eb', label: '蓝色' },
  { name: 'success', hex: '#16a34a', label: '绿色' },
  { name: 'warning', hex: '#d97706', label: '黄色' },
  { name: 'danger', hex: '#dc2626', label: '红色' },
  { name: 'purple', hex: '#9333ea', label: '紫色' },
  { name: 'cyan', hex: '#0891b2', label: '青色' },
  { name: 'orange', hex: '#ea580c', label: '橙色' },
  { name: 'info', hex: '#64748b', label: '灰色' }
]

const getOptionColorHex = (colorName?: string) => {
  const match = feishuPalette.find(c => c.name === colorName)
  return match ? match.hex : '#2563eb'
}

import { formatDate } from '@/utils/format'

interface FormOptionItem {
  label: string
  value: any
  color: string
}

const form = reactive<{
  label: string
  editType: 'input' | 'number' | 'select' | 'multi-select' | 'date'
  dateFormat: string
  allowCreate: boolean
  options: FormOptionItem[]
}>({
  label: '',
  editType: 'input',
  dateFormat: 'YYYY-MM-DD',
  allowCreate: true,
  options: []
})

const isDateColumn = computed(() => {
  if (form.editType === 'date') return true
  if (editingCol.value) {
    const col = editingCol.value
    if (col.dataType === 'date' || col.dataType === 'datetime') return true
    if (col.prop.endsWith('_at') || col.prop.endsWith('_date') || col.prop === 'sop_date') return true
  }
  return false
})

const getFormatPreview = (pattern?: string) => {
  return formatDate(new Date(), pattern || 'YYYY-MM-DD')
}

// 初始化表单数据
const initForm = (col: TableColumn) => {
  form.label = col.label || ''
  const isDate = col.dataType === 'date' || col.dataType === 'datetime' || col.editType === 'date' || col.prop.endsWith('_at') || col.prop.endsWith('_date') || col.prop === 'sop_date'
  form.editType = col.editType || (col.options ? 'select' : isDate ? 'date' : 'input')
  form.dateFormat = col.dateFormat || 'YYYY-MM-DD'
  form.allowCreate = col.allowCreate !== false

  const rawOpts = col.options || col.editOptions || []
  form.options = rawOpts.map((it, idx) => {
    if (typeof it === 'string') {
      const color = feishuPalette[idx % feishuPalette.length].name
      return { label: it, value: it, color }
    }
    return {
      label: it.label || String(it.value),
      value: it.value,
      color: it.color || feishuPalette[idx % feishuPalette.length].name
    }
  })
}

// 监听弹窗打开并初始化
watch(
  () => props.column,
  newCol => {
    if (newCol) {
      initForm(newCol)
    }
  },
  { immediate: true }
)

const addOption = () => {
  const count = form.options.length + 1
  const color = feishuPalette[(count - 1) % feishuPalette.length].name
  form.options.push({
    label: `新选项 ${count}`,
    value: `新选项 ${count}`,
    color
  })
}

const onOptionLabelChange = (opt: FormOptionItem) => {
  opt.value = opt.label
}

const moveOption = (index: number, delta: number) => {
  const target = index + delta
  if (target < 0 || target >= form.options.length) return
  const item = form.options.splice(index, 1)[0]
  form.options.splice(target, 0, item)
}

const removeOption = (index: number) => {
  form.options.splice(index, 1)
}

const handleSave = () => {
  if (!editingCol.value) return
  if (!form.label.trim()) {
    ElMessage.warning('字段显示名称不能为空')
    return
  }

  // 构建更新 payload
  const colorMap: Record<string, string> = {}
  const cleanOptions: TableOptionItem[] = []

  form.options.forEach(opt => {
    const val = opt.label.trim()
    if (val) {
      cleanOptions.push({
        label: val,
        value: val,
        color: opt.color
      })
      colorMap[val] = opt.color
    }
  })

  const changes: Partial<TableColumn> = {
    label: form.label.trim(),
    editable: editingCol.value.editable ?? (form.editType !== 'date'),
    editType: form.editType,
    dateFormat: form.dateFormat,
    allowCreate: form.allowCreate,
    options: cleanOptions,
    colorMap
  }

  emit('save', {
    prop: editingCol.value.prop,
    changes
  })

  visible.value = false
  ElMessage.success(`字段【${form.label}】属性与格式已更新生效`)
}
</script>

<style scoped>
.column-config-dialog :deep(.el-dialog__body) {
  padding: 16px 20px;
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.form-head-with-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-badge {
  font-size: 11.5px;
  color: #2563eb;
  background-color: #eff6ff;
  border: 1px solid #dbeafe;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.options-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.options-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 4px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: #ffffff;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.color-dot-trigger {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  cursor: pointer;
  flex-shrink: 0;
  border: 2px solid #ffffff;
  box-shadow: 0 0 0 1px #cbd5e1;
  transition: transform 0.12s ease;
}

.color-dot-trigger:hover {
  transform: scale(1.15);
}

.opt-name-input {
  flex: 1;
}

.opt-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.palette-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 4px;
}

.palette-item {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 14px;
  transition: transform 0.12s ease;
}

.palette-item:hover {
  transform: scale(1.12);
}

.empty-options-hint {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  padding: 16px 0;
}

.allow-create-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}

.allow-create-info {
  display: flex;
  flex-direction: column;
}

.ac-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.ac-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
