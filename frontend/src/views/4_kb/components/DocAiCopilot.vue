<template>
  <teleport to="body" v-if="dialogVisible">
    <div
      ref="paletteRef"
      class="ai-palette-window"
      :class="{ 'is-collapsed': isCollapsed, 'is-dragging': isDragging }"
      :style="paletteStyle"
    >
      <!-- 调色盘顶栏 (极简拖拽与控制栏) -->
      <div class="palette-header" @mousedown="onHeaderMouseDown">
        <div class="palette-header-left">
          <span class="palette-drag-grip" title="按住拖拽至屏幕任意位置">⋮⋮</span>
          <span class="palette-sparkle">✨</span>
          <span class="palette-title">AI 智写</span>
        </div>

        <div class="palette-header-right">
          <!-- 最小化/折叠开关 -->
          <button
            type="button"
            class="palette-ctrl-btn"
            @click.stop="isCollapsed = !isCollapsed"
            :title="isCollapsed ? '展开面板' : '折叠面板'"
          >
            <span>{{ isCollapsed ? '🗖' : '—' }}</span>
          </button>
          <!-- 关闭 -->
          <button
            type="button"
            class="palette-ctrl-btn close"
            @click.stop="handleCancel"
            title="关闭伴侣"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- 调色盘主体内容 (折叠时收起) -->
      <div class="palette-body" v-show="!isCollapsed">
        <div class="copilot-container">
          <!-- 1. 一体化沉浸式输入卡片 (对齐 Alt+X 交互：信标内联编辑 + 下方信标清单) -->
          <div class="command-card">
            <!-- 需求描述小标题栏 (含清空输入与存为预设) -->
            <div class="prompt-header-bar">
              <span class="prompt-header-title">
                <el-icon><EditPen /></el-icon>
                <span>需求描述</span>
              </span>
              <div class="prompt-header-actions">
                <button
                  v-if="promptText.trim()"
                  type="button"
                  class="prompt-action-link"
                  @click="handleClearPrompt"
                  title="清空当前输入文本"
                >
                  清空
                </button>
                <button
                  type="button"
                  class="prompt-action-link primary"
                  @click="openAddPresetDialog"
                  title="存为快捷预设指令"
                >
                  存为预设
                </button>
              </div>
            </div>

            <!-- 需求输入框 textarea (支持直接编辑 【信标 1】 【信标 2】 等并与文字混编) -->
            <textarea
              ref="promptTextareaRef"
              v-model="promptText"
              class="command-textarea"
              placeholder="输入需求描述（结合【信标】进行编写，如：【信标 1】 【信标 2】 进行优化）..."
              rows="3"
              @keydown.ctrl.enter="handleStartGenerate"
            ></textarea>

            <!-- 快捷指令预设池 (简洁紧凑，彻底杜绝换行截断与废话) -->
            <div class="preset-track-wrap">
              <div class="preset-scroll-track">
                <div
                  v-for="p in promptPresets"
                  :key="p.id"
                  class="preset-pill-item"
                >
                  <span
                    class="preset-pill"
                    :class="{ 'is-custom': !p.is_system }"
                    :title="p.prompt"
                    @click="applyPreset(p)"
                  >
                    {{ p.name }}
                  </span>
                  <div class="preset-pill-actions">
                    <el-icon
                      class="preset-action-btn edit-btn"
                      title="编辑此指令"
                      @click.stop="openEditPresetDialog(p)"
                    >
                      <Edit />
                    </el-icon>
                    <el-icon
                      class="preset-action-btn del-btn"
                      title="删除此指令"
                      @click.stop="deletePreset(p.id, p.name)"
                    >
                      <Close />
                    </el-icon>
                  </div>
                </div>

                <!-- 新增快捷指令标签 -->
                <span
                  class="preset-pill add-pill"
                  @click="openAddPresetDialog"
                  title="新增自定义快捷指令"
                >
                  <el-icon><Plus /></el-icon>
                  <span>增加指令</span>
                </span>
              </div>
            </div>

            <!-- 信标清单 (严格对齐 Alt+X 规范，展示在指令下方) -->
            <div v-if="beaconListWithTags.length > 0" class="beacons-cart-section">
              <div class="cart-header">
                <span class="cart-title">
                  <el-icon color="#6366f1"><Location /></el-icon>
                  <span>信标清单 ({{ beaconListWithTags.length }})</span>
                </span>
                <button
                  type="button"
                  class="cart-clear-btn"
                  @click="handleClearAllBeacons"
                  title="清空全部信标"
                >
                  清空
                </button>
              </div>

              <!-- 信标列表条目 -->
              <div class="beacons-list">
                <div
                  v-for="b in beaconListWithTags"
                  :key="b.id"
                  class="beacon-chip-card"
                  :title="`[${b.sectionName}] 行#${b.numStr} · ${b.typeName}\n${b.fullText}`"
                  @mouseenter="emit('highlight-beacon', { id: b.id, highlight: true })"
                  @mouseleave="emit('highlight-beacon', { id: b.id, highlight: false })"
                >
                  <span class="beacon-badge">{{ b.tag }}</span>
                  <span class="beacon-comp" v-if="b.sectionName">{{ b.sectionName }}</span>
                  <span class="beacon-line-tag">#{{ b.numStr }}</span>
                  <span class="beacon-snippet text-truncate">{{ b.previewText }}</span>
                  <button
                    type="button"
                    class="beacon-del-btn"
                    @click.stop="handleDeleteBeacon(b.id)"
                    title="移除此信标"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>

            <!-- 单纯选区时的紧凑感知条 (未选信标时) -->
            <div v-else-if="activeSelectedText" class="beacons-cart-section is-single">
              <div class="cart-header">
                <span class="cart-title">
                  <span class="pin-icon">📌</span>
                  <span>当前选区 ({{ activeSelectedText.length }}字)</span>
                </span>
                <span class="beacon-snippet text-truncate" :title="activeSelectedText">
                  "{{ activeSelectedText.slice(0, 24) + (activeSelectedText.length > 24 ? '…' : '') }}"
                </span>
              </div>
            </div>

            <!-- 卡片底栏：一键复制需求与信标发给 IDE，或粘贴 IDE 内容 -->
            <div class="command-action-bar">
              <div class="action-left">
                <button
                  v-if="promptText.trim()"
                  type="button"
                  class="action-clear-btn"
                  @click="handleClearPrompt"
                  title="一键清空需求描述"
                >
                  <el-icon><Delete /></el-icon>
                  <span>清空</span>
                </button>
                <span v-else class="rag-hint">
                  💡 复制后在 IDE 提问，再粘贴回此处
                </span>
              </div>

              <div class="action-right">
                <button
                  type="button"
                  class="action-btn pull-ide-btn"
                  @click="syncIdePreview(false)"
                  title="从后端检查并拉取 IDE 推送的最新规程草稿进入审查"
                >
                  <el-icon><Refresh /></el-icon>
                  <span>同步 IDE 推送</span>
                </button>
                <button
                  type="button"
                  class="action-btn paste-ide-btn"
                  @click="handlePasteIdeResult"
                  title="从剪贴板读取 IDE 中生成的内容进入下方审查与就地编辑"
                >
                  <el-icon><Download /></el-icon>
                  <span>粘贴 IDE 内容</span>
                </button>
                <button
                  type="button"
                  class="action-btn copy-prompt-btn"
                  @click="copyPromptForIde"
                  title="一键复制完整需求与信标，直接在 IDE 聊天框中粘贴发送"
                >
                  <el-icon><CopyDocument /></el-icon>
                  <span>一键复制需求与信标</span>
                </button>
              </div>
            </div>
          </div>

      <!-- 2. 无界通透审查预览区 (支持直接就地编辑修改内容与表格！) -->
      <div class="preview-card" v-if="generatedContent">
        <div class="preview-status-strip">
          <div class="strip-left">
            <span class="preview-dot live"></span>
            <span class="strip-title">生成结果审查</span>
            <span class="edit-tip-badge" title="支持在下方直接点击修改文字与公差表格">✏️ 支持直接就地修改</span>
          </div>
          <div class="strip-right">
            <button class="strip-btn" @click="handlePasteIdeResult" title="从剪贴板重新粘贴外部内容到此处预览审查">
              <el-icon><Download /></el-icon> 重新粘贴
            </button>
            <button class="strip-btn danger" @click="handleClearPreview" title="放弃并清空审查内容">
              <el-icon><Close /></el-icon> 放弃
            </button>
          </div>
        </div>

        <div class="preview-scroll-body">
          <!-- 就地可编辑的预览区：满足“如果需要，我再改完，确认是否写入” -->
          <div
            class="preview-html is-editable"
            contenteditable="true"
            @input="onPreviewInput"
            v-html="generatedContent"
            title="可直接在此处点击修改内容与表格，确认满意后再写入正文"
          ></div>
        </div>
      </div>

      <!-- 3. 底部人工决策动作栏 (仅在有内容时出现，信噪比极高) -->
      <div class="modal-footer" v-if="generatedContent">
        <div class="footer-note">
          <span class="safe-guard-hint">
            🛡️ 作用范围已锁定，写入时其余章节 100% 保持不变。
          </span>
        </div>
        <div class="footer-actions">
          <el-button @click="handleClearPreview" size="small">放弃</el-button>
          <el-button
            type="info"
            plain
            size="small"
            @click="handleCopyResult"
            title="复制审查内容至剪贴板"
          >
            📋 复制内容
          </el-button>
          <el-button
            type="primary"
            size="small"
            class="confirm-btn lock-confirm-btn"
            @click="confirmInsert('replace')"
            title="确认写入并精准替换目标段落"
          >
            ✅ 确认写入正文
          </el-button>
        </div>
      </div>
    </div>
  </div>
  </div>
  </teleport>

  <!-- 4. 快捷指令收藏/编辑弹窗 (持久化至 data/kb_prompt_presets.json) -->
  <el-dialog
    v-model="editPresetVisible"
    :title="presetForm.id ? '✏️ 编辑快捷指令' : '⭐ 新增快捷指令'"
    width="480px"
    append-to-body
    class="preset-edit-dialog"
  >
    <div class="preset-edit-form">
      <div class="form-row">
        <label class="form-label">指令简称（展示在快捷标签条上，建议 4~8 字）：</label>
        <el-input
          v-model="presetForm.name"
          placeholder="例如：⚙️ 减速机首检 SOP"
          maxlength="20"
          show-word-limit
        />
      </div>
      <div class="form-row" style="margin-top: 14px;">
        <label class="form-label">完整 Prompt 提示词要求：</label>
        <el-input
          v-model="presetForm.prompt"
          type="textarea"
          :rows="4"
          placeholder="输入触发该指令时发送给 AI 的详细专业要求..."
        />
      </div>
      <div class="preset-sync-tip">
        📁 保存后将自动持久化至 <code>data/kb_prompt_presets.json</code>，随 Git 跨电脑无缝同步。
      </div>
    </div>
    <template #footer>
      <el-button @click="editPresetVisible = false">取消</el-button>
      <el-button type="primary" :loading="savingPreset" @click="handleSavePreset">保存并同步</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Document, CopyDocument, Download, Refresh, Star, Close, Edit, Plus, Check, EditPen, Location, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { BeaconItem } from '@/components/editor/TiptapEditor.vue'

