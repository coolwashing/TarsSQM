<template>
  <Teleport to="body">
    <div
      v-if="isVisible"
      ref="panelRef"
      class="teleprompter-floating-panel"
      :style="panelStyle"
    >
      <!-- 1. Header (自由拖拽，简洁标题与模式切换) -->
      <div class="panel-header" @mousedown="startDrag">
        <div class="header-left">
          <el-tooltip content="按住可拖动面板位置" placement="top">
            <span class="drag-handle">
              <el-icon :size="15" color="#6366f1"><Rank /></el-icon>
            </span>
          </el-tooltip>
          <span class="panel-title">AI 提词器</span>
          <el-tag size="small" type="primary" effect="plain" class="hotkey-badge">Alt+X</el-tag>
        </div>

        <div class="header-right" @mousedown.stop>
          <!-- 双模态切换 (Tooltip 注解) -->
          <el-radio-group v-model="currentMode" size="small" class="mode-toggle-group">
            <el-tooltip content="拾取模式：悬浮高亮元素，点击捕获信标" placement="top">
              <el-radio-button value="picking">
                <span class="mode-btn-content">
                  <el-icon><Aim /></el-icon>
                  <span>拾取</span>
                </span>
              </el-radio-button>
            </el-tooltip>
            <el-tooltip content="交互模式：暂停拾取，恢复页面原生点击与滚动" placement="top">
              <el-radio-button value="interactive">
                <span class="mode-btn-content">
                  <el-icon><Pointer /></el-icon>
                  <span>交互</span>
                </span>
              </el-radio-button>
            </el-tooltip>
          </el-radio-group>

          <el-tooltip content="关闭面板 (Esc)" placement="top">
            <el-button
              link
              :icon="Close"
              @click="closePanel"
              class="close-btn"
            />
          </el-tooltip>
        </div>
      </div>

      <!-- 2. 面板主体 (紧凑无废话设计) -->
      <div class="panel-body">
        <!-- 偏好控制单行栏 -->
        <div class="preferences-bar">
          <div class="pref-left">
            <el-tooltip content="限制 AI 回复字数，留空或 0 为不限制" placement="top">
              <span class="pref-label">字数限制:</span>
            </el-tooltip>
            <el-input-number
              v-model="wordLimit"
              :step="50"
              :min="0"
              :max="3000"
              size="small"
              controls-position="right"
              placeholder="不限"
              class="word-limit-input"
            />
          </div>

          <div class="pref-right">
            <el-tooltip content="要求 AI 仅提供方案思路或解答，严禁修改/生成物理代码" placement="top">
              <el-checkbox v-model="noCodeOnlyPlan" size="small">
                <span class="no-code-label">⚠️ 仅出方案 (不改代码)</span>
              </el-checkbox>
            </el-tooltip>
          </div>
        </div>

        <!-- 需求输入区 -->
        <div class="prompt-input-section">
          <div class="section-sub-header">
            <span class="sub-title">需求描述</span>
            <div class="sub-header-actions">
              <el-tooltip content="清空当前输入需求与所有已选信标" placement="top">
                <el-button
                  v-if="userPrompt.trim() || beacons.length > 0"
                  link
                  type="danger"
                  size="small"
                  :icon="Delete"
                  @click="resetAll"
                >
                  一键清空
                </el-button>
              </el-tooltip>
              <el-tooltip content="将当前文本保存到常用指令收藏" placement="top">
                <el-button
                  link
                  type="primary"
                  size="small"
                  :icon="Star"
                  @click="openAddFavoriteDialog"
                >
                  收藏指令
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <el-input
            ref="promptTextareaRef"
            v-model="userPrompt"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入需求，点击页面元素可插入【信标】..."
            class="user-prompt-textarea"
          />
        </div>

        <!-- 常用指令胶囊栏 -->
        <div class="favorites-section">
          <div class="favorites-chips-wrap">
            <el-tag
              v-for="fav in allFavorites"
              :key="fav.id"
              class="fav-pill-tag"
              :type="fav.isCustom ? 'warning' : 'info'"
              effect="plain"
              size="small"
              :closable="fav.isCustom"
              @close="deleteFavorite(fav.id)"
              @click="applyFavorite(fav.prompt)"
            >
              {{ fav.title }}
            </el-tag>
          </div>
        </div>

        <!-- 信标清单 -->
        <div class="beacons-cart-section">
          <div class="cart-header">
            <span class="cart-title">
              <el-icon color="#4f46e5"><Box /></el-icon>
              <span>信标清单 ({{ beacons.length }})</span>
            </span>
            <el-button
              v-if="beacons.length > 0"
              link
              type="danger"
              size="small"
              :icon="Delete"
              @click="handleClearBeacons"
            >
              清空
            </el-button>
          </div>

          <!-- 已捕获信标列表 -->
          <div v-if="beacons.length > 0" class="beacons-list">
            <el-popover
              v-for="b in beacons"
              :key="b.id"
              placement="top"
              :width="360"
              trigger="hover"
              popper-class="beacon-deep-popover"
            >
              <template #reference>
                <div class="beacon-chip-card">
                  <span class="beacon-badge">{{ b.tag }}</span>
                  <span class="beacon-comp">{{ b.compName }}</span>
                  <span class="beacon-snippet text-truncate">{{ b.innerText ? `"${b.innerText}"` : b.domPath }}</span>
                  <el-button
                    link
                    type="info"
                    :icon="Close"
                    class="beacon-del-btn"
                    @click.stop="handleDeleteBeacon(b.id)"
                    title="移除"
                  />
                </div>
              </template>

              <!-- 悬浮深层画像 Tooltip -->
              <div class="beacon-portrait-box">
                <div class="portrait-head">
                  <el-icon color="#4f46e5"><Aim /></el-icon>
                  <strong>{{ b.tag }} 详情画像</strong>
                </div>
                <div class="portrait-grid">
                  <div class="portrait-item">
                    <span class="p-k">组件：</span>
                    <span class="p-v font-bold">{{ b.compName }}</span>
                  </div>
                  <div class="portrait-item">
                    <span class="p-k">文件：</span>
                    <span class="p-v font-mono text-break">{{ b.filePath }} {{ b.line ? `(L${b.line})` : '' }}</span>
                  </div>
                  <div class="portrait-item">
                    <span class="p-k">视口：</span>
                    <span class="p-v">{{ b.viewport }}</span>
                  </div>
                  <div class="portrait-item full-col">
                    <span class="p-k">DOM 路径：</span>
                    <code class="p-code">{{ b.domPath }}</code>
                  </div>
                  <div class="portrait-item full-col" v-if="b.className">
                    <span class="p-k">类名：</span>
                    <code class="p-code">{{ b.className }}</code>
                  </div>
                  <div class="portrait-item full-col" v-if="b.innerText">
                    <span class="p-k">文本：</span>
                    <span class="p-v text-muted">"{{ b.innerText }}"</span>
                  </div>
                </div>
              </div>
            </el-popover>
          </div>

          <!-- 空状态：极简单行提示 -->
          <div v-else class="empty-beacons-compact">
            <el-icon color="#94a3b8"><Aim /></el-icon>
            <span>未选信标，拾取模式下点击页面元素捕获</span>
          </div>
        </div>

        <!-- 3. 底部操作按钮 -->
        <div class="panel-footer">
          <div class="footer-left-actions">
            <el-tooltip content="一键清空当前需求描述与所有信标" placement="top">
              <el-button
                size="default"
                type="danger"
                plain
                @click="resetAll"
                :icon="Delete"
                class="clear-all-btn"
              >
                一键清空
              </el-button>
            </el-tooltip>
            <el-tooltip content="开启后，复制成功后自动清空当前指令与信标，再次按 Alt+X 打开即为干净面板" placement="top">
              <el-checkbox v-model="autoClearOnCopy" size="small" class="auto-clear-check">
                复制后清空
              </el-checkbox>
            </el-tooltip>
          </div>
          <el-button
            type="primary"
            size="default"
            class="copy-prompt-btn"
            @click="copyPrompt"
          >
            🚀 一键复制需求与信标
          </el-button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import {
  Aim,
  Pointer,
  Rank,
  Close,
  Star,
  Box,
  Delete,
  Refresh
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePicker, type BeaconItem } from './usePicker'

