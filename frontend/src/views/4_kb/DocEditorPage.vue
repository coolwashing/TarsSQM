<template>
  <div class="doc-editor-page" v-loading="loading">
    <!-- 顶部统一控制栏 (整合文档标题与轻量元数据，类似 Google Docs / 语雀) -->
    <header class="editor-nav-header">
      <div class="header-left">
        <el-button size="small" class="back-btn" @click="handleBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回知识库</span>
        </el-button>

        <div class="nav-divider"></div>

        <div class="nav-title-box" v-if="doc">
          <span class="crumb-icon">{{ doc?.icon || '📄' }}</span>
          <!-- 顶栏可直接编辑标题 (信标 2 上移，常驻置顶) -->
          <input
            v-model="doc.title"
            class="nav-title-input"
            placeholder="请输入质量规程文档标题..."
            @input="handleTitleChange"
            title="点击直接重命名质量规程标题"
          />
          <span v-if="doc?.biz_type === 'SHORTCUT'" class="shortcut-tag">🔗 快捷方式</span>
          <span v-else-if="doc?.biz_type" class="biz-tag">{{ doc.biz_type }}</span>
        </div>
      </div>

      <div class="header-right">
        <!-- 质量状态切换器 -->
        <div class="status-dropdown-wrap">
          <el-dropdown trigger="click" @command="handleStatusChange">
            <span class="status-badge-btn" :class="doc?.status?.toLowerCase() || 'active'">
              <span class="dot"></span>
              <span>{{ getStatusLabel(doc?.status) }} ▾</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="ACTIVE">🟢 正式生效 (Active)</el-dropdown-item>
                <el-dropdown-item command="REVIEW">🟡 质量评审中 (Review)</el-dropdown-item>
                <el-dropdown-item command="DRAFT">⚪ 草稿编制中 (Draft)</el-dropdown-item>
                <el-dropdown-item command="OBSOLETE" divided style="color: #ef4444;">🔴 已废止停用 (Obsolete)</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 0.5s 防抖静默保存指示器 -->
        <div :class="['save-badge', saveStatusClass]">
          <span class="save-dot"></span>
          <span>{{ saveStatusText }}</span>
        </div>

        <!-- 手动即时存盘 -->
        <el-button
          type="primary"
          size="small"
          :loading="saving"
          @click="handleManualSave"
        >
          保存同步
        </el-button>
      </div>
    </header>

    <!-- 居中 900px 飞书白纸式排版画布 (支持宽屏扩展，直接从工具栏和正文开始) -->
    <main class="editor-scroll-body">
      <div class="editor-paper-sheet" :class="{ 'is-wide': isWideMode }" v-if="doc">
        <!-- 现代化 Tiptap 质量公差富文本编辑器 (内置信标 1 AI 入口 与 信标 5 大纲树) -->
        <div class="tiptap-container">
          <TiptapEditor
            ref="tiptapRef"
            v-model="doc.content_html"
            :is-wide="isWideMode"
            :ai-active="aiCopilotVisible"
            @update:is-wide="handleWideChange"
            placeholder="在此键入标准作业规范、公差控制红线与抽样检验要求，支持点击上方插入 CTQ 公差表格..."
            @change="handleContentChange"
            @ai-click="handleOpenAiCopilot"
            @select-dom-node="handleSelectDomNode"
          />
        </div>
      </div>
    </main>

    <!-- AI 智写助手弹窗 (支持信标 5 正文/表格与信标 6 大纲精准靶向锁定，绝不乱覆盖) -->
    <DocAiCopilot
      v-model="aiCopilotVisible"
      :doc-id="doc?.id"
      :doc-title="doc?.title"
      :doc-content="doc?.content_html"
      :initial-target="copilotTargetContext"
      :beacons="copilotBeacons"
      @remove-beacon="handleRemoveBeacon"
      @clear-beacons="handleClearBeacons"
      @highlight-beacon="handleHighlightBeacon"
      @confirm-insert="handleAiInsert"
      @refresh-doc="loadDocData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import TiptapEditor from '@/components/editor/TiptapEditor.vue'
import DocAiCopilot from './components/DocAiCopilot.vue'
import { formatDate } from '@/utils/format'

interface DocDetail {
  id: number
  parent_id?: number | null
  title: string
  icon?: string
  is_folder: boolean
  sort_order: number
  content_html?: string
  content_text?: string
  biz_type?: string
  biz_id?: number | null
  author?: string
  status?: string
  is_favorite?: boolean
  created_at: string
  updated_at: string
}

const route = useRoute()
const router = useRouter()

