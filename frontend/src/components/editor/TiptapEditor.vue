<template>
  <div class="tiptap-editor-wrap">
    <!-- 顶部排版与表格工具栏 -->
    <div class="tiptap-toolbar" v-if="!readonly">
      <!-- ✨ AI 智写助手入口 (支持智能嗅探光标选区与表格上下文) -->
      <div class="toolbar-group ai-toolbar-group" v-if="showAi">
        <button
          type="button"
          class="t-btn ai-sparkle-btn"
          @click.stop="handleToolbarAiClick"
          title="呼出 AI 智写助手 (Ctrl+J)"
        >
          <span class="sparkle-icon">✨</span>
          <span class="ai-btn-text">AI 智写</span>
        </button>
      </div>

      <div class="t-sep" v-if="showAi"></div>

      <div class="toolbar-group">
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('bold') }"
          @click="editor?.chain().focus().toggleBold().run()"
          title="加粗 (Ctrl+B)"
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('italic') }"
          @click="editor?.chain().focus().toggleItalic().run()"
          title="斜体 (Ctrl+I)"
        >
          <em>I</em>
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('strike') }"
          @click="editor?.chain().focus().toggleStrike().run()"
          title="删除线"
        >
          <s>S</s>
        </button>
      </div>

      <div class="t-sep"></div>

      <!-- 分级标题 -->
      <div class="toolbar-group">
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('heading', { level: 1 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
          title="一级标题 (H1)"
        >
          H1
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('heading', { level: 2 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
          title="二级标题 (H2)"
        >
          H2
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('heading', { level: 3 }) }"
          @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
          title="三级标题 (H3)"
        >
          H3
        </button>
      </div>

      <div class="t-sep"></div>

      <!-- 列表与任务 -->
      <div class="toolbar-group">
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('bulletList') }"
          @click="editor?.chain().focus().toggleBulletList().run()"
          title="无序列表"
        >
          • 列表
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('orderedList') }"
          @click="editor?.chain().focus().toggleOrderedList().run()"
          title="编号列表"
        >
          1. 列表
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('taskList') }"
          @click="editor?.chain().focus().toggleTaskList().run()"
          title="检验任务清单"
        >
          ☑ 任务
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('blockquote') }"
          @click="editor?.chain().focus().toggleBlockquote().run()"
          title="引用/质量红线说明"
        >
          ❝ 引用
        </button>
        <button
          type="button"
          class="t-btn"
          :class="{ active: editor?.isActive('codeBlock') }"
          @click="editor?.chain().focus().toggleCodeBlock().run()"
          title="参数代码块"
        >
          &lt;/&gt;
        </button>
      </div>

      <div class="t-sep"></div>

      <!-- SQM 质量公差表格核心工具组 -->
      <div class="toolbar-group">
        <el-dropdown trigger="click" @command="handleTableCommand">
          <button type="button" class="t-btn table-trigger-btn">
            📊 质量表格 ▾
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="insertStandardTable">📐 插入标准 3×4 表格</el-dropdown-item>
              <el-dropdown-item command="insertCtqTable">🎯 插入 CTQ 关键公差表</el-dropdown-item>
              <el-dropdown-item command="insert8dTable">🔧 插入 8D 根本原因表</el-dropdown-item>
              <el-dropdown-item command="addColumnAfter" divided :disabled="!editor?.can().addColumnAfter()">
                ➕ 在右侧插入列
              </el-dropdown-item>
              <el-dropdown-item command="deleteColumn" :disabled="!editor?.can().deleteColumn()">
                ➖ 删除当前列
              </el-dropdown-item>
              <el-dropdown-item command="addRowAfter" :disabled="!editor?.can().addRowAfter()">
                ➕ 在下方插入行
              </el-dropdown-item>
              <el-dropdown-item command="deleteRow" :disabled="!editor?.can().deleteRow()">
                ➖ 删除当前行
              </el-dropdown-item>
              <el-dropdown-item command="mergeOrSplit" :disabled="!editor?.can().mergeOrSplit()">
                🔲 合并/拆分单元格
              </el-dropdown-item>
              <el-dropdown-item command="deleteTable" divided style="color: #ef4444;" :disabled="!editor?.can().deleteTable()">
                🗑️ 删除整个表格
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="t-sep"></div>

      <!-- 撤销/重做 -->
      <div class="toolbar-group">
        <button
          type="button"
          class="t-btn"
          :disabled="!editor?.can().undo()"
          @click="editor?.chain().focus().undo().run()"
          title="撤销 (Ctrl+Z)"
        >
          ↺
        </button>
        <button
          type="button"
          class="t-btn"
          :disabled="!editor?.can().redo()"
          @click="editor?.chain().focus().redo().run()"
          title="重做 (Ctrl+Y)"
        >
          ↻
        </button>
      </div>

      <!-- 右侧功能组：宽屏切换 (信标 1) + 章节大纲 (信标 2: 短标签) -->
      <div class="toolbar-group toolbar-right-group">
        <!-- 宽屏显示切换 icon (信标 1) -->
        <button
          type="button"
          class="t-btn wide-toggle-btn"
          :class="{ active: localWide }"
          @click="handleToggleWide"
          :title="localWide ? '恢复标准阅读宽度 (960px)' : '切换宽屏显示排版 (铺满横向空间)'"
        >
          <svg class="wide-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path v-if="!localWide" d="M17 7l5 5-5 5M7 7l-5 5 5 5M2 12h20" />
            <path v-else d="M2 7l5 5-5 5M22 7l-5 5 5 5M7 12h10" />
          </svg>
        </button>

        <div class="t-sep mini-sep"></div>

        <!-- 目录大纲切换入口 (信标 2: 改为 icon + 短标签 '大纲') -->
        <button
          type="button"
          class="t-btn outline-toggle-btn"
          :class="{ active: showOutline }"
          @click="showOutline = !showOutline"
          title="展开 / 收起文档目录大纲 (章节快速定位)"
        >
          <span class="outline-icon">📑</span>
          <span class="outline-short-label">大纲</span>
          <span class="outline-badge" v-if="outlineHeadings.length">
            {{ outlineHeadings.length }}
          </span>
        </button>
      </div>
    </div>

    <!-- Tiptap 编辑区核心 DOM 与右侧章节大纲树 -->
    <div class="editor-main-layout">
      <!-- 选区悬浮气泡菜单 (划选即刻唤出 AI 智写与快速排版) -->
      <bubble-menu
        v-if="editor && !readonly && showAi"
        :editor="editor"
        :options="{ strategy: 'fixed', placement: 'top' }"
        class="tiptap-bubble-menu"
      >
        <div class="bubble-menu-inner">
          <button
            type="button"
            class="bubble-ai-btn"
            @click.stop="handleBubbleAiClick"
            title="对选中文本进行 AI 智写润色、公差核算或表格化"
          >
            <span class="sparkle-icon">✨</span>
            <span class="bubble-ai-text">AI 智写与润色</span>
          </button>
          <span class="bubble-sep"></span>
          <button
            type="button"
            class="bubble-btn"
            :class="{ active: editor.isActive('bold') }"
            @click="editor.chain().focus().toggleBold().run()"
            title="加粗"
          >
            <strong>B</strong>
          </button>
          <button
            type="button"
            class="bubble-btn"
            :class="{ active: editor.isActive('italic') }"
            @click="editor.chain().focus().toggleItalic().run()"
            title="斜体"
          >
            <em>I</em>
          </button>
          <button
            type="button"
            class="bubble-btn"
            :class="{ active: editor.isActive('heading', { level: 2 }) }"
            @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
            title="转为二级标题"
          >
            H2
          </button>
          <button
            type="button"
            class="bubble-btn"
            @click="handleTableCommand('insertCtqTable')"
            title="将此处插入 CTQ 公差表格"
          >
            📊 表格
          </button>
        </div>
      </bubble-menu>

      <!-- 编辑器滚动工作台 (左侧 Gutter 行标槽 + 正文一体化平滑滚动) -->
      <div class="editor-scroll-stage" ref="scrollStageRef">
        <!-- 始终显示的左侧行标槽 (Gutter: 显示 01, 02, 03... 与类型图标 ¶/📊/H2) -->
        <div class="editor-gutter-column" v-if="!readonly">
          <!-- Gutter 顶栏：一键全选/取消全选 (问 3) -->
          <div
            class="gutter-header-cell"
            :class="{ 'all-selected': isAllSelected, 'has-selection': hasSelection }"
            @click.stop="toggleSelectAll"
            :title="isAllSelected ? '取消全选正文' : (hasSelection ? `已圈选 ${selectedBlockCount} 处，点击取消全选` : '一键全选正文全部信标 (Ctrl+A)')"
          >
            <span class="gutter-check-icon">{{ isAllSelected ? '☑' : hasSelection ? '⊟' : '☐' }}</span>
          </div>

          <div
            v-for="block in gutterBlocks"
            :key="block.id"
            class="gutter-cell"
            :class="{
              'is-active': isBlockSelected(block.id),
              'is-hovered': hoveredBlockId === block.id
            }"
            :style="{ top: `${block.top}px`, height: `${block.height}px` }"
            :title="`行/块 #${block.numStr} · ${block.typeName} (Ctrl/Shift+点击多选)`"
            @mouseenter="onGutterHover(block)"
            @mouseleave="onGutterLeave"
            @click.stop="onGutterClick(block, $event)"
          >
            <div class="gutter-pill">
              <span class="gutter-num">{{ block.numStr }}</span>
              <span class="gutter-icon">{{ block.icon }}</span>
            </div>
            <!-- 微型悬浮抓手/快速触发 AI 按钮 -->
            <button
              type="button"
              class="gutter-quick-ai-btn"
              @click.stop="onGutterQuickAi(block)"
              title="针对该 DOM 对象呼出 AI 智写"
            >
              ✨
            </button>
          </div>
        </div>

        <!-- Tiptap 富文本核心正文 DOM (支持直接文本编辑与 DOM 级悬停高亮) -->
        <editor-content
          :editor="editor"
          class="tiptap-content"
          ref="editorContentRef"
          @click="handleContentClick"
          @mousemove="handleContentMouseMove"
          @mouseleave="handleContentMouseLeave"
        />
      </div>

      <!-- 右侧悬浮/侧边章节大纲树 (信标 5) -->
      <transition name="outline-fade">
        <aside class="doc-outline-panel" v-if="showOutline">
          <div class="outline-panel-header">
            <div class="panel-title">
              <span>📑 文档大纲</span>
              <span class="panel-count">({{ outlineHeadings.length }})</span>
            </div>
            <button type="button" class="close-panel-btn" @click="showOutline = false" title="关闭大纲">
              ✕
            </button>
          </div>

          <div class="outline-list-wrap" v-if="outlineHeadings.length > 0">
            <div
              v-for="h in outlineHeadings"
              :key="h.id"
              class="outline-tree-item"
              :class="[`level-${h.level}`, { active: activeHeadingId === h.id }]"
              @click="selectHeadingSection(h)"
              :title="`点击定位并圈选【${h.text}】整章对象 (问 2)`"
            >
              <span class="level-indicator"></span>
              <span class="outline-text" :title="h.text">{{ h.text }}</span>
              <!-- 快捷靶向 AI 优化本章节 (信标 6 联动，绝对不乱覆盖) -->
              <button
                type="button"
                class="outline-item-ai-btn"
                @click.stop="triggerHeadingAi(h)"
                title="AI 靶向优化此章节 (绝不影响全文)"
              >
                ✨ AI
              </button>
            </div>
          </div>
          <div class="outline-empty" v-else>
            <p>暂无分级标题</p>
            <p class="empty-hint">在正文中使用 H1 / H2 即可生成大纲导航</p>
          </div>
        </aside>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, onMounted } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { BubbleMenu } from '@tiptap/vue-3/menus'
