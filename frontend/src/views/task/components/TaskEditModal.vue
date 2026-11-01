<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑协同任务' : '新建质量协同任务'"
    :sub-title="isEdit ? (formData.task_code || '') : '制造质量跨部门待办'"
    width="70%"
    :loading="saving || loadingDetails"
    :submit-text="isEdit ? '保存更改' : '立即创建'"
    cancel-text="取消"
    @submit="handleSave"
    @cancel="handleClose"
  >
    <div class="task-edit-drawer-content">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-position="right"
        label-width="96px"
        class="task-form-compact"
      >
        <!-- 任务标题 (全宽同行) -->
        <el-form-item label="任务标题" prop="title">
          <el-input
            v-model="formData.title"
            placeholder="请输入清晰的质量待办/整改任务标题..."
            clearable
          />
        </el-form-item>

        <!-- 业务源头 与 源头实体名 (2列同行) -->
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="业务源头" prop="source_type">
              <el-select v-model="formData.source_type" style="width: 100%">
                <el-option label="🏢 供应商清单" value="SUPPLIER" />
                <el-option label="⚙️ 零件开发试产" value="PART" />
                <el-option label="🎯 CTQ 关键特性" value="CTQ" />
                <el-option label="📑 质量规程知识" value="DOC_KB" />
                <el-option label="📋 协同待办" value="CUSTOM" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="源头实体" prop="source_title">
              <div class="source-title-input-row">
                <el-input
                  v-model="formData.source_title"
                  placeholder="如: 苏州精工模具 / 法兰盘"
                  clearable
                />
                <el-button
                  v-if="formData.source_url"
                  link
                  type="primary"
                  size="small"
                  class="jump-source-btn"
                  @click="jumpToSource(formData.source_url)"
                >
                  直达 ↗
                </el-button>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 责任人 与 任务优先级 (2列同行) -->
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="责任人" prop="assignee_name">
              <el-input
                v-model="formData.assignee_name"
                placeholder="指定责任工程师姓名"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="formData.priority" style="width: 100%">
                <el-option label="🟢 普通" value="MEDIUM" />
                <el-option label="🟡 重点关注" value="HIGH" />
                <el-option label="🔴 紧急红线" value="URGENT" />
                <el-option label="⚪ 低优先级" value="LOW" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 计划起止日 (2列同行) -->
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="计划开始">
              <el-date-picker
                v-model="formData.start_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择起始日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划截止" prop="due_date">
              <div class="due-date-row">
                <el-date-picker
                  v-model="formData.due_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择截止日期"
                  style="width: 100%"
                />
                <el-tag v-if="isOverdue" type="danger" size="small" effect="dark" class="overdue-badge">
                  超期
                </el-tag>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 流转状态 (同行) -->
        <el-form-item label="流转状态" prop="status">
          <el-radio-group v-model="formData.status" size="small">
            <el-radio-button value="TODO">待办</el-radio-button>
            <el-radio-button value="IN_PROGRESS">进行中</el-radio-button>
            <el-radio-button value="PENDING_REVIEW">待复核</el-radio-button>
            <el-radio-button value="DONE">已闭环</el-radio-button>
            <el-radio-button value="BLOCKED">已阻塞</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 验收说明与标准 (富文本) -->
        <el-form-item label="验收与说明">
          <div class="tiptap-drawer-editor-box">
            <TiptapEditor
              v-model="formData.description_html"
              placeholder="输入任务具体技术要求、验收清单 Checklist 或改善对策，支持表格与截图直接粘贴..."
              :show-ai="false"
            />
          </div>
        </el-form-item>

        <!-- 关联质量附件 (同行紧凑展示) -->
        <el-form-item v-if="isEdit" label="关联附件">
          <div class="attachments-compact-panel">
            <div class="attachments-compact-bar">
              <span class="att-count-text">共 {{ attachments.length }} 个附件</span>
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
                plain
                :loading="uploading"
                @click="triggerUpload"
              >
                + 上传附件
              </el-button>
            </div>

            <!-- 附件小卡片 -->
            <div v-if="attachments.length > 0" class="attachments-grid">
              <div
                v-for="att in attachments"
                :key="att.id"
                class="attachment-card"
              >
                <span class="att-icon">{{ getFileIcon(att.original_name) }}</span>
                <div class="att-info">
                  <span class="att-name" :title="att.original_name">{{ att.original_name }}</span>
                  <span class="att-meta">{{ formatFileSize(att.file_size) }}</span>
                </div>
                <div class="att-actions">
                  <el-button link type="primary" size="small" @click="previewAttachment(att)">
                    查阅
                  </el-button>
                  <el-button link type="info" size="small" @click="downloadAttachment(att)">
                    下载
                  </el-button>
                  <el-button link type="danger" size="small" @click="deleteAttachment(att.id)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
            <div v-else class="attachments-empty-line">
              <span>暂无关联附件，可点击右侧按钮上传</span>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 底部左侧快捷闭环操作 -->
    <template #footer-left>
      <el-button
        v-if="isEdit && formData.status !== 'DONE'"
        type="success"
        plain
        size="small"
        @click="markCompleted"
      >
        ✓ 一键标记已闭环
      </el-button>
    </template>

    <!-- 原生免下载图片全屏灯箱 -->
    <el-image-viewer
      v-if="lightboxVisible"
      :url-list="lightboxUrls"
      :initial-index="0"
      @close="lightboxVisible = false"
    />

    <!-- 多格式附件在线查阅弹窗 -->
    <AttachmentPreviewModal
      v-model="previewModalVisible"
      :attachment="activeAttachment"
    />
  </DrawerContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import axios from 'axios'
