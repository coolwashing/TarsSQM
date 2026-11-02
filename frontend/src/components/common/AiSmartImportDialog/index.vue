<template>
  <el-dialog
    :model-value="modelValue"
    :title="`AI 录入 - ${title || '数据'}`"
    width="920px"
    destroy-on-close
    append-to-body
    class="ai-smart-import-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="ai-import-dialog-body">
      <!-- 顶部紧凑步骤指示条 -->
      <div class="step-nav-bar">
        <div class="step-nav-item" :class="{ active: currentStep === 1, completed: currentStep > 1 }">
          <span class="step-num">1</span>
          <span class="step-label">贴入素材</span>
        </div>
        <div class="step-divider" />
        <div class="step-nav-item" :class="{ active: currentStep === 2, completed: currentStep > 2 }">
          <span class="step-num">2</span>
          <span class="step-label">回填结果</span>
        </div>
        <div class="step-divider" />
        <div class="step-nav-item" :class="{ active: currentStep === 3 }">
          <span class="step-num">3</span>
          <span class="step-label">校验入库</span>
        </div>
      </div>

      <!-- 步骤 1：粘贴原素材 (文本/图片) 并一键复制 Prompt -->
      <div v-if="currentStep === 1" class="step-content step-1-container">
        <div class="paste-zone-box">
          <div class="input-head">
            <div class="title-with-tip">
              <span class="input-title">提取素材</span>
              <el-tooltip content="支持直接 Ctrl+V 粘贴文字、网页表格或剪贴板截图图片" placement="top" :show-after="500">
                <el-icon class="info-tip-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
            <span v-if="pastedImages.length > 0" class="image-count-tag">
              已捕获 {{ pastedImages.length }} 张截图
            </span>
          </div>

          <!-- 粘贴捕获区 -->
          <el-input
            v-model="rawSourceText"
            type="textarea"
            :rows="5"
            placeholder="Ctrl + V 粘贴文本、表格或截图..."
            class="source-textarea"
            @paste="handlePaste"
          />

          <!-- 粘贴的图片缩略图展示 -->
          <div v-if="pastedImages.length > 0" class="pasted-images-row">
            <div
              v-for="(img, idx) in pastedImages"
              :key="idx"
              class="image-thumb-card"
            >
              <img :src="img.url" alt="截图预览" class="thumb-img" />
              <div class="thumb-mask" @click="removeImage(idx)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 自动生成的专属 Prompt 预览区 -->
        <div class="prompt-preview-card">
          <div class="prompt-head">
            <div class="ph-left">
              <span class="ph-title">自动提示词</span>
              <el-radio-group v-model="promptFormat" size="small" class="format-radio-group">
                <el-tooltip content="大模型将输出标准 Markdown 表格代码块，支持大模型聊天界面一键复制" placement="top" :show-after="500">
                  <el-radio-button label="markdown">Markdown 表格 (一键复制)</el-radio-button>
                </el-tooltip>
                <el-tooltip content="大模型将输出标准 JSON 数组代码块" placement="top" :show-after="500">
                  <el-radio-button label="json">JSON 数组</el-radio-button>
                </el-tooltip>
              </el-radio-group>
            </div>
            <div class="ph-right">
              <el-tooltip content="复制提示词与素材，发给大模型后可直接点击大模型代码块右上角【复制】" placement="top" :show-after="500">
                <el-button
                  type="primary"
                  size="small"
                  :icon="CopyDocument"
                  class="copy-prompt-btn"
                  @click="handleCopyPromptAndContent"
                >
                  复制提示词与素材
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <div class="prompt-text-display">
            {{ generatedPromptSnippet }}
          </div>
        </div>

        <div class="step-action-bar">
          <el-button type="primary" size="small" :icon="Right" @click="goToStep(2)">
            下一步：回填结果
          </el-button>
        </div>
      </div>

      <!-- 步骤 2：回填大模型生成的结构化输出 -->
      <div v-else-if="currentStep === 2" class="step-content step-2-container">
        <div class="paste-result-box">
          <div class="input-head">
            <div class="title-with-tip">
              <span class="input-title">大模型结果</span>
              <el-tooltip content="粘贴大模型生成的 Markdown 表格或 JSON 数组代码块" placement="top" :show-after="500">
                <el-icon class="info-tip-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="head-actions">
              <el-tooltip content="在大模型点击复制后，点击此按钮可直接从剪贴板读取并立即解析" placement="top" :show-after="500">
                <el-button
                  type="primary"
                  size="small"
                  plain
                  :icon="DocumentCopy"
                  @click="handlePasteFromClipboard"
                >
                  一键读取剪贴板并解析
                </el-button>
              </el-tooltip>
              <el-button
                v-if="aiResponseText.trim()"
                link
                type="info"
                size="small"
                @click="aiResponseText = ''"
              >
                清空
              </el-button>
            </div>
          </div>

          <el-input
            v-model="aiResponseText"
            type="textarea"
            :rows="9"
            placeholder="在此处粘贴大模型生成的 Markdown 表格或 JSON 数组 (Ctrl + V)..."
            class="ai-response-textarea"
            @input="handleAutoParseDebounced"
          />
        </div>

        <div v-if="parseError" class="parse-error-tip">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ parseError }}</span>
        </div>

        <div class="step-action-bar flex-between">
          <el-button size="small" :icon="Back" @click="goToStep(1)">上一步</el-button>
          <el-button
            type="primary"
            size="small"
            :icon="Check"
            :loading="parsing"
            :disabled="!aiResponseText.trim()"
            @click="triggerParseAndCheck"
          >
            解析并校验
          </el-button>
        </div>
      </div>

      <!-- 步骤 3：数据视检、冲突排重与确认入库 -->
      <div v-else-if="currentStep === 3" class="step-content step-3-container">
        <!-- 冲突排重策略与概览统计栏 -->
        <div class="conflict-control-panel">
          <div class="conflict-strategy-left">
            <span class="strategy-title">重复处理：</span>
            <el-radio-group v-model="conflictStrategy" size="small">
              <el-tooltip content="数据库已有记录仅填补空白字段，保护既有历史数据不被冲掉（推荐）" placement="top" :show-after="500">
                <el-radio-button label="supplement">补充空缺 (推荐)</el-radio-button>
              </el-tooltip>
              <el-tooltip content="遇到数据库已有主键时，覆写更新其所有属性字段" placement="top" :show-after="500">
                <el-radio-button label="overwrite">覆盖更新</el-radio-button>
              </el-tooltip>
              <el-tooltip content="遇到数据库已有主键时跳过，仅追加新记录" placement="top" :show-after="500">
                <el-radio-button label="skip">跳过重复</el-radio-button>
              </el-tooltip>
            </el-radio-group>
          </div>

          <div class="record-summary-badges">
            <span class="badge-item total">共 <strong>{{ parsedRows.length }}</strong> 条</span>
            <span v-if="newRecordsCount > 0" class="badge-item is-new">新增 <strong>{{ newRecordsCount }}</strong></span>
            <span v-if="duplicateRecordsCount > 0" class="badge-item is-dup">冲突 <strong>{{ duplicateRecordsCount }}</strong></span>
          </div>
        </div>

        <!-- 冲突提醒 (清晰指引) -->
        <el-alert
          v-if="duplicateRecordsCount > 0"
          :type="conflictStrategy === 'supplement' ? 'info' : conflictStrategy === 'overwrite' ? 'warning' : 'info'"
          :closable="false"
          show-icon
          class="conflict-alert"
        >
          <template #title>
            <div class="alert-title-box">
              <span>
                检测到 <strong>{{ duplicateRecordsCount }}</strong> 条已存在记录，全局按【<strong>{{ conflictStrategy === 'supplement' ? '补充空缺 (填补空白项，保护旧数据)' : conflictStrategy === 'overwrite' ? '全量覆盖更新' : '跳过不导入' }}</strong>】执行。
              </span>
              <span class="sub-alert-note">（提示：可在表格【状态】列单独切换指定行的策略）</span>
            </div>
          </template>
        </el-alert>

        <!-- 拟入库数据预览微型表格 -->
        <div class="preview-table-box">
          <el-table
            :data="parsedRows"
            size="small"
            border
            stripe
            max-height="320"
            class="mini-preview-table"
          >
            <!-- 状态标签与行级策略切换列 -->
            <el-table-column label="状态" width="105" align="center" fixed="left">
              <template #default="{ row }">
                <!-- 存在冲突行：支持行内自由切换 补充/覆盖/跳过 -->
                <template v-if="row._is_duplicate">
                  <el-popover
                    trigger="click"
                    placement="bottom-start"
                    :width="150"
                    popper-class="row-action-popover"
                  >
                    <template #reference>
                      <el-tag
                        size="small"
                        :type="getRowEffectiveAction(row) === 'supplement' ? 'primary' : getRowEffectiveAction(row) === 'overwrite' ? 'warning' : 'info'"
                        effect="light"
                        class="row-status-tag clickable-action-tag"
                        title="点击可修改该行处理方式"
                      >
                        {{ getRowEffectiveAction(row) === 'supplement' ? '补充' : getRowEffectiveAction(row) === 'overwrite' ? '覆盖' : '跳过' }}
                        <el-icon class="tag-arrow-icon"><ArrowDown /></el-icon>
                      </el-tag>
                    </template>
                    <div class="popover-action-list">
                      <div
                        class="action-item"
                        :class="{ active: getRowEffectiveAction(row) === 'supplement' }"
                        @click="setRowAction(row, 'supplement')"
                      >
                        <span class="dot dot-primary"></span>
                        <span>补充空缺</span>
                      </div>
                      <div
                        class="action-item"
                        :class="{ active: getRowEffectiveAction(row) === 'overwrite' }"
                        @click="setRowAction(row, 'overwrite')"
                      >
                        <span class="dot dot-warning"></span>
                        <span>覆盖更新</span>
                      </div>
                      <div
                        class="action-item"
                        :class="{ active: getRowEffectiveAction(row) === 'skip' }"
                        @click="setRowAction(row, 'skip')"
                      >
                        <span class="dot dot-info"></span>
                        <span>跳过此行</span>
                      </div>
                      <div
                        v-if="row._conflict_action"
                        class="action-item reset-item"
                        @click="setRowAction(row, null)"
                      >
                        <span>跟随全局</span>
                      </div>
                    </div>
                  </el-popover>
                </template>
                <el-tag
                  v-else
                  size="small"
                  type="success"
                  effect="light"
                  class="row-status-tag"
                >
                  新增
                </el-tag>
              </template>
            </el-table-column>

            <!-- 动态业务列 (支持字段级空缺/覆盖感知与就地微调) -->
            <el-table-column
              v-for="col in displayColumns"
              :key="col.prop"
              :prop="col.prop"
              :label="col.label"
              min-width="135"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <div class="cell-editor-container">
                  <el-input
                    v-model="row[col.prop]"
                    size="small"
                    placeholder="-"
                    class="preview-inline-input"
                    :class="{
                      'is-supplemented': isFieldSupplemented(row, col.prop),
                      'is-retained': isFieldRetained(row, col.prop)
                    }"
                  />
                  <!-- 字段级差异指示徽章 -->
                  <template v-if="row._is_duplicate && col.prop !== detectedUniqueKey">
                    <el-tooltip
                      v-if="isFieldSupplemented(row, col.prop)"
                      content="库中此项为空，本次将补充填入"
                      placement="top"
                      :show-after="500"
                    >
                      <span class="field-badge supp-badge">+补</span>
                    </el-tooltip>
                    <el-tooltip
                      v-else-if="isFieldRetained(row, col.prop)"
                      :content="`库中已有【${getFieldDbVal(row, col.prop)}】，按补充策略保留原值`"
                      placement="top"
                      :show-after="500"
                    >
                      <span class="field-badge retain-badge">留</span>
                    </el-tooltip>
                    <el-tooltip
                      v-else-if="isFieldOverwritten(row, col.prop)"
                      :content="`将覆盖库中旧值【${getFieldDbVal(row, col.prop)}】`"
                      placement="top"
                      :show-after="500"
                    >
                      <span class="field-badge overw-badge">改</span>
                    </el-tooltip>
                  </template>
                </div>
              </template>
            </el-table-column>

            <!-- 操作列 -->
            <el-table-column label="操作" width="60" align="center" fixed="right">
              <template #default="{ $index }">
                <el-button
                  link
                  type="danger"
                  size="small"
                  :icon="Delete"
                  title="移除此行"
                  @click="removeParsedRow($index)"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="step-action-bar flex-between">
          <el-button size="small" :icon="Back" @click="goToStep(2)">上一步</el-button>
          <div class="commit-btn-group">
            <el-button size="small" @click="$emit('update:modelValue', false)">取消</el-button>
            <el-button
              type="primary"
              size="small"
              :icon="Check"
              :loading="committing"
              :disabled="effectiveRowsCount === 0"
              @click="handleCommit"
            >
              确认入库 ({{ effectiveRowsCount }} 条)
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  CopyDocument,
  DocumentCopy,
  Right,
  Back,
  Check,
  WarningFilled,
  Delete,
  InfoFilled,
  ArrowDown
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import type { TableColumn } from '../DataTable/types'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    bizKey: string
    title?: string
    columns: TableColumn[]
    uniqueKey?: string
  }>(),
  {
    title: '数据',
    uniqueKey: ''
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'success'): void
  (e: 'refresh'): void
}>()

