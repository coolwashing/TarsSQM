<template>
  <DrawerContainer
    v-model="visible"
    :title="task?.title || '任务详情'"
    :sub-title="task?.task_code || ''"
    width="820px"
    :loading="loading"
    submit-text="保存更改"
    cancel-text="关闭"
    @submit="handleSave"
    @cancel="handleClose"
  >
    <div class="task-detail-body" v-if="task">
      <!-- 1. 顶部源头穿透与核心状态胶囊条 -->
      <div class="task-hero-banner">
        <!-- 业务源头指示条 -->
        <div class="source-info-bar">
          <span class="source-type-pill" :class="(task.source_type || 'custom').toLowerCase()">
            {{ getSourceIcon(task.source_type) }} {{ getSourceName(task.source_type) }}
          </span>
          <span class="source-title-text" :title="task.source_title || '通用待办'">
            {{ task.source_title || '通用自建质量协同任务' }}
          </span>
          <el-button
            v-if="task.source_url"
            size="small"
            type="primary"
            link
            class="jump-source-btn"
            @click="jumpToSource(task.source_url)"
          >
            直达原业务 ➔
          </el-button>
        </div>

        <!-- 状态与优先级快速调节栏 -->
        <div class="status-priority-bar">
          <div class="bar-item">
            <span class="bar-label">当前流转状态：</span>
            <el-select
              v-model="formData.status"
              size="small"
              class="status-select"
              @change="handleStatusQuickChange"
            >
              <el-option label="待办" value="TODO" />
              <el-option label="进行中" value="IN_PROGRESS" />
              <el-option label="待复核" value="PENDING_REVIEW" />
              <el-option label="已闭环" value="DONE" />
              <el-option label="已阻塞" value="BLOCKED" />
            </el-select>
          </div>

          <div class="bar-item">
            <span class="bar-label">优先级：</span>
            <el-select v-model="formData.priority" size="small" class="priority-select">
              <el-option label="🟢 普通" value="MEDIUM" />
              <el-option label="🟡 重点关注" value="HIGH" />
              <el-option label="🔴 紧急红线" value="URGENT" />
              <el-option label="⚪ 低优先级" value="LOW" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 2. 人员、时间与标签元数据网格 -->
      <div class="meta-field-grid">
        <div class="grid-cell">
          <span class="field-title">责任工程师</span>
          <el-input
            v-model="formData.assignee_name"
            placeholder="指派责任人姓名 (如: 张工 SQE)"
            size="small"
            clearable
          />
        </div>

        <div class="grid-cell">
          <span class="field-title">计划开始日期</span>
          <el-date-picker
            v-model="formData.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择起期"
            size="small"
            style="width: 100%"
          />
        </div>

        <div class="grid-cell">
          <span class="field-title">计划截止日期</span>
          <div class="due-date-wrapper">
            <el-date-picker
              v-model="formData.due_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择止期"
              size="small"
              style="width: 100%"
            />
            <span v-if="task.is_overdue" class="overdue-tag">⚠️ 已超期</span>
          </div>
        </div>

        <div class="grid-cell full-width">
          <span class="field-title">标签属性 (分类检索)</span>
          <div class="tags-row">
            <el-tag
              v-for="(tag, idx) in formData.tags"
              :key="idx"
              closable
              size="small"
              class="meta-tag-item"
              @close="removeTag(idx)"
            >
              {{ tag }}
            </el-tag>
            <el-input
              v-if="inputTagVisible"
              ref="tagInputRef"
              v-model="inputTagValue"
              size="small"
              class="add-tag-input"
              @keyup.enter="confirmAddTag"
              @blur="confirmAddTag"
            />
            <el-button v-else size="small" class="add-tag-btn" @click="showTagInput">
              + 添加标签
            </el-button>
          </div>
        </div>
      </div>

      <!-- 3. 任务要求与验收 Checklist (100% 复用 Tiptap 富文本) -->
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">
            <span>📝 任务描述与验收标准 (Checklist)</span>
          </span>
          <span class="section-hint">支持任务清单勾选、数据表格排版与质检截图直接粘贴</span>
        </div>
        <div class="tiptap-editor-stage">
          <TiptapEditor
            v-model="formData.description_html"
            placeholder="输入针对本任务的具体技术要求、CAPA对策条目或验收准则，支持在正文内勾选复选框..."
            :show-ai="false"
          />
        </div>
      </div>

      <!-- 4. 任务附件体系 (100% 复用 sys_attachment 与免下载直开) -->
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">
            <span>📎 关联质量附件清单 ({{ task.attachments?.length || 0 }})</span>
          </span>
          <!-- 隐藏上传 input -->
          <input
            type="file"
            ref="fileInputRef"
            style="display: none"
            multiple
            @change="handleFileUpload"
          />
          <el-button
            size="small"
            type="primary"
            :loading="uploading"
            @click="triggerUpload"
          >
            + 上传附件
          </el-button>
        </div>

        <!-- 附件卡片列表 -->
        <div class="attachments-list" v-if="task.attachments && task.attachments.length > 0">
          <div
            v-for="att in task.attachments"
            :key="att.id"
            class="attachment-card"
          >
            <div class="att-icon-box">
              <span class="file-ext-icon">{{ getFileIcon(att.original_name) }}</span>
            </div>
            <div class="att-info-box">
              <span class="att-name" :title="att.original_name">{{ att.original_name }}</span>
              <div class="att-meta">
                <span>{{ formatFileSize(att.file_size) }}</span>
                <span class="meta-dot">·</span>
                <span>{{ formatDate(att.created_at) }}</span>
              </div>
            </div>
            <div class="att-actions">
              <el-button
                size="small"
                link
                type="primary"
                @click="previewAttachment(att)"
              >
                👁️ 在线查阅
              </el-button>
              <el-button
                size="small"
                link
                type="info"
                @click="downloadAttachment(att)"
              >
                📥 下载
              </el-button>
            </div>
          </div>
        </div>

        <!-- 附件空状态支持拖入 -->
        <div
          v-else
          class="attachment-drop-box"
          @click="triggerUpload"
        >
          <span class="drop-icon">📂</span>
          <p class="drop-text">暂无附件，点击或拖拽 Excel尺寸表 / PDF报告 / 质检照片 至此上传</p>
          <p class="drop-hint">文件统一入库至系统附件池，支持在浏览器免下载就地直开</p>
        </div>
      </div>
    </div>

    <!-- 底部辅助按钮 -->
    <template #footer-left>
      <el-button
        v-if="task && task.status !== 'DONE'"
        type="success"
        plain
        size="small"
        @click="markCompleted"
      >
        ✓ 一键标记为已闭环
      </el-button>
    </template>

    <!-- 原生免下载图片全屏灯箱 (Lightbox) -->
    <el-image-viewer
      v-if="lightboxVisible"
      :url-list="lightboxUrls"
      :initial-index="0"
      @close="lightboxVisible = false"
    />

    <!-- 免下载即时直开附件预览模态窗 -->
    <AttachmentPreviewModal
      v-model="previewModalVisible"
      :attachment="activeAttachment"
    />
  </DrawerContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DrawerContainer from '@/components/common/DrawerContainer.vue'