import DrawerContainer from '@/components/common/DrawerContainer.vue'
import TiptapEditor from '@/components/editor/TiptapEditor.vue'
import AttachmentPreviewModal from './AttachmentPreviewModal.vue'
import { taskApi } from '@/api/task'
import type { TaskItem, TaskAttachmentItem, TaskStatus, TaskPriority, TaskSourceType } from '@/types/task'

const props = defineProps<{
  modelValue: boolean
  task?: Partial<TaskItem> | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'saved'): void
}>()

const router = useRouter()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.task?.id)
const formRef = ref<FormInstance>()
const saving = ref(false)
const loadingDetails = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const attachments = ref<TaskAttachmentItem[]>([])

// 图片灯箱与附件查阅弹窗
const lightboxVisible = ref(false)
const lightboxUrls = ref<string[]>([])
const previewModalVisible = ref(false)
const activeAttachment = ref<TaskAttachmentItem | null>(null)

const formData = reactive({
  id: undefined as number | undefined,
  task_code: '',
  title: '',
  source_type: 'CUSTOM' as TaskSourceType,
  source_id: null as string | number | null,
  source_title: '',
  source_url: '',
  assignee_name: '',
  priority: 'MEDIUM' as TaskPriority,
  status: 'TODO' as TaskStatus,
  start_date: null as string | null,
  due_date: null as string | null,
  description_html: ''
})

const formRules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择业务源头', trigger: 'change' }]
}

const isOverdue = computed(() => {
  if (!formData.due_date || formData.status === 'DONE') return false
  const today = new Date().toISOString().split('T')[0]
  return formData.due_date < today
})

// 监听打开与任务对象传入
watch(
  () => props.task,
  async (t) => {
    if (t) {
      formData.id = t.id
      formData.task_code = t.task_code || ''
      formData.title = t.title || ''
      formData.source_type = t.source_type || 'CUSTOM'
      formData.source_id = t.source_id !== undefined ? t.source_id : null
      formData.source_title = t.source_title || ''
      formData.source_url = t.source_url || ''
      formData.assignee_name = t.assignee_name || ''
      formData.priority = t.priority || 'MEDIUM'
      formData.status = t.status || 'TODO'
      formData.start_date = t.start_date || null
      formData.due_date = t.due_date || null
      formData.description_html = t.description_html || ''
      attachments.value = (t.attachments as TaskAttachmentItem[]) || []

      // 若有 ID 则获取服务端完整详情（补充附件等元数据）
      if (t.id) {
        try {
          loadingDetails.value = true
          const full = await taskApi.getTask(t.id)
          formData.task_code = full.task_code || formData.task_code
          formData.description_html = full.description_html || formData.description_html
          formData.source_url = full.source_url || formData.source_url
          attachments.value = full.attachments || []
        } catch {
          // 容错处理
        } finally {
          loadingDetails.value = false
        }
      }
    } else {
      formData.id = undefined
      formData.task_code = ''
      formData.title = ''
      formData.source_type = 'CUSTOM'
      formData.source_id = null
      formData.source_title = ''
      formData.source_url = ''
      formData.assignee_name = ''
      formData.priority = 'MEDIUM'
      formData.status = 'TODO'
      formData.start_date = null
      formData.due_date = null
      formData.description_html = ''
      attachments.value = []
    }
  },
  { immediate: true }
)

