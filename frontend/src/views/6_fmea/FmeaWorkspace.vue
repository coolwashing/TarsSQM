<template>
  <div class="fmea-workspace-shell">
    <!-- 44px 极简一字顶栏 (Figma × Linear 风格) -->
    <header class="fmea-topbar">
      <!-- 左侧：模块大纲折叠开关 + 多父级 BOM 下钻路径栈 + 上级借用反查 -->
      <div class="tb-left">
        <button
          type="button"
          class="tb-icon-btn"
          :class="{ active: !sidebarCollapsed }"
          :title="sidebarCollapsed ? '展开左侧模块与大纲目录' : '收起左侧模块目录'"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.65">
            <rect x="2" y="2.5" width="12" height="11" rx="2" />
            <path d="M6.2 2.5v11" />
          </svg>
        </button>

        <!-- BOM 下钻返回上级快捷钮 -->
        <button
          v-if="bomDrillStack.length > 0"
          type="button"
          class="bom-back-btn"
          title="返回上一级父系统画板"
          @click="popBomDrillStack"
        >
          ↑ 返回上级
        </button>

        <div v-if="activeBoard" class="board-crumb">
          <!-- 若处于多级 BOM 下钻态，展示可点击的父级链路 -->
          <template v-if="bomDrillStack.length > 0">
            <template v-for="(anc, idx) in bomDrillStack" :key="`${anc.id}_${idx}`">
              <button type="button" class="crumb-anc-btn" @click="jumpToBomAncestor(idx)">
                {{ anc.name }}
              </button>
              <span class="crumb-slash">▸</span>
            </template>
          </template>
          <template v-else>
            <span class="crumb-group">{{ activeBoard.group_name }}</span>
            <span class="crumb-slash">/</span>
          </template>

          <input
            v-if="renamingBoard"
            v-model="boardTitleDraft"
            class="board-rename-input"
            @blur="commitBoardRename"
            @keyup.enter="commitBoardRename"
            @keyup.esc="renamingBoard = false"
          />
          <span
            v-else
            class="crumb-board"
            title="双击重命名当前模块画板"
            @dblclick="startBoardRename"
          >
            {{ activeBoard.name }}
          </span>

          <!-- 多父级借用反查胶囊：即使从左侧树直接点开子画板，也能一键反查并跳回任一上级总成 -->
          <el-popover
            v-if="activeBoard.parent_boards && activeBoard.parent_boards.length > 0"
            placement="bottom-start"
            :width="270"
            trigger="click"
          >
            <template #reference>
              <button type="button" class="parent-ref-pill" title="查看借用此模块的所有上级父画板">
                被 {{ activeBoard.parent_boards.length }} 处上级借用 ▾
              </button>
            </template>
            <div class="parent-pop">
              <div class="pp-title">借用此画板的上级总成位置（点击跳转）：</div>
              <button
                v-for="(pb, pIdx) in activeBoard.parent_boards"
                :key="`${pb.board_id}_${pb.node_id || pIdx}`"
                type="button"
                class="pp-item"
                @click="handleJumpToBoard({ boardId: pb.board_id, nodeId: pb.node_id || undefined })"
              >
                <div class="ppi-name">{{ pb.board_name }}</div>
                <div class="ppi-sub">{{ pb.group_name }} · 实例：{{ pb.node_title || activeBoard.name }}</div>
              </button>
            </div>
          </el-popover>
        </div>
      </div>

      <!-- 中央：三视图同源切换器 [画板 | 图鉴 | 台账] -->
      <div class="tb-center">
        <div class="view-seg-bar">
          <button
            type="button"
            class="vs-btn"
            :class="{ active: viewMode === 'canvas' }"
            @click="viewMode = 'canvas'"
          >
            画板
          </button>
          <button
            type="button"
            class="vs-btn"
            :class="{ active: viewMode === 'gallery' }"
            @click="viewMode = 'gallery'"
          >
            图鉴
          </button>
          <button
            type="button"
            class="vs-btn"
            :class="{ active: viewMode === 'ledger' }"
            @click="viewMode = 'ledger'"
          >
            台账
          </button>
        </div>
      </div>

      <!-- 右侧：【信标 4】画布风险聚光灯 / 全局检索 + 高危开关 + AI 录入 + 更多 -->
      <div class="tb-right">
        <div class="search-pill">
          <svg class="s-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.65">
            <circle cx="7.2" cy="7.2" r="4.5" />
            <path d="M10.6 10.6l3 3" stroke-linecap="round" />
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            class="s-input"
            :placeholder="topbarSearchPlaceholder"
          />
          <button
            v-if="searchKeyword || refCodeFilter"
            type="button"
            class="s-clear"
            @click="clearFilters"
          >
            ×
          </button>
        </div>

        <button
          type="button"
          class="high-filter-btn"
          :class="{ active: highRiskOnly }"
          title="仅聚焦高危失效风险"
          @click="highRiskOnly = !highRiskOnly"
        >
          <i class="dot" />高危
        </button>

        <button type="button" class="ai-entry-btn" @click="aiDialogVisible = true">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.65">
            <path d="M8 2l1.4 3.6L13 7l-3.6 1.4L8 12 6.6 8.4 3 7l3.6-1.4L8 2z" stroke-linejoin="round" />
          </svg>
          <span>AI 录入</span>
        </button>

        <el-dropdown trigger="click" @command="onMoreCommand">
          <button type="button" class="tb-icon-btn" title="更多画板操作">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
              <circle cx="3.5" cy="8" r="1" fill="currentColor" />
              <circle cx="8" cy="8" r="1" fill="currentColor" />
              <circle cx="12.5" cy="8" r="1" fill="currentColor" />
            </svg>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="activeBoard" command="duplicate_board">
                复制当前画板（创建变体）
              </el-dropdown-item>
              <el-dropdown-item command="export_json">导出当前画板 JSON 备份</el-dropdown-item>
              <el-dropdown-item command="import_json">从 JSON 导入画板布局</el-dropdown-item>
              <el-dropdown-item command="seed_demo" divided>恢复预置示范画板与 BOM 示例</el-dropdown-item>
              <el-dropdown-item v-if="activeBoard" command="delete_board" style="color: #dc2626">
                删除当前画板…
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <input
          ref="importJsonInputRef"
          type="file"
          accept=".json,application/json"
          style="display: none"
          @change="onImportJsonChosen"
        />
      </div>
    </header>

    <!-- 主工作区：左侧可收起导航 + 三视图同源舞台 + 右侧按需悬浮机理卡 -->
    <div class="fmea-body">
      <FmeaModuleSidebar
        v-show="viewMode === 'canvas'"
        :collapsed="sidebarCollapsed"
        :groups="boardGroups"
        :active-board-id="activeBoardId"
        :canvas-data="canvasData"
        :board-items="boardItems"
        :sub-board-stats="activeBoard?.sub_board_stats"
        :selection="selection"
        @select-board="onSelectBoardFromTree"
        @create-board="handleCreateBoard"
        @rename-board="handleSidebarRenameBoard"
        @move-board-group="handleSidebarMoveBoardGroup"
        @duplicate-board="handleSidebarDuplicateBoard"
        @delete-board="handleSidebarDeleteBoard"
        @insert-sub-board="handleInsertSubBoardFromTree"
        @bind-sub-board="handleBindSubBoard"
        @drill-sub-board="handleDrillSubBoard"
        @rename-group="handleSidebarRenameGroup"
        @dissolve-group="handleSidebarDissolveGroup"
        @focus-element="handleFocusOutlineElement"
        @rename-element="handleOutlineRenameElement"
        @delete-element="handleOutlineDeleteElement"
        @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      />

      <!-- 视图 1：自由画板与连线 -->
      <div v-show="viewMode === 'canvas'" class="canvas-stage-container">
        <!-- 当侧边栏收起时，在画布左侧边缘提供快速展开把手 -->
        <button
          v-if="sidebarCollapsed"
          type="button"
          class="sidebar-float-expand-btn"
          title="展开左侧装配与大纲栏"
          @click="sidebarCollapsed = false"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <FmeaCanvasStage
          ref="canvasStageRef"
          :board-id="activeBoardId"
          :canvas-data="canvasData"
          :board-items="boardItems"
          :sub-board-stats="activeBoard?.sub_board_stats"
          :all-boards="flatBoards"
          :ancestor-board-ids="ancestorBoardIds"
          :smooth-focusing="isSmoothFocusing"
          :selection="selection"
          :search-keyword="searchKeyword"
          :high-risk-only="highRiskOnly"
          :can-undo="canUndo"
          :can-redo="canRedo"
          @select="handleCanvasSelect"
          @drill-sub-board="handleDrillSubBoard"
          @before-mutate="pushHistorySnapshot"
          @change="schedulePersist"
          @tidy="tidyLayout"
          @undo="undo"
          @redo="redo"
          @zoom="setZoom"
          @reset-view="resetViewport"
          @delete-element="handleOutlineDeleteElement"
        />

        <!-- 右侧按需滑出模块 FMEA 工作表抽屉 -->
        <FmeaFloatingPanel
          :active-board-id="activeBoardId"
          :selection="selection"
          :canvas-data="canvasData"
          :items="selectedTargetItems"
          :connected-edge-items="connectedEdgeItems"
          :all-board-items="boardItems"
          :sub-board-stats="activeBoard?.sub_board_stats"
          :unit-where-used="activeBoard?.unit_where_used"
          @close="selection = null"
          @rename-target="handleRenameSelectedTarget"
          @delete-target="handleDeleteSelectedTarget"
          @drill-sub-board="handleDrillSubBoard"
          @jump-to-board="handleJumpToBoard"
          @create-item="openCreateItemForSelection"
          @item-created="handleItemCreatedInline"
          @item-updated="handleItemUpdatedInline"
          @edit-item="openEditItemDialog"
          @delete-item="handleDeleteItem"
          @quick-risk="handleQuickRiskChange"
          @append-photo="handleAppendPhotoToCard"
        />
      </div>

      <!-- 视图 2：跨画板失效照片图鉴墙 -->
      <FmeaGalleryView
        v-if="viewMode === 'gallery'"
        :keyword="searchKeyword"
        :high-risk-only="highRiskOnly"
        :refresh-tick="globalRefreshTick"
        @locate="locateItemOnCanvas"
      />

      <!-- 视图 3：复用公共 DataTable 的全局同源台账 -->
      <FmeaLedgerView
        v-if="viewMode === 'ledger'"
        :boards="flatBoards"
        :keyword="searchKeyword"
        :high-risk-only="highRiskOnly"
        :initial-ref-code="refCodeFilter"
        :refresh-tick="globalRefreshTick"
        @locate="locateItemOnCanvas"
        @edit-item="openEditItemDialog"
        @create-global-item="openCreateGlobalItem"
        @mutated="onGlobalDataMutated"
      />
    </div>

    <!-- 新增/编辑 FMEA 机理卡弹窗 -->
    <FmeaItemDialog
      v-model="itemDialogVisible"
      :board-id="dialogTargetCtx.boardId"
      :target-kind="dialogTargetCtx.targetKind"
      :target-id="dialogTargetCtx.targetId"
      :target-title-snapshot="dialogTargetCtx.titleSnapshot"
      :shared-unit-code="dialogTargetCtx.sharedUnitCode"
      :default-part-code="dialogTargetCtx.defaultPartCode"
      :editing-item="editingItem"
      @saved="onItemSaved"
    />

    <!-- AI 多模态图文拆解录入弹窗 -->
    <FmeaAiImportDialog
      v-model="aiDialogVisible"
      :board-id="activeBoardId"
      :canvas-data="canvasData"
      @committed="reloadCurrentBoardAndTree"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type {
  FmeaViewMode,
  FmeaBoardGroup,
  FmeaBoardSummary,
  FmeaBoardDetail,
  FmeaItem,
  CanvasModuleNode,
  CanvasSelection,
  TargetKind,
  RiskLevel,
  FmeaPhoto
} from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import { useFmeaCanvas, cloneCanvasData } from '@/views/6_fmea/composables/useFmeaCanvas'
import { useFmeaUpload } from '@/views/6_fmea/composables/useFmeaUpload'
import FmeaModuleSidebar from './components/FmeaModuleSidebar.vue'
import FmeaCanvasStage from './components/FmeaCanvasStage.vue'
import FmeaFloatingPanel from './components/FmeaFloatingPanel.vue'
import FmeaItemDialog from './components/FmeaItemDialog.vue'
import FmeaGalleryView from './components/FmeaGalleryView.vue'
import FmeaLedgerView from './components/FmeaLedgerView.vue'
import FmeaAiImportDialog from './components/FmeaAiImportDialog.vue'

