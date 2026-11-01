<template>
  <el-dialog
    v-model="visible"
    :title="attachment?.original_name || '附件在线查阅'"
    width="85%"
    top="5vh"
    destroy-on-close
    append-to-body
    class="attachment-preview-dialog"
  >
    <!-- 弹窗顶栏操作 -->
    <template #header>
      <div class="custom-dialog-header">
        <div class="header-file-info">
          <span class="file-icon-tag">{{ fileIcon }}</span>
          <span class="file-title-name">{{ attachment?.original_name }}</span>
          <span class="file-size-tag">{{ formattedSize }}</span>
        </div>
        <div class="header-actions">
          <el-button
            size="small"
            type="primary"
            plain
            :icon="Download"
            @click="handleDownload"
          >
            下载原文件
          </el-button>
        </div>
      </div>
    </template>

    <!-- 预览主体内容容器 -->
    <div v-loading="loading" class="preview-content-box">
      <!-- 1. 图片预览 -->
      <div v-if="previewType === 'image'" class="image-viewer-stage">
        <img :src="fileUrl" :alt="attachment?.original_name" class="preview-img" />
      </div>

      <!-- 2. Word (.docx) 在线高保真排版渲染 (复用 mammoth.js) -->
      <div v-else-if="previewType === 'docx'" class="docx-viewer-stage">
        <div class="docx-paper-sheet" v-html="docxHtml"></div>
      </div>

      <!-- 3. PDF 在线查阅 (内置 iframe 滚动) -->
      <div v-else-if="previewType === 'pdf'" class="pdf-viewer-stage">
        <iframe :src="fileUrl" class="pdf-iframe" title="PDF 在线阅读器"></iframe>
      </div>

      <!-- 4. 纯文本 / 代码 / 日志 / 结构化 JSON 查阅 -->
      <div v-else-if="previewType === 'text'" class="text-viewer-stage">
        <pre class="code-pre-box"><code>{{ textContent }}</code></pre>
      </div>

      <!-- 5. 不支持就地渲染的格式 (压缩包、CAD 或专有二进制) -->
      <div v-else class="unsupported-viewer-stage">
        <el-empty description="该文件格式为专有工程/压缩文件，暂不支持浏览器就地预览">
          <el-button type="primary" :icon="Download" @click="handleDownload">
            立即下载至本地查看 ({{ attachment?.original_name }})
          </el-button>
        </el-empty>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import mammoth from 'mammoth'
import type { TaskAttachmentItem } from '@/types/task'

const props = defineProps<{
  modelValue: boolean
  attachment: TaskAttachmentItem | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const docxHtml = ref('')
const textContent = ref('')

const ext = computed(() => {
  return props.attachment?.original_name.split('.').pop()?.toLowerCase() || ''
})

const fileUrl = computed(() => {
  if (!props.attachment) return ''
  return `/api/storage/download/${props.attachment.id}`
})

const previewType = computed<'image' | 'docx' | 'pdf' | 'text' | 'unsupported'>(() => {
  const e = ext.value
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(e)) return 'image'
  if (e === 'docx') return 'docx'
  if (e === 'pdf') return 'pdf'
  if (['txt', 'log', 'json', 'md', 'py', 'sql', 'js', 'ts', 'csv'].includes(e)) return 'text'
  return 'unsupported'
})

const fileIcon = computed(() => {
  switch (previewType.value) {
    case 'image': return '🖼️'
    case 'docx': return '📝'
    case 'pdf': return '📕'
    case 'text': return '📃'
    default: return '📦'
  }
})

const formattedSize = computed(() => {
  if (!props.attachment?.file_size) return ''
  const bytes = props.attachment.file_size
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
})

// 加载文件内容
const loadFileContent = async () => {
  if (!props.attachment) return
  docxHtml.value = ''
  textContent.value = ''

  if (previewType.value === 'docx') {
    loading.value = true
    try {
      const res = await axios.get(fileUrl.value, { responseType: 'arraybuffer' })
      const result = await mammoth.convertToHtml({ arrayBuffer: res.data })
      docxHtml.value = result.value || '<p>文档内容为空</p>'
    } catch (err: any) {
      docxHtml.value = `<div class="error-tip">解析 Word 文档失败: ${err.message}</div>`
    } finally {
      loading.value = false
    }
  } else if (previewType.value === 'text') {
    loading.value = true
    try {
      const res = await axios.get(fileUrl.value, { responseType: 'text' })
      textContent.value = res.data
    } catch (err: any) {
      textContent.value = `读取文件失败: ${err.message}`
    } finally {
      loading.value = false
    }
  }
}

watch(
  () => [props.modelValue, props.attachment],
  ([vis]) => {
    if (vis && props.attachment) {
      loadFileContent()
    }
  }
)

const handleDownload = () => {
  if (!props.attachment) return
  const a = document.createElement('a')
  a.href = fileUrl.value
  a.download = props.attachment.original_name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  ElMessage.success('已开始下载文件')
}
</script>

<style scoped>
.custom-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 32px;
}

.header-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon-tag {
  font-size: 18px;
}

.file-title-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size-tag {
  font-size: 12px;
  color: #909399;
  background: #f0f2f5;
  padding: 1px 6px;
  border-radius: 4px;
}

.preview-content-box {
  min-height: 480px;
  max-height: 75vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border-radius: 6px;
  padding: 16px;
}

.image-viewer-stage {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.preview-img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.docx-viewer-stage {
  display: flex;
  justify-content: center;
  padding: 12px;
}

.docx-paper-sheet {
  background: #ffffff;
  width: 100%;
  max-width: 860px;
  min-height: 600px;
  padding: 40px 48px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  line-height: 1.7;
  color: #2c3e50;
}

.docx-paper-sheet :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}

.docx-paper-sheet :deep(th),
.docx-paper-sheet :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  font-size: 13px;
}

.docx-paper-sheet :deep(th) {
  background-color: #f5f7fa;
  font-weight: 600;
}

.pdf-viewer-stage {
  width: 100%;
  height: 70vh;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 4px;
}

.text-viewer-stage {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
}

.code-pre-box {
  margin: 0;
  font-family: 'Fira Code', Consolas, Monaco, monospace;
  font-size: 13px;
  color: #d4d4d4;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.unsupported-viewer-stage {
  padding: 60px 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