const handleClose = () => {
  visible.value = false
}

// 保存修改或创建任务
const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      saving.value = true
      if (isEdit.value && formData.id) {
        await taskApi.updateTask(formData.id, formData)
        ElMessage.success('任务信息已更新')
      } else {
        await taskApi.createTask(formData)
        ElMessage.success('协同任务创建成功')
      }
      emit('saved')
      handleClose()
    } catch (err: any) {
      ElMessage.error(`保存失败: ${err.message || '网络异常'}`)
    } finally {
      saving.value = false
    }
  })
}

// 一键标记为已闭环
const markCompleted = async () => {
  if (!formData.id) return
  try {
    saving.value = true
    await taskApi.updateStatus(formData.id, 'DONE')
    formData.status = 'DONE'
    ElMessage.success('任务已标记为已闭环')
    emit('saved')
  } catch {
    ElMessage.error('状态更新失败')
  } finally {
    saving.value = false
  }
}

// 直达原业务链接
const jumpToSource = (url: string) => {
  if (!url) return
  if (url.startsWith('/')) {
    router.push(url)
  } else {
    window.open(url, '_blank')
  }
}

// 附件上传与管理
const triggerUpload = () => {
  fileInputRef.value?.click()
}

const handleFileUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0 || !formData.id) return
  try {
    uploading.value = true
    for (let i = 0; i < target.files.length; i++) {
      const file = target.files[i]
      const form = new FormData()
      form.append('file', file)
      form.append('entity_type', 'TASK')
      form.append('entity_id', String(formData.id))
      await axios.post('/api/attachments/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    ElMessage.success('附件上传成功')
    const full = await taskApi.getTask(formData.id)
    attachments.value = full.attachments || []
  } catch (err: any) {
    ElMessage.error(`上传失败: ${err.message || '网络异常'}`)
  } finally {
    uploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

const deleteAttachment = async (attId: number) => {
  try {
    await axios.delete(`/api/attachments/${attId}`)
    ElMessage.success('附件已删除')
    if (formData.id) {
      const full = await taskApi.getTask(formData.id)
      attachments.value = full.attachments || []
    }
  } catch {
    ElMessage.error('删除失败')
  }
}

const previewAttachment = (att: TaskAttachmentItem) => {
  const ext = (att.original_name || '').split('.').pop()?.toLowerCase() || ''
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext)) {
    lightboxUrls.value = [`/api/attachments/${att.id}/download`]
    lightboxVisible.value = true
  } else {
    activeAttachment.value = att
    previewModalVisible.value = true
  }
}

const downloadAttachment = (att: TaskAttachmentItem) => {
  const url = `/api/attachments/${att.id}/download`
  window.open(url, '_blank')
}

const formatFileSize = (bytes?: number) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getFileIcon = (filename?: string) => {
  const ext = (filename || '').split('.').pop()?.toLowerCase() || ''
  if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) return '🖼️'
  if (['pdf'].includes(ext)) return '📕'
  if (['doc', 'docx'].includes(ext)) return '📘'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return '📗'
  return '📄'
}
</script>

<style scoped>
.task-edit-drawer-content {
  padding: 12px 18px 20px 18px;
}

/* 标签与输入框同行紧凑排版，行距紧凑防高度虚高 */
.task-form-compact :deep(.el-form-item) {
  margin-bottom: 8px !important;
}

.task-form-compact :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  line-height: 32px;
  padding-right: 10px;
}

.task-form-compact :deep(.el-form-item__content) {
  line-height: 32px;
}

.source-title-input-row,
.due-date-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.jump-source-btn {
  font-size: 12px;
  flex-shrink: 0;
}

.overdue-badge {
  flex-shrink: 0;
}

.tiptap-drawer-editor-box {
  width: 100%;
  height: 250px;
  min-height: 180px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

/* 关联附件紧凑面板 */
.attachments-compact-panel {
  width: 100%;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 12px;
}

.attachments-compact-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.att-count-text {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.attachment-card {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  gap: 6px;
}

.att-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.att-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.att-name {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.att-meta {
  font-size: 11px;
  color: #94a3b8;
}

.att-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.attachments-empty-line {
  font-size: 12px;
  color: #94a3b8;
  padding: 2px 0;
}
</style>
