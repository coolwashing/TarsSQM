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

      <!-- 2. 面板主体 (紧凑简洁、清晰无废话设计) -->
      <div class="panel-body">
        <!-- 偏好控制单行栏 -->
        <div class="preferences-bar">
          <div class="pref-left">
            <el-tooltip content="字数限制：限制 AI 回答的最大字数，留空为不限" placement="top" :show-after="500">
              <span class="pref-label">
                <el-icon><Document /></el-icon>
                <span>字数</span>
              </span>
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
            <el-tooltip content="【仅出方案模式】：要求 AI 仅提供方案思路与架构设计，严禁修改或重构物理代码" placement="top" :show-after="500">
              <el-checkbox v-model="noCodeOnlyPlan" size="small">
                <span :class="['no-code-tag', { 'is-active': noCodeOnlyPlan }]">
                  ⚠️ 仅出方案
                </span>
              </el-checkbox>
            </el-tooltip>
          </div>
        </div>

        <!-- 需求输入区 -->
        <div class="prompt-input-section">
          <div class="section-sub-header">
            <span class="sub-title">
              <el-icon><EditPen /></el-icon>
              <span>需求描述</span>
            </span>
            <div class="sub-header-actions">
              <el-tooltip content="清空当前输入文本" placement="top" :show-after="500">
                <el-button
                  v-if="userPrompt.trim()"
                  link
                  type="info"
                  size="small"
                  :icon="Close"
                  @click="userPrompt = ''"
                  class="sub-action-btn"
                >
                  清空
                </el-button>
              </el-tooltip>
              <el-tooltip content="将当前文本保存为快捷预设指令" placement="top" :show-after="500">
                <el-button
                  link
                  type="primary"
                  size="small"
                  :icon="Star"
                  @click="openAddPresetDialog"
                  class="sub-action-btn"
                >
                  存为预设
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <!-- 支持自然回车换行与自适应扩展 -->
          <el-input
            ref="promptTextareaRef"
            v-model="userPrompt"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 7 }"
            resize="vertical"
            @keydown.stop
            placeholder="输入需求描述（支持 Enter 换行，拾取模式下点击页面元素可插入【信标】）..."
            class="user-prompt-textarea"
          />
        </div>

        <!-- 常用指令胶囊栏 -->
        <div class="favorites-section">
          <div class="favorites-chips-wrap">
            <div
              v-for="fav in allFavorites"
              :key="fav.id"
              class="fav-pill-item"
              :class="{ 'is-custom': fav.isCustom }"
              :title="fav.prompt"
              @click="applyFavorite(fav.prompt)"
            >
              <span class="fav-pill-text">
                {{ formatPresetTitle(fav.title) }}
              </span>
              <!-- 快捷就地动作（支持编辑与删除任何指令） -->
              <div class="fav-pill-actions" @click.stop>
                <el-icon
                  class="fav-action-btn edit-btn"
                  title="编辑此指令"
                  @click.stop="openEditPresetDialog(fav)"
                >
                  <Edit />
                </el-icon>
                <el-icon
                  class="fav-action-btn del-btn"
                  title="删除此指令"
                  @click.stop="deleteFavorite(fav.id, fav.title)"
                >
                  <Close />
                </el-icon>
              </div>
            </div>

            <!-- 新增快捷指令标签 -->
            <span
              class="fav-pill-item add-pill-item"
              @click="openAddPresetDialog"
              title="新增自定义快捷指令，持久化至 data/teleprompter_presets.json"
            >
              <el-icon><Plus /></el-icon>
              <span>增加指令</span>
            </span>

            <!-- 指令集中管理弹窗入口 -->
            <span
              class="fav-pill-item manage-pill-item"
              @click="openManageDialog"
              title="打开指令管理窗口，集中进行查看、编辑、新增、删除与重置"
            >
              <el-icon><Setting /></el-icon>
              <span>管理</span>
            </span>
          </div>
        </div>

        <!-- 信标清单 -->
        <div class="beacons-cart-section">
          <div class="cart-header">
            <span class="cart-title">
              <el-icon color="#4f46e5"><Location /></el-icon>
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
                    title="移除此信标"
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
            <span>未选信标，拾取模式下点击页面元素即可捕获</span>
          </div>
        </div>
      </div>

      <!-- 3. 独立底部操作栏 (不在内部滚动条内，始终外置吸底) -->
      <div class="panel-footer">
        <div class="footer-left-actions">
          <el-tooltip content="一键清空当前输入与所有信标" placement="top" :show-after="500">
            <el-button
              size="default"
              type="danger"
              plain
              @click="resetAll"
              :icon="Delete"
              class="clear-all-btn"
            >
              清空
            </el-button>
          </el-tooltip>
          <el-tooltip content="开启后，复制成功后自动清空当前指令与信标，再次按 Alt+X 打开即为干净面板" placement="top" :show-after="500">
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
          <el-icon><CopyDocument /></el-icon>
          <span>一键复制需求与信标</span>
        </el-button>
      </div>
    </div>
  </Teleport>

  <!-- 1. 常用指令编辑与新增弹窗 (持久化至 data/teleprompter_presets.json) -->
  <el-dialog
    v-model="editDialogVisible"
    :title="formPreset.id ? '✏️ 编辑提词指令' : '⭐ 新增提词指令'"
    width="480px"
    append-to-body
    class="teleprompter-edit-dialog"
  >
    <div class="preset-edit-form">
      <div class="form-row">
        <label class="form-label">指令标签简称（建议带 Emoji，如：🎨 UI 视觉调优）：</label>
        <el-input
          v-model="formPreset.title"
          placeholder="例如：🎨 UI 视觉调优"
          maxlength="25"
          show-word-limit
        />
      </div>
      <div class="form-row" style="margin-top: 12px;">
        <label class="form-label">完整提示词内容 (可包含【信标 1】占位符)：</label>
        <el-input
          v-model="formPreset.prompt"
          type="textarea"
          :rows="4"
          placeholder="输入点击该标签时插入的详细需求与信标说明..."
        />
      </div>
      <div class="preset-sync-tip">
        📁 保存后将持久化至 <code>data/teleprompter_presets.json</code>，随 Git 自动跨设备同步。
      </div>
    </div>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="savingPreset" @click="handleSavePreset">保存并同步</el-button>
    </template>
  </el-dialog>

  <!-- 2. 快捷指令集中管理与配置弹窗 (解决：直接弄一个编辑窗口进行编辑、增加、删除等) -->
  <el-dialog
    v-model="manageDialogVisible"
    title="⚙️ 提词器快捷指令集中管理"
    width="640px"
    append-to-body
    class="teleprompter-manage-dialog"
  >
    <div class="manage-dialog-body">
      <div class="manage-top-bar">
        <span class="manage-tip-text">
          共有 <strong>{{ allFavorites.length }}</strong> 条常用提词指令，修改后实时保存至 <code>data/teleprompter_presets.json</code>。
        </span>
        <div class="manage-top-actions">
          <el-button size="small" type="primary" :icon="Plus" @click="openAddPresetDialog">
            新建指令
          </el-button>
          <el-button size="small" :icon="Refresh" @click="resetToDefaultPresets">
            恢复默认预设
          </el-button>
        </div>
      </div>

      <div class="presets-manage-list">
        <div
          v-for="(item, idx) in allFavorites"
          :key="item.id"
          class="preset-manage-row"
        >
          <div class="row-left">
            <div class="row-badge-line">
              <span class="row-index-badge">{{ idx + 1 }}</span>
              <span class="row-title-pill">{{ formatPresetTitle(item.title) }}</span>
              <span class="row-id-code font-mono">{{ item.id }}</span>
            </div>
            <p class="row-prompt-preview" :title="item.prompt">
              {{ item.prompt }}
            </p>
          </div>
          <div class="row-actions">
            <el-button
              size="small"
              link
              type="primary"
              :icon="Edit"
              @click="openEditPresetDialog(item)"
            >
              编辑
            </el-button>
            <el-button
              size="small"
              link
              type="danger"
              :icon="Delete"
              @click="deleteFavorite(item.id, item.title)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button type="primary" @click="manageDialogVisible = false">完成</el-button>
    </template>
  </el-dialog>
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
  Refresh,
  Edit,
  Plus,
  EditPen,
  Document,
  Location,
  CopyDocument,
  Setting
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