interface PromptPreset {
  id: string
  name: string
  prompt: string
  is_system?: boolean
}

interface ScopeItem {
  label: string
  value: string
  icon: string
  type: 'doc' | 'section' | 'table' | 'code'
}

interface InitialTarget {
  targetType?: string
  targetName?: string
  targetSection?: string
  selectedText?: string
  headingLevel?: number
  range?: { from: number; to: number }
}

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    docId?: number
    docTitle?: string
    selectedText?: string
    docContent?: string
    initialTarget?: InitialTarget
    beacons?: BeaconItem[]
  }>(),
  {
    docId: undefined,
    docTitle: '',
    selectedText: '',
    docContent: '',
    initialTarget: () => ({}),
    beacons: () => []
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'confirm-insert', payload: { html: string; mode: 'insert' | 'replace'; targetSection?: string; range?: { from: number; to: number } }): void
  (e: 'refresh-doc'): void
  (e: 'remove-beacon', id: string): void
  (e: 'clear-beacons'): void
  (e: 'highlight-beacon', payload: { id: string; highlight: boolean }): void
}>()

// 将选中的信标按照章节分组展示 (问 4: 分章节展示信标)
const groupedBeacons = computed(() => {
  if (!props.beacons || props.beacons.length === 0) return []
  const groups: { sectionName: string; items: BeaconItem[] }[] = []
  const groupMap = new Map<string, BeaconItem[]>()

  props.beacons.forEach(b => {
    const sec = b.sectionName || '引言 / 概述'
    if (!groupMap.has(sec)) {
      groupMap.set(sec, [])
    }
    groupMap.get(sec)!.push(b)
  })

  groupMap.forEach((items, sectionName) => {
    groups.push({ sectionName, items })
  })

  return groups
})