// 面板可视状态
const isVisible = ref(false)
const currentMode = ref<'picking' | 'interactive'>('picking')

// 偏好控制
const getInitialWordLimit = (): number | undefined => {
  const saved = localStorage.getItem('sqm_teleprompter_word_limit')
  return saved ? Number(saved) : undefined
}
const wordLimit = ref<number | undefined>(getInitialWordLimit())
const noCodeOnlyPlan = ref<boolean>(localStorage.getItem('sqm_teleprompter_no_code') === 'true')
const autoClearOnCopy = ref<boolean>(localStorage.getItem('sqm_teleprompter_auto_clear') !== 'false')

// 需求输入框
const userPrompt = ref('')
const promptTextareaRef = ref<any>(null)

// 拖拽面板定位
const panelRef = ref<HTMLElement | null>(null)
const panelPosition = ref({ x: Math.max(window.innerWidth - 490, 20), y: Math.max(window.innerHeight - 520, 20) })
let isDragging = false
let dragStartMouse = { x: 0, y: 0 }
let dragStartPos = { x: 0, y: 0 }

const panelStyle = computed(() => ({
  left: `${panelPosition.value.x}px`,
  top: `${panelPosition.value.y}px`
}))

// 常用与自定义指令收藏
interface FavoriteItem {
  id: string
  title: string
  prompt: string
  isCustom?: boolean
}