// 流程步进 1 | 2 | 3
const currentStep = ref<number>(1)

// 步骤 1 数据
const rawSourceText = ref<string>('')
const promptFormat = ref<'markdown' | 'json'>('markdown')
interface PastedImage {
  url: string
  file: File
}
const pastedImages = ref<PastedImage[]>([])

// 步骤 2 数据
const aiResponseText = ref<string>('')
const parsing = ref<boolean>(false)
const parseError = ref<string>('')

// 步骤 3 数据
const parsedRows = ref<Array<Record<string, any>>>([])
const existingKeysSet = ref<Set<string>>(new Set())
const existingRecordsMap = ref<Record<string, Record<string, any>>>({})
const conflictStrategy = ref<'supplement' | 'overwrite' | 'skip'>('supplement')
const committing = ref<boolean>(false)

// 提取当前表格展示业务列
const displayColumns = computed(() => {
  return props.columns.filter(c => c.prop && c.prop !== 'id' && c.prop !== 'actions' && c.label)
})

// 探测唯一主键字段名（如 code, part_no, project_code）
const detectedUniqueKey = computed(() => {
  if (props.uniqueKey) return props.uniqueKey
  const candidate = displayColumns.value.find(c =>
    ['code', 'part_no', 'project_code', 'task_code', 'issue_no'].includes(c.prop)
  )
  return candidate ? candidate.prop : (displayColumns.value[0]?.prop || '')
})