import StarterKit from '@tiptap/starter-kit'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import { TaskList } from '@tiptap/extension-task-list'
import { TaskItem } from '@tiptap/extension-task-item'
import { Image } from '@tiptap/extension-image'
import { Placeholder } from '@tiptap/extension-placeholder'

export interface BeaconItem {
  id: string
  numStr: string
  type: string
  typeName: string
  icon: string
  sectionName: string
  previewText: string
  pos: number
  nodeSize: number
  fullText: string
}

interface OutlineHeadingItem {
  id: string
  text: string
  level: number
  pos: number
  endPos: number
}

const props = withDefaults(
  defineProps<{
    modelValue?: string
    readonly?: boolean
    placeholder?: string
    showAi?: boolean
    isWide?: boolean
  }>(),
  {
    modelValue: '',
    readonly: false,
    placeholder: '输入质量标准内容，按回车换行，支持直接粘贴质检截图或插入 CTQ 公差表格...',
    showAi: true,
    isWide: false
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'change', val: string): void
  (e: 'ai-click', context?: {
    targetType?: string
    targetName?: string
    targetSection?: string
    selectedText?: string
    headingLevel?: number
    range?: { from: number; to: number }
  }): void
  (e: 'update:isWide', val: boolean): void
  (e: 'toggle-wide', val: boolean): void
  (e: 'select-dom-node', payload: {
    targetType: string
    targetName: string
    targetSection: string
    selectedText: string
    range?: { from: number; to: number }
    blockInfo?: any
    beacons?: BeaconItem[]
  }): void
}>()

