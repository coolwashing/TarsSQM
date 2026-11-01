<template>
  <el-dialog v-model="visible" title="AI 助手" width="min(960px, 94vw)" append-to-body :close-on-click-modal="false">
    <div class="ai-workspace">
      <div class="ai-setup">
        <el-radio-group v-model="operation" size="small" :disabled="!!task">
          <el-radio-button value="ask">知识问答</el-radio-button>
          <el-radio-button value="edit" :disabled="!editable || !docId">文档编辑</el-radio-button>
        </el-radio-group>
        <el-select v-model="provider" size="small" class="provider-select" :disabled="!!task" aria-label="生成方式">
          <el-option label="交给 Codex / IDE" value="ide" />
          <el-option label="使用后端配置的模型" value="api" />
        </el-select>
      </div>
      <p class="ai-subtitle">{{ operation === 'edit' ? `编辑「${docTitle || '当前文档'}」，生成后由你确认写入。` : '从文档和附件中查找资料，回答时保留来源。' }}</p>
      <el-checkbox v-if="folderId != null" v-model="wholeLibrary" :disabled="!!task">在整个知识库中查找资料</el-checkbox>
      <el-input v-model="prompt" type="textarea" :rows="3" maxlength="8000" :disabled="!!task"
        :placeholder="operation === 'edit' ? '说明要补充、改写或整理的内容…' : '例如：来料抽样的依据是什么？请列出对应资料。'"
        @keydown.ctrl.enter.prevent="createTask" />
      <div v-if="!task" class="preset-row">
        <button v-for="preset in presets.slice(0, 5)" :key="preset.id" type="button" :title="preset.prompt" @click="prompt = preset.prompt">{{ preset.name }}</button>
      </div>
      <div v-if="beacons.length" class="beacon-row">
        <span v-for="(beacon, index) in beacons" :key="beacon.id" class="beacon-tag" :title="beacon.text || beacon.previewText"
          @mouseenter="emit('highlight-beacon', { id: beacon.id, highlight: true })"
          @mouseleave="emit('highlight-beacon', { id: beacon.id, highlight: false })">
          参考 {{ index + 1 }}<button v-if="!task" type="button" aria-label="移除参考" @click="emit('remove-beacon', beacon.id)">×</button>
        </span>
      </div>
      <div v-else-if="selectedContext" class="selection-note">已附带当前选区作为参考，写入范围由下方按钮决定。</div>

      <div v-if="!task" class="create-row">
        <span class="muted">{{ provider === 'ide' ? '复制任务到 IDE 发送，结果会自动回到这里。' : '使用后端模型配置；连接失败会明确提示。' }}</span>
        <el-button type="primary" :loading="creating" :disabled="!prompt.trim() || restoreBlocked" @click="createTask">{{ provider === 'ide' ? '复制任务给 IDE' : '开始生成' }}</el-button>
      </div>

      <template v-if="task">
        <div class="task-status" :class="task.status" role="status">
          <span>{{ statusText }}</span>
          <div class="task-controls">
            <el-button v-if="task.provider === 'ide' && task.status !== 'applied'" text size="small" @click="copyTask">复制任务</el-button>
            <el-button v-if="task.status !== 'applied'" text size="small" :loading="polling" @click="pollTask">检查结果</el-button>
            <el-button text size="small" @click="resetTask">新任务</el-button>
          </div>
        </div>
        <p v-if="task.provider === 'ide' && (task.status === 'waiting' || task.status === 'invalid')" class="muted helper-note">
          请让 IDE 在本机执行任务中的文件写入。无需把生成内容粘回页面；关闭或刷新后可继续等待。
        </p>
        <el-collapse v-if="showPrompt" class="prompt-fallback">
          <el-collapse-item title="复制未成功：展开查看任务并手动复制" name="prompt">
            <el-input :model-value="task.ide_prompt" type="textarea" :rows="6" readonly />
          </el-collapse-item>
        </el-collapse>
        <el-collapse v-if="task.references.length" class="references-panel">
          <el-collapse-item :title="`参考资料 · ${task.references.length} 个片段`" name="references">
            <button v-for="reference in task.references" :key="reference.chunk_id" class="reference-item" type="button"
          :title="`${reference.title}\n${reference.location}\n${reference.snippet}`" @click="openReference(reference)">
              <span class="reference-title">{{ reference.title }}</span><span>{{ reference.location }}</span>
            </button>
          </el-collapse-item>
        </el-collapse>
        <p v-else class="muted">未检索到匹配资料，回答应明确说明依据不足。</p>

        <div v-if="task.result_html" class="comparison" :class="{ 'has-original': task.operation === 'edit' }">
          <section v-if="task.operation === 'edit'" class="result-pane">
            <h4>任务创建时的原文</h4><div class="result-body" v-html="task.before_html"></div>
          </section>
          <section class="result-pane">
            <h4>{{ task.operation === 'ask' ? '回答' : '生成结果 · 尚未写入' }}</h4><div class="result-body" v-html="task.result_html"></div>
          </section>
        </div>
      </template>
      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    </div>
    <template #footer>
      <div class="ai-footer">
        <span class="muted">{{ task?.status === 'ready' ? '请核对结果和引用，再决定是否写入。' : '生成与写入分开，原始附件不会被改写。' }}</span>
        <div class="footer-buttons">
          <el-button @click="visible = false">关闭</el-button>
          <template v-if="task?.status === 'ready'">
            <el-button :loading="applying" @click="applyResult('new')">另存为文档</el-button>
            <el-button v-if="task.operation === 'edit'" :loading="applying" @click="applyResult('append')">追加到文末</el-button>
            <el-button v-if="task.operation === 'edit'" type="primary" :loading="applying" @click="applyResult('replace')">替换全文</el-button>
          </template>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