// 常用与自定义指令收藏 (从 data/teleprompter_presets.json 同步)
interface FavoriteItem {
  id: string
  title: string
  prompt: string
  isCustom?: boolean
}

const formatPresetTitle = (title: string): string => {
  if (!title) return ''
  return title.replace(/^【|】$/g, '').trim()
}

const defaultPresets: FavoriteItem[] = [
  {
    id: 'preset_ui_ux',
    title: '🎨 UI 视觉调优',
    prompt: '请优化【信标 1】的视觉样式、间距对齐与整体质感',
    isCustom: false
  },
  {
    id: 'preset_form_check',
    title: '🛡️ 防呆与校验',
    prompt: '请为【信标 1】增加表单防呆校验、非法字符拦截与二次警示确认机制',
    isCustom: false
  },
  {
    id: 'preset_interact_anim',
    title: '⚡ 交互体验提升',
    prompt: '请优化【信标 1】的悬浮反馈、点击交互动效与平滑过渡效果',
    isCustom: false
  },
  {
    id: 'preset_api_link',
    title: '🔌 接口数据联调',
    prompt: '请将【信标 1】对接后端业务接口，并实现数据联动刷新与异常处理',
    isCustom: false
  },
  {
    id: 'preset_refactor',
    title: '📐 架构组件重构',
    prompt: '请将【信标 1】重构抽离为高内聚、易维护的独立子组件，并完善 Props 与 Emits 定义',
    isCustom: false
  },
  {
    id: 'preset_empty_skeleton',
    title: '⏳ 骨架屏与空态',
    prompt: '请为【信标 1】增加加载中骨架屏与数据为空时的引导插画占位',
    isCustom: false
  },
  {
    id: 'preset_debug_fix',
    title: '🐞 缺陷排查修复',
    prompt: '请排查修复【信标 1】的控制台异常报警、边界条件处理与逻辑缺陷',
    isCustom: false
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

// 提词器预设指令列表 (从后端 data/teleprompter_presets.json 动态同步)
const presetsList = ref<FavoriteItem[]>([])

const fetchPresets = async () => {
  try {
    const res = await fetch('/api/dev/teleprompter/prompts')
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        presetsList.value = data

        // 自动将历史 localStorage 中的自定义收藏迁移写入 JSON
        const localCustoms = getInitialCustomFavorites()
        if (localCustoms && localCustoms.length > 0) {
          const remoteIds = new Set(data.map((d: any) => d.id))
          const unmigrated = localCustoms.filter(c => !remoteIds.has(c.id))
          if (unmigrated.length > 0) {
            await fetch('/api/dev/teleprompter/prompts/batch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(unmigrated)
            })
            localStorage.removeItem('sqm_teleprompter_custom_favs')
            const refreshRes = await fetch('/api/dev/teleprompter/prompts')
            if (refreshRes.ok) {
              presetsList.value = await refreshRes.json()
            }
          }
        }
        return
      }
    }
  } catch {
    // 离线备用
  }

  if (presetsList.value.length === 0) {
    presetsList.value = [
      ...defaultPresets,
      ...getInitialCustomFavorites()
    ]
  }
}