const route = useRoute()
const router = useRouter()

const viewMode = ref<FmeaViewMode>('canvas')
const sidebarCollapsed = ref(false)
const searchKeyword = ref('')
const refCodeFilter = ref('')
const highRiskOnly = ref(false)
const globalRefreshTick = ref(0)

const boardGroups = ref<FmeaBoardGroup[]>([])
const flatBoards = ref<FmeaBoardSummary[]>([])
const activeBoardId = ref<number | null>(null)
const activeBoard = ref<FmeaBoardDetail | null>(null)
const boardItems = ref<FmeaItem[]>([])
const selection = ref<CanvasSelection | null>(null)

// 多级 BOM 下钻导航栈
const bomDrillStack = ref<Array<{ id: number; name: string }>>([])

const renamingBoard = ref(false)
const boardTitleDraft = ref('')
const importJsonInputRef = ref<HTMLInputElement | null>(null)
const canvasStageRef = ref<InstanceType<typeof FmeaCanvasStage> | null>(null)

const itemDialogVisible = ref(false)
const aiDialogVisible = ref(false)
const editingItem = ref<FmeaItem | null>(null)
const dialogTargetCtx = reactive<{
  boardId: number | null
  targetKind: TargetKind
  targetId: string | null
  titleSnapshot: string
  sharedUnitCode: string | null
  defaultPartCode: string
}>({
  boardId: null,
  targetKind: 'node',
  targetId: null,
  titleSnapshot: '',
  sharedUnitCode: null,
  defaultPartCode: ''
})