import TiptapEditor from '@/components/editor/TiptapEditor.vue'
import AttachmentPreviewModal from './AttachmentPreviewModal.vue'
import { taskApi } from '@/api/task'
import type { TaskItem, TaskAttachmentItem, TaskStatus } from '@/types/task'

const props = defineProps<{
  modelValue: boolean
  taskId?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'refresh'): void
}>()

const router = useRouter()
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const task = ref<TaskItem | null>(null)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

// 标签动态增删
const inputTagVisible = ref(false)
const inputTagValue = ref('')
const tagInputRef = ref<HTMLInputElement | null>(null)

// 图片免下载灯箱
const lightboxVisible = ref(false)
const lightboxUrls = ref<string[]>([])

// 免下载多格式直开预览
const previewModalVisible = ref(false)
const activeAttachment = ref<TaskAttachmentItem | null>(null)

const formData = reactive({
  title: '',
  description_html: '',
  status: 'TODO' as TaskStatus,
  priority: 'MEDIUM',
  assignee_name: '',
  start_date: null as string | null,
  due_date: null as string | null,
  tags: [] as string[]
})

// 加载任务详细信息
const loadTaskDetail = async (id: number) => {
  try {
    loading.value = true
    const res = await taskApi.getTaskDetail(id)
    task.value = res
    formData.title = res.title || ''
    formData.description_html = res.description_html || ''
    formData.status = res.status
    formData.priority = res.priority
    formData.assignee_name = res.assignee_name || ''
    formData.start_date = res.start_date || null
    formData.due_date = res.due_date || null
    formData.tags = Array.isArray(res.tags) ? [...res.tags] : []
  } catch (err: any) {
    ElMessage.error(`获取任务详情失败: ${err.message || '网络异常'}`)
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.taskId],
  ([v, id]) => {
    if (v && id) {
      loadTaskDetail(id as number)
    } else {
      task.value = null
    }
  },
  { immediate: true }
)