// 自动生成结构化 Prompt
const generatedFullPrompt = computed(() => {
  const fieldsDesc = displayColumns.value.map(c => {
    let line = `  - ${c.label} (字段标识: ${c.prop}): 字符串`
    if (c.options && c.options.length > 0) {
      const optLabels = c.options.map(o => (typeof o === 'string' ? o : o.label))
      line += `，枚举限定值: [${optLabels.join(', ')}]`
    }
    return line
  }).join('\n')

  const headerCols = displayColumns.value.map(c => c.label).join(' | ')
  const dividerCols = displayColumns.value.map(() => '---').join(' | ')
  const sampleCols = displayColumns.value.map(c => '样例' + c.label).join(' | ')

  if (promptFormat.value === 'markdown') {
    let prompt = `你是一个制造业数据分析与提取引擎。请从我提供的原始材料（图片或文本）中提取【${props.title}】表格数据。

【重要输出规范 - 必须遵守】：
1. 严禁任何寒暄、前言、总结或额外解释，只输出一个标准的 markdown 代码块。
2. 必须严格使用 \`\`\`markdown 代码块包裹输出，以便用户点击聊天界面代码块右上角的【一键复制】按钮。
3. 表格第 1 行表头必须严格使用以下标准列名：
| ${headerCols} |
| ${dividerCols} |
4. 各列字段约束与规范：
${fieldsDesc}
5. 若原始材料中某列未提及，请在该单元格填 "-"。
6. 输出示范（严格在代码块中输出）：
\`\`\`markdown
| ${headerCols} |
| ${dividerCols} |
| ${sampleCols} |
\`\`\`

【以下为用户提供的原始材料】：
`
    if (rawSourceText.value.trim()) {
      prompt += `\n${rawSourceText.value.trim()}\n`
    } else if (pastedImages.value.length > 0) {
      prompt += `\n[已附带 ${pastedImages.value.length} 张截图，请识别图中表格数据]\n`
    } else {
      prompt += `\n[请结合附件材料提取]\n`
    }
    return prompt
  }

  // JSON 输出规范
  let prompt = `你是一个制造业数据分析与提取引擎。请从我提供的原始材料（图片或文本）中提取【${props.title}】表格数据。

【重要输出规范 - 必须遵守】：
1. 严禁任何寒暄、前言、总结或额外解释，只输出一个标准的 json 代码块。
2. 必须严格使用 \`\`\`json 代码块包裹，以便用户点击聊天界面右上角【一键复制】按钮。
3. 每一个数据对象包含如下字段：
${fieldsDesc}
4. 严格遵循输出模板：
\`\`\`json
[
  {
${displayColumns.value.slice(0, 3).map(c => `    "${c.prop}": "样例值"`).join(',\n')}
  }
]
\`\`\`

【以下为用户提供的原始材料】：
`
  if (rawSourceText.value.trim()) {
    prompt += `\n${rawSourceText.value.trim()}\n`
  } else if (pastedImages.value.length > 0) {
    prompt += `\n[已附带 ${pastedImages.value.length} 张截图，请识别图中表格]\n`
  } else {
    prompt += `\n[请结合附件材料提取]\n`
  }

  return prompt
})