const localWide = ref(props.isWide)
watch(() => props.isWide, (v) => {
  localWide.value = v
})

const handleToggleWide = () => {
  localWide.value = !localWide.value
  emit('update:isWide', localWide.value)
  emit('toggle-wide', localWide.value)
}

// 选区悬浮气泡菜单唤出 AI 智写
const handleBubbleAiClick = () => {
  if (!editor.value) return
  const { from, to } = editor.value.state.selection
  if (from === to) return
  const selectedText = editor.value.state.doc.textBetween(from, to, ' ')
  emit('ai-click', {
    targetType: 'selection',
    targetName: `选中文本 (${selectedText.trim().substring(0, 16)}...)`,
    selectedText: selectedText.trim(),
    targetSection: 'SELECTION',
    range: { from, to }
  })
}

// 智能嗅探当前光标所在上下文触发 AI 智写
const handleToolbarAiClick = () => {
  let targetType = 'doc'
  let targetName = '全篇规程整体'
  let selectedText = ''
  let targetSection = 'ALL'
  let range: { from: number; to: number } | undefined = undefined

  if (editor.value) {
    const { from, to } = editor.value.state.selection
    if (from !== to) {
      selectedText = editor.value.state.doc.textBetween(from, to, ' ')
      if (selectedText.trim()) {
        targetType = 'selection'
        targetName = `选中文本 (${selectedText.trim().substring(0, 16)}...)`
        targetSection = 'SELECTION'
        range = { from, to }
      }
    } else if (editor.value.isActive('table')) {
      targetType = 'table'
      targetName = '当前质量公差表格'
      targetSection = 'TABLES'
    }
  }

  emit('ai-click', { targetType, targetName, selectedText, targetSection, range })
}

// 大纲直接精准锁定目标章节 (信标 6 联动)
const triggerHeadingAi = (h: OutlineHeadingItem) => {
  scrollToHeading(h)
  emit('ai-click', {
    targetType: 'section',
    targetName: h.text,
    targetSection: `heading_0_${h.text}`,
    headingLevel: h.level
  })
}

const showOutline = ref(false)
const outlineHeadings = ref<OutlineHeadingItem[]>([])
const activeHeadingId = ref<string>('')

interface GutterBlockItem {
  id: string
  index: number
  numStr: string
  type: string
  typeName: string
  icon: string
  top: number
  height: number
  pos: number
  nodeSize: number
  text: string
  sectionName: string
  previewText: string
}

const scrollStageRef = ref<HTMLElement | null>(null)
const gutterBlocks = ref<GutterBlockItem[]>([])
const hoveredBlockId = ref<string>('')
const selectedBlockIds = ref<Set<string>>(new Set())
const lastClickedBlockIndex = ref<number | null>(null)
let resizeObserver: ResizeObserver | null = null

const selectedBlockCount = computed(() => selectedBlockIds.value.size)
const hasSelection = computed(() => selectedBlockIds.value.size > 0)
const isBlockSelected = (id: string) => selectedBlockIds.value.has(id)

// 是否全部选中
const isAllSelected = computed(() => {
  return gutterBlocks.value.length > 0 && selectedBlockIds.value.size === gutterBlocks.value.length
})