const { extractImagesFromClipboard } = useFmeaUpload()

const {
  canvasData,
  canUndo,
  canRedo,
  isSmoothFocusing,
  loadCanvas,
  pushHistorySnapshot,
  schedulePersist,
  undo,
  redo,
  setZoom,
  resetViewport,
  tidyLayout,
  focusSelectionInStage
} = useFmeaCanvas(async (latestCanvas) => {
  if (!activeBoardId.value) return
  try {
    const updated = await fmeaApi.updateBoard(activeBoardId.value, { canvas_data: latestCanvas })
    activeBoard.value = updated
    boardItems.value = updated.items
  } catch (err: any) {
    if (err?.response?.status === 400 && err?.response?.data?.detail) {
      ElMessage.error(err.response.data.detail)
      await switchBoard(activeBoardId.value, true)
    }
  }
})

// 【信标 4】根据当前视图语义明确区分顶栏检索框提示词
const topbarSearchPlaceholder = computed(() =>
  viewMode.value === 'canvas' ? '聚光灯：搜失效 / 编码...' : '全局检索失效 / 机理 / 编码...'
)

const ancestorBoardIds = computed(() => bomDrillStack.value.map((x) => x.id))

// 右侧抽屉机理卡聚合：选中节点时聚合直属卡 + 共用本体卡 + 关联剖面热点卡 (如柔轮齿根过渡圆角归属谐波减速器柔轮)
const selectedTargetItems = computed(() => {
  if (!selection.value) return []
  if (selection.value.kind === 'node') {
    const nd = canvasData.value.nodes.find((n) => n.id === selection.value!.id)
    const uc = nd?.unit_code
    const nodeTitle = (nd?.title || '').trim()
    const coreKeyword = nodeTitle.replace(/^(谐波减速器|无框力矩电机|交叉滚子)/, '').trim() || nodeTitle

    return boardItems.value.filter((it) => {
      // 1. 直属该节点
      if (it.target_kind === 'node' && it.target_id === selection.value!.id) return true
      // 2. 绑定的共用单元或零件编码匹配
      if (uc && (it.target_id === uc || (it.ref_codes_text || '').includes(uc))) return true
      // 3. 关联的图纸剖面热点 (例如 柔轮齿根过渡圆角 属于 谐波减速器柔轮)
      if (it.target_kind === 'pin') {
        const pinTitle = it.target_title_snapshot || ''
        if (nodeTitle && pinTitle.includes(nodeTitle)) return true
        if (coreKeyword && coreKeyword.length >= 2 && (pinTitle.includes(coreKeyword) || it.failure_mode.includes(coreKeyword))) return true
      }
      return false
    })
  }
  return boardItems.value.filter(
    (it) => it.target_kind === selection.value!.kind && it.target_id === selection.value!.id
  )
})