const generatedPromptSnippet = computed(() => {
  const full = generatedFullPrompt.value
  return full.length > 340 ? full.slice(0, 340) + '...' : full
})

// 处理剪贴板粘贴（支持图片与文本）
const handlePaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.indexOf('image') !== -1) {
      const file = item.getAsFile()
      if (file) {
        const url = URL.createObjectURL(file)
        pastedImages.value.push({ url, file })
        ElMessage.success('已自动捕获剪贴板截图')
      }
    }
  }
}

const removeImage = (index: number) => {
  const [removed] = pastedImages.value.splice(index, 1)
  if (removed?.url) URL.revokeObjectURL(removed.url)
}

// 一键复制 Prompt
const handleCopyPromptAndContent = async () => {
  try {
    await navigator.clipboard.writeText(generatedFullPrompt.value)
    ElMessage.success('已复制提示词与素材到剪贴板！请前往大模型粘贴')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = generatedFullPrompt.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制提示词与素材到剪贴板！请前往大模型粘贴')
  }
}

// 步骤 2：一键从剪贴板读取并解析
const handlePasteFromClipboard = async () => {
  try {
    const text = await navigator.clipboard.readText()
    if (!text || !text.trim()) {
      ElMessage.warning('剪贴板中暂无文本，请先在大模型对话中点击【复制】')
      return
    }
    aiResponseText.value = text
    const ok = parseAiOutput(text)
    if (ok) {
      ElMessage.success('已从剪贴板成功读取并自动解析！')
      await runPreCheckDuplicates()
      currentStep.value = 3
    } else {
      ElMessage.info('已粘贴剪贴板内容，请检查格式后点击解析')
    }
  } catch (e: any) {
    ElMessage.info('未能直接获取系统剪贴板权限，请在文本框中直接按 Ctrl+V 粘贴')
  }
}