// 从 Tiptap 文档顶级节点解析生成左侧行标 Gutter 槽数据
const refreshGutterBlocks = () => {
  if (!editor.value || !editor.value.view) return
  const pmDom = editor.value.view.dom as HTMLElement
  if (!pmDom) return

  const children = Array.from(pmDom.children) as HTMLElement[]
  const blocks: GutterBlockItem[] = []
  const doc = editor.value.state.doc

  let childIdx = 0
  let currentSection = '引言 / 概述'

  doc.forEach((node, offset, index) => {
    const el = children[childIdx]
    const num = index + 1
    const numStr = String(num).padStart(2, '0')

    const type = node.type.name
    let icon = '¶'
    let typeName = '正文段落'

    if (type === 'table') {
      icon = '📊'
      typeName = '质量表格'
    } else if (type === 'heading') {
      const level = node.attrs.level || 1
      icon = `H${level}`
      typeName = `${level}级章节`
      const headingTitle = node.textContent.trim()
      if (headingTitle) {
        currentSection = headingTitle
      }
    } else if (type === 'blockquote') {
      icon = '❝'
      typeName = '准则引用'
    } else if (type === 'taskList') {
      icon = '☑'
      typeName = '任务清单'
    } else if (type === 'bulletList') {
      icon = '•'
      typeName = '无序列表'
    } else if (type === 'orderedList') {
      icon = '1.'
      typeName = '有序编号'
    } else if (type === 'codeBlock') {
      icon = '</>'
      typeName = '代码块'
    }

    const top = el ? el.offsetTop : 0
    const height = el ? Math.max(el.offsetHeight, 26) : 26
    const rawText = node.textContent.trim()
    const preview = rawText
      ? (rawText.length > 10 ? rawText.slice(0, 10) + '…' : rawText)
      : (type === 'table' ? '质量数据表' : '空段落')

    blocks.push({
      id: `block_${index}`,
      index,
      numStr,
      type,
      typeName,
      icon,
      top,
      height,
      pos: offset,
      nodeSize: node.nodeSize,
      text: rawText,
      sectionName: currentSection,
      previewText: preview
    })

    childIdx++
  })

  gutterBlocks.value = blocks
  syncDomSelectionClasses()
}

// 悬停行标：联动高亮正文 DOM 轮廓
const onGutterHover = (block: GutterBlockItem) => {
  hoveredBlockId.value = block.id
  highlightDomHover(block.index, true)
}

const onGutterLeave = () => {
  hoveredBlockId.value = ''
  clearDomHover()
}

// 行标快速呼出 AI
const onGutterQuickAi = (block: GutterBlockItem) => {
  handleBlockSelect(block)
  emit('ai-click', {
    targetType: block.type === 'table' ? 'table' : block.type === 'heading' ? 'section' : 'paragraph',
    targetName: `行 #${block.numStr} · ${block.typeName}`,
    targetSection: block.type === 'table' ? 'TABLES' : (block.type === 'heading' ? `heading_0_${block.text}` : `block_${block.index}`),
    selectedText: block.text,
    range: { from: block.pos, to: block.pos + block.nodeSize }
  })
}

// 同步 DOM 节点的选中视觉样式
const syncDomSelectionClasses = () => {
  if (!editor.value?.view?.dom) return
  const children = Array.from(editor.value.view.dom.children) as HTMLElement[]
  children.forEach((el, i) => {
    const block = gutterBlocks.value[i]
    if (block && selectedBlockIds.value.has(block.id)) {
      el.classList.add('is-dom-selected')
    } else {
      el.classList.remove('is-dom-selected')
    }
  })
}

// 收集已选择的信标集合并向外界发射
const emitSelectedBeacons = () => {
  const selectedBlocks = gutterBlocks.value.filter(b => selectedBlockIds.value.has(b.id))
  const beacons: BeaconItem[] = selectedBlocks.map(b => ({
    id: b.id,
    numStr: b.numStr,
    type: b.type,
    typeName: b.typeName,
    icon: b.icon,
    sectionName: b.sectionName,
    previewText: b.previewText,
    pos: b.pos,
    nodeSize: b.nodeSize,
    fullText: b.text
  }))

  let targetType = 'selection'
  let targetName = '未选择对象'
  let targetSection = 'ALL'
  let selectedText = ''
  let range: { from: number; to: number } | undefined = undefined

  if (beacons.length === 0) {
    targetType = 'doc'
    targetName = '全篇规程整体'
    targetSection = 'ALL'
  } else if (beacons.length === 1) {
    const b = beacons[0]
    targetType = b.type === 'table' ? 'table' : (b.type === 'heading' ? 'section' : 'paragraph')
    targetName = `行 #${b.numStr} · ${b.typeName} (${b.previewText})`
    targetSection = b.type === 'table' ? 'TABLES' : (b.type === 'heading' ? `heading_0_${b.fullText}` : b.id)
    selectedText = b.fullText
    range = { from: b.pos, to: b.pos + b.nodeSize }
  } else {
    targetType = 'multi'
    targetName = `多选对象 (已选 ${beacons.length} 处信标)`
    targetSection = 'MULTI_SELECTION'
    selectedText = beacons.map(b => `[${b.sectionName} - 行#${b.numStr}] ${b.fullText}`).join('\n')
    const minPos = Math.min(...beacons.map(b => b.pos))
    const maxPos = Math.max(...beacons.map(b => b.pos + b.nodeSize))
    range = { from: minPos, to: maxPos }
  }

  emit('select-dom-node', {
    targetType,
    targetName,
    targetSection,
    selectedText,
    range,
    blockInfo: beacons[0] || null,
    beacons
  })
}

// 统一的处理选中块逻辑 (支持 Ctrl 点选多选、Shift 范围连选、常规单选)
const handleBlockSelect = (block: GutterBlockItem, event?: MouseEvent) => {
  const isCtrl = event ? (event.ctrlKey || event.metaKey) : false
  const isShift = event ? event.shiftKey : false

  if (isShift && lastClickedBlockIndex.value !== null) {
    // Shift 范围多选
    const start = Math.min(lastClickedBlockIndex.value, block.index)
    const end = Math.max(lastClickedBlockIndex.value, block.index)
    const newSet = new Set(selectedBlockIds.value)
    for (let i = start; i <= end; i++) {
      if (gutterBlocks.value[i]) {
        newSet.add(gutterBlocks.value[i].id)
      }
    }
    selectedBlockIds.value = newSet
  } else if (isCtrl) {
    // Ctrl 切换多选
    const newSet = new Set(selectedBlockIds.value)
    if (newSet.has(block.id)) {
      newSet.delete(block.id)
    } else {
      newSet.add(block.id)
    }
    selectedBlockIds.value = newSet
    lastClickedBlockIndex.value = block.index
  } else {
    // 单选
    selectedBlockIds.value = new Set([block.id])
    lastClickedBlockIndex.value = block.index
  }

  syncDomSelectionClasses()
  emitSelectedBeacons()

  // 编辑器光标或选区联动
  if (editor.value && selectedBlockIds.value.has(block.id)) {
    if (block.type === 'table') {
      try {
        editor.value.chain().focus().setNodeSelection(block.pos).run()
      } catch (e) {
        editor.value.chain().focus().setTextSelection({ from: block.pos, to: block.pos + block.nodeSize }).run()
      }
    } else {
      editor.value.chain().focus().setTextSelection({ from: block.pos, to: block.pos + block.nodeSize }).run()
    }
  }
}