// 与当前选中节点或热点相关的连线/接口/工艺挑战失效项
const connectedEdgeItems = computed(() => {
  if (!selection.value) return []
  if (selection.value.kind !== 'node' && selection.value.kind !== 'pin') return []
  const targetId = selection.value.id
  const connectedEdgeIds = (canvasData.value.edges || [])
    .filter((e) => e.from === targetId || e.to === targetId)
    .map((e) => e.id)
  if (connectedEdgeIds.length === 0) return []
  return boardItems.value.filter(
    (it) => it.target_kind === 'edge' && Boolean(it.target_id) && connectedEdgeIds.includes(it.target_id as string)
  )
})

function handleItemCreatedInline(newItem: FmeaItem) {
  boardItems.value.push(newItem)
  globalRefreshTick.value += 1
}

function handleItemUpdatedInline(updatedItem: FmeaItem) {
  const idx = boardItems.value.findIndex((x) => x.id === updatedItem.id)
  if (idx !== -1) {
    boardItems.value[idx] = { ...boardItems.value[idx], ...updatedItem }
  }
  globalRefreshTick.value += 1
}

// ==================== 数据加载、画板切换与多父级 BOM 下钻 ====================

async function fetchTree() {
  const tree = await fmeaApi.getBoardTree()
  boardGroups.value = tree.groups
  flatBoards.value = tree.boards
  return tree.boards
}

async function switchBoard(boardId: number, preserveSelection = false) {
  const detail = await fmeaApi.getBoardDetail(boardId)
  activeBoardId.value = detail.id
  activeBoard.value = detail
  boardItems.value = detail.items
  loadCanvas(detail.canvas_data)
  if (!preserveSelection) {
    selection.value = null
  }
}

async function onSelectBoardFromTree(boardId: number) {
  bomDrillStack.value = []
  await switchBoard(boardId)
}

async function handleDrillSubBoard(subBoardId: number) {
  if (!subBoardId || subBoardId === activeBoardId.value) return
  if (activeBoard.value) {
    const existingIdx = bomDrillStack.value.findIndex((x) => x.id === subBoardId)
    if (existingIdx >= 0) {
      bomDrillStack.value = bomDrillStack.value.slice(0, existingIdx)
    } else {
      bomDrillStack.value.push({ id: activeBoard.value.id, name: activeBoard.value.name })
    }
  }
  await switchBoard(subBoardId)
}

async function popBomDrillStack() {
  const prev = bomDrillStack.value.pop()
  if (prev) {
    await switchBoard(prev.id)
  }
}

async function jumpToBomAncestor(idx: number) {
  const target = bomDrillStack.value[idx]
  if (!target) return
  bomDrillStack.value = bomDrillStack.value.slice(0, idx)
  await switchBoard(target.id)
}

async function handleJumpToBoard(payload: { boardId: number; nodeId?: string }) {
  bomDrillStack.value = []
  viewMode.value = 'canvas'
  if (activeBoardId.value !== payload.boardId) {
    await switchBoard(payload.boardId)
  }
  await nextTick()
  if (payload.nodeId) {
    handleFocusOutlineElement({ kind: 'node', id: payload.nodeId })
  }
}

async function reloadCurrentBoardAndTree() {
  await fetchTree()
  if (activeBoardId.value) {
    await switchBoard(activeBoardId.value, true)
  }
  globalRefreshTick.value += 1
}

// ==================== 【信标 1】左侧目录右键菜单全部处理动作 ====================

async function handleCreateBoard(payload: { group_name: string; name: string; board_type: string }) {
  try {
    const created = await fmeaApi.createBoard(payload)
    bomDrillStack.value = []
    await fetchTree()
    await switchBoard(created.id)
    ElMessage.success(`已创建模块画板「${created.name}」`)
  } catch {
    ElMessage.error('创建画板失败')
  }
}

async function handleSidebarRenameBoard(payload: { boardId: number; name: string }) {
  await fmeaApi.updateBoard(payload.boardId, { name: payload.name })
  if (activeBoard.value?.id === payload.boardId) {
    activeBoard.value.name = payload.name
  }
  await fetchTree()
  ElMessage.success('画板已重命名')
}

async function handleSidebarMoveBoardGroup(payload: { boardId: number; groupName: string }) {
  await fmeaApi.updateBoard(payload.boardId, { group_name: payload.groupName })
  if (activeBoard.value?.id === payload.boardId) {
    activeBoard.value.group_name = payload.groupName
  }
  await fetchTree()
  ElMessage.success(`已移至「${payload.groupName}」`)
}

async function handleSidebarDuplicateBoard(boardId: number) {
  try {
    const dup = await fmeaApi.duplicateBoard(boardId)
    bomDrillStack.value = []
    await fetchTree()
    await switchBoard(dup.id)
    ElMessage.success(`已复制创建画板「${dup.name}」`)
  } catch {
    ElMessage.error('复制画板失败')
  }
}

async function handleSidebarDeleteBoard(payload: { boardId: number; deleteItems: boolean }) {
  try {
    await fmeaApi.deleteBoard(payload.boardId, payload.deleteItems)
    bomDrillStack.value = bomDrillStack.value.filter((x) => x.id !== payload.boardId)
    const list = await fetchTree()
    if (activeBoardId.value === payload.boardId) {
      if (list.length > 0) {
        await switchBoard(list[0].id)
      } else {
        activeBoardId.value = null
        activeBoard.value = null
        boardItems.value = []
      }
    } else if (activeBoardId.value) {
      await switchBoard(activeBoardId.value, true)
    }
    globalRefreshTick.value += 1
    ElMessage.success(payload.deleteItems ? '画板及本地机理卡已删除' : '画板已移除，机理卡已保留至全局台账')
  } catch {
    ElMessage.error('删除画板失败')
  }
}