const goToStep = (step: number) => {
  currentStep.value = step
}

let parseTimer: any = null
const handleAutoParseDebounced = () => {
  clearTimeout(parseTimer)
  parseTimer = setTimeout(() => {
    if (aiResponseText.value.trim()) {
      parseAiOutput(aiResponseText.value)
    }
  }, 400)
}

// 核心多格式鲁棒解析引擎
const parseAiOutput = (text: string): boolean => {
  parseError.value = ''
  let cleaned = text.trim()
  if (!cleaned) return false

  // 1. 尝试匹配 ```markdown ... ``` 或普通 ``` ... ``` 中的表格
  const codeBlockRegex = /```(?:markdown|md)?\s*([\s\S]*?)\s*```/i
  const match = cleaned.match(codeBlockRegex)
  if (match && match[1]) {
    const insideBlock = match[1].trim()
    if (insideBlock.includes('|') && insideBlock.includes('\n')) {
      const mdRows = parseMarkdownTable(insideBlock)
      if (mdRows.length > 0) {
        normalizeParsedRows(mdRows)
        return true
      }
    }
  }

  // 2. 尝试提取 ```json ... ``` 代码块
  const jsonBlockRegex = /```(?:json)?\s*([\s\S]*?)\s*```/i
  const jsonMatch = cleaned.match(jsonBlockRegex)
  const jsonContent = jsonMatch && jsonMatch[1] ? jsonMatch[1].trim() : cleaned

  // 3. 尝试 JSON.parse
  if (jsonContent.startsWith('[') && jsonContent.endsWith(']')) {
    try {
      const arr = JSON.parse(jsonContent)
      if (Array.isArray(arr) && arr.length > 0) {
        normalizeParsedRows(arr)
        return true
      }
    } catch {}
  }

  // 4. 尝试在任意位置寻找 [ ... ]
  const arrayRegex = /\[\s*\{[\s\S]*\}\s*\]/
  const arrMatch = cleaned.match(arrayRegex)
  if (arrMatch) {
    try {
      const arr = JSON.parse(arrMatch[0])
      if (Array.isArray(arr) && arr.length > 0) {
        normalizeParsedRows(arr)
        return true
      }
    } catch {}
  }

  // 5. 尝试直接解析纯 Markdown 表格 (包含 | 与 \n)
  if (cleaned.includes('|') && cleaned.includes('\n')) {
    const mdRows = parseMarkdownTable(cleaned)
    if (mdRows.length > 0) {
      normalizeParsedRows(mdRows)
      return true
    }
  }

  // 6. 尝试解析 TSV 制表符分隔文本 (从 Excel 或网页直接复制)
  if (cleaned.includes('\t') && cleaned.includes('\n')) {
    const tsvRows = parseTsvTable(cleaned)
    if (tsvRows.length > 0) {
      normalizeParsedRows(tsvRows)
      return true
    }
  }

  parseError.value = '未能自动识别有效表格数据，请确保大模型输出了标准的 Markdown 表格或 JSON 数组'
  return false
}