const selectedScope = ref<string>('ALL')

const activeSelectedText = computed(() => {
  return (props.initialTarget?.selectedText || props.selectedText || '').trim()
})

const headingScopes = computed(() => {
  if (!props.docContent) return []
  try {
    const parser = new DOMParser()
    const dom = parser.parseFromString(props.docContent, 'text/html')
    const headings = dom.querySelectorAll('h1, h2, h3')
    const list: { label: string; value: string; icon: string }[] = []
    headings.forEach((h, idx) => {
      const text = h.textContent?.trim()
      if (text) {
        const tag = h.tagName.toLowerCase()
        list.push({
          label: text,
          value: `heading_${idx}_${text}`,
          icon: tag === 'h1' ? '🏷️' : tag === 'h2' ? '📑' : '▫️'
        })
      }
    })
    return list
  } catch {
    return []
  }
})

const selectedHeadingScope = ref('')
const handleSelectHeadingScope = (val: string) => {
  if (val) {
    selectedScope.value = val
  }
}

const applySelectionPrompt = (action: 'polish' | 'ctq' | 'table' | '8d') => {
  switch (action) {
    case 'polish':
      promptText.value = '对当前选区文本进行质量工程规范化润色与精简，消除口语化表达，突出关键质量控制要求'
      break
    case 'ctq':
      promptText.value = '深入分析当前选区技术要求，提取核心 CTQ 特征项目，并生成规范的公差上下限与检验要求表格'
      break
    case 'table':
      promptText.value = '将当前选区的内容结构化转化为 SQM 标准质量表格，包含检查项目、公差标准与判定规则'
      break
    case '8d':
      promptText.value = '针对选区描述的质量问题，推演标准 8D 分析：应急遏制措施(D3)、根本原因(D4)及永久防错措施(D5)'
      break
  }
  handleStartGenerate()
}

const applyTablePrompt = (action: 'ctq' | 'audit' | 'expand' | '8d') => {
  switch (action) {
    case 'ctq':
      promptText.value = '为当前质量表格补充严格的 CTQ 尺寸公差上下限(USL/LSL)、抽样频次与阻断处置准则'
      break
    case 'audit':
      promptText.value = '审核当前质量表格中的检验项目与公差标准是否符合 SQM 汽车级零部件准入规范，指出不合理项并修正'
      break
    case 'expand':
      promptText.value = '扩充当前表格的工序控制点，增加外观检验、材料硬度及三坐标测量要素'
      break
    case '8d':
      promptText.value = '基于当前表格中的不良项目，生成对应的 8D 根本原因分析与纠正防错对策表'
      break
  }
  handleStartGenerate()
}

const availableScopes = computed<ScopeItem[]>(() => {
  const list: ScopeItem[] = [
    { label: '全篇规程整体 (整体润色/续写)', value: 'ALL', icon: '🌐', type: 'doc' }
  ]

  // 选中文本
  if (activeSelectedText.value) {
    list.push({
      label: `当前选中文本 (${activeSelectedText.value.substring(0, 16)}...)`,
      value: 'SELECTION',
      icon: '📌',
      type: 'section'
    })
  }

  // 初始表格靶向锁定
  if (props.initialTarget?.targetSection === 'TABLES') {
    list.push({
      label: '正文质量公差表格 (当前激活)',
      value: 'TABLES',
      icon: '📊',
      type: 'table'
    })
  }

  if (props.docContent) {
    try {
      const parser = new DOMParser()
      const dom = parser.parseFromString(props.docContent, 'text/html')

      // 解析章节 H1, H2, H3
      const headings = dom.querySelectorAll('h1, h2, h3')
      headings.forEach((h, idx) => {
        const text = h.textContent?.trim()
        if (text) {
          const tag = h.tagName.toLowerCase()
          list.push({
            label: text,
            value: `heading_${idx}_${text}`,
            icon: tag === 'h1' ? '🏷️' : tag === 'h2' ? '📑' : '▫️',
            type: 'section'
          })
        }
      })

      // 解析表格 (若未添加)
      const tables = dom.querySelectorAll('table')
      if (tables.length > 0 && !list.some(s => s.value === 'TABLES')) {
        list.push({
          label: `正文质量公差表格 (共 ${tables.length} 个)`,
          value: 'TABLES',
          icon: '📊',
          type: 'table'
        })
      }

      // 解析代码/公差参数块
      const codes = dom.querySelectorAll('pre, code')
      if (codes.length > 0) {
        list.push({
          label: '参数代码与技术规则块',
          value: 'CODES',
          icon: '💻',
          type: 'code'
        })
      }
    } catch {}
  }

  // 如果 initialTarget 指定了某章节/目标但不在上述列表，自动补齐
  if (props.initialTarget?.targetSection && !list.some(s => s.value === props.initialTarget?.targetSection)) {
    const isTable = props.initialTarget.targetSection === 'TABLES'
    list.push({
      label: props.initialTarget.targetName || props.initialTarget.targetSection,
      value: props.initialTarget.targetSection,
      icon: isTable ? '📊' : '📑',
      type: isTable ? 'table' : 'section'
    })
  }

  return list
})