function handleInsertSubBoardFromTree(board: FmeaBoardSummary) {
  if (!activeBoardId.value || !canvasStageRef.value) return
  canvasStageRef.value.insertSubBoardNode(board)
}

async function handleBindSubBoard(payload: { parentBoardId: number; childBoard: FmeaBoardSummary }) {
  if (payload.parentBoardId === payload.childBoard.id) {
    ElMessage.warning('不能将画板嵌套为自身的子模块')
    return
  }

  // 1. 如果目标父画板就是当前正在编辑的画板，直接在当前画布上插入子画板节点
  if (payload.parentBoardId === activeBoardId.value) {
    if (canvasStageRef.value) {
      canvasStageRef.value.insertSubBoardNode(payload.childBoard)
      await fetchTree()
    }
    return
  }

  // 2. 如果拖拽到的是后台其他画板，拉取该父画板详情并注入该子画板节点
  try {
    const parentDetail = await fmeaApi.getBoardDetail(payload.parentBoardId)
    const cd = cloneCanvasData(parentDetail.canvas_data)

    // 防止重复插入或已有循环
    const exists = (cd.nodes || []).some(n => n.sub_board_id === payload.childBoard.id)
    if (exists) {
      ElMessage.info(`「${parentDetail.name}」已存在对「${payload.childBoard.name}」的子模块绑定引用`)
      return
    }

    let maxX = 100
    for (const nd of (cd.nodes || [])) {
      if (nd.x > maxX) maxX = nd.x
    }
    const newNode: CanvasModuleNode = {
      id: `nd_${Date.now().toString(36)}`,
      title: payload.childBoard.name,
      sub: payload.childBoard.board_code,
      sub_board_id: payload.childBoard.id,
      x: maxX + 180,
      y: 120
    }
    cd.nodes.push(newNode)

    await fmeaApi.updateBoard(payload.parentBoardId, {
      canvas_data: cd
    })

    await fetchTree()
    ElMessage.success(`已将「${payload.childBoard.name}」拖拽绑定为「${parentDetail.name}」的子模块！`)
  } catch (err: any) {
    console.error('拖拽绑定子画板失败', err)
    ElMessage.error('拖拽绑定子画板失败：' + (err?.message || '未知错误'))
  }
}

async function handleSidebarRenameGroup(payload: { oldName: string; newName: string }) {
  await fmeaApi.renameGroup(payload.oldName, payload.newName)
  if (activeBoard.value?.group_name === payload.oldName) {
    activeBoard.value.group_name = payload.newName
  }
  await fetchTree()
  ElMessage.success('系统分组已重命名')
}

async function handleSidebarDissolveGroup(groupName: string) {
  try {
    await ElMessageBox.confirm(
      `确认解散分组「${groupName}」吗？（旗下画板不会丢失，将自动移入「未分组系统」）`,
      '解散分组',
      { type: 'info' }
    )
    await fmeaApi.dissolveGroup(groupName)
    await reloadCurrentBoardAndTree()
    ElMessage.success('分组已解散')
  } catch {
    // 取消
  }
}

function startBoardRename() {
  if (!activeBoard.value) return
  boardTitleDraft.value = activeBoard.value.name
  renamingBoard.value = true
}

async function commitBoardRename() {
  if (!renamingBoard.value || !activeBoard.value) return
  renamingBoard.value = false
  const nextName = boardTitleDraft.value.trim()
  if (!nextName || nextName === activeBoard.value.name) return
  await fmeaApi.updateBoard(activeBoard.value.id, { name: nextName })
  activeBoard.value.name = nextName
  await fetchTree()
}

function clearFilters() {
  searchKeyword.value = ''
  refCodeFilter.value = ''
  if (route.query.refCode || route.query.keyword) {
    router.replace({ path: '/fmea/workspace' })
  }
}

// ==================== 【信标 2】画布稳态选择、大纲平滑定位与元素编辑 ====================

function handleCanvasSelect(sel: CanvasSelection | null) {
  // 画布内单击节点/热点/连线时，视口保持 100% 原地静止，绝不自动乱跳！
  selection.value = sel
}

function handleFocusOutlineElement(sel: CanvasSelection) {
  // 仅当用户在左侧大纲点击或从图鉴/台账执行「定位画板」时，平滑居中至可视区
  selection.value = sel
  if (canvasStageRef.value) {
    const { width, height } = canvasStageRef.value.getStageDimensions()
    focusSelectionInStage(sel, width, height, false)
  }
}

async function handleRenameSelectedTarget(payload: {
  title?: string
  sub?: string
  unit_code?: string | null
  is_limit?: boolean
  limit_spec?: string
  kind?: 'normal' | 'process_challenge'
}) {
  const sel = selection.value
  if (!sel) return
  pushHistorySnapshot()
  let unitCodeChanged = false

  if (sel.kind === 'node') {
    const nd = canvasData.value.nodes.find((n) => n.id === sel.id)
    if (nd) {
      if (payload.title !== undefined) nd.title = payload.title
      if (payload.sub !== undefined) nd.sub = payload.sub
      if (payload.unit_code !== undefined && nd.unit_code !== payload.unit_code) {
        nd.unit_code = payload.unit_code
        unitCodeChanged = true
      }
    }
  } else if (sel.kind === 'edge') {
    const ed = canvasData.value.edges.find((e) => e.id === sel.id)
    if (ed) {
      if (payload.title !== undefined) ed.label = payload.title
      if (payload.sub !== undefined) ed.sub = payload.sub
      if (payload.kind !== undefined) ed.kind = payload.kind
    }
  } else if (sel.kind === 'pin') {
    for (const ib of canvasData.value.image_boards) {
      const p = ib.pins.find((pin) => pin.id === sel.id)
      if (p) {
        if (payload.title !== undefined) p.title = payload.title
        if (payload.sub !== undefined) p.sub = payload.sub
        if (payload.is_limit !== undefined) p.is_limit = payload.is_limit
        if (payload.limit_spec !== undefined) p.limit_spec = payload.limit_spec
      }
    }
  }

  if (unitCodeChanged && activeBoardId.value) {
    const updated = await fmeaApi.updateBoard(activeBoardId.value, {
      canvas_data: cloneCanvasData(canvasData.value)
    })
    activeBoard.value = updated
    boardItems.value = updated.items
    await fetchTree()
  } else {
    schedulePersist(true)
  }
}

