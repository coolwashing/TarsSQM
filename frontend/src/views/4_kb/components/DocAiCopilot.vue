<template>
  <teleport to="body">
    <div
      v-if="dialogVisible"
      ref="paletteRef"
      class="ai-palette-window"
      :class="{ 'is-collapsed': isCollapsed, 'is-dragging': isDragging }"
      :style="paletteStyle"
    >
      <!-- 调色盘顶栏 (可拖拽手柄、折叠与关闭，完全非模态无背景遮罩，背景内容随时可点可编辑) -->
      <div class="palette-header" @mousedown="onHeaderMouseDown">
        <div class="palette-header-left">
          <span class="palette-drag-grip" title="按住拖拽至屏幕任意位置">⋮⋮</span>
          <span class="palette-sparkle">✨</span>
          <span class="palette-title">{{ isCollapsed ? (currentScopeObj.label || 'AI 智写伴侣') : 'AI 智写伴侣' }}</span>
          <span class="palette-mode-tag" v-if="!isCollapsed">非模态调色盘</span>
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
            title="关闭伴侣 (随时可从上方工具栏或划选呼出)"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- 调色盘主体内容 (折叠时收起) -->
      <div class="palette-body" v-show="!isCollapsed">
        <div class="copilot-container">
          <!-- 1. 一体化沉浸式输入卡片 (Linear / Raycast 质感) -->
          <div class="command-card">
        <!-- 🎯 作用目标靶向状态栏 -->
        <div class="scope-lock-card" :class="{ 'is-targeted': selectedScope !== 'ALL' }">
          <div class="lock-card-main">
            <div class="lock-status-badge" :class="{ 'is-locked': selectedScope !== 'ALL' }">
              <span class="lock-icon">{{ selectedScope === 'SELECTION' ? '📌' : selectedScope !== 'ALL' ? '🔒' : '🌐' }}</span>
              <span class="lock-label">作用目标：</span>
              <span class="lock-target-name">{{ currentScopeObj.label }}</span>
              <span class="lock-tag" v-if="selectedScope !== 'ALL'">
                {{ selectedScope === 'SELECTION' ? '选区直选' : currentScopeObj.type === 'table' ? '质量表格' : '章节隔离' }}
              </span>
            </div>

            <!-- 若当前为选区直选，直接展示选中文本气泡引用片段 (信标 1 革命性体验升级) -->
            <div class="selected-text-quote" v-if="selectedScope === 'SELECTION' && activeSelectedText">
              <span class="quote-symbol">“</span>
              <span class="quote-body">{{ activeSelectedText.length > 60 ? activeSelectedText.slice(0, 60) + '...' : activeSelectedText }}</span>
              <span class="quote-symbol">”</span>
            </div>
            <div class="lock-reassurance" v-else>
              <span v-if="selectedScope !== 'ALL'" class="reassurance-safe">
                <el-icon><Check /></el-icon> 强隔离保护中 · 其余章节 100% 留存不覆盖
              </span>
              <span v-else class="reassurance-all">
                💡 全篇规程模式 · 可划选正文或点击下方芯片锁定局部
              </span>
            </div>
          </div>

          <div class="lock-card-actions" v-if="selectedScope !== 'ALL'">
            <button
              type="button"
              class="unlock-scope-btn"
              @click="selectedScope = 'ALL'"
              title="切换为全篇规程整体模式"
            >
              切为全篇
            </button>
          </div>
        </div>

        <!-- 针对选区模式的专属快操作捷径条 (信标 1: 用户选区后一键触发) -->
        <div class="selection-actions-bar" v-if="selectedScope === 'SELECTION'">
          <span class="sel-bar-title">⚡ 选区速写：</span>
          <button type="button" class="sel-action-btn" @click="applySelectionPrompt('polish')">✨ 润色精炼</button>
          <button type="button" class="sel-action-btn" @click="applySelectionPrompt('ctq')">🎯 提取 CTQ</button>
          <button type="button" class="sel-action-btn" @click="applySelectionPrompt('table')">📊 转为表格</button>
          <button type="button" class="sel-action-btn" @click="applySelectionPrompt('8d')">🔧 补充 8D</button>
        </div>

        <!-- 针对表格模式的专属快操作捷径条 (信标 3 点击表格立即呈现) -->
        <div class="selection-actions-bar table-bar" v-else-if="selectedScope === 'TABLES' || currentScopeObj.type === 'table'">
          <span class="sel-bar-title">📊 表格速写：</span>
          <button type="button" class="sel-action-btn" @click="applyTablePrompt('ctq')">🎯 补全公差</button>
          <button type="button" class="sel-action-btn" @click="applyTablePrompt('audit')">🔍 审核合规</button>
          <button type="button" class="sel-action-btn" @click="applyTablePrompt('expand')">➕ 扩充项目</button>
          <button type="button" class="sel-action-btn" @click="applyTablePrompt('8d')">🔧 8D 对策</button>
        </div>

        <!-- 目标切换芯片条 (极简紧凑，避免横向长列表溢出) -->
        <div class="target-pills-row" v-else-if="availableScopes.length > 1">
          <span class="target-pills-label">🎯 目标切换：</span>
          <div class="target-pills-scroll">
            <button
              v-if="activeSelectedText"
              type="button"
              class="target-pill-btn"
              :class="{ active: selectedScope === 'SELECTION' }"
              @click="selectedScope = 'SELECTION'"
            >
              <span>📌 当前选区 ({{ activeSelectedText.length }}字)</span>
            </button>
            <button
              type="button"
              class="target-pill-btn"
              :class="{ active: selectedScope === 'ALL' }"
              @click="selectedScope = 'ALL'"
            >
              <span>🌐 全篇整体</span>
            </button>
            <button
              v-if="initialTarget?.targetSection === 'TABLES'"
              type="button"
              class="target-pill-btn"
              :class="{ active: selectedScope === 'TABLES' }"
              @click="selectedScope = 'TABLES'"
            >
              <span>📊 当前表格</span>
            </button>

            <!-- 章节下拉，告别铺开几十个按钮的臃肿 -->
            <el-select
              v-if="headingScopes.length > 0"
              v-model="selectedHeadingScope"
              size="small"
              placeholder="📑 选择指定章节..."
              class="heading-scope-select"
              @change="handleSelectHeadingScope"
            >
              <el-option
                v-for="h in headingScopes"
                :key="h.value"
                :label="`${h.icon} ${h.label}`"
                :value="h.value"
              />
            </el-select>
          </div>
        </div>

        <!-- 信标锁定展示区 (分章节展示圈选信标，前10字预览，精准联动，问 4) -->
        <div class="beacon-capsules-group" v-if="beacons && beacons.length > 0">
          <div class="beacon-group-header">
            <span class="beacon-header-title">
              <span class="beacon-radar-icon">🎯</span>
              <span>已锁定 <strong>{{ beacons.length }}</strong> 处信标对象</span>
            </span>
            <button
              type="button"
              class="beacon-clear-all-btn"
              @click="emit('clear-beacons')"
              title="清空已选信标"
            >
              清空全部
            </button>
          </div>

          <div class="beacon-sections-list">
            <div
              v-for="sec in groupedBeacons"
              :key="sec.sectionName"
              class="beacon-section-row"
            >
              <div class="beacon-section-title">
                <span class="section-badge">📑 {{ sec.sectionName }}</span>
                <span class="section-count">({{ sec.items.length }})</span>
              </div>
              <div class="beacon-chips-wrap">
                <div
                  v-for="b in sec.items"
                  :key="b.id"
                  class="beacon-chip"
                  :title="`行 #${b.numStr} · ${b.typeName}\n${b.fullText}`"
                  @mouseenter="emit('highlight-beacon', { id: b.id, highlight: true })"
                  @mouseleave="emit('highlight-beacon', { id: b.id, highlight: false })"
                >
                  <span class="chip-icon">{{ b.icon }}</span>
                  <span class="chip-num">#{{ b.numStr }}</span>
                  <span class="chip-preview">{{ b.previewText }}</span>
                  <button
                    type="button"
                    class="chip-remove-btn"
                    @click.stop="emit('remove-beacon', b.id)"
                    title="移除此信标"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 需求输入框 -->
        <textarea
          v-model="promptText"
          class="command-textarea"
          :placeholder="selectedScope === 'SELECTION'
            ? '针对当前选中文本输入编写/润色要求，或点选上方快速动作（Ctrl+Enter 生成）...'
            : (selectedScope !== 'ALL'
              ? `针对【${currentScopeObj.label}】进行定向优化与分析（Ctrl+Enter 生成）...`
              : '在此输入质量规程编制或优化需求（Ctrl+Enter 生成）...')"
          rows="2"
          @keydown.ctrl.enter="handleStartGenerate"
        ></textarea>

        <!-- 快捷指令预设池 (全篇模式时展示通用指令) -->
        <div class="preset-track-wrap" v-if="selectedScope !== 'SELECTION'">
          <div class="preset-scroll-track">
            <span class="preset-track-label">💡 快捷指令：</span>
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
              title="新增自定义快捷指令，持久化至 data/kb_prompt_presets.json"
            >
              <el-icon><Plus /></el-icon>
              <span>增加指令</span>
            </span>
          </div>
        </div>

        <!-- 卡片底栏：RAG 信息与生成/取消按钮 -->
        <div class="command-action-bar">
          <div class="action-left">
            <span v-if="referencedDocs.length > 0" class="rag-pill" :title="'已关联标准: ' + referencedDocs.join('、')">
              <el-icon><Document /></el-icon>
              <span>对齐: {{ referencedDocs[0] }} {{ referencedDocs.length > 1 ? `+${referencedDocs.length - 1}` : '' }}</span>
            </span>
            <span v-else class="rag-hint">
              💡 点选快捷动作或按 Ctrl+Enter 立即生成
            </span>
          </div>

          <div class="action-right">
            <button
              v-if="!generatedContent && !generating"
              type="button"
              class="cancel-btn"
              @click="handleCancel"
            >
              取消
            </button>
            <button
              class="generate-main-btn"
              :class="{ loading: generating }"
              :disabled="!promptText.trim() || generating"
              @click="handleStartGenerate"
            >
              <span v-if="generating" class="spin-icon">⏳</span>
              <span v-else>✨</span>
              <span>{{ generating ? '正在智写...' : (generatedContent ? '重新生成' : '开始智能生成') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 2. 无界通透审查预览区 (信标 3 修复：仅在生成中或生成完毕时展开，避免未生成时的巨大空白) -->
      <div class="preview-card" v-if="generatedContent || generating">
        <div class="preview-status-strip">
          <div class="strip-left">
            <span class="preview-dot" :class="{ live: generating }"></span>
            <span class="strip-title">生成结果审查</span>
            <span v-if="generating" class="live-tag">实时流式打字中...</span>
          </div>
          <div class="strip-right">
            <button class="strip-btn" @click="handlePasteIdeResult" title="从剪贴板粘贴外部内容到此处预览审查">
              <el-icon><Download /></el-icon> 粘贴
            </button>
            <button class="strip-btn" @click="handleRefreshDoc" title="刷新页面文档">
              <el-icon><Refresh /></el-icon> 刷新
            </button>
          </div>
        </div>

        <div class="preview-scroll-body">
          <div v-if="generatedContent" class="preview-html" v-html="generatedContent"></div>
          <div v-else-if="generating" class="preview-empty">
            <div class="loading-wave">
              <span></span><span></span><span></span>
            </div>
            <p>正在结合质量知识库标准进行深度推理与结构化排版...</p>
          </div>
        </div>
      </div>

      <!-- 3. 底部人工决策动作栏 (仅在有内容时出现，信噪比极高) -->
      <div class="modal-footer" v-if="generatedContent">
        <div class="footer-note">
          <span v-if="selectedScope === 'SELECTION'" class="safe-guard-hint">
            🛡️ 原生坐标保护：本次将精准替换选区正文，其余段落与章节 100% 绝对留存。
          </span>
          <span v-else-if="selectedScope !== 'ALL'" class="safe-guard-hint">
            🛡️ 章节隔离保护：仅更新【{{ currentScopeObj.label }}】，其余章节绝不覆盖。
          </span>
          <span v-else class="safe-guard-hint">
            ⚠️ 请人工核对技术参数与公差标准后，再确认写入正文。
          </span>
        </div>
        <div class="footer-actions">
          <el-button @click="handleCancel" size="small">取消</el-button>
          <el-button
            type="info"
            plain
            size="small"
            @click="handleCopyResult"
            title="仅复制生成内容至剪贴板"
          >
            📋 复制
          </el-button>
          <el-button
            v-if="selectedScope !== 'ALL'"
            type="primary"
            size="small"
            class="confirm-btn lock-confirm-btn"
            @click="confirmInsert('replace')"
          >
            🟢 {{ selectedScope === 'SELECTION' ? '精准替换选区正文' : '精准替换锁定目标' }}
          </el-button>
          <el-button
            v-else
            type="primary"
            size="small"
            class="confirm-btn"
            @click="confirmInsert('replace')"
          >
            🟢 确认写入正文
          </el-button>
          <el-button
            type="default"
            size="small"
            @click="confirmInsert('insert')"
          >
            ➕ {{ selectedScope === 'SELECTION' ? '插入在选区之后' : (selectedScope !== 'ALL' ? '追加至该章节末尾' : '追加至文末') }}
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
import { ref, computed, watch, onMounted } from 'vue'
import { Document, CopyDocument, Download, Refresh, Star, Close, Edit, Plus, Check } from '@element-plus/icons-vue'
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
const generating = ref(false)
const generatedContent = ref('')
const referencedDocs = ref<string[]>([])

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

// 2. 点击标签应用 Prompt
const applyPreset = (preset: PromptPreset) => {
  promptText.value = preset.prompt || preset.name.replace(/^[^\s]+\s*/, '')
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

watch(
  () => [props.modelValue, props.initialTarget, props.beacons] as const,
  ([visible, target, beacons]) => {
    if (visible) {
      fetchPromptPresets()
      const sel = target?.selectedText || props.selectedText
      if (beacons && beacons.length > 0) {
        if (!promptText.value) {
          promptText.value = `对当前锁定的 ${beacons.length} 处信标对象进行针对性质量优化与技术标准核对`
        }
      } else if (sel && sel.trim()) {
        selectedScope.value = 'SELECTION'
        if (!promptText.value) {
          promptText.value = '对选区文本进行质量工程规范化润色与精简'
        }
      } else if (target?.targetSection) {
        selectedScope.value = target.targetSection
        if (target.targetName && target.targetName !== '全篇规程整体') {
          promptText.value = `针对【${target.targetName}】，补充完善质量控制要求与检验规范`
        }
      } else {
        selectedScope.value = 'ALL'
        if (!promptText.value) {
          promptText.value = '根据当前质量知识库标准，帮我写一份现场检验作业指导书(SOP)'
        }
      }
      // 自动检查是否有 IDE 推送给当前文档的审查内容
      if (!generatedContent.value) {
        syncIdePreview(true)
      }
    } else {
      generating.value = false
    }
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  fetchPromptPresets()
})

// 发起流式生成
const handleStartGenerate = async () => {
  if (!promptText.value.trim() || generating.value) return

  generating.value = true
  generatedContent.value = ''
  referencedDocs.value = []

  let selectedTextPayload = props.selectedText || props.initialTarget?.selectedText || ''
  if (props.beacons && props.beacons.length > 0) {
    const beaconLines = props.beacons.map(b => {
      return `[章节: ${b.sectionName} | 行#${b.numStr} · ${b.typeName}] ${b.fullText}`
    }).join('\n')
    selectedTextPayload = selectedTextPayload ? `${selectedTextPayload}\n\n[锁定信标清单]:\n${beaconLines}` : `[锁定信标清单]:\n${beaconLines}`
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

// 一键复制 IDE 专用 Prompt
const copyPromptForIde = async () => {
  const refText = referencedDocs.value.length > 0
    ? `已关联质量知识库标准：\n- ${referencedDocs.value.join('\n- ')}`
    : '请基于通用 SQM 供应商与制造质量管理规范基准'

  const scopeItem = availableScopes.value.find(s => s.value === selectedScope.value)
  const scopeText = scopeItem && scopeItem.value !== 'ALL'
    ? `【作用范围/章节靶向】：${scopeItem.label}\n注意：仅需重写/生成该章节或区域对应内容！\n`
    : '【作用范围】：全篇规程整体\n'

  const promptPayload = `【质量知识库 AI 智写指令】
目标文档：${props.docTitle || '当前质量文档'} (ID: ${props.docId || '新文档'})
${refText}
${scopeText}
【用户编写需求】
${promptText.value.trim()}
${props.selectedText ? `\n【选中文本参考】\n${props.selectedText}` : ''}

【输出要求】
请作为 SQM 资深质量专家，输出结构严谨、包含 Callout 提示块、标准表格与控制要素的专业富文本 HTML。
请直接生成富文本 HTML 内容，或者执行代码调用本地接口 [PUT http://127.0.0.1:8010/api/kb/docs/${props.docId || ''}] 写入该文档！`


  try {
    await navigator.clipboard.writeText(promptPayload)
    ElMessage.success('已复制 IDE 专用 Prompt！请直接粘贴到 IDE 聊天框中发送')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = promptPayload
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制 IDE 专用 Prompt！请直接粘贴到 IDE 聊天框中发送')
  }
}

// 一键拉取 IDE 生成的审查内容
const syncIdePreview = async (silent = false) => {
  try {
    const res = await fetch(`/api/kb/copilot/preview?doc_id=${props.docId || 'default'}`)
    if (res.ok) {
      const data = await res.json()
      if (data && data.html) {
        generatedContent.value = data.html
        if (!silent) {
          ElMessage.success('已成功同步 IDE 生成的规程！请在下方预览审查，满意后点击「确认填入」')
        }
        return true
      }
    }
  } catch {}
  if (!silent) {
    ElMessage.info('暂未检测到 IDE 推送的审查内容，您也可以点击左下角「粘贴 IDE 内容」')
  }
  return false
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

.palette-mode-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.2);
  color: #93c5fd;
  border: 1px solid rgba(147, 197, 253, 0.3);
  font-weight: 500;
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

.selection-actions-bar.table-bar {
  background: linear-gradient(90deg, #f0fdf4 0%, #dcfce7 100%) !important;
  border-bottom: 1px solid #bbf7d0 !important;
}
.selection-actions-bar.table-bar .sel-bar-title {
  color: #166534 !important;
}
.selection-actions-bar.table-bar .sel-action-btn {
  background: #ffffff !important;
  color: #15803d !important;
  border: 1px solid #86efac !important;
}
.selection-actions-bar.table-bar .sel-action-btn:hover {
  background: #16a34a !important;
  color: #ffffff !important;
  border-color: #16a34a !important;
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

/* 目标靶向锁定与防覆盖隔离横幅 (信标 3 & 4 交互优化) */
.scope-lock-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  border-top-left-radius: 9px;
  border-top-right-radius: 9px;
  transition: all 0.2s ease;
  gap: 12px;
}

.scope-lock-card.is-targeted {
  background: linear-gradient(90deg, #f0fdf4 0%, #ecfdf5 100%);
  border-bottom: 1px solid #bbf7d0;
}

.lock-card-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  flex: 1;
  min-width: 0;
}

.lock-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 3px 10px;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.lock-status-badge.is-locked {
  background: #ffffff;
  border-color: #86efac;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.12);
}

.lock-icon {
  font-size: 13px;
}

.lock-label {
  font-weight: 600;
  color: #475569;
}

.lock-target-name {
  font-weight: 700;
  color: #0f172a;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lock-tag {
  font-size: 10.5px;
  font-weight: 600;
  background: #dcfce7;
  color: #15803d;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.3px;
}

.lock-reassurance {
  font-size: 11.5px;
  line-height: 1.4;
}

.reassurance-safe {
  color: #16a34a;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.reassurance-all {
  color: #64748b;
}

.lock-card-actions {
  flex-shrink: 0;
}

.unlock-scope-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.unlock-scope-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #94a3b8;
}

/* 快捷靶向快选芯片条 */
.target-pills-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #ffffff;
  border-bottom: 1px dashed #f1f5f9;
  overflow: hidden;
}

.target-pills-label {
  font-size: 11.5px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
  flex-shrink: 0;
}

.target-pills-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 2px 0;
}

.target-pills-scroll::-webkit-scrollbar {
  display: none;
}

.target-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 11.5px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 200px;
}

.target-pill-btn .pill-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.target-pill-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #1e293b;
}

.target-pill-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
  font-weight: 600;
}