const currentScopeObj = computed<ScopeItem>(() => {
  const found = availableScopes.value.find(s => s.value === selectedScope.value)
  if (found) return found
  return {
    label: props.initialTarget?.targetName || (selectedScope.value === 'ALL' ? '全篇规程整体' : selectedScope.value),
    value: selectedScope.value,
    icon: selectedScope.value === 'TABLES' ? '📊' : selectedScope.value === 'ALL' ? '🌐' : '📑',
    type: (selectedScope.value === 'TABLES' ? 'table' : selectedScope.value === 'ALL' ? 'doc' : 'section') as any
  }
})

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const paletteRef = ref<HTMLElement | null>(null)
const palettePos = ref({ x: typeof window !== 'undefined' ? Math.max(20, window.innerWidth - 560) : 1000, y: 76 })
const isDragging = ref(false)
const isCollapsed = ref(false)

const paletteStyle = computed(() => {
  return {
    left: `${Math.max(16, Math.min(window.innerWidth - 120, palettePos.value.x))}px`,
    top: `${Math.max(16, Math.min(window.innerHeight - 80, palettePos.value.y))}px`,
    width: isCollapsed.value ? '280px' : '530px'
  }
})

let dragStartX = 0
let dragStartY = 0
let initialPaletteX = 0
let initialPaletteY = 0