interface Reference { id: number; title: string; location: string; snippet: string; chunk_id: string; kind: string }
interface AiTask {
  id: string; status: 'waiting' | 'invalid' | 'ready' | 'failed' | 'applied'
  provider: 'ide' | 'api'; operation: 'ask' | 'edit'; message: string
  prompt: string; ide_prompt: string; references: Reference[]; before_html: string; source_html: string; result_html: string
  folder_id?: number | null
}
const props = withDefaults(defineProps<{
  modelValue: boolean; docId?: number; docTitle?: string; docContent?: string; selectedText?: string
  folderId?: number | null; editable?: boolean
  initialTarget?: { selectedText?: string; targetName?: string; range?: { from: number; to: number } }
  beacons?: any[]
}>(), { docTitle: '', editable: true, beacons: () => [], initialTarget: () => ({}) })
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh-doc'): void
  (e: 'confirm-insert', payload: any): void
  (e: 'remove-beacon', id: string): void
  (e: 'clear-beacons'): void
  (e: 'highlight-beacon', value: { id: string; highlight: boolean }): void
}>()
const visible = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
const operation = ref<'ask' | 'edit'>('ask')
const provider = ref<'ide' | 'api'>('ide')
const prompt = ref('')
const task = ref<AiTask | null>(null)
const presets = ref<{ id: string; name: string; prompt: string }[]>([])
const creating = ref(false)
const applying = ref(false)
const polling = ref(false)
const errorMessage = ref('')
const showPrompt = ref(false)
const wholeLibrary = ref(true)
const restoreBlocked = ref(false)
const selectedContext = computed(() => props.initialTarget?.selectedText || props.selectedText || '')
const storageKey = computed(() => `sqm_kb_ai_${props.docId || 'all'}_${props.folderId || 'root'}`)
const statusText = computed(() => task.value?.status === 'ready' ? '结果已回传，请预览后确认' : task.value?.message || '')
let pollTimer: ReturnType<typeof setTimeout> | undefined
let generation = 0