// 解析 Markdown 表格
const parseMarkdownTable = (mdText: string): Array<Record<string, any>> => {
  const lines = mdText.split(/\r?\n/).map(l => l.trim()).filter(l => l.includes('|'))
  if (lines.length < 2) return []

  const headerLine = lines[0]
  const rawHeaders = headerLine.split('|').map(s => s.trim()).filter(Boolean)
  if (rawHeaders.length === 0) return []

  // 建立表头中文/英文到 prop 的映射
  const propMap: Record<string, string> = {}
  displayColumns.value.forEach(col => {
    propMap[col.label.trim().toLowerCase()] = col.prop
    propMap[col.prop.trim().toLowerCase()] = col.prop
  })

  const mappedProps = rawHeaders.map(h => {
    const key = h.toLowerCase()
    return propMap[key] || h
  })

  const rows: Array<Record<string, any>> = []
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    // 跳过分隔线如 |---|---| 或 |:---|
    if (/^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$/.test(line)) {
      continue
    }
    const cells = line.split('|').map(s => s.trim())
    if (line.startsWith('|') && cells[0] === '') cells.shift()
    if (line.endsWith('|') && cells[cells.length - 1] === '') cells.pop()

    if (cells.length > 0 && cells.some(c => c !== '')) {
      const rowObj: Record<string, any> = {}
      mappedProps.forEach((p, idx) => {
        const val = cells[idx] ?? ''
        rowObj[p] = val === '-' ? '' : val
      })
      rows.push(rowObj)
    }
  }
  return rows
}

// 解析 TSV 制表符分隔
const parseTsvTable = (tsvText: string): Array<Record<string, any>> => {
  const lines = tsvText.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length < 2) return []
  const headers = lines[0].split('\t').map(s => s.trim())
  const propMap: Record<string, string> = {}
  displayColumns.value.forEach(col => {
    propMap[col.label.trim().toLowerCase()] = col.prop
    propMap[col.prop.trim().toLowerCase()] = col.prop
  })
  const mappedProps = headers.map(h => propMap[h.toLowerCase()] || h)
  const rows: Array<Record<string, any>> = []
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split('\t').map(s => s.trim())
    if (cells.some(c => c !== '')) {
      const rowObj: Record<string, any> = {}
      mappedProps.forEach((p, idx) => {
        rowObj[p] = cells[idx] ?? ''
      })
      rows.push(rowObj)
    }
  }
  return rows
}

// 标准化与修剪行数据
const normalizeParsedRows = (rawList: Array<Record<string, any>>) => {
  parsedRows.value = rawList.map(item => {
    const cleanRow: Record<string, any> = {}
    displayColumns.value.forEach(col => {
      cleanRow[col.prop] = item[col.prop] !== undefined ? item[col.prop] : (item[col.label] ?? '')
    })

    // 智能自愈：针对供应商主数据，若只识别到“供应商简称(code)”但“企业全称(name)”为空，自动互补填充
    if (props.bizKey === 'supplier') {
      const codeVal = cleanRow.code ? String(cleanRow.code).trim() : ''
      const nameVal = cleanRow.name ? String(cleanRow.name).trim() : ''
      if (codeVal && (!nameVal || nameVal === '-')) {
        cleanRow.name = codeVal
      } else if (nameVal && (!codeVal || codeVal === '-')) {
        cleanRow.code = nameVal
      }
    } else if (props.bizKey === 'project') {
      if (cleanRow.project_code && (!cleanRow.name || cleanRow.name === '-')) {
        cleanRow.name = cleanRow.project_code
      }
    } else if (props.bizKey === 'task') {
      if (cleanRow.task_code && (!cleanRow.title || cleanRow.title === '-')) {
        cleanRow.title = cleanRow.task_code
      }
    }

    cleanRow._is_duplicate = false
    cleanRow._conflict_action = null
    return cleanRow
  })
}

// 触发解析并预检排重
const triggerParseAndCheck = async () => {
  parsing.value = true
  try {
    const ok = parseAiOutput(aiResponseText.value)
    if (!ok) return

    await runPreCheckDuplicates()
    currentStep.value = 3
  } finally {
    parsing.value = false
  }
}

// 调后台预检已有 keys 与快照记录
const runPreCheckDuplicates = async () => {
  const uKey = detectedUniqueKey.value
  if (!uKey || !props.bizKey) return

  const candidateKeys = parsedRows.value
    .map(r => String(r[uKey] || '').trim())
    .filter(Boolean)

  if (candidateKeys.length === 0) return

  try {
    const res = await axios.post(`/api/smart-import/pre-check/${props.bizKey}`, {
      keys: candidateKeys
    })
    const existing = res.data?.existing_keys || []
    existingKeysSet.value = new Set(existing.map((k: any) => String(k).trim()))
    existingRecordsMap.value = res.data?.existing_records || {}

    // 标记每行是否属于已有记录
    parsedRows.value.forEach(row => {
      const k = String(row[uKey] || '').trim()
      row._is_duplicate = existingKeysSet.value.has(k)
      if (row._is_duplicate && !row._conflict_action) {
        row._conflict_action = null
      }
    })
  } catch (err: any) {
    console.warn('查重预检接口异常，转由前端直显', err)
  }
}

