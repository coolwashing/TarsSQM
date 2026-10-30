<template>
  <div class="uploader-container" :class="{ 'is-disabled': disabled }">
    <!-- 拖拽上传与按钮触发区 -->
    <el-upload
      ref="uploadRef"
      class="upload-drop-zone"
      drag
      action="#"
      :auto-upload="false"
      :show-file-list="false"
      :multiple="multiple"
      :accept="accept"
      :disabled="disabled || isExceedLimit"
      :on-change="handleFileChange"
    >
      <div class="drop-content">
        <el-icon class="drop-icon" :size="36"><UploadFilled /></el-icon>
        <div class="drop-text">
          <span>将文件拖拽至此处，或 <em class="browse-link">点击浏览上传</em></span>
          <p class="drop-tip" v-if="tipText">
            {{ tipText }}
          </p>
        </div>
      </div>
    </el-upload>

    <!-- 附件卡片清单渲染 -->
    <div class="attachment-list" v-if="fileList.length > 0">
      <div
        v-for="item in fileList"
        :key="item.id"
        class="attachment-card"
        :class="`status-${item.status || 'success'}`"
      >
        <div class="card-left">
          <div class="file-icon-box">
            <el-icon :size="20">
              <component :is="getFileIcon(item.originalName, item.mimeType)" />
            </el-icon>
          </div>
          <div class="file-info">
            <span class="file-name" :title="item.originalName">{{ item.originalName }}</span>
            <div class="file-meta">
              <span class="file-size">{{ formatFileSize(item.fileSize) }}</span>
              <el-tag
                v-if="item.status === 'uploading'"
                size="small"
                type="warning"
                effect="plain"
              >
                上传中 {{ item.progress }}%
              </el-tag>
              <el-tag
                v-else-if="item.status === 'error'"
                size="small"
                type="danger"
                effect="plain"
              >
                上传失败
              </el-tag>
              <el-tag
                v-else
                size="small"
                type="success"
                effect="plain"
              >
                已入库
              </el-tag>
            </div>
          </div>
        </div>

        <div class="card-actions">
          <!-- 上传中进度条 -->
          <el-progress
            v-if="item.status === 'uploading'"
            :percentage="item.progress || 0"
            :stroke-width="3"
            :show-text="false"
            class="mini-progress"
          />

          <!-- 成功操作按钮 -->
          <template v-if="item.status === 'success' || !item.status">
            <el-button
              link
              type="primary"
              :icon="Download"
              title="下载/预览"
              @click="handleDownload(item)"
            >
              下载
            </el-button>
          </template>

          <!-- 移除按钮 -->
          <el-popconfirm
            v-if="!disabled"
            title="确认移除此附件？"
            confirm-button-text="确认"
            cancel-button-text="取消"
            @confirm="handleRemove(item)"
          >
            <template #reference>
              <el-button link type="danger" :icon="Delete" title="删除附件" />
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, onMounted } from 'vue'
import {
  UploadFilled,
  Download,
  Delete,
  Document,
  Picture,
  Film,
  FolderOpened
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import type { AttachmentItem, UploaderProps, UploaderEmits } from './types'
import { useUploader } from './useUploader'

const props = withDefaults(defineProps<UploaderProps>(), {
  bizType: 'general',
  bizId: null,
  accept: '',
  maxSizeMB: 50,
  limit: 10,
  disabled: false,
  multiple: true,
  modelValue: () => []
})

const emit = defineEmits<UploaderEmits>()

const {
  fileList,
  formatFileSize,
  uploadSingleFile,
  fetchAttachments,
  removeAttachment,
  bindAttachmentsToBiz
} = useUploader()

// 数量上限检查
const isExceedLimit = computed(() => fileList.value.length >= props.limit)

// 提示文案
const tipText = computed(() => {
  const parts = []
  if (props.accept) parts.push(`支持格式: ${props.accept}`)
  if (props.maxSizeMB) parts.push(`单文件不超过 ${props.maxSizeMB}MB`)
  if (props.limit) parts.push(`最多可上传 ${props.limit} 个`)
  return parts.join(' · ')
})

// 根据扩展名匹配图标
const getFileIcon = (filename: string, mime: string) => {
  const lower = filename.toLowerCase()
  if (mime.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/.test(lower)) {
    return Picture
  }
  if (mime.startsWith('video/') || /\.(mp4|avi|mov)$/.test(lower)) {
    return Film
  }
  if (/\.(zip|rar|7z|tar|gz)$/.test(lower)) {
    return FolderOpened
  }
  return Document
}

// 处理文件选择
const handleFileChange = async (uploadFile: UploadFile) => {
  if (props.disabled) return
  if (isExceedLimit.value) {
    ElMessage.warning(`上传文件数量已达到上限 (${props.limit}个)`)
    return
  }

  const raw = uploadFile.raw
  if (!raw) return

  const item = await uploadSingleFile(
    raw,
    props.bizType,
    props.bizId,
    props.maxSizeMB
  )

  if (item) {
    emit('success', item)
    emit('update:modelValue', fileList.value)
    emit('change', fileList.value)
  }
}

// 下载/预览
const handleDownload = (item: AttachmentItem) => {
  const downloadUrl = item.url || `/api/storage/file/${item.id}`
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = item.originalName
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 移除附件
const handleRemove = async (item: AttachmentItem) => {
  const ok = await removeAttachment(item)
  if (ok) {
    emit('remove', item)
    emit('update:modelValue', fileList.value)
    emit('change', fileList.value)
  }
}

// 监听外部 modelValue 注入
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal && Array.isArray(newVal)) {
      fileList.value = [...newVal]
    }
  },
  { immediate: true }
)

// 若已指定业务外键则自动加载已有附件
onMounted(async () => {
  if (props.bizType && props.bizId != null && props.bizId > 0) {
    const list = await fetchAttachments(props.bizType, props.bizId)
    emit('update:modelValue', list)
  }
})

// 对外暴露绑定接口，方便父表单在新建完成后调用
defineExpose({
  fileList,
  bindToBizId: async (bizId: number) => {
    const ids = fileList.value.map((f) => f.id).filter((id) => id > 0)
    return bindAttachmentsToBiz(ids, bizId)
  }
})
</script>

<style scoped>
.uploader-container {
  width: 100%;
}

.upload-drop-zone {
  width: 100%;
}

:deep(.el-upload-dragger) {
  padding: 16px 20px;
  background-color: #fafbfc;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  transition: all 0.2s ease;
}

:deep(.el-upload-dragger:hover) {
  border-color: #6366f1;
  background-color: #f5f3ff;
}

.drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.drop-icon {
  color: #6366f1;
}

.drop-text {
  font-size: 13px;
  color: #4b5563;
}

.browse-link {
  color: #6366f1;
  font-style: normal;
  font-weight: 600;
  cursor: pointer;
}

.drop-tip {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

/* 附件卡片列表 */
.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.attachment-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  transition: border-color 0.2s ease;
}

.attachment-card:hover {
  border-color: #cbd5e1;
}

.attachment-card.status-uploading {
  border-color: #fde68a;
  background-color: #fffbeb;
}

.attachment-card.status-error {
  border-color: #fecaca;
  background-color: #fef2f2;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.file-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-size {
  font-size: 11px;
  color: #9ca3af;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.mini-progress {
  width: 80px;
}

.is-disabled {
  opacity: 0.6;
  pointer-events: none;
}
</style>