const allFavorites = computed(() => {
  return presetsList.value.length > 0 ? presetsList.value : defaultPresets
})

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

// 常用指令弹窗控制与表单状态 (持久化至 data/teleprompter_presets.json)
const editDialogVisible = ref(false)
const manageDialogVisible = ref(false)
const savingPreset = ref(false)
const formPreset = ref<{ id?: string; title: string; prompt: string }>({
  title: '',
  prompt: ''
})

const openAddPresetDialog = () => {
  formPreset.value = {
    title: '',
    prompt: userPrompt.value.trim()
  }
  editDialogVisible.value = true
}

const openEditPresetDialog = (preset: FavoriteItem) => {
  formPreset.value = {
    id: preset.id,
    title: preset.title,
    prompt: preset.prompt
  }
  editDialogVisible.value = true
}

const openManageDialog = () => {
  manageDialogVisible.value = true
}

const resetToDefaultPresets = async () => {
  try {
    await ElMessageBox.confirm('确定要恢复系统标准预设指令吗？将重置为标准的 7 条高频开发场景指令。', '恢复预设确认', {
      type: 'warning',
      confirmButtonText: '确定重置',
      cancelButtonText: '取消'
    })
    const res = await fetch('/api/dev/teleprompter/prompts/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(defaultPresets)
    })
    if (res.ok) {
      ElMessage.success('已恢复系统标准指令预设！')
      await fetchPresets()
    }
  } catch {}
}

const handleSavePreset = async () => {
  if (!formPreset.value.title.trim() || !formPreset.value.prompt.trim()) {
    ElMessage.warning('请填写指令简称和提示词内容')
    return
  }
  savingPreset.value = true
  const title = formPreset.value.title.trim()
  const payload = {
    id: formPreset.value.id || ('custom_' + Date.now()),
    title: title,
    prompt: formPreset.value.prompt.trim(),
    isCustom: true
  }

  try {
    const res = await fetch('/api/dev/teleprompter/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      ElMessage.success('已保存并持久化至 data/teleprompter_presets.json！')
      editDialogVisible.value = false
      await fetchPresets()
      savingPreset.value = false
      return
    }
  } catch {}

  // 离线兜底
  const idx = presetsList.value.findIndex(p => p.id === payload.id)
  if (idx >= 0) {
    presetsList.value[idx] = payload
  } else {
    presetsList.value.push(payload)
  }
  editDialogVisible.value = false
  ElMessage.success('已保存至常用收藏！')
  savingPreset.value = false
}