function schedulePoll() {
  clearTimeout(pollTimer)
  if (visible.value && task.value && ['waiting', 'invalid'].includes(task.value.status)) {
    pollTimer = setTimeout(pollTask, 2200)
  }
}
async function pollTask() {
  if (!task.value || polling.value) return
  const id = task.value.id
  polling.value = true
  try {
    const response = await axios.get<AiTask>(`/api/kb/ai/tasks/${id}`)
    if (task.value?.id === id) { task.value = response.data; errorMessage.value = '' }
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '暂时无法检查结果，稍后自动重试'
    if (error.response?.status === 404 && task.value?.id === id) {
      localStorage.removeItem(storageKey.value)
      task.value = null
    }
  } finally { polling.value = false; schedulePoll() }
}
async function copyTask() {
  if (!task.value) return
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(task.value.ide_prompt)
    else {
      const input = document.createElement('textarea')
      input.value = task.value.ide_prompt
      input.style.position = 'fixed'; input.style.opacity = '0'
      document.body.appendChild(input); input.select()
      const copied = document.execCommand('copy'); input.remove()
      if (!copied) throw new Error('copy unavailable')
    }
    showPrompt.value = false
    ElMessage.success('任务已复制，请粘贴到本机 Codex 或 IDE 发送')
  } catch { showPrompt.value = true; ElMessage.info('任务已创建，请展开任务内容手动复制') }
}
async function createTask() {
  if (!prompt.value.trim() || creating.value || task.value || restoreBlocked.value) return
  creating.value = true; errorMessage.value = ''
  const key = storageKey.value
  const currentGeneration = generation
  try {
    const beaconText = props.beacons.map((beacon, index) => `参考 ${index + 1}：${beacon.sectionName || ''}\n${beacon.text || beacon.fullText || beacon.previewText || ''}`).join('\n\n')
    const response = await axios.post<AiTask>('/api/kb/ai/tasks', {
      prompt: prompt.value, operation: operation.value, provider: provider.value,
      doc_id: props.docId, folder_id: wholeLibrary.value ? null : props.folderId,
      source_html: operation.value === 'edit' ? props.docContent : undefined,
      selected_text: (beaconText || selectedContext.value).slice(0, 20000)
    })
    localStorage.setItem(key, response.data.id)
    if (generation !== currentGeneration) return
    task.value = response.data
    if (provider.value === 'ide') await copyTask()
    schedulePoll()
  } catch (error: any) { errorMessage.value = error.response?.data?.detail || '任务创建失败，请检查后端连接' }
  finally { creating.value = false }
}
async function applyResult(mode: 'append' | 'replace' | 'new') {
  if (!task.value || applying.value) return
  if (mode !== 'new' && props.docContent !== undefined && props.docContent !== task.value.source_html) {
    errorMessage.value = '当前正文已发生变化，请先保存并重新创建任务，避免覆盖新内容'; return
  }
  if (mode === 'replace') {
    try { await ElMessageBox.confirm(`将用生成结果替换「${props.docTitle || '当前文档'}」的全部正文，是否继续？`, '确认替换全文', { confirmButtonText: '替换全文', cancelButtonText: '取消', type: 'warning' }) }
    catch { return }
  }
  applying.value = true
  try {
    await axios.post(`/api/kb/ai/tasks/${task.value.id}/apply`, { mode, parent_id: props.folderId, title: `${prompt.value.slice(0, 45)} · AI 记录` })
    task.value.status = 'applied'; task.value.message = '已确认写入'
    emit('refresh-doc'); ElMessage.success(mode === 'new' ? '已另存为在线文档' : '正文已更新')
  } catch (error: any) { errorMessage.value = error.response?.data?.detail || '写入失败，结果仍保留，可稍后重试' }
  finally { applying.value = false }
}
async function resetTask() {
  if (creating.value || applying.value) return
  if (task.value) {
    if (task.value.status !== 'applied') {
      try { await ElMessageBox.confirm('结束当前任务并清除其结果？文档正文不会改变。', '新建任务', { confirmButtonText: '结束并新建', cancelButtonText: '取消' }) }
      catch { return }
    }
    try { await axios.delete(`/api/kb/ai/tasks/${task.value.id}`) }
    catch (error: any) { if (error.response?.status !== 404) { errorMessage.value = '无法结束任务，请稍后重试'; return } }
  }
  clearTimeout(pollTimer); localStorage.removeItem(storageKey.value)
  task.value = null; errorMessage.value = ''; showPrompt.value = false; restoreBlocked.value = false
}
function openReference(reference: Reference) {
  window.open(reference.kind === 'file' ? `/api/kb/files/${reference.id}/download` : `/kb/editor/${reference.id}`, '_blank', 'noopener')
}
watch(() => [props.modelValue, props.docId, props.folderId] as const, async ([open]) => {
  generation++; clearTimeout(pollTimer)
  if (!open) return
  const version = generation
  const key = storageKey.value
  task.value = null; errorMessage.value = ''; showPrompt.value = false
  operation.value = props.editable && props.docId ? 'edit' : 'ask'
  try {
    const id = localStorage.getItem(key)
    if (id) {
      const response = await axios.get<AiTask>(`/api/kb/ai/tasks/${id}`)
      if (version !== generation) return
      task.value = response.data; prompt.value = response.data.prompt
      operation.value = response.data.operation; provider.value = response.data.provider
      wholeLibrary.value = response.data.folder_id == null
      schedulePoll()
    }
  } catch (error: any) {
    if (version !== generation) return
    if (error.response?.status === 404) localStorage.removeItem(key)
    else { restoreBlocked.value = true; errorMessage.value = '任务恢复暂未完成，请检查连接后重新打开面板'; return }
  }
  try { const response = await axios.get('/api/kb/prompts'); if (version === generation) presets.value = response.data || [] }
  catch { /* Presets are optional; task entry remains available. */ }
}, { immediate: true })
onBeforeUnmount(() => { generation++; clearTimeout(pollTimer) })
</script>