function handleOutlineRenameElement(payload: { sel: CanvasSelection; title: string }) {
  selection.value = payload.sel
  handleRenameSelectedTarget({ title: payload.title })
}

async function removeCanvasElement(sel: CanvasSelection) {
  // 统计仅归属于该元素的本地机理卡（绝不误删跨画板共用本体卡 shared_unit）
  const localCards = boardItems.value.filter(
    (it) => it.target_kind === sel.kind && it.target_id === sel.id
  )
  const msg =
    localCards.length > 0
      ? `确定移除此画布元素吗？其名下 ${localCards.length} 张本地机理卡将一并删除（跨画板共用件本体经验不受影响）。`
      : '确定从当前画布移除此元素吗？'

  try {
    await ElMessageBox.confirm(msg, '移除元素', {
      type: 'warning',
      confirmButtonText: '确认移除',
      cancelButtonText: '取消'
    })
    pushHistorySnapshot()
    if (sel.kind === 'node') {
      canvasData.value.nodes = canvasData.value.nodes.filter((n) => n.id !== sel.id)
      canvasData.value.edges = canvasData.value.edges.filter((e) => e.from !== sel.id && e.to !== sel.id)
    } else if (sel.kind === 'edge') {
      canvasData.value.edges = canvasData.value.edges.filter((e) => e.id !== sel.id)
    } else if (sel.kind === 'pin') {
      for (const ib of canvasData.value.image_boards) {
        ib.pins = ib.pins.filter((p) => p.id !== sel.id)
      }
    }
    for (const it of localCards) {
      await fmeaApi.deleteItem(it.id)
    }
    if (selection.value?.kind === sel.kind && selection.value?.id === sel.id) {
      selection.value = null
    }
    if (activeBoardId.value) {
      await fmeaApi.updateBoard(activeBoardId.value, {
        canvas_data: cloneCanvasData(canvasData.value)
      })
    }
    await reloadCurrentBoardAndTree()
  } catch {
    // 取消
  }
}

async function handleDeleteSelectedTarget() {
  if (!selection.value) return
  await removeCanvasElement(selection.value)
}

async function handleOutlineDeleteElement(sel: CanvasSelection) {
  await removeCanvasElement(sel)
}

// ==================== 机理卡增删改与跨视图一键定位 ====================

function openCreateItemForSelection() {
  if (!selection.value || !activeBoardId.value) return
  editingItem.value = null
  dialogTargetCtx.boardId = activeBoardId.value
  dialogTargetCtx.targetKind = selection.value.kind
  dialogTargetCtx.targetId = selection.value.id
  dialogTargetCtx.sharedUnitCode = null

  if (selection.value.kind === 'node') {
    const nd = canvasData.value.nodes.find((n) => n.id === selection.value!.id)
    dialogTargetCtx.titleSnapshot = nd?.title || ''
    dialogTargetCtx.sharedUnitCode = nd?.sub_board_id ? null : nd?.unit_code || null
    dialogTargetCtx.defaultPartCode = nd?.sub?.startsWith('PRT-') ? nd.sub : ''
  } else if (selection.value.kind === 'edge') {
    const ed = canvasData.value.edges.find((e) => e.id === selection.value!.id)
    dialogTargetCtx.titleSnapshot = ed?.label || ''
    dialogTargetCtx.defaultPartCode = ''
  } else {
    let snap = ''
    for (const ib of canvasData.value.image_boards) {
      const p = ib.pins.find((pin) => pin.id === selection.value!.id)
      if (p) snap = p.title
    }
    dialogTargetCtx.titleSnapshot = snap
    dialogTargetCtx.defaultPartCode = ''
  }
  itemDialogVisible.value = true
}

function openCreateGlobalItem() {
  editingItem.value = null
  dialogTargetCtx.boardId = activeBoardId.value
  dialogTargetCtx.targetKind = 'unassigned'
  dialogTargetCtx.targetId = null
  dialogTargetCtx.titleSnapshot = ''
  dialogTargetCtx.sharedUnitCode = null
  dialogTargetCtx.defaultPartCode = ''
  itemDialogVisible.value = true
}

function openEditItemDialog(item: FmeaItem) {
  editingItem.value = item
  dialogTargetCtx.boardId = item.board_id || activeBoardId.value
  dialogTargetCtx.targetKind = item.target_kind
  dialogTargetCtx.targetId = item.target_id
  dialogTargetCtx.titleSnapshot = item.target_title_snapshot || ''
  dialogTargetCtx.sharedUnitCode =
    item.target_kind === 'shared_unit'
      ? item.target_id
      : selection.value?.kind === 'node'
        ? canvasData.value.nodes.find((n) => n.id === selection.value!.id)?.unit_code || null
        : null
  dialogTargetCtx.defaultPartCode = ''
  itemDialogVisible.value = true
}