const onHeaderMouseDown = (e: MouseEvent) => {
  if ((e.target as HTMLElement).closest('.palette-ctrl-btn')) return
  isDragging.value = true
  dragStartX = e.clientX
  dragStartY = e.clientY
  initialPaletteX = palettePos.value.x
  initialPaletteY = palettePos.value.y

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

const onMouseMove = (e: MouseEvent) => {
  if (!isDragging.value) return
  const dx = e.clientX - dragStartX
  const dy = e.clientY - dragStartY
  palettePos.value = {
    x: initialPaletteX + dx,
    y: initialPaletteY + dy
  }
}

const onMouseUp = () => {
  isDragging.value = false
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

// 自动响应外界目标切换 (信标 1/2/3 实时联动，绝不阻塞正文点击)
watch(
  () => props.initialTarget,
  (newTarget) => {
    if (!newTarget) return
    if (newTarget.targetSection) {
      selectedScope.value = newTarget.targetSection
    } else if (newTarget.selectedText) {
      selectedScope.value = 'SELECTION'
    } else if (newTarget.targetType === 'table') {
      selectedScope.value = 'TABLES'
    }
  },
  { deep: true, immediate: true }
)

const promptText = ref('')
const promptTextareaRef = ref<HTMLTextAreaElement | null>(null)
const generating = ref(false)
const generatedContent = ref('')
const referencedDocs = ref<string[]>([])

// 格式化信标标号与详情 (严格对齐 Alt+X 规范：【信标 1】、 【信标 2】 等)
const beaconListWithTags = computed(() => {
  return (props.beacons || []).map((b, idx) => ({
    ...b,
    tag: `【信标 ${idx + 1}】`
  }))
})

// 光标位置插入占位符 (同 Alt+X 提词器交互)
const insertTagAtCursor = (tag: string) => {
  const textarea = promptTextareaRef.value
  if (!textarea) {
    promptText.value += (promptText.value ? ' ' : '') + tag
    return
  }
  const start = textarea.selectionStart ?? promptText.value.length
  const end = textarea.selectionEnd ?? promptText.value.length
  const text = promptText.value
  const before = text.substring(0, start)
  const after = text.substring(end)
  const insertContent = (before && !before.endsWith(' ') ? ' ' : '') + tag + (after && !after.startsWith(' ') ? ' ' : '')
  promptText.value = before + insertContent + after

  nextTick(() => {
    textarea.focus()
    const newPos = before.length + insertContent.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

// 清空需求输入
const handleClearPrompt = () => {
  promptText.value = ''
  if (promptTextareaRef.value) {
    promptTextareaRef.value.focus()
  }
}

// 放弃/清空审查内容
const handleClearPreview = () => {
  generatedContent.value = ''
}

// 移除单个信标 (同步剔除输入框中对应的 【信标 X】 占位符)
const handleDeleteBeacon = (id: string) => {
  const b = beaconListWithTags.value.find(item => item.id === id)
  if (b) {
    promptText.value = promptText.value.replace(new RegExp(`\\s*${b.tag}\\s*`, 'g'), ' ').replace(/\s+/g, ' ').trim()
  }
  emit('remove-beacon', id)
}

// 清空全部信标 (同步剔除输入框中所有的信标占位符)
const handleClearAllBeacons = () => {
  promptText.value = promptText.value.replace(/【信标\s*\d+】/g, '').replace(/\s+/g, ' ').trim()
  emit('clear-beacons')
}

// 快捷预设指令列表 (从后端 data/kb_prompt_presets.json 动态同步)
const promptPresets = ref<PromptPreset[]>([])
const editPresetVisible = ref(false)
const savingPreset = ref(false)
const presetForm = ref<{ id?: string; name: string; prompt: string }>({
  name: '',
  prompt: ''
})

const trackRef = ref<HTMLElement | null>(null)
const handleTrackWheel = (e: WheelEvent) => {
  if (trackRef.value && e.deltaY) {
    trackRef.value.scrollLeft += e.deltaY
  }
}

// 1. 获取指令列表 (从后端 data/kb_prompt_presets.json 同步)
const fetchPromptPresets = async () => {
  try {
    const res = await fetch('/api/kb/prompts')
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        promptPresets.value = data
        return
      }
    }
  } catch {}
}

// 2. 点击标签应用 Prompt (保留已有信标，自然组合为 Prompt)
const applyPreset = (preset: PromptPreset) => {
  const pText = preset.prompt || preset.name.replace(/^[^\s]+\s*/, '')
  const tags = (promptText.value.match(/【信标\s*\d+】/g) || []).join(' ')
  if (tags) {
    promptText.value = `${tags} ${pText}`
  } else if (promptText.value.trim()) {
    promptText.value += '\n' + pText
  } else {
    promptText.value = pText
  }
  nextTick(() => {
    if (promptTextareaRef.value) {
      promptTextareaRef.value.focus()
      promptTextareaRef.value.setSelectionRange(promptText.value.length, promptText.value.length)
    }
  })
}

// 3. 打开收藏/新建指令弹窗
const openAddPresetDialog = () => {
  presetForm.value = {
    name: '',
    prompt: promptText.value.trim()
  }
  editPresetVisible.value = true
}

// 4. 打开编辑指令弹窗
const openEditPresetDialog = (preset: PromptPreset) => {
  presetForm.value = {
    id: preset.id,
    name: preset.name,
    prompt: preset.prompt
  }
  editPresetVisible.value = true
}

// 5. 保存指令至 data/kb_prompt_presets.json
const handleSavePreset = async () => {
  if (!presetForm.value.name.trim() || !presetForm.value.prompt.trim()) {
    ElMessage.warning('请填写指令简称和完整的提示词')
    return
  }
  savingPreset.value = true
  try {
    const res = await fetch('/api/kb/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(presetForm.value)
    })
    if (res.ok) {
      ElMessage.success('已保存并持久化至 data/kb_prompt_presets.json！')
      editPresetVisible.value = false
      await fetchPromptPresets()
    } else {
      throw new Error(res.statusText)
    }
  } catch (err: any) {
    ElMessage.error(`保存指令失败: ${err.message || '网络异常'}`)
  } finally {
    savingPreset.value = false
  }
}

// 6. 删除指令
const deletePreset = async (presetId: string, presetName?: string) => {
  try {
    await ElMessageBox.confirm(`确定要删除指令「${presetName || presetId}」吗？（将同步更新 data/kb_prompt_presets.json）`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    const res = await fetch(`/api/kb/prompts/${presetId}`, { method: 'DELETE' })
    if (res.ok) {
      ElMessage.success('已删除该指令并同步文件')
      await fetchPromptPresets()
    }
  } catch {}
}

let idePollTimer: any = null
let lastSyncedTimestamp: number | null = null

// 一键拉取 IDE 生成的审查内容 (支持静默轮询与主动点击)
const syncIdePreview = async (silent = false) => {
  try {
    const res = await fetch(`/api/kb/copilot/preview?doc_id=${props.docId || 'default'}`)
    if (res.ok) {
      const data = await res.json()
      if (data && data.html) {
        const isNewer = data.updated_at && (lastSyncedTimestamp === null || data.updated_at > lastSyncedTimestamp)
        if (isNewer || !silent || !generatedContent.value) {
          if (data.updated_at) {
            lastSyncedTimestamp = data.updated_at
          }
          if (generatedContent.value !== data.html) {
            generatedContent.value = data.html
            if (silent) {
              ElMessage.success('⚡ 已自动接收到 IDE 推送的最新规程！请在下方审查')
            }
          }
          if (!silent) {
            ElMessage.success('已成功同步 IDE 生成的规程！请在下方预览审查，满意后点击「确认写入正文」')
          }
          return true
        }
      }
    }
  } catch {}
  if (!silent) {
    ElMessage.info('暂未检测到 IDE 推送的审查内容，您也可以点击左下角「粘贴 IDE 内容」')
  }
  return false
}

// 开启 2.5 秒轻量静默轮询 (只要面板打开就实时监听 IDE 推送)
const startIdePoll = () => {
  stopIdePoll()
  syncIdePreview(true)
  idePollTimer = setInterval(() => {
    if (!dialogVisible.value || generating.value) return
    syncIdePreview(true)
  }, 2500)
}

const stopIdePoll = () => {
  if (idePollTimer) {
    clearInterval(idePollTimer)
    idePollTimer = null
  }
}

watch(
  () => [props.modelValue, props.initialTarget, props.beacons] as const,
  ([visible, target, beacons]) => {
    if (visible) {
      isCollapsed.value = false
      fetchPromptPresets()
      nextTick(() => {
        if (promptTextareaRef.value) {
          promptTextareaRef.value.focus()
        }
      })
      const sel = target?.selectedText || props.selectedText
      if (beacons && beacons.length > 0) {
        // 如果输入框为空，自动注入格式化后的信标占位符
        const tags = beaconListWithTags.value.map(b => b.tag).join(' ')
        if (!promptText.value.trim()) {
          promptText.value = `${tags} 进行优化`
        } else {
          // 如果已有内容，且有新捕获的信标，插入到光标处
          beaconListWithTags.value.forEach(b => {
            if (!promptText.value.includes(b.tag)) {
              insertTagAtCursor(b.tag)
            }
          })
        }
      } else if (sel && sel.trim()) {
        selectedScope.value = 'SELECTION'
        if (!promptText.value) {
          promptText.value = '对选区文本进行质量工程规范化润色与精简'
        }
      } else if (target?.targetSection) {
        selectedScope.value = target.targetSection
        if (target.targetName && target.targetName !== '全篇规程整体' && !promptText.value) {
          promptText.value = `针对【${target.targetName}】，补充完善质量控制要求与检验规范`
        }
      } else {
        selectedScope.value = 'ALL'
        if (!promptText.value) {
          promptText.value = '根据当前质量知识库标准，帮我写一份现场检验作业指导书(SOP)'
        }
      }
      // 启动对 IDE 推送的实时轮询监听 (2.5 秒静默检测)
      startIdePoll()
    } else {
      generating.value = false
      stopIdePoll()
    }
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  fetchPromptPresets()
})

onBeforeUnmount(() => {
  stopIdePoll()
})

// 发起流式生成
const handleStartGenerate = async () => {
  if (!promptText.value.trim() || generating.value) return

  generating.value = true
  generatedContent.value = ''
  referencedDocs.value = []

  let selectedTextPayload = props.selectedText || props.initialTarget?.selectedText || ''
  if (beaconListWithTags.value.length > 0) {
    const beaconLines = beaconListWithTags.value.map(b => {
      return `${b.tag}\n所在章节：${b.sectionName || '正文'}\n定位行号：#${b.numStr} · ${b.typeName}\n包含文本：${b.fullText}`
    }).join('\n\n')
    selectedTextPayload = `### [附带定位信标详情 - 共 ${beaconListWithTags.value.length} 个] ###\n\n${beaconLines}`
  }

  try {
    const res = await fetch('/api/kb/ai-copilot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prompt: promptText.value.trim(),
        doc_id: props.docId,
        selected_text: selectedTextPayload,
        scope: selectedScope.value,
        scope_name: currentScopeObj.value.label
      })
    })

    if (!res.ok) {
      throw new Error(`服务响应异常: ${res.statusText}`)
    }

    if (!res.body) {
      throw new Error('未收到流式数据传输通道')
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6)
          if (dataStr === '[DONE]') {
            break
          }
          try {
            const parsed = jsonParseSafe(dataStr)
            if (parsed.type === 'meta' && parsed.references) {
              referencedDocs.value = parsed.references
            } else if (parsed.type === 'chunk' && parsed.text) {
              generatedContent.value += parsed.text
            }
          } catch {
            // 忽略碎片解析异常
          }
        }
      }
    }
  } catch (err: any) {
    ElMessage.error(`AI 智写遇到异常: ${err.message || '网络连接错误'}`)
  } finally {
    generating.value = false
  }
}