// 行标点击
const onGutterClick = (block: GutterBlockItem, event: MouseEvent) => {
  handleBlockSelect(block, event)
}

// 一键全选/取消全选 (问 3)
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedBlockIds.value = new Set()
  } else {
    selectedBlockIds.value = new Set(gutterBlocks.value.map(b => b.id))
  }
  syncDomSelectionClasses()
  emitSelectedBeacons()
}

const highlightDomHover = (index: number, add: boolean) => {
  if (!editor.value?.view?.dom) return
  const children = Array.from(editor.value.view.dom.children) as HTMLElement[]
  children.forEach((el, i) => {
    if (i === index && add) {
      el.classList.add('is-dom-hovered')
    } else {
      el.classList.remove('is-dom-hovered')
    }
  })
}

const clearDomHover = () => {
  if (!editor.value?.view?.dom) return
  const children = Array.from(editor.value.view.dom.children) as HTMLElement[]
  children.forEach(el => el.classList.remove('is-dom-hovered'))
}

// 鼠标悬停正文：DOM 检查器效果
const handleContentMouseMove = (e: MouseEvent) => {
  if (!editor.value?.view?.dom) return
  const target = e.target as HTMLElement
  const pmDom = editor.value.view.dom as HTMLElement
  const topBlock = target.closest('.ProseMirror > *') as HTMLElement
  if (topBlock && pmDom.contains(topBlock)) {
    const idx = Array.from(pmDom.children).indexOf(topBlock)
    if (idx >= 0 && idx < gutterBlocks.value.length) {
      hoveredBlockId.value = gutterBlocks.value[idx].id
      highlightDomHover(idx, true)
    }
  }
}

const handleContentMouseLeave = () => {
  hoveredBlockId.value = ''
  clearDomHover()
}

// 点击正文：可直接进行就地文字/表格编辑，支持 Ctrl/Shift 多选
const handleContentClick = (e: MouseEvent) => {
  if (!editor.value?.view?.dom) return
  const target = e.target as HTMLElement
  const pmDom = editor.value.view.dom as HTMLElement
  const topBlock = target.closest('.ProseMirror > *') as HTMLElement
  if (topBlock && pmDom.contains(topBlock)) {
    const idx = Array.from(pmDom.children).indexOf(topBlock)
    if (idx >= 0 && idx < gutterBlocks.value.length) {
      const block = gutterBlocks.value[idx]
      handleBlockSelect(block, e)
    }
  }
}

// 从 Tiptap 文档树中动态提取章节标题并计算覆盖区间
const refreshHeadings = () => {
  if (!editor.value) return
  const list: OutlineHeadingItem[] = []
  const { doc } = editor.value.state
  doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      const text = node.textContent?.trim()
      const level = node.attrs.level || 1
      if (text) {
        list.push({
          id: `heading-${pos}`,
          text,
          level,
          pos,
          endPos: doc.content.size
        })
      }
    }
  })

  // 计算每个标题所覆盖的章节结束位置 (到下一个同级或更高级标题的起始位置)
  for (let i = 0; i < list.length; i++) {
    const cur = list[i]
    for (let j = i + 1; j < list.length; j++) {
      if (list[j].level <= cur.level) {
        cur.endPos = list[j].pos
        break
      }
    }
  }

  outlineHeadings.value = list
}

// 快速跳转至指定章节
const scrollToHeading = (item: OutlineHeadingItem) => {
  if (!editor.value) return
  activeHeadingId.value = item.id
  editor.value.chain().focus().setTextSelection(item.pos).run()
  const domNode = editor.value.view.nodeDOM(item.pos) as HTMLElement
  if (domNode && domNode.scrollIntoView) {
    domNode.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 选择整章对象 (问 2: 点击大纲标题，圈选该章节内包含的全部块)
const selectHeadingSection = (h: OutlineHeadingItem) => {
  activeHeadingId.value = h.id
  scrollToHeading(h)

  // 圈选处于 [h.pos, h.endPos) 范围内的所有 gutterBlocks
  const newSet = new Set<string>()
  gutterBlocks.value.forEach(b => {
    if (b.pos >= h.pos && b.pos < h.endPos) {
      newSet.add(b.id)
    }
  })

  if (newSet.size > 0) {
    selectedBlockIds.value = newSet
    syncDomSelectionClasses()
    emitSelectedBeacons()
  }
}

// 外部移除单个信标
const removeBeacon = (id: string) => {
  if (selectedBlockIds.value.has(id)) {
    const newSet = new Set(selectedBlockIds.value)
    newSet.delete(id)
    selectedBlockIds.value = newSet
    syncDomSelectionClasses()
    emitSelectedBeacons()
  }
}

// 清空全部信标
const clearAllBeacons = () => {
  selectedBlockIds.value = new Set()
  syncDomSelectionClasses()
  emitSelectedBeacons()
}

// 外部悬停信标胶囊高亮正文 DOM
const highlightBeaconDom = (id: string, highlight: boolean) => {
  const block = gutterBlocks.value.find(b => b.id === id)
  if (block) {
    highlightDomHover(block.index, highlight)
  }
}

const editor = useEditor({
  content: props.modelValue || '',
  editable: !props.readonly,
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] }
    }),
    Table.configure({
      resizable: true
    }),
    TableRow,
    TableHeader,
    TableCell,
    TaskList,
    TaskItem.configure({
      nested: true
    }),
    Image.configure({
      inline: true,
      allowBase64: true
    }),
    Placeholder.configure({
      placeholder: props.placeholder
    })
  ],
  onCreate: () => {
    refreshHeadings()
    refreshGutterBlocks()
  },
  onUpdate: () => {
    if (!editor.value) return
    const html = editor.value.getHTML()
    emit('update:modelValue', html)
    emit('change', html)
    refreshHeadings()
    refreshGutterBlocks()
  }
})