async function onItemSaved() {
  await reloadCurrentBoardAndTree()
}

function onGlobalDataMutated() {
  reloadCurrentBoardAndTree()
}

async function handleDeleteItem(card: FmeaItem) {
  try {
    const warnTxt =
      card.target_kind === 'shared_unit'
        ? `该卡片为跨画板共用本体经验「${card.failure_mode}」，删除后所有借用单元将同步移除，确认删除吗？`
        : `确认删除机理卡「${card.failure_mode}」吗？`
    await ElMessageBox.confirm(warnTxt, '删除确认', {
      type: 'warning'
    })
    await fmeaApi.deleteItem(card.id)
    ElMessage.success('机理卡已删除')
    await reloadCurrentBoardAndTree()
  } catch {
    // 取消
  }
}

async function handleQuickRiskChange(card: FmeaItem, risk: RiskLevel) {
  await fmeaApi.updateItem(card.id, { risk_level: risk })
  await reloadCurrentBoardAndTree()
}

function handleAppendPhotoToCard(card: FmeaItem, photo: FmeaPhoto) {
  const target = boardItems.value.find((it) => it.id === card.id)
  if (target) {
    if (!target.photos) target.photos = []
    if (!target.photos.some((p) => p.id === photo.id)) {
      target.photos.push(photo)
    }
  }
  globalRefreshTick.value += 1
}

async function locateItemOnCanvas(item: FmeaItem) {
  // 支持定位跨画板共用件本体卡 (shared_unit)
  if (item.target_kind === 'shared_unit' && item.target_id) {
    const currMatch = canvasData.value.nodes.find((n) => n.unit_code === item.target_id)
    if (currMatch) {
      viewMode.value = 'canvas'
      await nextTick()
      handleFocusOutlineElement({ kind: 'node', id: currMatch.id })
      return
    }
    for (const b of flatBoards.value) {
      const detail = await fmeaApi.getBoardDetail(b.id)
      const hit = detail.canvas_data.nodes.find((n) => n.unit_code === item.target_id)
      if (hit) {
        viewMode.value = 'canvas'
        await switchBoard(b.id)
        await nextTick()
        handleFocusOutlineElement({ kind: 'node', id: hit.id })
        return
      }
    }
    ElMessage.info(`暂未在画板上找到引用「${item.target_id}」的节点`)
    return
  }

  if (!item.board_id) {
    ElMessage.info('该条目尚未分配至具体画板节点')
    return
  }
  viewMode.value = 'canvas'
  if (activeBoardId.value !== item.board_id) {
    bomDrillStack.value = []
    await switchBoard(item.board_id)
  }
  await nextTick()
  if (item.target_id && (item.target_kind === 'pin' || item.target_kind === 'node' || item.target_kind === 'edge')) {
    const sel: CanvasSelection = { kind: item.target_kind, id: item.target_id }
    handleFocusOutlineElement(sel)
  }
}

// ==================== 快捷键与全局粘贴底图 + JSON 备份 ====================

async function onGlobalKeyDown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName
  const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable
  if (e.key === 'Escape' && !isTyping) {
    selection.value = null
    return
  }
  if (isTyping || viewMode.value !== 'canvas') return

  if ((e.key === 'Delete' || e.key === 'Backspace') && selection.value) {
    e.preventDefault()
    await handleDeleteSelectedTarget()
    return
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {
    e.preventDefault()
    undo()
  } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) {
    e.preventDefault()
    redo()
  }
}

async function onGlobalPaste(e: ClipboardEvent) {
  if (itemDialogVisible.value || aiDialogVisible.value || viewMode.value !== 'canvas') return
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return
  const files = extractImagesFromClipboard(e)
  if (files.length > 0 && canvasStageRef.value) {
    e.preventDefault()
    await canvasStageRef.value.createBlueprintFromFile(files[0])
  }
}

async function onMoreCommand(cmd: string) {
  if (cmd === 'duplicate_board' && activeBoard.value) {
    await handleSidebarDuplicateBoard(activeBoard.value.id)
  } else if (cmd === 'export_json' && activeBoard.value) {
    const blob = new Blob(
      [JSON.stringify({ board: activeBoard.value, canvas_data: canvasData.value, items: boardItems.value }, null, 2)],
      { type: 'application/json' }
    )
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${activeBoard.value.board_code}_${activeBoard.value.name}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  } else if (cmd === 'import_json') {
    importJsonInputRef.value?.click()
  } else if (cmd === 'seed_demo') {
    await fmeaApi.seedDemoBoards()
    await reloadCurrentBoardAndTree()
    ElMessage.success('预置示范画板与多级 BOM 示例已恢复')
  } else if (cmd === 'delete_board' && activeBoard.value) {
    try {
      await ElMessageBox.confirm(
        `确认删除画板「${activeBoard.value.name}」吗？（旗下机理卡将保留在全局台账中）`,
        '删除画板',
        { type: 'warning' }
      )
      await handleSidebarDeleteBoard({ boardId: activeBoard.value.id, deleteItems: false })
    } catch {
      // 取消
    }
  }
}

async function onImportJsonChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f || !activeBoardId.value) return
  try {
    const txt = await f.text()
    const parsed = JSON.parse(txt)
    const incomingCanvas = parsed.canvas_data || parsed
    if (incomingCanvas.nodes && Array.isArray(incomingCanvas.nodes)) {
      pushHistorySnapshot()
      loadCanvas(incomingCanvas)
      schedulePersist(true)
      ElMessage.success('已导入画板空间布局')
    }
  } catch {
    ElMessage.error('JSON 文件格式无法识别')
  }
}