const docId = computed(() => Number(route.params.id))
const doc = ref<DocDetail | null>(null)
const loading = ref(false)
const saving = ref(false)
const saveStatusText = ref('已同步')
const saveStatusClass = ref('status-synced')
const aiCopilotVisible = ref(false)
const tiptapRef = ref<InstanceType<typeof TiptapEditor> | null>(null)
const copilotTargetContext = ref<{
  targetType?: string
  targetName?: string
  targetSection?: string
  selectedText?: string
  range?: { from: number; to: number }
}>({})
const copilotBeacons = ref<any[]>([])
let debounceTimer: any = null

const handleOpenAiCopilot = (ctx?: any) => {
  // 如果是来自顶部工具栏的点击 (isToolbarToggle 为 true)
  if (ctx?.isToolbarToggle) {
    // 如果没有新的选中文本或新勾选的信标，且面板已经处于打开状态，则执行 Toggle 收起/关闭
    const hasSelection = (ctx.beacons && ctx.beacons.length > 0) || (ctx.selectedText && ctx.selectedText.trim())
    if (aiCopilotVisible.value && !hasSelection) {
      aiCopilotVisible.value = false
      return
    }
  }

  copilotTargetContext.value = ctx || {}
  if (ctx?.beacons && ctx.beacons.length > 0) {
    copilotBeacons.value = ctx.beacons
  }
  aiCopilotVisible.value = true
}

const handleSelectDomNode = (nodeCtx: any) => {
  copilotTargetContext.value = nodeCtx || {}
  copilotBeacons.value = nodeCtx?.beacons || []
}

const handleRemoveBeacon = (beaconId: string) => {
  tiptapRef.value?.removeBeacon(beaconId)
}

const handleClearBeacons = () => {
  tiptapRef.value?.clearAllBeacons()
}

const handleHighlightBeacon = (payload: { id: string; highlight: boolean }) => {
  tiptapRef.value?.highlightBeaconDom(payload.id, payload.highlight)
}

const isWideMode = ref(localStorage.getItem('sqm_doc_wide_mode') === 'true')

const handleWideChange = (val: boolean) => {
  isWideMode.value = val
  try {
    localStorage.setItem('sqm_doc_wide_mode', String(val))
  } catch (e) {
    // ignore
  }
}

const wordCount = computed(() => {
  if (!doc.value?.content_html) return 0
  return doc.value.content_html.replace(/<[^>]+>/g, '').trim().length
})

const getStatusLabel = (status?: string) => {
  switch (status) {
    case 'ACTIVE': return '🟢 已正式生效'
    case 'REVIEW': return '🟡 质量评审中'
    case 'DRAFT': return '⚪ 草稿编制中'
    case 'OBSOLETE': return '🔴 已废止停用'
    default: return '🟢 已正式生效'
  }
}

// 加载文档
const loadDocData = async () => {
  if (!docId.value) return
  loading.value = true
  try {
    const res = await axios.get(`/api/kb/docs/${docId.value}`)
    doc.value = res.data
    saveStatusText.value = '已同步云端'
    saveStatusClass.value = 'status-synced'

    // 恢复退出前的正文滚动位置 (记忆机制)
    setTimeout(() => {
      const savedTop = sessionStorage.getItem(`sqm_doc_scroll_${docId.value}`)
      if (savedTop) {
        const el = document.querySelector('.tiptap-content')
        if (el) {
          el.scrollTop = parseInt(savedTop, 10)
        }
      }
    }, 150)
  } catch (err: any) {
    ElMessage.error(`加载文档详情失败: ${err.message || '网络异常'}`)
  } finally {
    loading.value = false
  }
}

// 返回
const handleBack = () => {
  if (window.opener && !window.opener.closed) {
    window.close()
  } else {
    router.push('/kb/docs')
  }
}

// 变更质量状态
const handleStatusChange = async (newStatus: string) => {
  if (!doc.value) return
  try {
    await axios.put(`/api/kb/explorer/status/${doc.value.id}`, { status: newStatus })
    doc.value.status = newStatus
    ElMessage.success(`文档状态已更新为: ${getStatusLabel(newStatus)}`)
  } catch (err: any) {
    ElMessage.error(`更新状态失败: ${err.message}`)
  }
}

const handleTitleChange = () => {
  triggerDebouncedSave()
}

const handleContentChange = () => {
  triggerDebouncedSave()
}

const triggerDebouncedSave = () => {
  saveStatusText.value = '保存中...'
  saveStatusClass.value = 'status-saving'

  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    executeSave()
  }, 500)
}

const executeSave = async () => {
  if (!doc.value) return
  saving.value = true
  try {
    await axios.put(`/api/kb/docs/${doc.value.id}`, {
      title: doc.value.title,
      icon: doc.value.icon,
      content_html: doc.value.content_html
    })
    saveStatusText.value = '已同步'
    saveStatusClass.value = 'status-synced'
  } catch {
    saveStatusText.value = '保存失败'
    saveStatusClass.value = 'status-error'
  } finally {
    saving.value = false
  }
}