// 监听外界数据变化并同步
watch(
  () => props.modelValue,
  (newVal) => {
    if (!editor.value) return
    const isSame = editor.value.getHTML() === newVal
    if (!isSame) {
      editor.value.commands.setContent(newVal || '', { emitUpdate: false })
      refreshHeadings()
      refreshGutterBlocks()
    }
  }
)

watch(
  () => props.readonly,
  (val) => {
    editor.value?.setEditable(!val)
  }
)

// 处理表格指令
const handleTableCommand = (cmd: string) => {
  if (!editor.value) return
  switch (cmd) {
    case 'insertStandardTable':
      editor.value.chain().focus().insertTable({ rows: 3, cols: 4, withHeaderRow: true }).run()
      break
    case 'insertCtqTable':
      // 插入标准 CTQ 质量公差模板表
      editor.value.chain().focus().insertContent(`
        <table class="ctq-spec-table">
          <thead>
            <tr>
              <th>CTQ 特征编号</th>
              <th>控制项目 / 尺寸</th>
              <th>图纸公差标称值</th>
              <th>公差上限 (USL)</th>
              <th>公差下限 (LSL)</th>
              <th>检测量具与抽样</th>
              <th>判定准则</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>CTQ-01</strong></td>
              <td>法兰盘外径</td>
              <td>Ø45.00 mm</td>
              <td>+0.015 mm</td>
              <td>-0.010 mm</td>
              <td>三坐标 / 5件/批</td>
              <td>Cpk ≥ 1.33</td>
            </tr>
            <tr>
              <td><strong>CTQ-02</strong></td>
              <td>安装孔同轴度</td>
              <td>0.02 mm</td>
              <td>0.025 mm</td>
              <td>0.000 mm</td>
              <td>气动量仪 / 100%</td>
              <td>零缺陷接收</td>
            </tr>
          </tbody>
        </table>
      `).run()
      break
    case 'insert8dTable':
      editor.value.chain().focus().insertContent(`
        <table class="eight-d-table">
          <thead>
            <tr>
              <th>步骤 (8D)</th>
              <th>主要内容</th>
              <th>责任工程师</th>
              <th>关闭目标日期</th>
              <th>验证状态</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>D1 成立团队</td>
              <td>质量、工艺、采购专家小组</td>
              <td>SQM 团队</td>
              <td>2026-11-05</td>
              <td>已闭环</td>
            </tr>
            <tr>
              <td>D2 问题描述</td>
              <td>法兰面微裂纹缺陷</td>
              <td>工艺部</td>
              <td>2026-11-07</td>
              <td>评审中</td>
            </tr>
          </tbody>
        </table>
      `).run()
      break
    case 'addColumnAfter':
      editor.value.chain().focus().addColumnAfter().run()
      break
    case 'deleteColumn':
      editor.value.chain().focus().deleteColumn().run()
      break
    case 'addRowAfter':
      editor.value.chain().focus().addRowAfter().run()
      break
    case 'deleteRow':
      editor.value.chain().focus().deleteRow().run()
      break
    case 'mergeOrSplit':
      editor.value.chain().focus().mergeOrSplit().run()
      break
    case 'deleteTable':
      editor.value.chain().focus().deleteTable().run()
      break
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && (e.key === 'j' || e.key === 'J')) {
    if (props.showAi && !props.readonly) {
      e.preventDefault()
      emit('ai-click')
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', refreshGutterBlocks)
  setTimeout(() => {
    refreshGutterBlocks()
    if (editor.value?.view?.dom) {
      resizeObserver = new ResizeObserver(() => {
        refreshGutterBlocks()
      })
      resizeObserver.observe(editor.value.view.dom)
    }
  }, 100)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', refreshGutterBlocks)
  if (resizeObserver) resizeObserver.disconnect()
  editor.value?.destroy()
})

// 原生绝对坐标 AI 内容精准替换与插入 (彻底解决乱放/正则替换错位问题)
const insertAiContent = (payload: {
  html: string
  mode: 'insert' | 'replace'
  targetSection?: string
  range?: { from: number; to: number }
}): boolean => {
  if (!editor.value) return false

  // 1. 若传了精确的选区坐标 range (用户划选内容精准替换)
  if (payload.range && payload.range.from !== payload.range.to) {
    try {
      editor.value
        .chain()
        .focus()
        .setTextSelection({ from: payload.range.from, to: payload.range.to })
        .deleteSelection()
        .insertContent(payload.html)
        .run()
      return true
    } catch (e) {
      console.warn('精准坐标替换异常，降级为常规插入', e)
    }
  }

  // 2. 当前编辑器有选区且为 replace
  const { from, to } = editor.value.state.selection
  if (payload.mode === 'replace' && from !== to) {
    editor.value
      .chain()
      .focus()
      .deleteSelection()
      .insertContent(payload.html)
      .run()
    return true
  }

  // 3. 靶向表格
  if (payload.targetSection === 'TABLES' && editor.value.isActive('table')) {
    if (payload.mode === 'replace') {
      editor.value.chain().focus().deleteTable().insertContent(payload.html).run()
    } else {
      editor.value.chain().focus().insertContent(payload.html).run()
    }
    return true
  }

  // 4. 当前光标位置安全插入
  editor.value.chain().focus().insertContent(payload.html).run()
  return true
}

defineExpose({
  editor,
  refreshHeadings,
  outlineHeadings,
  gutterBlocks,
  refreshGutterBlocks,
  insertAiContent,
  focus: () => editor.value?.commands.focus(),
  toggleSelectAll,
  removeBeacon,
  clearAllBeacons,
  highlightBeaconDom
})
</script>

<style scoped>
.tiptap-editor-wrap {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

/* 顶部排版与表格工具栏 (信标 1 & 信标 4: 固定最顶部，紧凑高信噪比) */
.tiptap-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 3px;
  padding: 4px 8px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 11.5px;
  user-select: none;
  z-index: 10;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.t-btn {
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: #334155;
  cursor: pointer;
  font-size: 11.5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 25px;
  height: 25px;
  transition: all 0.12s ease;
}
.t-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
}
.t-btn.active {
  background: #e0f2fe;
  color: #0284c7;
  font-weight: 600;
  border-color: #bae6fd;
}
.t-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* AI 智写高光质感按钮 */
.ai-sparkle-btn {
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border: none !important;
  cursor: pointer !important;
  gap: 4px;
  padding: 2px 8px !important;
  height: 25px !important;
  position: relative;
  z-index: 2;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.25);
  pointer-events: auto !important;
}
.ai-sparkle-btn * {
  pointer-events: none !important;
}
.ai-sparkle-btn:hover {
  background: linear-gradient(135deg, #0369a1 0%, #1d4ed8 100%) !important;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35);
}

.table-trigger-btn {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
  font-weight: 500;
  padding: 2px 7px;
}
.table-trigger-btn:hover {
  background: #dcfce7;
}

.t-sep {
  width: 1px;
  height: 14px;
  background: #cbd5e1;
  margin: 0 2px;
}

.editor-main-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
  background: #ffffff;
}