<style scoped>
.ai-workspace { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.ai-setup, .create-row, .task-status, .ai-footer, .footer-buttons, .task-controls { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.provider-select { width: 210px; }
.ai-subtitle { margin: 0; color: #475569; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.muted, .selection-note { font-size: 12px; color: #64748b; line-height: 1.7; }
.helper-note, .error-message { margin: 0; }
.preset-row, .beacon-row { display: flex; flex-wrap: wrap; gap: 6px; }
.preset-row button { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border: 1px solid #e2e8f0; background: #fff; color: #475569; padding: 4px 9px; border-radius: 5px; cursor: pointer; }
.beacon-tag { padding: 3px 7px; border-radius: 4px; background: #eff6ff; color: #2563eb; font-size: 12px; }
.beacon-tag button { border: 0; background: transparent; cursor: pointer; margin-left: 5px; }
.task-status { padding: 9px 12px; background: #f1f5f9; border-radius: 6px; font-size: 13px; }
.task-status.ready, .task-status.applied { background: #f0fdf4; color: #166534; }
.task-status.failed, .task-status.invalid { background: #fff7ed; color: #9a3412; }
.references-panel, .prompt-fallback { border-top: 0; }
.reference-item { display: flex; justify-content: space-between; gap: 12px; width: 100%; text-align: left; background: #fff; border: 0; padding: 5px 0; color: #64748b; cursor: pointer; }
.reference-title { color: #2563eb; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.comparison { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; }
.comparison.has-original { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.result-pane { min-width: 0; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; }
.result-pane h4 { font-size: 12px; font-weight: 500; margin: 0; padding: 10px 12px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
.result-body { padding: 12px; max-height: 42vh; overflow: auto; overflow-wrap: anywhere; line-height: 1.7; font-size: 13px; }
.result-body :deep(table) { border-collapse: collapse; width: 100%; }
.result-body :deep(th), .result-body :deep(td) { border: 1px solid #cbd5e1; padding: 5px; }
.error-message { color: #b91c1c; line-height: 1.7; font-size: 13px; }
.ai-footer { text-align: left; }
.footer-buttons { justify-content: flex-end; margin-left: auto; }
.footer-buttons .el-button + .el-button { margin-left: 0; }
@media (max-width: 640px) { .comparison.has-original { grid-template-columns: minmax(0, 1fr); } .provider-select { width: 100%; } }
</style>