const defaultPresets: FavoriteItem[] = [
  {
    id: 'preset_1',
    title: '【UI/UX样式调优】',
    prompt: '请优化【信标 1】的视觉样式、边距与响应式对齐'
  },
  {
    id: 'preset_2',
    title: '【表单防呆与校验】',
    prompt: '请为【信标 1】增加表单防呆校验与二次警示确认机制'
  },
  {
    id: 'preset_3',
    title: '【次级警告色与间距对齐】',
    prompt: '请把【信标 1】的按钮颜色修改为【信标 2】的次级警告色，并增加外边距。'
  },
  {
    id: 'preset_4',
    title: '【接口对接与联动】',
    prompt: '请将【信标 1】对接后端业务接口，并实现数据联动刷新'
  }
]

const getInitialCustomFavorites = (): FavoriteItem[] => {
  try {
    const raw = localStorage.getItem('sqm_teleprompter_custom_favs')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const customFavorites = ref<FavoriteItem[]>(getInitialCustomFavorites())

const allFavorites = computed(() => [
  ...defaultPresets,
  ...customFavorites.value
])

// 光标位置插入占位符
const insertTagAtCursor = (tag: string) => {
  const textarea = promptTextareaRef.value?.$el?.querySelector('textarea') || promptTextareaRef.value
  if (!textarea) {
    userPrompt.value += (userPrompt.value ? ' ' : '') + tag
    return
  }
  const start = textarea.selectionStart ?? userPrompt.value.length
  const end = textarea.selectionEnd ?? userPrompt.value.length
  const text = userPrompt.value
  const before = text.substring(0, start)
  const after = text.substring(end)
  const insertContent = (before && !before.endsWith(' ') ? ' ' : '') + tag + (after && !after.startsWith(' ') ? ' ' : '')
  userPrompt.value = before + insertContent + after

  nextTick(() => {
    textarea.focus()
    const newPos = before.length + insertContent.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

// 拾取器回调
const onPickElement = (beacon: BeaconItem) => {
  insertTagAtCursor(beacon.tag)
  ElMessage.success(`已捕获 ${beacon.tag} (${beacon.compName})`)
}

const {
  isPicking,
  beacons,
  startPicking,
  stopPicking,
  removeHighlightElements,
  removeBeacon,
  clearBeacons
} = usePicker(onPickElement)

// 模式切换监听
watch(currentMode, (newMode) => {
  if (!isVisible.value) return
  if (newMode === 'picking') {
    startPicking()
  } else {
    stopPicking()
  }
})

// 偏好本地存储保存
watch(wordLimit, (val) => {
  if (val !== undefined && val > 0) {
    localStorage.setItem('sqm_teleprompter_word_limit', String(val))
  } else {
    localStorage.removeItem('sqm_teleprompter_word_limit')
  }
})

watch(noCodeOnlyPlan, (val) => {
  localStorage.setItem('sqm_teleprompter_no_code', String(val))
})

watch(autoClearOnCopy, (val) => {
  localStorage.setItem('sqm_teleprompter_auto_clear', String(val))
})

// 收藏相关
const openAddFavoriteDialog = async () => {
  if (!userPrompt.value.trim()) {
    ElMessage.warning('请先输入需要收藏的指令文本')
    return
  }
  try {
    const { value: title } = await ElMessageBox.prompt('请输入指令简短标题：', '收藏当前指令', {
      confirmButtonText: '确定保存',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：【表格批量操作】',
      inputValidator: (v) => !!v.trim() || '标题不能为空'
    })
    const newFav: FavoriteItem = {
      id: 'custom_' + Date.now(),
      title: title.trim().startsWith('【') ? title.trim() : `【${title.trim()}】`,
      prompt: userPrompt.value.trim(),
      isCustom: true
    }
    customFavorites.value.push(newFav)
    localStorage.setItem('sqm_teleprompter_custom_favs', JSON.stringify(customFavorites.value))
    ElMessage.success('已保存至常用收藏！')
  } catch {
    // 取消
  }
}

const deleteFavorite = (id: string) => {
  customFavorites.value = customFavorites.value.filter(f => f.id !== id)
  localStorage.setItem('sqm_teleprompter_custom_favs', JSON.stringify(customFavorites.value))
  ElMessage.info('已移除收藏')
}

const applyFavorite = (promptStr: string) => {
  if (userPrompt.value.trim()) {
    userPrompt.value += '\n' + promptStr
  } else {
    userPrompt.value = promptStr
  }
  nextTick(() => {
    const textarea = promptTextareaRef.value?.$el?.querySelector('textarea') || promptTextareaRef.value
    if (textarea) {
      textarea.focus()
      textarea.setSelectionRange(userPrompt.value.length, userPrompt.value.length)
    }
  })
}

// 信标移除
const handleDeleteBeacon = (id: number) => {
  const item = beacons.value.find(b => b.id === id)
  if (item) {
    removeBeacon(id)
    userPrompt.value = userPrompt.value.replace(new RegExp(`\\s*${item.tag}\\s*`, 'g'), ' ').trim()
  }
}

const handleClearBeacons = () => {
  clearBeacons()
}

const resetAll = () => {
  userPrompt.value = ''
  clearBeacons()
  ElMessage.info('已一键清空需求与信标')
}

// 格式化输出 Prompt 标准范式
const buildStructuredPrompt = (): string => {
  const lines: string[] = ['要求是：']

  // 1. 字数限制
  if (wordLimit.value && wordLimit.value > 0) {
    lines.push(`【字数限制】请将回复控制在 ${wordLimit.value} 字左右。`)
  }

  // 2. 仅出方案
  if (noCodeOnlyPlan.value) {
    lines.push('【禁止开发代码】⚠️ 我只是提问或需要方案，请不要编写、修改或重构任何物理代码，直接回答或制定计划即可。')
  }

  // 3. 用户需求输入
  const promptText = userPrompt.value.trim()
  if (promptText) {
    lines.push(promptText)
  } else {
    lines.push('请基于附带的定位信标进行针对性开发优化与调整。')
  }

  // 4. 信标列表
  if (beacons.value.length > 0) {
    lines.push('=====================')
    lines.push(`### [附带定位信标详情 - 共 ${beacons.value.length} 个] ###`)
    beacons.value.forEach(b => {
      lines.push(`${b.tag}`)
      lines.push(`所在组件：${b.compName}`)
      lines.push(`源码文件：${b.filePath}${b.line ? ` (Line ${b.line})` : ''}`)
      lines.push(`所属视口：${b.viewport}`)
      lines.push(`DOM 层级：${b.domPath}`)
      lines.push(`当前类名：${b.className || '(无独立class)'}`)
      lines.push(`包含文本：${b.innerText ? `"${b.innerText}"` : '(无直接文本)'}`)
    })
  }

  return lines.join('\n')
}

// 一键复制
const copyPrompt = async () => {
  const prompt = buildStructuredPrompt()
  try {
    await navigator.clipboard.writeText(prompt)
    ElMessage.success({
      message: '🚀 需求与信标已复制到剪贴板！',
      duration: 3000
    })
    if (autoClearOnCopy.value) {
      userPrompt.value = ''
      clearBeacons()
    }
    closePanel()
  } catch {
    ElMessage.error('复制失败，请手动选中文本复制')
  }
}

// 面板唤出与关闭
const openPanel = () => {
  isVisible.value = true
  currentMode.value = 'picking'
  nextTick(() => {
    startPicking()
  })
}

const closePanel = () => {
  isVisible.value = false
  stopPicking()
}

let lastToggleTime = 0
const togglePanel = () => {
  const now = Date.now()
  if (now - lastToggleTime < 250) return
  lastToggleTime = now

  if (isVisible.value) {
    closePanel()
  } else {
    openPanel()
  }
}

// 拖拽面板逻辑
const startDrag = (e: MouseEvent) => {
  isDragging = true
  dragStartMouse = { x: e.clientX, y: e.clientY }
  dragStartPos = { x: panelPosition.value.x, y: panelPosition.value.y }
  document.addEventListener('mousemove', onDragging)
  document.addEventListener('mouseup', stopDrag)
}

const onDragging = (e: MouseEvent) => {
  if (!isDragging) return
  const dx = e.clientX - dragStartMouse.x
  const dy = e.clientY - dragStartMouse.y
  const maxX = window.innerWidth - 460
  const maxY = window.innerHeight - 100
  panelPosition.value = {
    x: Math.min(Math.max(dragStartPos.x + dx, 10), Math.max(maxX, 10)),
    y: Math.min(Math.max(dragStartPos.y + dy, 10), Math.max(maxY, 10))
  }
}

const stopDrag = () => {
  isDragging = false
  document.removeEventListener('mousemove', onDragging)
  document.removeEventListener('mouseup', stopDrag)
}

// 快捷键全局监听 (Alt + X 与 Esc，捕获阶段)
const handleGlobalKeydown = (e: KeyboardEvent) => {
  const isAltX = e.altKey && (e.key.toLowerCase() === 'x' || e.code === 'KeyX')
  if (isAltX) {
    e.preventDefault()
    e.stopPropagation()
    togglePanel()
  } else if (isVisible.value && (e.key === 'Escape' || e.code === 'Escape')) {
    e.preventDefault()
    closePanel()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown, { capture: true })
  window.addEventListener('sqm:toggle-teleprompter', togglePanel)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleGlobalKeydown, { capture: true })
  window.removeEventListener('sqm:toggle-teleprompter', togglePanel)
  removeHighlightElements()
})
</script>

<style scoped>
.teleprompter-floating-panel {
  position: fixed;
  width: 440px;
  max-width: calc(100vw - 24px);
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14), 0 2px 6px rgba(99, 102, 241, 0.08);
  z-index: 999999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: auto;
  animation: modalPop 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalPop {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Header */
.panel-header {
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: move;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}

.drag-handle {
  display: flex;
  align-items: center;
  cursor: grab;
  padding: 2px;
}

.panel-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
}

.hotkey-badge {
  font-family: monospace;
  font-size: 10.5px;
  font-weight: 600;
  padding: 0 4px;
  height: 18px;
  line-height: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.mode-toggle-group {
  display: inline-flex;
  white-space: nowrap;
}

.mode-toggle-group :deep(.el-radio-button__inner) {
  padding: 3px 8px;
  font-size: 11.5px;
  white-space: nowrap;
}

.mode-btn-content {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.close-btn {
  color: #94a3b8;
  font-size: 15px;
  padding: 2px;
}
.close-btn:hover {
  color: #ef4444;
}

/* Body */
.panel-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(85vh - 50px);
  overflow-y: auto;
}

/* 偏好控制单行 */
.preferences-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 5px 10px;
}

.pref-left,
.pref-right {
  display: flex;
  align-items: center;
  gap: 5px;
}

.pref-label {
  font-size: 11.5px;
  color: #64748b;
  cursor: help;
}

.word-limit-input {
  width: 82px;
}

.word-limit-input :deep(.el-input__inner) {
  font-size: 11.5px;
  padding-left: 6px;
}

.no-code-label {
  font-size: 11.5px;
  color: #b45309;
  font-weight: 600;
  cursor: help;
}

/* 需求输入区 */
.prompt-input-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.section-sub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sub-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sub-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
}

.user-prompt-textarea :deep(textarea) {
  font-family: inherit;
  font-size: 12px;
  line-height: 1.45;
  background-color: #fafafa;
  border-radius: 6px;
  padding: 7px 9px;
  border-color: #e2e8f0;
}
.user-prompt-textarea :deep(textarea:focus) {
  background-color: #ffffff;
  border-color: #6366f1;
}

/* 常用指令胶囊 */
.favorites-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.fav-pill-tag {
  cursor: pointer;
  border-radius: 5px;
  font-size: 11px;
  user-select: none;
  transition: all 0.1s ease;
}
.fav-pill-tag:hover {
  border-color: #6366f1;
  color: #4f46e5;
  background-color: #f5f3ff;
}

/* 信标区域 */
.beacons-cart-section {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.cart-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 600;
  color: #1e293b;
}

.beacons-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.beacon-chip-card {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #ffffff;
  border: 1px solid #c7d2fe;
  padding: 3px 6px;
  border-radius: 5px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.beacon-chip-card:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.18);
}

.beacon-badge {
  background: #6366f1;
  color: #ffffff;
  font-family: monospace;
  font-weight: 700;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
}

.beacon-comp {
  font-weight: 600;
  color: #1e293b;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.beacon-snippet {
  color: #64748b;
  font-size: 10.5px;
  max-width: 80px;
}

.beacon-del-btn {
  padding: 0 2px;
  font-size: 11px;
  color: #94a3b8;
}
.beacon-del-btn:hover {
  color: #ef4444;
}

.empty-beacons-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  color: #94a3b8;
  font-size: 11px;
}

/* 底部操作 */
.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 2px;
}

.footer-left-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.clear-all-btn {
  font-size: 12px;
  padding: 8px 12px;
}

.auto-clear-check {
  font-size: 11px;
  color: #64748b;
  margin-right: 2px;
}

.copy-prompt-btn {
  flex: 1;
  font-weight: 600;
  letter-spacing: 0.3px;
}

/* 画像 Tooltip */
.beacon-portrait-box {
  padding: 2px;
}

.portrait-head {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #1e293b;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f1f5f9;
}

.portrait-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
}

.portrait-item {
  display: flex;
  align-items: baseline;
  gap: 5px;
}

.portrait-item.full-col {
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.p-k {
  color: #64748b;
  font-weight: 600;
  min-width: 55px;
}

.p-v {
  color: #0f172a;
}

.font-bold {
  font-weight: 600;
}

.font-mono {
  font-family: monospace;
  font-size: 10.5px;
}

.text-break {
  word-break: break-all;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.text-muted {
  color: #475569;
}

.p-code {
  background: #f1f5f9;
  color: #4338ca;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 10px;
  word-break: break-all;
  display: block;
  width: 100%;
}
</style>