const deleteFavorite = async (id: string, title?: string) => {
  try {
    await ElMessageBox.confirm(`确定要删除指令「${title || id}」吗？（将同步更新 data/teleprompter_presets.json）`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    try {
      const res = await fetch(`/api/dev/teleprompter/prompts/${id}`, { method: 'DELETE' })
      if (res.ok) {
        ElMessage.success('已从 JSON 移除该指令')
        await fetchPresets()
        return
      }
    } catch {}

    // 离线兜底
    presetsList.value = presetsList.value.filter(f => f.id !== id)
    ElMessage.info('已移除收藏')
  } catch {
    // 取消
  }
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
  if (
    panelPosition.value.x > window.innerWidth - 80 ||
    panelPosition.value.y > window.innerHeight - 50 ||
    panelPosition.value.x < 0 ||
    panelPosition.value.y < 0
  ) {
    panelPosition.value = {
      x: Math.max(window.innerWidth - 490, 20),
      y: Math.max(window.innerHeight - 520, 20)
    }
  }
  isVisible.value = true
  currentMode.value = 'picking'
  fetchPresets()
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
  fetchPresets()
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
  width: 460px;
  max-width: calc(100vw - 24px);
  background: #14151a;
  border: 1px solid #27272a;
  border-radius: 12px;
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.08);
  z-index: 999999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: auto;
  color: #e4e4e7;
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
  background: #1c1d22;
  border-bottom: 1px solid #27272a;
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
  font-size: 13.5px;
  font-weight: 700;
  color: #f4f4f5;
  white-space: nowrap;
}

.hotkey-badge {
  font-family: monospace;
  font-size: 10.5px;
  font-weight: 600;
  padding: 0 5px;
  height: 18px;
  line-height: 16px;
  background: #312e81;
  border: 1px solid #4338ca;
  color: #c7d2fe;
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
  padding: 4px 9px;
  font-size: 11.5px;
  white-space: nowrap;
  background: #27272a;
  border-color: #3f3f46;
  color: #a1a1aa;
}

.mode-toggle-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #ffffff;
  box-shadow: -1px 0 0 0 #4f46e5;
}

.mode-btn-content {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.close-btn {
  color: #71717a;
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
  max-height: calc(85vh - 120px);
  overflow-y: auto;
}

/* 偏好控制单行 */
.preferences-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1c1d22;
  border: 1px solid #27272a;
  border-radius: 7px;
  padding: 5px 10px;
}

.pref-left,
.pref-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pref-label {
  font-size: 11.5px;
  color: #a1a1aa;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.word-limit-input {
  width: 86px;
}

.word-limit-input :deep(.el-input__wrapper) {
  background-color: #14151a;
  box-shadow: 0 0 0 1px #3f3f46 inset;
}

.word-limit-input :deep(.el-input__inner) {
  font-size: 11.5px;
  padding-left: 6px;
  color: #f4f4f5;
}

.word-limit-input :deep(.el-input-number__decrease),
.word-limit-input :deep(.el-input-number__increase) {
  background: #27272a;
  color: #a1a1aa;
  border-color: #3f3f46;
}

.no-code-tag {
  font-size: 11.5px;
  color: #a1a1aa;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.no-code-tag.is-active {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.16);
  font-weight: 600;
}

:deep(.el-checkbox__label) {
  color: #a1a1aa;
}

:deep(.el-checkbox__input .el-checkbox__inner) {
  background-color: #14151a;
  border-color: #52525b;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4f46e5;
  border-color: #4f46e5;
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
  font-size: 12px;
  font-weight: 600;
  color: #e4e4e7;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sub-action-btn {
  font-size: 11.5px;
}

.user-prompt-textarea :deep(textarea) {
  font-family: inherit;
  font-size: 12.5px;
  line-height: 1.5;
  background-color: #1c1d22;
  border-radius: 6px;
  padding: 8px 10px;
  border-color: #3f3f46;
  color: #f4f4f5;
  transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
}
.user-prompt-textarea :deep(textarea:focus) {
  background-color: #14151a;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
}
.user-prompt-textarea :deep(textarea::placeholder) {
  color: #71717a;
}