/* 编辑器滚动工作台 (左侧 Gutter 行标槽 + 正文内容一体化滚动) */
.editor-scroll-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  background: #ffffff;
}

.editor-scroll-stage::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.editor-scroll-stage::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.editor-scroll-stage::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
.editor-scroll-stage::-webkit-scrollbar-track {
  background: transparent;
}

/* 始终显示的左侧行标槽 (Gutter) */
.editor-gutter-column {
  width: 48px;
  flex-shrink: 0;
  position: relative;
  background: #f8fafc;
  border-right: 1px solid #f1f5f9;
  user-select: none;
  z-index: 5;
}

.gutter-header-cell {
  position: sticky;
  top: 0;
  left: 0;
  width: 100%;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  z-index: 10;
  transition: all 0.15s ease;
}

.gutter-header-cell:hover {
  background: #e2e8f0;
}

.gutter-header-cell.all-selected,
.gutter-header-cell.has-selection {
  background: #e0f2fe;
}

.gutter-check-icon {
  font-size: 13px;
  color: #64748b;
  line-height: 1;
}

.gutter-header-cell.all-selected .gutter-check-icon {
  color: #0284c7;
  font-weight: bold;
}

.gutter-header-cell.has-selection .gutter-check-icon {
  color: #2563eb;
  font-weight: bold;
}

.gutter-cell {
  position: absolute;
  left: 0;
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 3px 4px 0 4px;
  box-sizing: border-box;
  cursor: pointer;
  transition: all 0.12s ease;
  border-left: 2px solid transparent;
}

.gutter-cell:hover,
.gutter-cell.is-hovered {
  background: #e0f2fe;
  border-left-color: #38bdf8;
}

.gutter-cell.is-active {
  background: #dbeafe;
  border-left-color: #2563eb;
}

.gutter-pill {
  display: flex;
  align-items: center;
  gap: 2px;
}

.gutter-num {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
}

.gutter-cell:hover .gutter-num,
.gutter-cell.is-hovered .gutter-num {
  color: #0284c7;
}

.gutter-cell.is-active .gutter-num {
  color: #1d4ed8;
  font-weight: 700;
}

.gutter-icon {
  font-size: 10px;
  opacity: 0.65;
}

.gutter-quick-ai-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: #3b82f6;
  color: #ffffff;
  font-size: 9px;
  cursor: pointer;
  transition: transform 0.1s ease;
}

.gutter-cell:hover .gutter-quick-ai-btn,
.gutter-cell.is-hovered .gutter-quick-ai-btn {
  display: inline-flex;
}

.gutter-quick-ai-btn:hover {
  transform: scale(1.15);
  background: #1d4ed8;
}

/* 编辑器内容区排版样式 */
.tiptap-content {
  flex: 1;
  min-width: 0;
  padding: 12px 18px;
  outline: none;
  font-size: 13.5px;
  line-height: 1.65;
  color: #1e293b;
  overflow: visible;
}

:deep(.ProseMirror) {
  outline: none;
  min-height: 100%;
  position: relative;
}

:deep(.ProseMirror > *) {
  transition: outline 0.12s ease, background-color 0.12s ease, box-shadow 0.12s ease;
  position: relative;
}

:deep(.ProseMirror > *.is-dom-hovered) {
  outline: 2px dashed #60a5fa !important;
  outline-offset: 3px !important;
  border-radius: 4px;
  background-color: rgba(239, 246, 255, 0.45) !important;
}

:deep(.ProseMirror > *.is-dom-selected) {
  outline: 2px solid #2563eb !important;
  outline-offset: 4px !important;
  border-radius: 6px;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14) !important;
  background-color: rgba(239, 246, 255, 0.25) !important;
}

:deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: #94a3b8;
  pointer-events: none;
  height: 0;
}

/* 标题样式 (紧凑留白) */
:deep(.ProseMirror h1) {
  font-size: 19px;
  font-weight: 700;
  margin: 10px 0 5px 0;
  color: #0f172a;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 4px;
}
:deep(.ProseMirror h2) {
  font-size: 16px;
  font-weight: 600;
  margin: 8px 0 4px 0;
  color: #1e293b;
}
:deep(.ProseMirror h3) {
  font-size: 14px;
  font-weight: 600;
  margin: 6px 0 3px 0;
  color: #334155;
}