const jsonParseSafe = (str: string) => {
  try {
    return JSON.parse(str)
  } catch {
    return {}
  }
}

// 复制生成内容到剪贴板
const handleCopyResult = async () => {
  if (!generatedContent.value) return
  try {
    await navigator.clipboard.writeText(generatedContent.value)
    ElMessage.success('已复制生成内容到剪贴板！')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = generatedContent.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制生成内容到剪贴板！')
  }
}

// 确认填入正文 (支持全篇与特定章节/表格靶向重写，绝不乱覆盖)
const confirmInsert = (mode: 'insert' | 'replace') => {
  if (!generatedContent.value) return
  emit('confirm-insert', {
    html: generatedContent.value,
    mode,
    targetSection: selectedScope.value,
    range: props.initialTarget?.range
  })
  dialogVisible.value = false
  ElMessage.success(
    selectedScope.value === 'SELECTION'
      ? '已精准替换选区正文 (其余全文100%保持原样)'
      : selectedScope.value !== 'ALL'
        ? `已成功更新锁定目标【${currentScopeObj.value.label}】(其余全文绝不覆盖)`
        : '已填入正文并触发自动保存'
  )
}

// 用户在审查区就地打字/编辑修改
const onPreviewInput = (e: Event) => {
  const el = e.target as HTMLElement
  if (el) {
    generatedContent.value = el.innerHTML
  }
}

// 一键复制 IDE 专用 Prompt (对齐标准结构，包含需求与已选信标详情画像)
const copyPromptForIde = async () => {
  const lines: string[] = ['要求是：']
  lines.push(promptText.value.trim() || '请针对附带的定位信标进行针对性质量优化与技术标准核对。')

  if (beaconListWithTags.value.length > 0) {
    lines.push('=====================')
    lines.push(`### [附带定位信标详情 - 共 ${beaconListWithTags.value.length} 个] ###`)
    beaconListWithTags.value.forEach(b => {
      lines.push(`${b.tag}`)
      lines.push(`所属章节：${b.sectionName || '规程正文'}`)
      lines.push(`定位行号：#${b.numStr} · ${b.typeName}`)
      lines.push(`包含文本：${b.fullText ? `"${b.fullText}"` : '(无直接文本)'}`)
    })
  } else if (activeSelectedText.value) {
    lines.push('=====================')
    lines.push(`【参考选区文本】\n${activeSelectedText.value}`)
  }

  lines.push('\n【输出要求】')
  lines.push('请作为 SQM 质量专家输出规范严谨的质量技术规程 HTML 片段（含 <h2>、<p>、<table border="1">、<ul> 等），支持直接写入编辑器。')

  const promptPayload = lines.join('\n')

  try {
    await navigator.clipboard.writeText(promptPayload)
    ElMessage.success('🚀 需求与信标已复制！请直接粘贴到 IDE 聊天框中发送')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = promptPayload
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('🚀 需求与信标已复制！请直接粘贴到 IDE 聊天框中发送')
  }
}

