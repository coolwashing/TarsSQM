<template>
  <el-dialog v-model="visible" title="上传文件" width="min(560px, 94vw)" append-to-body
    :close-on-click-modal="!uploading" :close-on-press-escape="!uploading" :show-close="!uploading">
    <p class="upload-help">保存到：{{ folderName || '知识库根目录' }}</p>
    <div class="upload-drop" @dragover.prevent @drop.prevent="addFiles(Array.from($event.dataTransfer?.files || []))">
      <span class="upload-symbol">↑</span>
      <p>拖入文件，或 <button type="button" :disabled="uploading" @click="inputRef?.click()">选择文件</button></p>
      <span>原件存储，支持批量上传；单个文件不超过 50 MB</span>
      <input ref="inputRef" type="file" multiple hidden @change="handleSelect" />
    </div>
    <p class="upload-help">Excel、PDF、Word 和文本会尝试提取正文，供搜索与 AI 引用；无需转成在线文档。</p>
    <div class="upload-queue">
      <div v-for="(item, index) in queue" :key="index" class="upload-item">
        <div class="upload-item-heading"><span :title="item.file.name">{{ item.file.name }}</span><span class="upload-state" :class="item.status">{{ labels[item.status] }}</span></div>
        <el-progress v-if="item.status === 'uploading'" :percentage="item.progress" :stroke-width="3" />
        <p v-if="item.message" :class="{ 'upload-error': item.status === 'error' }">{{ item.message }}</p>
      </div>
    </div>
    <template #footer>
      <el-button :disabled="uploading" @click="visible = false">{{ queue.some(item => item.status === 'done') ? '完成' : '取消' }}</el-button>
      <el-button type="primary" :loading="uploading" :disabled="!queue.some(item => item.status === 'pending' || item.status === 'error')" @click="upload">开始上传</el-button>
    </template>
  </el-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
const props = withDefaults(defineProps<{ modelValue: boolean; folderId?: number | null; folderName?: string; files?: File[] }>(), { files: () => [] })
const emit = defineEmits<{ (event: 'update:modelValue', value: boolean): void; (event: 'uploaded'): void }>()
const visible = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
type QueueItem = { file: File; status: 'pending' | 'uploading' | 'done' | 'error'; progress: number; message: string }
const queue = ref<QueueItem[]>([])
const uploading = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)
const labels = { pending: '待上传', uploading: '上传中', done: '已保存', error: '未完成' }
function addFiles(files: File[]) {
  if (uploading.value) return
  for (const file of files) queue.value.push({ file, status: 'pending', progress: 0, message: '' })
}
function handleSelect(event: Event) {
  const input = event.target as HTMLInputElement
  addFiles(Array.from(input.files || [])); input.value = ''
}
async function upload() {
  if (uploading.value) return
  uploading.value = true
  const parentId = props.folderId
  let succeeded = false
  try {
    for (const item of queue.value) {
      if (item.status === 'done') continue
      if (item.file.size > 50 * 1024 * 1024 || !item.file.size) {
        item.status = 'error'; item.message = '请选择非空且不超过 50 MB 的文件'; continue
      }
      item.status = 'uploading'; item.message = ''
      const form = new FormData(); form.append('file', item.file)
      if (parentId != null) form.append('parent_id', String(parentId))
      try {
        const response = await axios.post('/api/kb/files', form, { onUploadProgress: progress => {
          item.progress = Math.min(99, Math.round(progress.loaded / (progress.total || item.file.size) * 100))
        } })
        item.status = 'done'; item.progress = 100; item.message = response.data.index_message
        succeeded = true
      } catch (error: any) {
        item.status = 'error'; item.message = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : '上传未完成，请检查连接后重试'
      }
    }
  } finally { uploading.value = false; if (succeeded) emit('uploaded') }
}
watch(() => props.modelValue, open => { if (open && !uploading.value) { queue.value = []; addFiles(props.files) } })
</script>
<style scoped>
.upload-drop { border: 1px dashed #cbd5e1; border-radius: 8px; padding: 24px 12px; text-align: center; background: #f8fafc; }
.upload-symbol { font-size: 28px; color: #2563eb; }
.upload-drop p { font-size: 14px; margin: 8px 0; }
.upload-drop button { color: #2563eb; border: 0; background: transparent; cursor: pointer; font-size: inherit; }
.upload-drop > span:last-of-type, .upload-help { font-size: 12px; color: #64748b; line-height: 1.8; }
.upload-queue { max-height: 36vh; overflow-y: auto; overflow-x: hidden; }
.upload-item { padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.upload-item-heading { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; }
.upload-item-heading > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.upload-state { flex-shrink: 0; color: #64748b; }
.upload-state.done { color: #15803d; }.upload-state.error, .upload-error { color: #b91c1c !important; }
.upload-item p { font-size: 12px; color: #64748b; margin: 6px 0 0; overflow-wrap: anywhere; }
</style>