const handleClose = () => {
  visible.value = false
}

// 快速变更流转状态
const handleStatusQuickChange = async () => {
  if (!task.value) return
  try {
    await taskApi.updateStatus(task.value.id, formData.status)
    ElMessage.success(`状态已切换至【${getStatusLabel(formData.status)}】`)
    emit('refresh')
  } catch (err: any) {
    ElMessage.error('状态更新失败')
  }
}

// 保存整体修改
const handleSave = async () => {
  if (!task.value) return
  try {
    loading.value = true
    await taskApi.updateTask(task.value.id, {
      title: formData.title,
      description_html: formData.description_html,
      status: formData.status,
      priority: formData.priority as any,
      assignee_name: formData.assignee_name,
      start_date: formData.start_date,
      due_date: formData.due_date,
      tags: formData.tags
    })
    ElMessage.success('任务信息已保存')
    emit('refresh')
    handleClose()
  } catch (err: any) {
    ElMessage.error(`保存失败: ${err.message || '服务异常'}`)
  } finally {
    loading.value = false
  }
}

// 一键标记闭环
const markCompleted = async () => {
  if (!task.value) return
  try {
    await taskApi.updateStatus(task.value.id, 'DONE')
    formData.status = 'DONE'
    if (task.value) task.value.status = 'DONE'
    ElMessage.success('任务已标记为【已闭环】')
    emit('refresh')
  } catch {
    ElMessage.error('操作失败')
  }
}

// 标签操作
const showTagInput = () => {
  inputTagVisible.value = true
  nextTick(() => {
    tagInputRef.value?.focus()
  })
}
const confirmAddTag = () => {
  const val = inputTagValue.value.trim()
  if (val && !formData.tags.includes(val)) {
    formData.tags.push(val)
  }
  inputTagValue.value = ''
  inputTagVisible.value = false
}
const removeTag = (index: number) => {
  formData.tags.splice(index, 1)
}

// 业务源头回跳
const jumpToSource = (url: string) => {
  router.push(url)
}

// 附件管理 (直接调用已有 /api/storage)
const triggerUpload = () => {
  fileInputRef.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || !files.length || !task.value) return

  try {
    uploading.value = true
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const fd = new FormData()
      fd.append('file', file)
      fd.append('biz_type', 'task')
      fd.append('biz_id', String(task.value.id))
      await axios.post('/api/storage/upload', fd)
    }
    ElMessage.success('附件上传入库成功')
    await loadTaskDetail(task.value.id)
    emit('refresh')
  } catch (err: any) {
    ElMessage.error(`附件上传失败: ${err.message || '网络异常'}`)
  } finally {
    uploading.value = false
    target.value = ''
  }
}