.pill-check {
  font-size: 11px;
  color: #2563eb;
  font-weight: bold;
}

/* 选中文本气泡引用与快操作条 (信标 1 体验核心) */
.selected-text-quote {
  width: 100%;
  margin-top: 4px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 11.5px;
  color: #1e3a8a;
  line-height: 1.4;
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.quote-symbol {
  font-family: Georgia, serif;
  font-size: 14px;
  font-weight: bold;
  color: #3b82f6;
}

.quote-body {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-style: italic;
}

.selection-actions-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 14px;
  background: #f0fdf4;
  border-bottom: 1px solid #dcfce7;
}

.sel-bar-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #15803d;
  flex-shrink: 0;
}

.sel-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border-radius: 5px;
  background: #ffffff;
  border: 1px solid #86efac;
  color: #166534;
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.sel-action-btn:hover {
  background: #22c55e;
  color: #ffffff;
  border-color: #16a34a;
  transform: translateY(-1px);
}

.heading-scope-select {
  width: 150px;
}

.cancel-btn {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #64748b;
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cancel-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
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

/* 信标锁定展示区 (分章节展示信标芯片) */
.beacon-capsules-group {
  margin: 6px 12px 2px 12px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.beacon-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: #334155;
}

.beacon-header-title {
  display: flex;
  align-items: center;
  gap: 4px;
}

.beacon-radar-icon {
  font-size: 12px;
}

.beacon-clear-all-btn {
  padding: 1px 6px;
  font-size: 10.5px;
  color: #ef4444;
  background: transparent;
  border: 1px solid #fecaca;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.beacon-clear-all-btn:hover {
  background: #fee2e2;
}

.beacon-sections-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 130px;
  overflow-y: auto;
  padding-right: 2px;
}

.beacon-sections-list::-webkit-scrollbar {
  width: 4px;
}
.beacon-sections-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}

.beacon-section-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.beacon-section-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  color: #64748b;
  font-weight: 600;
}

.section-badge {
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 4px;
  color: #334155;
}

.section-count {
  font-size: 10px;
  color: #94a3b8;
}

.beacon-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.beacon-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  font-size: 11px;
  color: #1e293b;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: default;
  transition: all 0.15s ease;
}

.beacon-chip:hover {
  border-color: #38bdf8;
  background: #f0f9ff;
  box-shadow: 0 2px 4px rgba(56, 189, 248, 0.15);
}

.chip-icon {
  font-size: 10px;
}

.chip-num {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  color: #0284c7;
  font-size: 10px;
}

.chip-preview {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: #334155;
}

.chip-remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  padding: 0;
  margin-left: 2px;
  background: transparent;
  border: none;
  border-radius: 50%;
  color: #94a3b8;
  font-size: 9px;
  cursor: pointer;
  transition: all 0.1s ease;
}

.chip-remove-btn:hover {
  background: #fee2e2;
  color: #ef4444;
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
  font-size: 11.5px;
  color: #94a3b8;
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