// 粘贴 IDE 内容并载入审查
const handlePasteIdeResult = async () => {
  try {
    const text = await navigator.clipboard.readText()
    if (text && text.trim()) {
      generatedContent.value = text.trim()
      ElMessage.success('已从剪贴板读取 IDE 内容，请在下方预览审查')
      return
    }
  } catch {}

  // 降级：如果浏览器受安全限制无法读取剪贴板，弹出输入框让用户按 Ctrl+V 粘贴
  try {
    const { value } = await ElMessageBox.prompt('请在此处按 Ctrl+V 粘贴 IDE 中生成的内容：', '粘贴 IDE 生成内容', {
      inputType: 'textarea',
      confirmButtonText: '载入审查',
      cancelButtonText: '取消',
      inputPlaceholder: '在此处按 Ctrl+V 粘贴...'
    })
    if (value && value.trim()) {
      generatedContent.value = value.trim()
      ElMessage.success('已载入内容，请在下方预览审查')
    }
  } catch {}
}

// 刷新文档
const handleRefreshDoc = () => {
  emit('refresh-doc')
  ElMessage.success('已触发最新文档内容刷新')
}

const handleCancel = () => {
  dialogVisible.value = false
}
</script>

<style scoped>
/* 自由浮动非模态调色盘窗口 (零遮罩穿透 · 支持自由拖拽与折叠) */
.ai-palette-window {
  position: fixed;
  z-index: 1500;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 50px -10px rgba(15, 23, 42, 0.28), 0 0 0 1px rgba(226, 232, 240, 0.9);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
  user-select: text;
}

.ai-palette-window.is-dragging {
  cursor: grabbing !important;
  user-select: none;
  box-shadow: 0 25px 65px -12px rgba(15, 23, 42, 0.38), 0 0 0 2px rgba(99, 102, 241, 0.6);
}

.palette-header {
  height: 38px;
  padding: 0 12px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: grab;
  user-select: none;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-palette-window.is-dragging .palette-header {
  cursor: grabbing;
}

.palette-header-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.palette-drag-grip {
  color: #64748b;
  font-size: 13px;
  letter-spacing: -1px;
}

.palette-sparkle {
  font-size: 14px;
}

.palette-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #f8fafc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.palette-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.palette-ctrl-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.palette-ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.palette-ctrl-btn.close:hover {
  background: #ef4444;
  color: #ffffff;
}

.palette-body {
  padding: 12px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  background: #f8fafc;
}

.palette-body::-webkit-scrollbar {
  width: 5px;
}
.palette-body::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.copilot-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 1. 一体化沉浸命令卡片 (Linear / Raycast 质感) */
.command-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.command-card:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

/* 需求描述标题栏 (对齐 Alt+X) */
.prompt-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 4px 14px;
}

.prompt-header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
}

.prompt-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prompt-action-link {
  background: transparent;
  border: none;
  font-size: 11.5px;
  color: #64748b;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 4px;
  transition: all 0.12s ease;
}

.prompt-action-link:hover {
  color: #4f46e5;
  background: #f1f5f9;
}

.prompt-action-link.primary {
  color: #4f46e5;
  font-weight: 500;
}

.prompt-action-link.primary:hover {
  color: #4338ca;
  background: #eef2ff;
}