/* 常用指令胶囊 */
.favorites-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fav-pill-item {
  display: inline-flex;
  align-items: center;
  position: relative;
  background: #1c1d22;
  border: 1px solid #33353f;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}

.fav-pill-item:hover {
  background: #2e2b5c;
  border-color: #6366f1;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(99, 102, 241, 0.2);
}

.fav-pill-item:active {
  transform: translateY(0);
}

.fav-pill-item.is-custom {
  background: #271a38;
  border-color: #581c87;
}

.fav-pill-text {
  font-size: 11.5px;
  font-weight: 500;
  color: #d4d4d8;
  padding: 4px 8px;
  cursor: pointer;
  white-space: nowrap;
}

.fav-pill-item:hover .fav-pill-text {
  color: #c7d2fe;
}

.fav-pill-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding-right: 5px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.fav-pill-item:hover .fav-pill-actions {
  opacity: 1;
}

.fav-action-btn {
  font-size: 11px;
  padding: 1px;
  border-radius: 2px;
  color: #a1a1aa;
  cursor: pointer;
  transition: all 0.12s;
}

.fav-action-btn.edit-btn:hover {
  color: #818cf8;
  background: rgba(99, 102, 241, 0.25);
}

.fav-action-btn.del-btn:hover {
  color: #f87171;
  background: rgba(239, 68, 68, 0.25);
}

.fav-pill-item.add-pill-item {
  background: rgba(99, 102, 241, 0.12);
  border: 1px dashed #6366f1;
  color: #a5b4fc;
  font-size: 11.5px;
  padding: 4px 9px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
}

.fav-pill-item.add-pill-item:hover {
  background: rgba(99, 102, 241, 0.22);
  border-color: #818cf8;
  color: #c7d2fe;
}

.fav-pill-item.manage-pill-item {
  background: #27272a;
  border: 1px solid #3f3f46;
  color: #d4d4d8;
  font-size: 11.5px;
  padding: 4px 9px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
}

.fav-pill-item.manage-pill-item:hover {
  background: #3f3f46;
  border-color: #52525b;
  color: #ffffff;
}

/* 提词指令集中管理弹窗 */
.manage-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.manage-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.manage-tip-text {
  font-size: 12px;
  color: #475569;
}

.manage-top-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.presets-manage-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.preset-manage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.preset-manage-row:hover {
  border-color: #a5b4fc;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.08);
}

.row-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.row-badge-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.row-index-badge {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.row-title-pill {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 1px 8px;
  border-radius: 4px;
}

.row-id-code {
  font-size: 11px;
  color: #94a3b8;
}

.row-prompt-preview {
  margin: 0;
  font-size: 11.5px;
  color: #64748b;
  line-height: 1.45;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

/* 提词器预设编辑表单 */
.preset-edit-form {
  display: flex;
  flex-direction: column;
}

.form-label {
  font-size: 12px;
  color: #334155;
  font-weight: 500;
  margin-bottom: 5px;
  display: block;
}

.preset-sync-tip {
  font-size: 11px;
  color: #64748b;
  margin-top: 12px;
  padding: 6px 10px;
  background: #f8fafc;
  border-radius: 4px;
  border: 1px dashed #e2e8f0;
}

/* 信标区域 */
.beacons-cart-section {
  background: #1c1d22;
  border: 1px dashed #3f3f46;
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
  font-size: 12px;
  font-weight: 600;
  color: #f4f4f5;
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
  background: #14151a;
  border: 1px solid #4338ca;
  padding: 3px 7px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.beacon-chip-card:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.28);
}

.beacon-badge {
  background: #4f46e5;
  color: #ffffff;
  font-family: monospace;
  font-weight: 700;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
}

.beacon-comp {
  font-weight: 600;
  color: #f4f4f5;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.beacon-snippet {
  color: #a1a1aa;
  font-size: 10.5px;
  max-width: 90px;
}

.beacon-del-btn {
  padding: 0 2px;
  font-size: 11px;
  color: #71717a;
}
.beacon-del-btn:hover {
  color: #ef4444;
}

.empty-beacons-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  color: #71717a;
  font-size: 11px;
}

/* 底部操作 */
.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px 12px 14px;
  border-top: 1px solid #27272a;
  background: #18191f;
  flex-shrink: 0;
}

.footer-left-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.clear-all-btn {
  font-size: 12px;
  padding: 6px 10px;
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.35);
  color: #f87171;
}
.clear-all-btn:hover {
  background: rgba(239, 68, 68, 0.28);
  border-color: #ef4444;
  color: #ffffff;
}

.auto-clear-check {
  font-size: 11px;
  color: #a1a1aa;
  margin-right: 2px;
}

.copy-prompt-btn {
  flex: 1;
  font-weight: 600;
  letter-spacing: 0.3px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border: none;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.28);
  transition: all 0.15s ease;
}
.copy-prompt-btn:hover {
  background: linear-gradient(135deg, #4f46e5, #4338ca);
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.36);
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
