<template>
  <el-dialog
    :model-value="modelValue"
    :title="`批量导入 - ${title || '数据列表'}`"
    width="920px"
    destroy-on-close
    append-to-body
    class="excel-import-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="import-dialog-body">
      <!-- 步骤 1: 模板指引与下载栏 -->
      <div class="step-card template-guide-card">
        <div class="guide-content">
          <div class="guide-icon-wrapper">
            <el-icon class="guide-icon"><Document /></el-icon>
          </div>
          <div class="guide-text">
            <div class="guide-title">步骤 1：下载标准录入模板</div>
            <div class="guide-desc">
              请务必使用系统生成的 Excel 模板填报数据。模板内已预置字段规范、必填项（标星号*）及下拉校验。
            </div>
          </div>
        </div>
        <el-button
          type="primary"
          plain
          :icon="Download"
          :loading="downloadingTemplate"
          class="download-btn"
          @click="handleDownloadTemplate"
        >
          下载Excel规范模板
        </el-button>
      </div>

      <!-- 步骤 2: 文件上传区 (尚未解析完成时突出显示) -->
      <div v-if="!report" class="step-card upload-card">
        <div class="upload-header">
          <span class="upload-title">步骤 2：上传填报完成的 Excel 文件</span>
          <span class="upload-sub">支持 .xlsx / .xls 格式，自动执行 5 层深度规则与排重校验</span>
        </div>

        <el-upload
          drag
          action="#"
          :auto-upload="false"
          :show-file-list="false"
          accept=".xlsx, .xls"
          class="custom-dropzone"
          :disabled="validating"
          @change="handleFileSelected"
        >
          <div v-if="!validating" class="dropzone-content">
            <el-icon class="dropzone-icon"><UploadFilled /></el-icon>
            <div class="dropzone-main-text">将 Excel 文件拖拽到此处，或 <em>点击选取文件上传</em></div>
            <div class="dropzone-hint">
              系统将自动扫描空行、检验必填项、校验枚举值、匹配外键关联并进行库内查重
            </div>
          </div>
          <div v-else class="validating-box">
            <el-icon class="is-loading loading-icon"><Loading /></el-icon>
            <div class="validating-title">正在进行深度规则与排重校验...</div>
            <div class="validating-sub">正在比对关联主数据与数据库唯一性限制</div>
          </div>
        </el-upload>
      </div>

      <!-- 步骤 3: 校验结果报告与纠错视检区 -->
      <div v-else class="step-card report-card">
        <!-- 概览指标卡片条 -->
        <div class="report-metrics-bar">
          <div class="metric-item total">
            <span class="metric-label">解析总行数</span>
            <span class="metric-value">{{ report.total_rows }}</span>
          </div>
          <div class="metric-item valid">
            <span class="metric-label">校验通过 (可入库)</span>
            <span class="metric-value">{{ report.valid_rows_count }}</span>
          </div>
          <div class="metric-item invalid">
            <span class="metric-label">校验失败 (待修正)</span>
            <span class="metric-value">{{ report.invalid_rows_count }}</span>
          </div>

          <div class="filter-switch-area">
            <el-radio-group v-model="filterMode" size="small">
              <el-radio-button label="ALL">全部行 ({{ report.total_rows }})</el-radio-button>
              <el-radio-button label="INVALID">
                仅看异常 ({{ report.invalid_rows_count }})
              </el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <!-- 异常提示条 -->
        <el-alert
          v-if="report.invalid_rows_count > 0"
          type="warning"
          :closable="false"
          show-icon
          class="invalid-alert"
        >
          <template #title>
            检测到 {{ report.invalid_rows_count }} 行数据存在格式或关联关系异常。您可以选择重新上传，或跳过异常数据仅导入合规的 {{ report.valid_rows_count }} 条记录。
          </template>
        </el-alert>

        <!-- 行级明细表格 -->
        <div class="table-container">
          <el-table
            :data="displayedRows"
            border
            stripe
            size="small"
            max-height="360"
            class="report-table"
          >
            <el-table-column
              prop="row_num"
              label="Excel行号"
              width="90"
              align="center"
              fixed="left"
            >
              <template #default="{ row }">
                <span class="row-num-badge">第 {{ row.row_num }} 行</span>
              </template>
            </el-table-column>

            <el-table-column
              label="校验状态"
              width="100"
              align="center"
              fixed="left"
            >
              <template #default="{ row }">
                <el-tag
                  v-if="row.is_valid"
                  type="success"
                  size="small"
                  effect="light"
                  class="status-tag"
                >
                  <el-icon><Check /></el-icon> 合规
                </el-tag>
                <el-tag
                  v-else
                  type="danger"
                  size="small"
                  effect="light"
                  class="status-tag"
                >
                  <el-icon><Close /></el-icon> 异常
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column
              label="异常原因 / 校验反馈"
              min-width="240"
              fixed="left"
            >
              <template #default="{ row }">
                <div v-if="row.is_valid" class="text-success-hint">
                  <el-icon><CircleCheckFilled /></el-icon> 校验通过，就绪入库
                </div>
                <div v-else class="error-messages-list">
                  <div
                    v-for="(err, idx) in row.errors"
                    :key="idx"
                    class="error-message-item"
                  >
                    <el-icon class="err-icon"><WarningFilled /></el-icon>
                    <span>{{ err }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 动态数据列回显 -->
            <el-table-column
              v-for="col in report.columns"
              :key="col.prop"
              :prop="col.prop"
              :label="col.label"
              min-width="140"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span :class="{ 'cell-error-highlight': !row.is_valid && hasFieldError(row, col.label) }">
                  {{ row.raw_data[col.prop] || '-' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 底部操作按钮 -->
    <template #footer>
      <div class="dialog-footer-layout">
        <div class="footer-left-info">
          <span v-if="report && report.valid_rows_count > 0" class="ready-badge">
            已准备好 {{ report.valid_rows_count }} 条合规数据待入库
          </span>
        </div>

        <div class="footer-right-actions">
          <el-button @click="handleClose">取消</el-button>

          <!-- 重新上传按钮 -->
          <el-button
            v-if="report"
            :icon="RefreshRight"
            @click="handleResetFile"
          >
            重新选择文件
          </el-button>

          <!-- 批量提交入库按钮 -->
          <el-button
            v-if="report"
            type="primary"
            :icon="Check"
            :loading="committing"
            :disabled="report.valid_rows_count === 0"
            @click="handleCommit"
          >
            确认批量导入 ({{ report.valid_rows_count }} 条)
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download,
  UploadFilled,
  Document,
  Loading,
  Check,
  Close,
  CircleCheckFilled,
  WarningFilled,
  RefreshRight
} from '@element-plus/icons-vue'

interface ColumnMeta {
  prop: string
  label: string
}

interface RowItem {
  row_num: number
  is_valid: boolean
  errors: string[]
  raw_data: Record<string, any>
  clean_data: Record<string, any>
}

interface ValidationReport {
  biz_key: string
  title: string
  total_rows: number
  valid_rows_count: number
  invalid_rows_count: number
  columns: ColumnMeta[]
  rows: RowItem[]
}

const props = defineProps<{
  modelValue: boolean
  bizKey: string
  title?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'success'): void
}>()

const downloadingTemplate = ref(false)
const validating = ref(false)
const committing = ref(false)
const report = ref<ValidationReport | null>(null)
const filterMode = ref<'ALL' | 'INVALID'>('ALL')

// 根据筛选项过滤展示行
const displayedRows = computed(() => {
  if (!report.value) return []
  if (filterMode.value === 'INVALID') {
    return report.value.rows.filter(r => !r.is_valid)
  }
  return report.value.rows
})

// 字段是否属于异常字段
const hasFieldError = (row: RowItem, label: string) => {
  return row.errors.some(e => e.includes(`【${label}】`))
}

// 步骤 1: 下载 Excel 模板
const handleDownloadTemplate = async () => {
  downloadingTemplate.value = true
  try {
    const res = await axios.get(`/api/excel/template/${props.bizKey}`, {
      responseType: 'blob'
    })

    // 解析文件名
    let filename = `SQM_${props.title || '数据'}_导入模板.xlsx`
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

    ElMessage.success('模板下载就绪，请填写后上传')
  } catch (err: any) {
    ElMessage.error(`下载模板失败: ${err.message || '网络连接异常'}`)
  } finally {
    downloadingTemplate.value = false
  }
}

// 步骤 2: 选择文件并上传至校验端点
const handleFileSelected = async (fileObj: any) => {
  const file = fileObj.raw || fileObj
  if (!file) return

  const isExcel =
    file.name.endsWith('.xlsx') ||
    file.name.endsWith('.xls') ||
    file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    file.type === 'application/vnd.ms-excel'

  if (!isExcel) {
    ElMessage.error('仅支持上传 .xlsx 或 .xls 格式的标准 Excel 文件')
    return
  }

  validating.value = true
  report.value = null

  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await axios.post(`/api/excel/validate/${props.bizKey}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    report.value = res.data

    if (res.data.total_rows === 0) {
      ElMessage.warning('上传的 Excel 文件内未检测到有效数据行')
    } else if (res.data.invalid_rows_count === 0) {
      ElMessage.success(`校验通过！全部 ${res.data.total_rows} 行数据格式合规，可直接入库`)
    } else {
      ElMessage.warning(`校验完成：发现 ${res.data.invalid_rows_count} 行存在异常，请核对下方报告`)
    }
  } catch (err: any) {
    ElMessage.error(`数据校验失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    validating.value = false
  }
}

// 重新选择文件
const handleResetFile = () => {
  report.value = null
  filterMode.value = 'ALL'
}

// 步骤 3: 确认提交入库
const handleCommit = async () => {
  if (!report.value || report.value.valid_rows_count === 0) return

  const validRows = report.value.rows.filter(r => r.is_valid)

  if (report.value.invalid_rows_count > 0) {
    try {
      await ElMessageBox.confirm(
        `当前 Excel 文件中包含 ${report.value.invalid_rows_count} 条异常记录。确定忽略异常记录并仅将 ${validRows.length} 条有效数据写入数据库吗？`,
        '部分数据存在异常确认',
        {
          confirmButtonText: '确认仅导入有效数据',
          cancelButtonText: '暂缓导入（修正后再传）',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  committing.value = true
  try {
    const res = await axios.post(`/api/excel/commit/${props.bizKey}`, {
      rows: validRows
    })

    ElMessage.success(res.data.message || `成功导入 ${validRows.length} 条数据`)
    emit('success')
    emit('update:modelValue', false)
    report.value = null
  } catch (err: any) {
    ElMessage.error(`数据导入失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    committing.value = false
  }
}

const handleClose = () => {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.import-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

/* 步骤通用卡片 */
.step-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background-color: #fafafa;
  padding: 16px;
  transition: all 0.2s ease;
}

/* 模板指引卡片 */
.template-guide-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f4ff 100%);
  border-color: #bae0ff;
}

.guide-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.guide-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background-color: #1677ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 22px;
}

.guide-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.guide-desc {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.4;
}

.download-btn {
  font-weight: 500;
  white-space: nowrap;
}

/* 上传卡片 */
.upload-card {
  background: #ffffff;
  border: 1px dashed #d9d9d9;
}

.upload-header {
  margin-bottom: 12px;
}

.upload-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  display: inline-block;
  margin-right: 8px;
}

.upload-sub {
  font-size: 12px;
  color: #8c8c8c;
}

.custom-dropzone :deep(.el-upload-dragger) {
  padding: 30px 20px;
  border-radius: 8px;
  background-color: #fbfcfe;
}

.custom-dropzone :deep(.el-upload-dragger:hover) {
  border-color: #1677ff;
  background-color: #f0f7ff;
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dropzone-icon {
  font-size: 48px;
  color: #1677ff;
  margin-bottom: 8px;
}

.dropzone-main-text {
  font-size: 14px;
  color: #374151;
  margin-bottom: 6px;
}

.dropzone-main-text em {
  color: #1677ff;
  font-style: normal;
  font-weight: 600;
  text-decoration: underline;
}

.dropzone-hint {
  font-size: 12px;
  color: #9ca3af;
}

.validating-box {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.loading-icon {
  font-size: 36px;
  color: #1677ff;
  margin-bottom: 12px;
}

.validating-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.validating-sub {
  font-size: 13px;
  color: #6b7280;
}

/* 校验报告卡片 */
.report-card {
  background: #ffffff;
  padding: 12px;
}

.report-metrics-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background-color: #f8fafc;
  border-radius: 6px;
  margin-bottom: 12px;
}

.metric-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-label {
  font-size: 13px;
  color: #64748b;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
}

.metric-item.total .metric-value {
  color: #1e293b;
}

.metric-item.valid .metric-value {
  color: #16a34a;
}

.metric-item.invalid .metric-value {
  color: #dc2626;
}

.filter-switch-area {
  margin-left: auto;
}

.invalid-alert {
  margin-bottom: 12px;
}

.table-container {
  border-radius: 4px;
  overflow: hidden;
}

.row-num-badge {
  font-family: monospace;
  font-weight: 600;
  color: #4b5563;
}

.status-tag {
  font-weight: 600;
}

.text-success-hint {
  color: #16a34a;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.error-messages-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.error-message-item {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  color: #dc2626;
  font-size: 12px;
  line-height: 1.3;
}

.err-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

.cell-error-highlight {
  color: #dc2626;
  font-weight: 600;
}

/* 底部操作区 */
.dialog-footer-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ready-badge {
  font-size: 13px;
  color: #16a34a;
  background-color: #f0fdf4;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #bbf7d0;
  font-weight: 500;
}

.footer-right-actions {
  display: flex;
  gap: 10px;
}
</style>