const handleManualSave = () => {
  clearTimeout(debounceTimer)
  executeSave()
  ElMessage.success('已即时同步至云端知识库')
}

// AI 内容插入 (原生坐标精准原子替换，彻底消灭错位与乱放)
const handleAiInsert = (payload: {
  html: string
  mode: 'insert' | 'replace'
  targetSection?: string
  range?: { from: number; to: number }
}) => {
  if (!doc.value) return

  // 1. 如果是全篇整体替换
  if (payload.targetSection === 'ALL' && payload.mode === 'replace') {
    doc.value.content_html = payload.html
    triggerDebouncedSave()
    ElMessage.success('AI 已成功重构全篇规程')
    return
  }

  // 2. 优先通过 Tiptap 原生精确坐标 (ProseMirror Pos) 进行原子替换
  const effectiveRange = payload.range || copilotTargetContext.value.range
  const handled = tiptapRef.value?.insertAiContent({
    html: payload.html,
    mode: payload.mode,
    targetSection: payload.targetSection,
    range: effectiveRange
  })

  if (handled) {
    ElMessage.success(
      payload.targetSection === 'SELECTION'
        ? 'AI 已精准替换选区正文 (其余全文100%保持原样)'
        : 'AI 内容已成功写入指定位置 (无损留存其余章节)'
    )
    return
  }

  // 3. 兜底回退：若未命中坐标
  if (payload.mode === 'replace') {
    doc.value.content_html = payload.html
  } else {
    doc.value.content_html = (doc.value.content_html || '') + payload.html
  }
  triggerDebouncedSave()
  ElMessage.success('AI 质量规程已成功更新写入文档')
}

let scrollDebounceTimer: any = null
const handleContentScroll = (e: Event) => {
  const el = e.target as HTMLElement
  if (!el || !docId.value) return
  if (scrollDebounceTimer) clearTimeout(scrollDebounceTimer)
  scrollDebounceTimer = setTimeout(() => {
    sessionStorage.setItem(`sqm_doc_scroll_${docId.value}`, String(el.scrollTop))
  }, 100)
}

onMounted(() => {
  loadDocData()
  setTimeout(() => {
    const contentEl = document.querySelector('.tiptap-content')
    if (contentEl) {
      contentEl.addEventListener('scroll', handleContentScroll, { passive: true })
    }
  }, 200)
})

onBeforeUnmount(() => {
  const contentEl = document.querySelector('.tiptap-content')
  if (contentEl) {
    contentEl.removeEventListener('scroll', handleContentScroll)
  }
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    executeSave()
  }
})
</script>

<style scoped>
.doc-editor-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  background: #f8fafc;
  overflow: hidden;
}

/* 顶部控制栏 */
.editor-nav-header {
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.back-btn {
  font-size: 12.5px;
  flex-shrink: 0;
}
.nav-divider {
  width: 1px;
  height: 18px;
  background: #e2e8f0;
  margin: 0 4px;
  flex-shrink: 0;
}
.nav-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.crumb-icon {
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
}
.nav-title-input {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 4px 8px;
  background: transparent;
  outline: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 120px;
  max-width: 380px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-title-input:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}
.nav-title-input:focus {
  background: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}
.shortcut-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
  background: #e0f2fe;
  color: #0369a1;
  flex-shrink: 0;
}
.biz-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  flex-shrink: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 状态胶囊 */
.status-badge-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.status-badge-btn .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.status-badge-btn.active {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}
.status-badge-btn.active .dot { background: #22c55e; }

.status-badge-btn.review {
  background: #fefce8;
  color: #a16207;
  border-color: #fef08a;
}
.status-badge-btn.review .dot { background: #eab308; }

.status-badge-btn.draft {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}
.status-badge-btn.draft .dot { background: #94a3b8; }

.status-badge-btn.obsolete {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}
.status-badge-btn.obsolete .dot { background: #ef4444; }

.save-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  padding: 3px 8px;
  border-radius: 12px;
  background: #f1f5f9;
  color: #64748b;
}
.save-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-synced .save-dot { background: #10b981; }
.status-saving .save-dot { background: #f59e0b; }
.status-error .save-dot { background: #ef4444; }

.ai-smart-btn {
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
  border: none;
  font-weight: 600;
}

/* 居中排版画布 (信标 3: 消除外层多余滚动，由内部独立滚动) */
.editor-scroll-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 8px 16px 12px 16px;
  display: flex;
  justify-content: center;
}

.editor-paper-sheet {
  width: 100%;
  max-width: 960px;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid #e2e8f0;
  padding: 0;
  overflow: hidden;
  transition: max-width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.editor-paper-sheet.is-wide {
  max-width: 96%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.tiptap-container {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tiptap-container :deep(.tiptap-editor-wrap) {
  border: none !important;
  border-radius: 0 !important;
  height: 100% !important;
}
</style>