/* 信标清单区域 (严格对齐 Alt+X 交互与视觉) */
.beacons-cart-section {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  margin: 4px 14px 10px 14px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.beacons-cart-section.is-single {
  border-style: solid;
  border-color: #e2e8f0;
  background: #fafafa;
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

.cart-clear-btn {
  background: transparent;
  border: none;
  font-size: 11px;
  color: #ef4444;
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 3px;
  transition: all 0.12s ease;
}

.cart-clear-btn:hover {
  color: #dc2626;
  background: #fee2e2;
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
  padding: 3px 8px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.beacon-chip-card:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.18);
  transform: translateY(-1px);
}

.beacon-badge {
  background: #4f46e5;
  color: #ffffff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 700;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  letter-spacing: -0.2px;
}

.beacon-comp {
  font-weight: 600;
  color: #1e293b;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.beacon-line-tag {
  font-size: 10px;
  color: #4338ca;
  background: #e0e7ff;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
}

.beacon-snippet {
  color: #64748b;
  font-size: 10.5px;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.beacon-del-btn {
  background: transparent;
  border: none;
  padding: 0 2px;
  font-size: 10.5px;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.12s ease;
}

.beacon-del-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

.safe-guard-hint {
  font-size: 11.5px;
  color: #15803d;
  background: #f0fdf4;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid #bbf7d0;
  font-weight: 500;
}

.lock-confirm-btn {
  background: #16a34a !important;
  border-color: #16a34a !important;
}

.lock-confirm-btn:hover {
  background: #15803d !important;
  border-color: #15803d !important;
}

.command-textarea {
  border: none;
  outline: none;
  width: 100%;
  resize: none;
  font-size: 13.5px;
  line-height: 1.6;
  color: #1e293b;
  background: transparent;
  padding: 10px 14px 4px 14px;
  box-sizing: border-box;
  font-family: inherit;
}

.command-textarea::placeholder {
  color: #94a3b8;
}

/* 快捷胶囊预设池 (自然自适应换行，彻底杜绝单行溢出截断) */
.preset-track-wrap {
  width: 100%;
  box-sizing: border-box;
}

.preset-scroll-track {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 14px 10px 14px;
}

.preset-track-label {
  font-size: 11.5px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
  user-select: none;
}

.preset-pill-item {
  display: inline-flex;
  align-items: center;
  position: relative;
  flex-shrink: 0;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.preset-pill-item:hover {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.preset-pill {
  white-space: nowrap;
  font-size: 11.5px;
  color: #475569;
  padding: 3px 6px 3px 9px;
  cursor: pointer;
  user-select: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.preset-pill-item:hover .preset-pill {
  color: #1e293b;
}

.preset-pill-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding-right: 5px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.preset-pill-item:hover .preset-pill-actions {
  opacity: 1;
}

.preset-action-btn {
  font-size: 11px;
  padding: 2px;
  border-radius: 3px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.12s;
}

.preset-action-btn.edit-btn:hover {
  color: #4f46e5;
  background: #e0e7ff;
}

.preset-action-btn.del-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

.preset-pill.add-pill {
  background-color: #f8fafc;
  border: 1px dashed #cbd5e1;
  color: #4f46e5;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.preset-pill.add-pill:hover {
  background-color: #eef2ff;
  border-color: #818cf8;
}

/* 命令底栏 */
.command-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-top: 1px solid #f1f5f9;
  background: #fafbfc;
  border-radius: 0 0 9px 9px;
  min-height: 42px;
}

.action-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rag-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background-color: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rag-hint {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}

.action-clear-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: transparent;
  border: none;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 4px;
  transition: all 0.12s ease;
}

.action-clear-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 4px 9px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tool-btn:hover:not(:disabled) {
  background: #f8fafc;
  color: #1e293b;
  border-color: #cbd5e1;
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tool-btn.fav-btn {
  color: #d97706;
  border-color: #fde68a;
  background: #fffbeb;
}

.tool-btn.fav-btn:hover:not(:disabled) {
  background: #fef3c7;
}

.tool-btn.sync-btn {
  color: #059669;
  border-color: #a7f3d0;
  background: #f0fdf4;
}

.tool-btn.sync-btn:hover {
  background: #dcfce7;
}

.action-btn.copy-prompt-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #4f46e5;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(79, 70, 229, 0.3);
  transition: all 0.15s ease;
}

.action-btn.copy-prompt-btn:hover {
  background: #4338ca;
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.45);
  transform: translateY(-1px);
}

.action-btn.paste-ide-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #ffffff;
  color: #475569;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 500;
  padding: 5px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn.paste-ide-btn:hover {
  background: #f8fafc;
  border-color: #6366f1;
  color: #4f46e5;
}

.edit-tip-badge {
  font-size: 10.5px;
  color: #4f46e5;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: 6px;
}

.preview-html.is-editable {
  outline: none;
  min-height: 120px;
  cursor: text;
  border-radius: 6px;
  padding: 6px 8px;
  transition: all 0.15s ease;
}

.preview-html.is-editable:focus {
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.generate-main-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #ffffff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(124, 58, 237, 0.25);
  transition: all 0.2s ease;
}

.generate-main-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(124, 58, 237, 0.35);
  opacity: 0.95;
}

.generate-main-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1.2s infinite linear;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 2. 审查预览卡片 (紧凑高质感，平滑展开) */
.preview-card {
  flex: 1;
  min-height: 140px;
  max-height: 280px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.preview-status-strip {
  height: 34px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.strip-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.preview-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #94a3b8;
}

.preview-dot.live {
  background-color: #2563eb;
  animation: pulse 1s infinite alternate;
}

@keyframes pulse {
  0% { transform: scale(0.8); opacity: 0.5; }
  100% { transform: scale(1.2); opacity: 1; }
}

.strip-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #475569;
}

.live-tag {
  font-size: 11px;
  color: #2563eb;
}

.strip-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strip-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #64748b;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s;
}

.strip-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.strip-btn.danger {
  color: #ef4444;
}

.strip-btn.danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.preview-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  font-size: 13.5px;
  line-height: 1.7;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 12.5px;
  text-align: center;
  padding: 30px;
  gap: 8px;
}

.empty-icon {
  font-size: 28px;
  opacity: 0.7;
}

.loading-wave {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}

.loading-wave span {
  width: 6px;
  height: 6px;
  background-color: #4f46e5;
  border-radius: 50%;
  animation: wave 1.2s infinite ease-in-out;
}

.loading-wave span:nth-child(2) { animation-delay: 0.2s; }
.loading-wave span:nth-child(3) { animation-delay: 0.4s; }

@keyframes wave {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.preview-html :deep(h2) {
  font-size: 16px;
  font-weight: 700;
  margin: 12px 0 6px 0;
  color: #0f172a;
}

.preview-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 12.5px;
}

.preview-html :deep(th), .preview-html :deep(td) {
  border: 1px solid #cbd5e1;
  padding: 6px 10px;
  text-align: left;
}

.preview-html :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}

/* 3. 底部操作栏 */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 4px;
}

.footer-note {
  font-size: 11.5px;
  color: #d97706;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confirm-btn {
  background: #10b981 !important;
  border-color: #10b981 !important;
  font-weight: 500;
}

.confirm-btn:hover {
  background: #059669 !important;
  border-color: #059669 !important;
}

/* 4. 指令收藏表单 */
.form-row .form-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
  display: block;
}

.preset-sync-tip {
  font-size: 11.5px;
  color: #64748b;
  margin-top: 12px;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
}

.preset-sync-tip code {
  color: #2563eb;
  font-weight: 600;
}
</style>

<style>
/* 弹窗拖拽及高阶样式穿透 */
.ai-copilot-dialog {
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 20px 48px -12px rgba(15, 23, 42, 0.2), 0 0 0 1px rgba(15, 23, 42, 0.08) !important;
}

.ai-copilot-dialog .el-dialog__header {
  cursor: move !important;
  padding: 14px 18px 10px 18px !important;
  margin-right: 0 !important;
  border-bottom: 1px solid #f1f5f9 !important;
  background: #fafbfc !important;
  user-select: none !important;
}

.ai-copilot-dialog .el-dialog__title {
  font-size: 14.5px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

.ai-copilot-dialog .el-dialog__body {
  padding: 14px 18px 16px 18px !important;
}
</style>