// 行级有效策略计算（若行单独指定则优先，否则跟随全局）
const getRowEffectiveAction = (row: any): 'supplement' | 'overwrite' | 'skip' => {
  if (!row._is_duplicate) return 'supplement'
  return row._conflict_action || conflictStrategy.value
}

const setRowAction = (row: any, action: 'supplement' | 'overwrite' | 'skip' | null) => {
  row._conflict_action = action
}

// 获取库中已有字段值
const getFieldDbVal = (row: any, prop: string): string => {
  const uKey = detectedUniqueKey.value
  const keyVal = String(row[uKey] || '').trim()
  const dbRec = existingRecordsMap.value[keyVal]
  if (!dbRec) return ''
  return String(dbRec[prop] ?? '').trim()
}

// 是否为“补充字段”（库中原值为空，新录入有值，且策略为 supplement）
const isFieldSupplemented = (row: any, prop: string): boolean => {
  if (!row._is_duplicate) return false
  if (getRowEffectiveAction(row) !== 'supplement') return false
  const newVal = String(row[prop] || '').trim()
  if (!newVal || newVal === '-') return false
  const dbVal = getFieldDbVal(row, prop)
  return !dbVal || dbVal === '-'
}

// 是否为“保留旧值”（库中有非空值，且策略为 supplement）
const isFieldRetained = (row: any, prop: string): boolean => {
  if (!row._is_duplicate) return false
  if (getRowEffectiveAction(row) !== 'supplement') return false
  const dbVal = getFieldDbVal(row, prop)
  return !!dbVal && dbVal !== '-'
}

// 是否为“覆盖旧值”（库中有旧值，新录入有不同值，且策略为 overwrite）
const isFieldOverwritten = (row: any, prop: string): boolean => {
  if (!row._is_duplicate) return false
  if (getRowEffectiveAction(row) !== 'overwrite') return false
  const dbVal = getFieldDbVal(row, prop)
  const newVal = String(row[prop] || '').trim()
  return !!dbVal && dbVal !== '-' && newVal !== dbVal
}

// 统计指示
const duplicateRecordsCount = computed(() => {
  return parsedRows.value.filter(r => r._is_duplicate).length
})

const newRecordsCount = computed(() => {
  return parsedRows.value.filter(r => !r._is_duplicate).length
})

const effectiveRowsCount = computed(() => {
  return parsedRows.value.filter(r => {
    if (!r._is_duplicate) return true
    return getRowEffectiveAction(r) !== 'skip'
  }).length
})

const removeParsedRow = (idx: number) => {
  parsedRows.value.splice(idx, 1)
}

// 确认提交落库
const handleCommit = async () => {
  if (parsedRows.value.length === 0) return

  committing.value = true
  try {
    const payloadRows = parsedRows.value.map(row => {
      const clean: Record<string, any> = {}
      displayColumns.value.forEach(c => {
        clean[c.prop] = row[c.prop]
      })

      if (props.bizKey === 'supplier') {
        const effName = clean.name || clean.code || clean.short_name
        if (effName && effName !== '-') {
          if (!clean.name || clean.name === '-') clean.name = effName
          if (!clean.code || clean.code === '-') clean.code = effName
          if (!clean.short_name || clean.short_name === '-') clean.short_name = effName
        }
      }

      if (row._conflict_action) {
        clean['_conflict_action'] = row._conflict_action
      }
      return clean
    })

    const res = await axios.post(`/api/smart-import/commit/${props.bizKey}`, {
      rows: payloadRows,
      conflict_strategy: conflictStrategy.value
    })

    ElMessage.success(res.data?.message || '批量入库成功！')
    emit('success')
    emit('refresh')
    emit('update:modelValue', false)
  } catch (err: any) {
    ElMessage.error(`批量入库失败: ${err.response?.data?.detail || err.message || '网络连接异常'}`)
  } finally {
    committing.value = false
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      currentStep.value = 1
      rawSourceText.value = ''
      pastedImages.value = []
      aiResponseText.value = ''
      parsedRows.value = []
      parseError.value = ''
      existingKeysSet.value.clear()
      existingRecordsMap.value = {}
      conflictStrategy.value = 'supplement'
    }
  }
)
</script>