const previewAttachment = (att: TaskAttachmentItem) => {
  activeAttachment.value = att
  previewModalVisible.value = true
}

const downloadAttachment = (att: TaskAttachmentItem) => {
  const url = `/api/storage/download/${att.id}`
  const a = document.createElement('a')
  a.href = url
  a.download = att.original_name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// 辅助方法
const getSourceIcon = (type: string) => {
  const map: Record<string, string> = {
    SUPPLIER: '🏢',
    PART: '⚙️',
    CTQ: '🎯',
    DOC_KB: '📑',
    CUSTOM: '📋'
  }
  return map[type] || '📌'
}

const getSourceName = (type: string) => {
  const map: Record<string, string> = {
    SUPPLIER: '供应商业务',
    PART: '零件试产',
    CTQ: '关键质量特性',
    DOC_KB: '质量规程',
    CUSTOM: '自建协同'
  }
  return map[type] || '协同任务'
}

const getStatusLabel = (s: string) => {
  const map: Record<string, string> = {
    TODO: '待办',
    IN_PROGRESS: '进行中',
    PENDING_REVIEW: '待复核验收',
    DONE: '已闭环',
    BLOCKED: '已阻塞'
  }
  return map[s] || s
}

const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['xlsx', 'xls', 'csv'].includes(ext)) return '📊'
  if (['doc', 'docx'].includes(ext)) return '📄'
  if (['pdf'].includes(ext)) return '📕'
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) return '🖼️'
  return '📁'
}

const formatFileSize = (bytes: number) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return dateStr.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
.task-detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

/* 顶部源头穿透横幅 */
.task-hero-banner {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.source-type-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e2e8f0;
  color: #334155;
}
.source-type-pill.supplier {
  background: #eff6ff;
  color: #1d4ed8;
}
.source-type-pill.part {
  background: #f0fdf4;
  color: #15803d;
}
.source-type-pill.ctq {
  background: #fef2f2;
  color: #b91c1c;
}
.source-type-pill.doc_kb {
  background: #faf5ff;
  color: #7e22ce;
}

.source-title-text {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.jump-source-btn {
  font-size: 12px;
  font-weight: 500;
}

/* 状态与优先级栏 */
.status-priority-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}
.bar-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.bar-label {
  font-size: 12px;
  color: #64748b;
}
.status-select {
  width: 170px;
}
.priority-select {
  width: 150px;
}

/* 元数据网格 */
.meta-field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  background: #ffffff;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 12px;
}
.grid-cell {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.grid-cell.full-width {
  grid-column: span 3;
}
.field-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #475569;
}
.due-date-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.overdue-tag {
  position: absolute;
  right: 8px;
  font-size: 10px;
  color: #ef4444;
  font-weight: bold;
  pointer-events: none;
}

/* 标签行 */
.tags-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.meta-tag-item {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #334155;
}
.add-tag-input {
  width: 90px;
}
.add-tag-btn {
  font-size: 11px;
}

/* 卡片容器 */
.section-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.section-hint {
  font-size: 11px;
  color: #94a3b8;
}

/* Tiptap 富文本嵌入容器 */
.tiptap-editor-stage {
  min-height: 200px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

/* 附件卡片列表 */
.attachments-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.attachment-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  transition: all 0.12s ease;
}
.attachment-card:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}
.att-icon-box {
  font-size: 20px;
  flex-shrink: 0;
}
.att-info-box {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.att-name {
  font-size: 12.5px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.att-meta {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
}
.meta-dot {
  opacity: 0.5;
}
.att-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 拖拽上传空状态 */
.attachment-drop-box {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  background: #fafbfc;
  transition: all 0.15s ease;
}
.attachment-drop-box:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}
.drop-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
}
.drop-text {
  font-size: 12.5px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
}
.drop-hint {
  font-size: 11px;
  color: #94a3b8;
}
</style>