// 支持从「质量问题清单 / 零件清单」携带路由参数直达对应画板或台账过滤
async function applyRouteDeepLink() {
  const qBoardId = Number(route.query.boardId)
  const qTargetKind = String(route.query.targetKind || '')
  const qTargetId = String(route.query.targetId || '')
  const qRefCode = String(route.query.refCode || '')
  const qView = String(route.query.view || '')

  if (qRefCode) {
    refCodeFilter.value = qRefCode
    searchKeyword.value = qRefCode
    viewMode.value = 'ledger'
    return
  }
  if (qView === 'ledger' || qView === 'gallery') {
    viewMode.value = qView
  }
  if (qBoardId && flatBoards.value.some((b) => b.id === qBoardId)) {
    viewMode.value = 'canvas'
    bomDrillStack.value = []
    await switchBoard(qBoardId)
    await nextTick()
    if (qTargetId && (qTargetKind === 'node' || qTargetKind === 'pin' || qTargetKind === 'edge')) {
      handleFocusOutlineElement({ kind: qTargetKind, id: qTargetId })
    }
  }
}

watch(
  () => route.query,
  () => {
    if (flatBoards.value.length) applyRouteDeepLink()
  }
)

onMounted(async () => {
  window.addEventListener('keydown', onGlobalKeyDown)
  window.addEventListener('paste', onGlobalPaste)
  const list = await fetchTree()
  if (list.length > 0) {
    // 默认优先打开最具代表性的旋转关节模组或首张总成画板
    const preferred = list.find((b) => b.board_code === 'BRD-ACT-G2') || list[0]
    await switchBoard(preferred.id)
  }
  await applyRouteDeepLink()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeyDown)
  window.removeEventListener('paste', onGlobalPaste)
})
</script>

<style scoped>
.fmea-workspace-shell {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  overflow: hidden;
}

.fmea-topbar {
  height: 44px;
  padding: 0 12px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  z-index: 20;
}

.tb-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.tb-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.14s;
}

.tb-icon-btn svg {
  width: 15px;
  height: 15px;
}

.tb-icon-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.tb-icon-btn.active {
  background: #f1f5f9;
  color: #0f172a;
}

.bom-back-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: 5px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}

.bom-back-btn:hover {
  background: #e0e7ff;
}

.board-crumb {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  min-width: 0;
}

.crumb-group {
  color: #64748b;
  white-space: nowrap;
}

.crumb-anc-btn {
  border: none;
  background: transparent;
  padding: 1px 4px;
  border-radius: 4px;
  color: #4f46e5;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.crumb-anc-btn:hover {
  background: #eef2ff;
}

.crumb-slash {
  color: #cbd5e1;
  font-size: 11px;
}

.crumb-board {
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.parent-ref-pill {
  height: 21px;
  padding: 0 7px;
  border-radius: 10px;
  border: 1px solid #e0e7ff;
  background: #f5f7ff;
  color: #4338ca;
  font-size: 10.5px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  flex-shrink: 0;
}

.parent-ref-pill:hover {
  background: #eef2ff;
  border-color: #c7d2fe;
}

.parent-pop {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.pp-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
  padding-bottom: 4px;
  border-bottom: 1px solid #f1f5f9;
}

.pp-item {
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}

.pp-item:hover {
  background: #eef2ff;
  border-color: #c7d2fe;
}

.ppi-name {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.ppi-sub {
  font-size: 10.5px;
  color: #64748b;
  margin-top: 1px;
}

.board-rename-input {
  height: 24px;
  padding: 0 6px;
  border-radius: 4px;
  border: 1px solid #2563eb;
  font-size: 13px;
  font-weight: 600;
  outline: none;
}

.tb-center {
  display: flex;
  justify-content: center;
}

.view-seg-bar {
  height: 30px;
  padding: 2px;
  border-radius: 8px;
  background: #f1f5f9;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.vs-btn {
  height: 26px;
  padding: 0 13px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.14s;
}

.vs-btn:hover {
  color: #0f172a;
}

.vs-btn.active {
  background: #ffffff;
  color: #0f172a;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.tb-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.search-pill {
  width: 186px;
  height: 28px;
  padding: 0 8px;
  border-radius: 7px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: border-color 0.14s, width 0.18s;
}

.search-pill:focus-within {
  width: 222px;
  background: #ffffff;
  border-color: #93c5fd;
}

.s-ico {
  width: 13px;
  height: 13px;
  color: #94a3b8;
  flex-shrink: 0;
}

.s-input {
  flex: 1;
  width: 100%;
  border: none;
  background: transparent;
  font-size: 12px;
  color: #0f172a;
  outline: none;
}

.s-clear {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
}

.high-filter-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: 7px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.high-filter-btn .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
}

.high-filter-btn.active {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #b91c1c;
  font-weight: 600;
}

.ai-entry-btn {
  height: 28px;
  padding: 0 11px;
  border-radius: 7px;
  border: none;
  background: #0f172a;
  color: #ffffff;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: background 0.14s;
}

.ai-entry-btn svg {
  width: 13.5px;
  height: 13.5px;
}

.ai-entry-btn:hover {
  background: #1e293b;
}

.fmea-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.canvas-stage-container {
  position: relative;
  flex: 1;
  height: 100%;
  display: flex;
  overflow: hidden;
}

.sidebar-float-expand-btn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 48px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-left: none;
  border-radius: 0 6px 6px 0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 25;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.08);
  transition: all 0.15s ease;
  padding: 0;
}

.sidebar-float-expand-btn:hover {
  width: 20px;
  background: #eff6ff;
  color: #2563eb;
  border-color: #93c5fd;
}

.sidebar-float-expand-btn svg {
  width: 12px;
  height: 12px;
}
</style>