/* 列表样式 */
:deep(.ProseMirror ul), :deep(.ProseMirror ol) {
  padding-left: 20px;
  margin: 6px 0;
}
:deep(.ProseMirror ul[data-type="taskList"]) {
  list-style: none;
  padding-left: 2px;
}
:deep(.ProseMirror ul[data-type="taskList"] li) {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 引用块 */
:deep(.ProseMirror blockquote) {
  border-left: 4px solid #0284c7;
  margin: 8px 0;
  padding: 6px 12px;
  background: #f0f9ff;
  color: #0369a1;
  border-radius: 0 4px 4px 0;
}

/* 质量公差表格核心样式 (CTQ Spec Table) */
:deep(.ProseMirror table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  overflow: hidden;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid #cbd5e1;
}

:deep(.ProseMirror th) {
  background: #f1f5f9;
  color: #0f172a;
  font-weight: 600;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  text-align: left;
}

:deep(.ProseMirror td) {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  color: #334155;
  position: relative;
}

:deep(.ProseMirror .selectedCell:after) {
  z-index: 2;
  position: absolute;
  content: "";
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(2, 132, 199, 0.15);
  pointer-events: none;
}

:deep(.ProseMirror table.ctq-spec-table th) {
  background: #f0fdf4;
  color: #166534;
  border-color: #bbf7d0;
}
:deep(.ProseMirror table.eight-d-table th) {
  background: #eff6ff;
  color: #1e40af;
  border-color: #bfdbfe;
}

/* 图片样式 */
:deep(.ProseMirror img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  margin: 12px 0;
}

/* AI 智写按钮 (信标 1 移入 信标 2) */
.ai-sparkle-btn {
  background: linear-gradient(135deg, #eff6ff 0%, #e0e7ff 100%);
  color: #2563eb;
  border: 1px solid #bfdbfe;
  font-weight: 600;
  padding: 3px 9px;
  gap: 4px;
  border-radius: 4px;
}
.ai-sparkle-btn:hover {
  background: linear-gradient(135deg, #dbeafe 0%, #c7d2fe 100%);
  color: #1d4ed8;
  border-color: #93c5fd;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.2);
}
.sparkle-icon {
  font-size: 13px;
}
.ai-btn-text {
  font-size: 12px;
}

/* 右侧工具组：宽屏切换与大纲 */
.toolbar-right-group {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 3px;
}
.wide-toggle-btn {
  color: #475569;
  padding: 4px;
}
.wide-toggle-btn.active {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}
.wide-icon {
  display: block;
}
.mini-sep {
  height: 14px;
  margin: 0 2px;
}
.outline-toggle-btn {
  gap: 4px;
  font-weight: 500;
  color: #475569;
  padding: 4px 8px;
}
.outline-toggle-btn.active {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}
.outline-icon {
  font-size: 13px;
  line-height: 1;
}
.outline-short-label {
  font-size: 12px;
}
.outline-badge {
  font-size: 10px;
  font-weight: 600;
  background: #e2e8f0;
  color: #475569;
  padding: 0 5px;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  border-radius: 8px;
}
.outline-toggle-btn.active .outline-badge {
  background: #2563eb;
  color: #ffffff;
}

/* 编辑区主布局与右侧大纲抽屉 */
.editor-main-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.doc-outline-panel {
  width: 240px;
  min-width: 240px;
  background: #f8fafc;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 10;
}

.outline-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-count {
  font-size: 11px;
  color: #94a3b8;
  font-weight: normal;
}

.close-panel-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #94a3b8;
  font-size: 13px;
  padding: 2px 5px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.close-panel-btn:hover {
  color: #0f172a;
  background: #e2e8f0;
}

.outline-list-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.outline-tree-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.12s ease;
  position: relative;
}

.outline-tree-item:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.outline-tree-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

/* 大纲项 Hover 浮现 AI 靶向微按钮 */
.outline-item-ai-btn {
  display: none;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  padding: 1px 5px;
  cursor: pointer;
  margin-left: auto;
  flex-shrink: 0;
  transition: all 0.15s ease;
}
.outline-item-ai-btn:hover {
  background: #2563eb;
  color: #ffffff;
}
.outline-tree-item:hover .outline-item-ai-btn {
  display: inline-flex;
}

.outline-tree-item.level-1 {
  font-weight: 600;
  padding-left: 10px;
}

.outline-tree-item.level-2 {
  padding-left: 20px;
  font-size: 12px;
}

.outline-tree-item.level-3 {
  padding-left: 30px;
  font-size: 11.5px;
  color: #64748b;
}

.level-indicator {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #94a3b8;
  flex-shrink: 0;
}

.outline-tree-item.active .level-indicator {
  background: #2563eb;
  transform: scale(1.3);
}

.outline-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.outline-empty {
  padding: 32px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

.empty-hint {
  font-size: 11px;
  margin-top: 4px;
  color: #cbd5e1;
}

.outline-fade-enter-active,
.outline-fade-leave-active {
  transition: all 0.2s ease;
}

.outline-fade-enter-from,
.outline-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 选区气泡工具栏 (Bubble Menu) */
.tiptap-bubble-menu {
  display: flex;
  align-items: center;
  background: #0f172a;
  color: #ffffff;
  padding: 4px 6px;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.12);
  z-index: 50;
  user-select: none;
}

.bubble-menu-inner {
  display: flex;
  align-items: center;
  gap: 3px;
}

.bubble-ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #ffffff;
  border: none;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.bubble-ai-btn:hover {
  filter: brightness(1.12);
  transform: translateY(-1px);
}

.bubble-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 26px;
  padding: 0 6px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.bubble-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.bubble-btn.active {
  background: #3b82f6;
  color: #ffffff;
}

.bubble-sep {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.2);
  margin: 0 3px;
}
</style>