<style scoped>
.ai-import-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 顶部步骤导航条 */
.step-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.step-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.step-nav-item.active {
  color: #2563eb;
}
.step-nav-item.active .step-num {
  background-color: #2563eb;
  color: #ffffff;
}

.step-nav-item.completed {
  color: #10b981;
}
.step-nav-item.completed .step-num {
  background-color: #10b981;
  color: #ffffff;
}

.step-divider {
  flex: 1;
  height: 1px;
  background-color: #e2e8f0;
  margin: 0 16px;
}

.title-with-tip {
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-tip-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.15s;
}

.info-tip-icon:hover {
  color: #2563eb;
}

/* 步骤 1 */
.step-1-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.paste-zone-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.input-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
}

.image-count-tag {
  font-size: 11.5px;
  color: #2563eb;
  background-color: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.pasted-images-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.image-thumb-card {
  position: relative;
  width: 90px;
  height: 70px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.65);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 11px;
  opacity: 0;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.image-thumb-card:hover .thumb-mask {
  opacity: 1;
}

/* Prompt 预览卡片 */
.prompt-preview-card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prompt-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ph-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ph-right {
  display: flex;
  align-items: center;
}

.format-radio-group :deep(.el-radio-button__inner) {
  font-size: 12px;
  padding: 5px 10px;
}

.ph-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
}

.prompt-text-display {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 11.5px;
  color: #475569;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 10px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 90px;
  overflow-y: auto;
}

/* 步骤 2 */
.step-2-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.parse-error-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 12.5px;
}

/* 步骤 3 */
.step-3-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conflict-control-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.conflict-strategy-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 4px;
}

.record-summary-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-item {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-item.total {
  background-color: #e2e8f0;
  color: #334155;
}

.badge-item.is-new {
  background-color: #dcfce7;
  color: #166534;
}

.badge-item.is-dup {
  background-color: #fef3c7;
  color: #92400e;
}

.conflict-alert {
  margin-bottom: 2px;
}

.alert-title-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  font-size: 12.5px;
  line-height: 1.5;
}

.sub-alert-note {
  font-size: 12px;
  color: #64748b;
}

.preview-table-box {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.mini-preview-table :deep(.el-table__header th) {
  background-color: #f8fafc;
  font-weight: 600;
  color: #334155;
  padding: 6px 0;
}

.mini-preview-table :deep(.el-table__body td) {
  padding: 4px 0;
}

.clickable-action-tag {
  cursor: pointer;
  user-select: none;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  transition: all 0.15s ease;
}

.clickable-action-tag:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

.tag-arrow-icon {
  font-size: 10px;
}

/* 单元格行内编辑与差异徽章 */
.cell-editor-container {
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;
  width: 100%;
}

.preview-inline-input {
  flex: 1;
}

.preview-inline-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 0 4px;
}

.preview-inline-input:hover :deep(.el-input__wrapper) {
  background: #f1f5f9;
}

.preview-inline-input.is-supplemented :deep(.el-input__inner) {
  color: #0369a1;
  font-weight: 500;
}

.preview-inline-input.is-retained :deep(.el-input__inner) {
  color: #475569;
}

.field-badge {
  font-size: 10px;
  line-height: 14px;
  padding: 0 4px;
  border-radius: 3px;
  white-space: nowrap;
  font-weight: 600;
  cursor: help;
  user-select: none;
}

.field-badge.supp-badge {
  background-color: #e0f2fe;
  color: #0284c7;
  border: 1px solid #bae6fd;
}

.field-badge.retain-badge {
  background-color: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.field-badge.overw-badge {
  background-color: #fef3c7;
  color: #d97706;
  border: 1px solid #fde68a;
}

.step-action-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  gap: 12px;
}

.step-action-bar.flex-between {
  justify-content: space-between;
}

.commit-btn-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

<style>
/* 弹出菜单全局样式 */
.row-action-popover {
  padding: 6px !important;
  min-width: 130px !important;
}

.popover-action-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.popover-action-list .action-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  font-size: 12px;
  color: #334155;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.popover-action-list .action-item:hover {
  background-color: #f1f5f9;
}

.popover-action-list .action-item.active {
  background-color: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.popover-action-list .action-item.reset-item {
  margin-top: 4px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 6px;
  color: #64748b;
  font-size: 11.5px;
}

.popover-action-list .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.popover-action-list .dot-primary {
  background-color: #2563eb;
}

.popover-action-list .dot-warning {
  background-color: #f59e0b;
}

.popover-action-list .dot-info {
  background-color: #94a3b8;
}
</style>
