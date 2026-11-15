<template>
  <div
    ref="stageRef"
    class="fmea-canvas-stage"
    :class="[`mode-${toolMode}`, { 'is-panning': isPanning, 'is-linking': !!linkingState }]"
    :style="gridStyle"
    @mousedown="onStageMouseDown"
    @mousemove="onStageMouseMove"
    @mouseup="onStageMouseUp"
    @mouseleave="onStageMouseUp"
    @wheel.prevent="onStageWheel"
    @dragover.prevent="isDragOver = true"
    @dragleave="isDragOver = false"
    @drop.prevent="onStageDrop"
  >
    <!-- 拖拽上传图纸视觉反馈遮罩 -->
    <div v-if="isDragOver" class="drop-overlay">
      <div class="drop-card">松开鼠标，上传图纸/照片作为画布底板</div>
    </div>

    <!-- 缩放平移世界层（仅在跨面板定位时开启 220ms 平滑过渡，日常拖拽零延迟） -->
    <div class="canvas-world" :class="{ 'is-smooth': smoothFocusing }" :style="worldTransformStyle">
      <!-- 1. 图纸/实拍底板层 -->
      <div
        v-for="ib in canvasData.image_boards"
        :key="ib.id"
        class="blueprint-board"
        :style="{ left: `${ib.x}px`, top: `${ib.y}px`, width: `${ib.w}px`, height: `${ib.h}px` }"
      >
        <div class="bp-header" @mousedown.stop="startDragBlueprint($event, ib)">
          <svg class="bp-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
            <rect x="2" y="2.5" width="12" height="11" rx="2" />
            <path d="M2 10.5l3.5-3 2.8 2.4 2.2-1.8L14 11" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <input
            v-if="editingBpId === ib.id"
            v-model="ib.title"
            class="bp-title-input"
            @blur="finishBpRename"
            @keyup.enter="finishBpRename"
            @mousedown.stop
          />
          <span
            v-else
            class="bp-title"
            title="双击修改底图标题"
            @dblclick.stop="editingBpId = ib.id"
          >
            {{ ib.title }}
          </span>
          <span v-if="toolMode === 'pin'" class="bp-pin-hint">点击图面落点</span>
          <button
            type="button"
            class="bp-del-btn"
            title="移除此底图"
            @mousedown.stop
            @click.stop="removeBlueprint(ib.id)"
          >
            ×
          </button>
        </div>

        <div
          class="bp-body"
          :class="{ 'pin-cursor': toolMode === 'pin' }"
          @click.stop="onBlueprintBodyClick($event, ib)"
          @dblclick.stop="onBlueprintDblClick($event, ib)"
        >
          <img :src="ib.img_url" :alt="ib.title" class="bp-img" draggable="false" />

          <!-- 底图上的圆形编号风险热点 Pins -->
          <div
            v-for="pin in ib.pins"
            :key="pin.id"
            class="risk-pin"
            :class="[
              getTargetRiskClass('pin', pin.id),
              {
                selected: selection?.kind === 'pin' && selection?.id === pin.id,
                dimmed: isPinOrEdgeDimmed('pin', pin.id, pin.title),
                'is-limit': pin.is_limit
              }
            ]"
            :style="{ left: `${pin.rx * 100}%`, top: `${pin.ry * 100}%` }"
            :title="`${pin.is_limit ? `[设计极限: ${pin.limit_spec || '需重点关注制程难点'}] ` : ''}${pin.title}`"
            @mousedown.stop="startDragPin($event, ib, pin)"
            @mouseup.stop="finishLinkOnPin(pin)"
            @click.stop="$emit('select', { kind: 'pin', id: pin.id, boardImgId: ib.id })"
            @contextmenu.prevent="openPinContextMenu($event, pin, ib)"
          >
            {{ pin.num }}
            <span v-if="pin.is_limit" class="pin-limit-badge" title="图纸设计极限">📐</span>
            <!-- 连线端口微把手 (支持从图纸热点直接连线到模块节点) -->
            <span
              class="pin-port"
              title="按住拖拽连线至关联模块"
              @mousedown.stop="startLinkFromPin($event, ib, pin)"
            />
          </div>
        </div>

        <!-- 右下角自由缩放手柄 -->
        <div
          class="bp-resize-grip"
          title="拖拽缩放底图尺寸"
          @mousedown.stop="startResizeBlueprint($event, ib)"
        />
      </div>

      <!-- 2. SVG 贝塞尔接口连线层 -->
      <svg class="edges-svg-layer">
        <defs>
          <marker id="fmea-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1.2 L7,4 L1,6.8" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-linecap="round" />
          </marker>
          <marker id="fmea-arrow-active" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1.2 L7,4 L1,6.8" fill="none" stroke="#2563eb" stroke-width="1.6" stroke-linecap="round" />
          </marker>
          <marker id="fmea-arrow-high" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1.2 L7,4 L1,6.8" fill="none" stroke="#ef4444" stroke-width="1.6" stroke-linecap="round" />
          </marker>
          <marker id="fmea-arrow-challenge" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1.2 L7,4 L1,6.8" fill="none" stroke="#f97316" stroke-width="1.6" stroke-linecap="round" />
          </marker>
        </defs>

        <g
          v-for="ed in renderedEdges"
          :key="ed.edge.id"
          class="edge-group"
          :class="{
            selected: selection?.kind === 'edge' && selection?.id === ed.edge.id,
            'is-high': ed.highCount > 0,
            'is-challenge': ed.edge.kind === 'process_challenge',
            dimmed: isPinOrEdgeDimmed('edge', ed.edge.id, ed.edge.label)
          }"
          @mousedown.stop
          @click.stop="$emit('select', { kind: 'edge', id: ed.edge.id })"
          @contextmenu.prevent="openEdgeContextMenu($event, ed.edge)"
        >
          <path :d="ed.path" class="edge-hit-path" />
          <path
            :d="ed.path"
            class="edge-vis-path"
            :marker-end="
              selection?.kind === 'edge' && selection?.id === ed.edge.id
                ? 'url(#fmea-arrow-active)'
                : ed.edge.kind === 'process_challenge'
                  ? 'url(#fmea-arrow-challenge)'
                  : ed.highCount > 0
                    ? 'url(#fmea-arrow-high)'
                    : 'url(#fmea-arrow)'
            "
          />
        </g>

        <path
          v-if="linkingPreviewPath"
          :d="linkingPreviewPath"
          class="edge-linking-preview"
        />
      </svg>

      <!-- 连线中央 4~5 字极简微胶囊标签 -->
      <div
        v-for="ed in renderedEdges"
        :key="`pill_${ed.edge.id}`"
        class="edge-short-pill"
        :class="{
          selected: selection?.kind === 'edge' && selection?.id === ed.edge.id,
          'has-high': ed.highCount > 0,
          'is-challenge': ed.edge.kind === 'process_challenge',
          dimmed: isPinOrEdgeDimmed('edge', ed.edge.id, ed.edge.label)
        }"
        :style="{ left: `${ed.midX}px`, top: `${ed.midY}px` }"
        @mousedown.stop
        @click.stop="$emit('select', { kind: 'edge', id: ed.edge.id })"
        @contextmenu.prevent="openEdgeContextMenu($event, ed.edge)"
      >
        <span v-if="ed.edge.kind === 'process_challenge'" class="challenge-pill-icon" title="设计极限挑战制造工艺">⚠️</span>
        <span v-else-if="ed.totalCount > 0" class="pill-dot" :class="ed.highCount > 0 ? 'high' : 'med'" />
        <span class="pill-txt">{{ shortEdgeText(ed.edge.label) }}</span>
      </div>

      <!-- 3. 184px 极简模块/工序节点层（支持普通节点、跨画板共用件节点、可下钻子模块黑盒节点） -->
      <div
        v-for="nd in canvasData.nodes"
        :key="nd.id"
        class="module-node"
        :class="{
          'is-sub-board': !!nd.sub_board_id,
          'is-shared-unit': !nd.sub_board_id && !!nd.unit_code,
          selected: selection?.kind === 'node' && selection?.id === nd.id,
          dimmed: isNodeDimmed(nd)
        }"
        :style="{ left: `${nd.x}px`, top: `${nd.y}px` }"
        @mousedown.stop="startDragNode($event, nd)"
        @mouseup.stop="onNodeMouseUp($event, nd)"
        @click.stop="onNodeClick(nd)"
        @dblclick.stop="onNodeDblClick(nd)"
        @contextmenu.prevent="openNodeContextMenu($event, nd)"
      >
        <!-- 悬停快捷删除按钮 (【信标 1】节点快捷删除) -->
        <button
          type="button"
          class="node-del-btn"
          title="移除此节点 (右键或按 Delete 键)"
          @mousedown.stop
          @click.stop="triggerDeleteElement({ kind: 'node', id: nd.id })"
        >
          ×
        </button>

        <div class="node-head">
          <div class="node-title-row">
            <span class="node-title" :title="nd.title">{{ nd.title }}</span>
            <button
              v-if="nd.sub_board_id"
              type="button"
              class="drill-chip-btn"
              title="双击节点或点击此处下钻进入子模块画板"
              @mousedown.stop
              @click.stop="$emit('drill-sub-board', nd.sub_board_id)"
            >
              下钻 ↘
            </button>
            <span
              v-else-if="nd.unit_code"
              class="bom-micro-badge shared"
              title="跨画板共用件"
            >
              共用
            </span>
          </div>

          <div v-if="nd.sub || nd.unit_code || nd.sub_board_id" class="node-sub-row">
            <span
              v-if="nd.sub_board_id"
              class="bom-micro-badge sub"
              title="嵌入式子画板"
            >
              子画板
            </span>
            <span class="node-sub">
              {{ nd.unit_code || nd.sub || (nd.sub_board_id ? getSubBoardCode(nd.sub_board_id) : '') }}
            </span>
          </div>
        </div>

        <div class="node-foot">
          <div class="node-risk-summary">
            <template v-if="getNodeCombinedStat(nd).total > 0">
              <span v-if="getNodeCombinedStat(nd).high > 0" class="r-chip high">
                <i class="dot" />{{ getNodeCombinedStat(nd).high }} 高危
              </span>
              <span v-if="getNodeCombinedStat(nd).other > 0" class="r-chip normal">
                <i class="dot" />{{ getNodeCombinedStat(nd).other }} 项
              </span>
            </template>
            <span v-else class="r-empty">-</span>
          </div>

          <span v-if="getNodeCombinedStat(nd).photos > 0" class="photo-cnt" title="包含实拍/标准图">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="3.5" width="12" height="9.5" rx="1.8" />
              <circle cx="8" cy="8.2" r="2" />
            </svg>
            {{ getNodeCombinedStat(nd).photos }}
          </span>
        </div>

        <!-- 四向连线端口 -->
        <span
          v-for="side in PORT_SIDES"
          :key="side"
          class="node-port"
          :class="`port-${side}`"
          title="按住拖出配合接口连线"
          @mousedown.stop="startLinkFromPort($event, nd, side)"
          @mouseup.stop="finishLinkOnNode(nd, side)"
        />
      </div>
    </div>

    <!-- 底部「节点」三合一上浮选择器（普通节点 / 引用共用件 / 嵌入子模块画板） -->
    <div v-if="nodeMenuOpen" class="node-insert-popover" @mousedown.stop>
      <button type="button" class="ni-quick-create" @click="addPlainModuleNode">
        <span class="ni-icon plain">+</span>
        <div class="ni-txt">
          <div class="ni-main">新建普通部件 / 工序节点</div>
          <div class="ni-sub">当前画板独立单元</div>
        </div>
      </button>

      <div class="ni-tabs">
        <button
          type="button"
          class="ni-tab"
          :class="{ active: nodeMenuTab === 'shared' }"
          @click="switchNodeMenuTab('shared')"
        >
          引用共用零件/单元
        </button>
        <button
          type="button"
          class="ni-tab"
          :class="{ active: nodeMenuTab === 'sub_board' }"
          @click="switchNodeMenuTab('sub_board')"
        >
          嵌入已有子模块画板
        </button>
      </div>

      <input
        v-model="nodeMenuSearch"
        type="text"
        class="ni-search"
        :placeholder="nodeMenuTab === 'shared' ? '搜图号/名称，或直接回车创建共用编码...' : '过滤可嵌入的子模块画板...'"
        @keyup.enter="onNodeMenuSearchEnter"
      />

      <!-- Tab A: 引用跨画板共用件 -->
      <div v-if="nodeMenuTab === 'shared'" class="ni-list">
        <div v-if="filteredSharedUnits.length === 0" class="ni-empty">
          按回车以「{{ nodeMenuSearch || 'PRT-NEW' }}」新建共用单元
        </div>
        <button
          v-for="u in filteredSharedUnits"
          :key="u.unit_code"
          type="button"
          class="ni-option"
          @click="insertSharedUnitNode(u)"
        >
          <div class="nio-left">
            <span class="nio-code">{{ u.unit_code }}</span>
            <span class="nio-title">{{ u.title }}</span>
          </div>
          <span v-if="u.used_board_count > 0" class="nio-meta">{{ u.used_board_count }}画板共用</span>
        </button>
      </div>

      <!-- Tab B: 嵌入已有子模块画板 -->
      <div v-else class="ni-list">
        <div v-if="filteredCandidateSubBoards.length === 0" class="ni-empty">
          暂无其他可嵌入的模块画板
        </div>
        <button
          v-for="sb in filteredCandidateSubBoards"
          :key="sb.id"
          type="button"
          class="ni-option"
          @click="insertSubBoardNode(sb)"
        >
          <div class="nio-left">
            <span class="nio-code sub">BOM</span>
            <span class="nio-title">{{ sb.name }}</span>
          </div>
          <span class="nio-meta">{{ sb.group_name }}</span>
        </button>
      </div>
    </div>

    <!-- 底部居中极简短工具坞：选择 · 打点 · 底图 · 节点 · 理线 -->
    <div class="bottom-short-dock" @mousedown.stop>
      <button
        type="button"
        class="dock-btn"
        :class="{ active: toolMode === 'select' && !nodeMenuOpen }"
        title="选择与拖拽画布元素 (V)"
        @click="toolMode = 'select'; nodeMenuOpen = false"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <path d="M3.5 2.5l9 4.2-4.2 1.3-1.5 4.5-3.3-10z" stroke-linejoin="round" />
        </svg>
        <span>选择</span>
      </button>

      <button
        type="button"
        class="dock-btn"
        :class="{ active: toolMode === 'pin' }"
        title="点击底图任意位置打风险热点 (P)"
        @click="activatePinTool"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <path d="M8 14s4.5-4.1 4.5-7.5a4.5 4.5 0 10-9 0C3.5 9.9 8 14 8 14z" />
          <circle cx="8" cy="6.5" r="1.4" />
        </svg>
        <span>打点</span>
      </button>

      <span class="dock-sep" />

      <button
        type="button"
        class="dock-btn"
        title="上传图纸剖面图或实拍图作为画布底板 (也可直接 Ctrl+V 粘贴)"
        @click="triggerBlueprintPicker"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <rect x="2" y="2.5" width="12" height="11" rx="2" />
          <path d="M2 11l3.5-3.2 2.6 2.2 2.4-2L14 11" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>底图</span>
      </button>

      <button
        type="button"
        class="dock-btn"
        :class="{ active: nodeMenuOpen }"
        title="新增普通节点 / 引用跨画板共用零件 / 嵌入子模块画板"
        @click="toggleNodeInsertMenu"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <rect x="2.5" y="2.5" width="11" height="11" rx="2.2" />
          <path d="M8 5.2v5.6M5.2 8h5.6" stroke-linecap="round" />
        </svg>
        <span>节点 ▾</span>
      </button>

      <button
        type="button"
        class="dock-btn"
        title="一键整齐排列节点与接口连线"
        @click="nodeMenuOpen = false; $emit('tidy')"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <circle cx="3.5" cy="4.5" r="1.5" />
          <circle cx="12.5" cy="4.5" r="1.5" />
          <circle cx="8" cy="11.5" r="1.5" />
          <path d="M5 4.5h6M4.5 5.8l2.5 4.4M11.5 5.8L9 10.2" stroke-linecap="round" />
        </svg>
        <span>理线</span>
      </button>

      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        style="display: none"
        @change="onBlueprintFileChosen"
      />
    </div>

    <!-- 右下角微缩控制条：撤销/重做 + 缩放百分比 -->
    <div class="zoom-undo-bar" @mousedown.stop>
      <button
        type="button"
        class="micro-btn"
        :disabled="!canUndo"
        title="撤销 (Ctrl+Z)"
        @click="$emit('undo')"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <path d="M6 4L2.5 7.5 6 11" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M3 7.5h6.5a3.5 3.5 0 010 7H8" stroke-linecap="round" />
        </svg>
      </button>
      <button
        type="button"
        class="micro-btn"
        :disabled="!canRedo"
        title="重做 (Ctrl+Y)"
        @click="$emit('redo')"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
          <path d="M10 4l3.5 3.5L10 11" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M13 7.5H6.5a3.5 3.5 0 000 7H8" stroke-linecap="round" />
        </svg>
      </button>
      <span class="micro-sep" />
      <button type="button" class="micro-btn" title="缩小" @click="$emit('zoom', viewport.zoom - 0.1)">
        −
      </button>
      <button type="button" class="zoom-pct-btn" title="点击复位 100% 视口" @click="$emit('reset-view')">
        {{ Math.round(viewport.zoom * 100) }}%
      </button>
      <button type="button" class="micro-btn" title="放大" @click="$emit('zoom', viewport.zoom + 0.1)">
        +
      </button>
    </div>

    <!-- 画布元素右键上下文菜单 (【信标 1】右键删除与下钻操作) -->
    <div
      v-if="canvasCtxMenu.visible"
      class="canvas-ctx-menu"
      :style="{ left: `${canvasCtxMenu.x}px`, top: `${canvasCtxMenu.y}px` }"
      @mousedown.stop
      @contextmenu.prevent
    >
      <div class="ctx-header">
        <span class="ctx-type">{{ canvasCtxMenu.kind === 'node' ? '模块节点' : canvasCtxMenu.kind === 'edge' ? '配合接口' : '图纸热点' }}</span>
        <span class="ctx-title" :title="canvasCtxMenu.title">{{ canvasCtxMenu.title }}</span>
      </div>

      <div
        v-if="canvasCtxMenu.kind === 'node' && canvasCtxMenu.node?.sub_board_id"
        class="ctx-item"
        @click="onCtxDrillSubBoard"
      >
        <span class="ctx-ico">↘</span>
        <span>穿透下钻进入子画板</span>
      </div>

      <div class="ctx-item" @click="onCtxCreateItem">
        <span class="ctx-ico">➕</span>
        <span>为此元素新建机理卡</span>
      </div>

      <div class="ctx-divider" />

      <div class="ctx-item danger" @click="onCtxDeleteElement">
        <span class="ctx-ico">🗑️</span>
        <span>移除此{{ canvasCtxMenu.kind === 'node' ? '节点' : canvasCtxMenu.kind === 'edge' ? '连线接口' : '图纸热点' }}</span>
        <span class="ctx-shortcut">Delete</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type {
  BoardCanvasData,
  CanvasImageBoard,
  BlueprintPin,
  CanvasModuleNode,
  PortSide,
  FmeaItem,
  CanvasSelection,
  CanvasToolMode,
  FmeaBoardSummary,
  SubBoardRollupStat,
  SharedUnitOption
} from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import { getPortPoint, buildBezierEdgePath } from '@/views/6_fmea/composables/useFmeaCanvas'
import { useFmeaUpload } from '@/views/6_fmea/composables/useFmeaUpload'

const PORT_SIDES: PortSide[] = ['top', 'right', 'bottom', 'left']

// 【信标 2】单击防手抖拖拽死区阈值提升至 6px，确保普通单击 100% 稳态不漂移
const DRAG_DEADZONE_PX = 6

const props = defineProps<{
  boardId: number | null
  canvasData: BoardCanvasData
  boardItems: FmeaItem[]
  subBoardStats?: Record<string, SubBoardRollupStat>
  allBoards?: FmeaBoardSummary[]
  ancestorBoardIds?: number[]
  smoothFocusing?: boolean
  selection: CanvasSelection | null
  searchKeyword: string
  highRiskOnly: boolean
  canUndo: boolean
  canRedo: boolean
}>()

const emit = defineEmits<{
  (e: 'select', sel: CanvasSelection | null): void
  (e: 'drill-sub-board', subBoardId: number): void
  (e: 'before-mutate'): void
  (e: 'change', immediate?: boolean): void
  (e: 'tidy'): void
  (e: 'undo'): void
  (e: 'redo'): void
  (e: 'zoom', nextZoom: number, pivotX?: number, pivotY?: number): void
  (e: 'reset-view'): void
  (e: 'delete-element', sel: CanvasSelection): void
}>()

const stageRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const toolMode = ref<CanvasToolMode>('select')
const isPanning = ref(false)
const isDragOver = ref(false)
const editingBpId = ref<string | null>(null)

// 底部三合一节点添加菜单状态
const nodeMenuOpen = ref(false)
const nodeMenuTab = ref<'shared' | 'sub_board'>('shared')
const nodeMenuSearch = ref('')
const sharedUnitOptions = ref<SharedUnitOption[]>([])

const { uploadImageFile, extractImagesFromDrop } = useFmeaUpload()

const viewport = computed(() => props.canvasData.viewport || { panX: 40, panY: 36, zoom: 1 })

const worldTransformStyle = computed(() => ({
  transform: `translate(${viewport.value.panX}px, ${viewport.value.panY}px) scale(${viewport.value.zoom})`
}))

const gridStyle = computed(() => {
  const step = 20 * viewport.value.zoom
  return {
    backgroundSize: `${step}px ${step}px`,
    backgroundPosition: `${viewport.value.panX}px ${viewport.value.panY}px`
  }
})

// 聚合每个容器（包含 shared_unit:编码）的风险与实拍照片计数
const containerStats = computed(() => {
  const map = new Map<string, { total: number; high: number; med: number; other: number; photos: number; blob: string }>()
  for (const it of props.boardItems) {
    const k = `${it.target_kind}:${it.target_id}`
    const st = map.get(k) || { total: 0, high: 0, med: 0, other: 0, photos: 0, blob: '' }
    st.total += 1
    if (it.risk_level === 'HIGH') st.high += 1
    else {
      st.other += 1
      if (it.risk_level === 'MED') st.med += 1
    }
    st.photos += it.photos?.length || 0
    st.blob += ` ${it.failure_mode} ${it.failure_mech || ''} ${it.ref_codes_text || ''}`
    map.set(k, st)
  }
  return map
})

function getSubBoardCode(subBoardId?: number | null): string {
  if (!subBoardId || !props.subBoardStats) return ''
  return props.subBoardStats[String(subBoardId)]?.board_code || ''
}

// 综合计算单个画布节点的展示风险（局部专属 + 跨画板共用本体 + 子画板内部汇总）
function getNodeCombinedStat(nd: CanvasModuleNode) {
  const local = containerStats.value.get(`node:${nd.id}`) || {
    total: 0,
    high: 0,
    med: 0,
    other: 0,
    photos: 0,
    blob: ''
  }
  let total = local.total
  let high = local.high
  let other = local.other
  let photos = local.photos
  let blob = local.blob

  if (nd.unit_code) {
    const shared = containerStats.value.get(`shared_unit:${nd.unit_code}`)
    if (shared) {
      total += shared.total
      high += shared.high
      other += shared.other
      photos += shared.photos
      blob += ` ${shared.blob}`
    }
  }

  if (nd.sub_board_id && props.subBoardStats) {
    const sb = props.subBoardStats[String(nd.sub_board_id)]
    if (sb) {
      total += sb.total_items
      high += sb.high_risk_count
      other += Math.max(0, sb.total_items - sb.high_risk_count)
      photos += sb.photo_count
      blob += ` ${sb.name} ${sb.board_code}`
    }
  }

  return { total, high, other, photos, blob }
}

function getTargetRiskClass(kind: string, id: string): string {
  const st = containerStats.value.get(`${kind}:${id}`)
  if (!st || st.total === 0) return 'risk-none'
  if (st.high > 0) return 'risk-high'
  if (st.med > 0) return 'risk-med'
  return 'risk-low'
}

function isPinOrEdgeDimmed(kind: string, id: string, titleText: string): boolean {
  const st = containerStats.value.get(`${kind}:${id}`)
  if (props.highRiskOnly && (!st || st.high === 0)) {
    return true
  }
  const kw = props.searchKeyword.trim().toLowerCase()
  if (kw) {
    const hay = `${titleText} ${st?.blob || ''}`.toLowerCase()
    if (!hay.includes(kw)) return true
  }
  return false
}

function isNodeDimmed(nd: CanvasModuleNode): boolean {
  const st = getNodeCombinedStat(nd)
  if (props.highRiskOnly && st.high === 0) {
    return true
  }
  const kw = props.searchKeyword.trim().toLowerCase()
  if (kw) {
    const hay = `${nd.title} ${nd.sub || ''} ${nd.unit_code || ''} ${st.blob}`.toLowerCase()
    if (!hay.includes(kw)) return true
  }
  return false
}

function getPinPoint(pinId: string): { x: number; y: number } | null {
  for (const ib of props.canvasData.image_boards || []) {
    const p = (ib.pins || []).find((pin) => pin.id === pinId)
    if (p) {
      return {
        x: ib.x + p.rx * ib.w,
        y: ib.y + 36 + p.ry * (ib.h - 36)
      }
    }
  }
  return null
}

function getElementPortPoint(targetId: string, preferredPort: PortSide = 'right'): { x: number; y: number; port: PortSide } | null {
  const nd = props.canvasData.nodes.find((n) => n.id === targetId)
  if (nd) {
    return {
      ...getPortPoint(nd, preferredPort),
      port: preferredPort
    }
  }
  const pt = getPinPoint(targetId)
  if (pt) {
    return {
      ...pt,
      port: 'right'
    }
  }
  return null
}

// 计算所有贝塞尔连线几何数据 (支持 节点-节点、热点-节点、热点-热点)
const renderedEdges = computed(() => {
  const list: Array<{
    edge: BoardCanvasData['edges'][number]
    path: string
    midX: number
    midY: number
    totalCount: number
    highCount: number
  }> = []

  for (const ed of props.canvasData.edges || []) {
    const p1 = getElementPortPoint(ed.from, ed.fromPort || 'right')
    const p2 = getElementPortPoint(ed.to, ed.toPort || 'left')
    if (!p1 || !p2) continue
    const bz = buildBezierEdgePath(p1, p1.port, p2, p2.port)
    const st = containerStats.value.get(`edge:${ed.id}`)
    list.push({
      edge: ed,
      path: bz.path,
      midX: bz.midX,
      midY: bz.midY,
      totalCount: st?.total || 0,
      highCount: st?.high || 0
    })
  }
  return list
})

function shortEdgeText(label?: string): string {
  const clean = (label || '接口').trim()
  return clean.length > 6 ? `${clean.slice(0, 5)}…` : clean
}

// ==================== 拖拽交互状态机 ====================
let suppressNextNodeClick = false

let dragContext:
  | { type: 'pan'; startX: number; startY: number; origPanX: number; origPanY: number; moved: boolean }
  | { type: 'node'; node: CanvasModuleNode; startX: number; startY: number; origX: number; origY: number; moved: boolean }
  | { type: 'blueprint'; bp: CanvasImageBoard; startX: number; startY: number; origX: number; origY: number; moved: boolean }
  | { type: 'resize-bp'; bp: CanvasImageBoard; startX: number; startY: number; origW: number; origH: number }
  | { type: 'pin'; bp: CanvasImageBoard; pin: BlueprintPin; startX: number; startY: number; origRx: number; origRy: number; moved: boolean }
  | null = null

const linkingState = ref<{
  fromKind: 'node' | 'pin'
  fromId: string
  fromNode?: CanvasModuleNode
  fromPin?: BlueprintPin
  fromPort: PortSide
  currWorldX: number
  currWorldY: number
} | null>(null)

const linkingPreviewPath = computed(() => {
  if (!linkingState.value) return ''
  const ls = linkingState.value
  let p1: { x: number; y: number }
  if (ls.fromKind === 'pin' && ls.fromPin) {
    p1 = getPinPoint(ls.fromPin.id) || { x: ls.currWorldX, y: ls.currWorldY }
  } else if (ls.fromNode) {
    p1 = getPortPoint(ls.fromNode, ls.fromPort)
  } else {
    p1 = { x: ls.currWorldX, y: ls.currWorldY }
  }
  const p2 = { x: ls.currWorldX, y: ls.currWorldY }
  const oppPort: PortSide =
    ls.fromPort === 'right'
      ? 'left'
      : ls.fromPort === 'left'
        ? 'right'
        : ls.fromPort === 'top'
          ? 'bottom'
          : 'top'
  return buildBezierEdgePath(p1, ls.fromPort, p2, oppPort).path
})

function clientToWorld(clientX: number, clientY: number) {
  const rect = stageRef.value?.getBoundingClientRect()
  const sx = clientX - (rect?.left || 0)
  const sy = clientY - (rect?.top || 0)
  return {
    x: (sx - viewport.value.panX) / viewport.value.zoom,
    y: (sy - viewport.value.panY) / viewport.value.zoom,
    sx,
    sy
  }
}

function onStageMouseDown(e: MouseEvent) {
  nodeMenuOpen.value = false
  if (e.button !== 0 && e.button !== 1) return
  isPanning.value = true
  dragContext = {
    type: 'pan',
    startX: e.clientX,
    startY: e.clientY,
    origPanX: viewport.value.panX,
    origPanY: viewport.value.panY,
    moved: false
  }
}

function startDragNode(e: MouseEvent, node: CanvasModuleNode) {
  nodeMenuOpen.value = false
  if (e.button !== 0) return
  suppressNextNodeClick = false
  dragContext = {
    type: 'node',
    node,
    startX: e.clientX,
    startY: e.clientY,
    origX: node.x,
    origY: node.y,
    moved: false
  }
}

function onNodeClick(node: CanvasModuleNode) {
  if (suppressNextNodeClick) {
    suppressNextNodeClick = false
    return
  }
  emit('select', { kind: 'node', id: node.id })
}

function onNodeDblClick(node: CanvasModuleNode) {
  if (node.sub_board_id) {
    emit('drill-sub-board', node.sub_board_id)
  }
}

function startDragBlueprint(e: MouseEvent, bp: CanvasImageBoard) {
  nodeMenuOpen.value = false
  if (e.button !== 0) return
  dragContext = {
    type: 'blueprint',
    bp,
    startX: e.clientX,
    startY: e.clientY,
    origX: bp.x,
    origY: bp.y,
    moved: false
  }
}

function startResizeBlueprint(e: MouseEvent, bp: CanvasImageBoard) {
  if (e.button !== 0) return
  emit('before-mutate')
  dragContext = {
    type: 'resize-bp',
    bp,
    startX: e.clientX,
    startY: e.clientY,
    origW: bp.w,
    origH: bp.h
  }
}

function startDragPin(e: MouseEvent, bp: CanvasImageBoard, pin: BlueprintPin) {
  nodeMenuOpen.value = false
  if (e.button !== 0) return
  dragContext = {
    type: 'pin',
    bp,
    pin,
    startX: e.clientX,
    startY: e.clientY,
    origRx: pin.rx,
    origRy: pin.ry,
    moved: false
  }
}

function startLinkFromPort(e: MouseEvent, node: CanvasModuleNode, port: PortSide) {
  nodeMenuOpen.value = false
  const pt = clientToWorld(e.clientX, e.clientY)
  linkingState.value = {
    fromKind: 'node',
    fromId: node.id,
    fromNode: node,
    fromPort: port,
    currWorldX: pt.x,
    currWorldY: pt.y
  }
}

function startLinkFromPin(e: MouseEvent, ib: CanvasImageBoard, pin: BlueprintPin) {
  nodeMenuOpen.value = false
  const pt = clientToWorld(e.clientX, e.clientY)
  linkingState.value = {
    fromKind: 'pin',
    fromId: pin.id,
    fromPin: pin,
    fromPort: 'right',
    currWorldX: pt.x,
    currWorldY: pt.y
  }
}

function finishLinkOnNode(targetNode: CanvasModuleNode, targetPort?: PortSide) {
  if (!linkingState.value) return
  const src = linkingState.value
  linkingState.value = null
  if (src.fromId === targetNode.id) return

  const existing = (props.canvasData.edges || []).find(
    (ed) =>
      (ed.from === src.fromId && ed.to === targetNode.id) ||
      (ed.from === targetNode.id && ed.to === src.fromId)
  )
  if (existing) {
    emit('select', { kind: 'edge', id: existing.id })
    return
  }

  const autoToPort: PortSide =
    targetPort ||
    (src.fromNode && Math.abs(targetNode.x - src.fromNode.x) >= Math.abs(targetNode.y - src.fromNode.y)
      ? targetNode.x >= src.fromNode.x
        ? 'left'
        : 'right'
      : 'left')

  const fromTitle = src.fromPin?.title || src.fromNode?.title || '要素'
  const newEdgeId = `ed_${Date.now().toString(36)}`

  emit('before-mutate')
  if (!props.canvasData.edges) props.canvasData.edges = []
  props.canvasData.edges.push({
    id: newEdgeId,
    from: src.fromId,
    fromPort: src.fromPort || 'right',
    to: targetNode.id,
    toPort: autoToPort,
    label: src.fromKind === 'pin' ? '热点关联' : '配合接口',
    sub: `${fromTitle} → ${targetNode.title}`
  })
  emit('change')
  emit('select', { kind: 'edge', id: newEdgeId })
  ElMessage.success(`已连接「${fromTitle}」至「${targetNode.title}」`)
}

function finishLinkOnPin(targetPin: BlueprintPin) {
  if (!linkingState.value) return
  const src = linkingState.value
  linkingState.value = null
  if (src.fromId === targetPin.id) return

  const existing = (props.canvasData.edges || []).find(
    (ed) =>
      (ed.from === src.fromId && ed.to === targetPin.id) ||
      (ed.from === targetPin.id && ed.to === src.fromId)
  )
  if (existing) {
    emit('select', { kind: 'edge', id: existing.id })
    return
  }

  const fromTitle = src.fromPin?.title || src.fromNode?.title || '要素'
  const newEdgeId = `ed_${Date.now().toString(36)}`

  emit('before-mutate')
  if (!props.canvasData.edges) props.canvasData.edges = []
  props.canvasData.edges.push({
    id: newEdgeId,
    from: src.fromId,
    fromPort: src.fromPort || 'right',
    to: targetPin.id,
    toPort: 'left',
    label: '热点关联',
    sub: `${fromTitle} → ${targetPin.title}`
  })
  emit('change')
  emit('select', { kind: 'edge', id: newEdgeId })
  ElMessage.success(`已连接「${fromTitle}」至「${targetPin.title}」`)
}

function onNodeMouseUp(e: MouseEvent, nd: CanvasModuleNode) {
  if (linkingState.value) {
    finishLinkOnNode(nd)
  }
  // 核心修复【信标 1】：节点释放时立即终止拖拽上下文，防止点击后持续粘滞拖拽
  onStageMouseUp()
}

function onWindowMouseUp() {
  if (dragContext || linkingState.value) {
    onStageMouseUp()
  }
}

function getNodeInstanceIndex(node: CanvasModuleNode): number {
  if (!node.sub_board_id) return 1
  let count = 0
  for (const n of props.canvasData.nodes || []) {
    if (n.sub_board_id === node.sub_board_id) {
      count++
      if (n.id === node.id) return count
    }
  }
  return 1
}

// ==================== 画布元素右键上下文菜单与快捷删除 ====================
const canvasCtxMenu = reactive<{
  visible: boolean
  x: number
  y: number
  kind: 'node' | 'edge' | 'pin'
  id: string
  title: string
  node?: CanvasModuleNode
  boardImgId?: string
}>({
  visible: false,
  x: 0,
  y: 0,
  kind: 'node',
  id: '',
  title: ''
})

function closeCanvasCtxMenu() {
  canvasCtxMenu.visible = false
}

function openNodeContextMenu(e: MouseEvent, nd: CanvasModuleNode) {
  closeCanvasCtxMenu()
  emit('select', { kind: 'node', id: nd.id })
  canvasCtxMenu.visible = true
  canvasCtxMenu.x = Math.min(window.innerWidth - 190, e.clientX)
  canvasCtxMenu.y = Math.min(window.innerHeight - 170, e.clientY)
  canvasCtxMenu.kind = 'node'
  canvasCtxMenu.id = nd.id
  canvasCtxMenu.title = nd.title
  canvasCtxMenu.node = nd
}

function openEdgeContextMenu(e: MouseEvent, edge: { id: string; label?: string }) {
  closeCanvasCtxMenu()
  emit('select', { kind: 'edge', id: edge.id })
  canvasCtxMenu.visible = true
  canvasCtxMenu.x = Math.min(window.innerWidth - 190, e.clientX)
  canvasCtxMenu.y = Math.min(window.innerHeight - 170, e.clientY)
  canvasCtxMenu.kind = 'edge'
  canvasCtxMenu.id = edge.id
  canvasCtxMenu.title = edge.label || '配合接口'
  canvasCtxMenu.node = undefined
}

function openPinContextMenu(e: MouseEvent, pin: BlueprintPin, ib: CanvasImageBoard) {
  closeCanvasCtxMenu()
  emit('select', { kind: 'pin', id: pin.id, boardImgId: ib.id })
  canvasCtxMenu.visible = true
  canvasCtxMenu.x = Math.min(window.innerWidth - 190, e.clientX)
  canvasCtxMenu.y = Math.min(window.innerHeight - 170, e.clientY)
  canvasCtxMenu.kind = 'pin'
  canvasCtxMenu.id = pin.id
  canvasCtxMenu.title = `#${pin.num} ${pin.title}`
  canvasCtxMenu.boardImgId = ib.id
  canvasCtxMenu.node = undefined
}

function triggerDeleteElement(sel: CanvasSelection) {
  closeCanvasCtxMenu()
  emit('delete-element', sel)
}

function onCtxDeleteElement() {
  const sel: CanvasSelection = {
    kind: canvasCtxMenu.kind,
    id: canvasCtxMenu.id,
    boardImgId: canvasCtxMenu.boardImgId
  }
  triggerDeleteElement(sel)
}

function onCtxDrillSubBoard() {
  if (canvasCtxMenu.node?.sub_board_id) {
    emit('drill-sub-board', canvasCtxMenu.node.sub_board_id)
  }
  closeCanvasCtxMenu()
}

function onCtxCreateItem() {
  const sel: CanvasSelection = {
    kind: canvasCtxMenu.kind,
    id: canvasCtxMenu.id,
    boardImgId: canvasCtxMenu.boardImgId
  }
  emit('select', sel)
  closeCanvasCtxMenu()
}

onMounted(() => {
  window.addEventListener('mouseup', onWindowMouseUp)
  window.addEventListener('click', closeCanvasCtxMenu)
})

onBeforeUnmount(() => {
  window.removeEventListener('mouseup', onWindowMouseUp)
  window.removeEventListener('click', closeCanvasCtxMenu)
})

function onStageMouseMove(e: MouseEvent) {
  if (linkingState.value) {
    const pt = clientToWorld(e.clientX, e.clientY)
    linkingState.value.currWorldX = pt.x
    linkingState.value.currWorldY = pt.y
    return
  }
  if (!dragContext) return

  const z = viewport.value.zoom
  const dx = e.clientX - dragContext.startX
  const dy = e.clientY - dragContext.startY
  const dist = Math.hypot(dx, dy)

  if (dragContext.type === 'pan') {
    if (!dragContext.moved && dist > DRAG_DEADZONE_PX) {
      dragContext.moved = true
    }
    if (dragContext.moved) {
      props.canvasData.viewport.panX = Math.round(dragContext.origPanX + dx)
      props.canvasData.viewport.panY = Math.round(dragContext.origPanY + dy)
    }
  } else if (dragContext.type === 'node') {
    if (!dragContext.moved && dist > DRAG_DEADZONE_PX) {
      emit('before-mutate')
      dragContext.moved = true
    }
    if (dragContext.moved) {
      dragContext.node.x = Math.round(dragContext.origX + dx / z)
      dragContext.node.y = Math.round(dragContext.origY + dy / z)
    }
  } else if (dragContext.type === 'blueprint') {
    if (!dragContext.moved && dist > DRAG_DEADZONE_PX) {
      emit('before-mutate')
      dragContext.moved = true
    }
    if (dragContext.moved) {
      dragContext.bp.x = Math.round(dragContext.origX + dx / z)
      dragContext.bp.y = Math.round(dragContext.origY + dy / z)
    }
  } else if (dragContext.type === 'resize-bp') {
    dragContext.bp.w = Math.max(220, Math.round(dragContext.origW + dx / z))
    dragContext.bp.h = Math.max(150, Math.round(dragContext.origH + dy / z))
  } else if (dragContext.type === 'pin') {
    if (!dragContext.moved && dist > 4) {
      emit('before-mutate')
      dragContext.moved = true
    }
    if (dragContext.moved) {
      const bodyH = Math.max(80, dragContext.bp.h - 32)
      dragContext.pin.rx = Number(
        Math.min(0.95, Math.max(0.05, dragContext.origRx + dx / z / dragContext.bp.w)).toFixed(3)
      )
      dragContext.pin.ry = Number(
        Math.min(0.94, Math.max(0.06, dragContext.origRy + dy / z / bodyH)).toFixed(3)
      )
    }
  }
}

function onStageMouseUp() {
  if (linkingState.value) {
    linkingState.value = null
  }
  if (!dragContext) return

  const ctx = dragContext
  dragContext = null
  isPanning.value = false

  if (ctx.type === 'pan') {
    if (!ctx.moved) {
      emit('select', null)
    } else {
      emit('change')
    }
  } else if (ctx.type === 'node') {
    if (ctx.moved) {
      suppressNextNodeClick = true
      emit('change')
    }
  } else if (ctx.type === 'resize-bp' || ctx.moved) {
    emit('change')
  }
}

function onStageWheel(e: WheelEvent) {
  const rect = stageRef.value?.getBoundingClientRect()
  const sx = e.clientX - (rect?.left || 0)
  const sy = e.clientY - (rect?.top || 0)
  const delta = e.deltaY < 0 ? 0.08 : -0.08
  emit('zoom', viewport.value.zoom + delta, sx, sy)
}

// ==================== 底图打点、上传与三合一节点插入 ====================

function activatePinTool() {
  nodeMenuOpen.value = false
  if (!props.canvasData.image_boards.length) {
    ElMessage.info('请先点击「底图」或按 Ctrl+V 贴入一张剖面图/照片，即可在图上打风险热点')
  }
  toolMode.value = toolMode.value === 'pin' ? 'select' : 'pin'
}

function placePinAtEvent(e: MouseEvent, ib: CanvasImageBoard) {
  const targetEl = e.currentTarget as HTMLElement
  const rect = targetEl.getBoundingClientRect()
  const rx = Number(Math.min(0.95, Math.max(0.05, (e.clientX - rect.left) / rect.width)).toFixed(3))
  const ry = Number(Math.min(0.94, Math.max(0.06, (e.clientY - rect.top) / rect.height)).toFixed(3))

  const nextNum = ib.pins.reduce((m, p) => Math.max(m, p.num), 0) + 1
  const newPin: BlueprintPin = {
    id: `pin_${Date.now().toString(36)}`,
    num: nextNum,
    rx,
    ry,
    title: `图纸热点 #${nextNum}`,
    sub: ib.title
  }

  emit('before-mutate')
  ib.pins.push(newPin)
  toolMode.value = 'select'
  emit('change')
  emit('select', { kind: 'pin', id: newPin.id, boardImgId: ib.id })
}

function onBlueprintBodyClick(e: MouseEvent, ib: CanvasImageBoard) {
  if (toolMode.value === 'pin') {
    placePinAtEvent(e, ib)
  } else {
    emit('select', null)
  }
}

function onBlueprintDblClick(e: MouseEvent, ib: CanvasImageBoard) {
  placePinAtEvent(e, ib)
}

function finishBpRename() {
  editingBpId.value = null
  emit('change')
}

async function removeBlueprint(ibId: string) {
  const ib = props.canvasData.image_boards.find((b) => b.id === ibId)
  if (!ib) return
  try {
    await ElMessageBox.confirm(`确认从画布移除底图「${ib.title}」及其打点标记吗？`, '移除底图', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '取消'
    })
    emit('before-mutate')
    props.canvasData.image_boards = props.canvasData.image_boards.filter((b) => b.id !== ibId)
    if (props.selection?.boardImgId === ibId) {
      emit('select', null)
    }
    emit('change')
  } catch {
    // 取消
  }
}

function triggerBlueprintPicker() {
  nodeMenuOpen.value = false
  fileInputRef.value?.click()
}

async function createBlueprintFromFile(file: File) {
  const uploaded = await uploadImageFile(file, 'fmea_blueprint', props.boardId)
  if (!uploaded) return

  const rect = stageRef.value?.getBoundingClientRect()
  const centerX = ((rect?.width || 900) * 0.36 - viewport.value.panX) / viewport.value.zoom
  const centerY = ((rect?.height || 600) * 0.42 - viewport.value.panY) / viewport.value.zoom

  emit('before-mutate')
  props.canvasData.image_boards.push({
    id: `ib_${Date.now().toString(36)}`,
    title: uploaded.name || '新建图纸底板',
    img_url: uploaded.url,
    attachment_id: uploaded.attachment_id,
    x: Math.max(24, Math.round(centerX - 190)),
    y: Math.max(24, Math.round(centerY - 130)),
    w: 390,
    h: 268,
    pins: []
  })
  emit('change', true)
  ElMessage.success('底图已放入画布，点击底部「打点」或双击图面可标记风险热点')
}

async function onBlueprintFileChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (f) {
    await createBlueprintFromFile(f)
  }
}

async function onStageDrop(e: DragEvent) {
  isDragOver.value = false
  // 1. 优先解析从左侧大纲树拖入的画板 (直接拖拽到画布精准落点并绑定 BOM 映射)
  const rawData = e.dataTransfer?.getData('application/json') || e.dataTransfer?.getData('text/plain')
  if (rawData) {
    try {
      const payload = JSON.parse(rawData)
      if (payload.type === 'fmea-sub-board' && payload.board) {
        const rect = stageRef.value?.getBoundingClientRect()
        const stageX = e.clientX - (rect?.left || 0)
        const stageY = e.clientY - (rect?.top || 0)
        const worldX = Math.round((stageX - viewport.value.panX) / viewport.value.zoom - 92)
        const worldY = Math.round((stageY - viewport.value.panY) / viewport.value.zoom - 38)
        insertSubBoardNode(payload.board, { x: Math.max(20, worldX), y: Math.max(20, worldY) })
        return
      }
    } catch {
      // 忽略普通字符串
    }
  }

  // 2. 检查图片文件拖放上传
  const files = extractImagesFromDrop(e)
  if (files.length > 0) {
    await createBlueprintFromFile(files[0])
  }
}

// ==================== 三合一节点创建（普通 / 共用件 / 子模块画板） ====================

function getSpawnCoords() {
  const rect = stageRef.value?.getBoundingClientRect()
  const worldX = ((rect?.width || 900) * 0.45 - viewport.value.panX) / viewport.value.zoom
  const worldY = ((rect?.height || 600) * 0.42 - viewport.value.panY) / viewport.value.zoom
  const offset = (props.canvasData.nodes.length % 5) * 24
  return {
    x: Math.round(worldX - 92 + offset),
    y: Math.round(worldY - 38 + offset)
  }
}

async function toggleNodeInsertMenu() {
  nodeMenuOpen.value = !nodeMenuOpen.value
  if (nodeMenuOpen.value) {
    nodeMenuSearch.value = ''
    try {
      sharedUnitOptions.value = await fmeaApi.listSharedUnits()
    } catch {
      sharedUnitOptions.value = []
    }
  }
}

async function switchNodeMenuTab(tab: 'shared' | 'sub_board') {
  nodeMenuTab.value = tab
  nodeMenuSearch.value = ''
  if (tab === 'shared' && sharedUnitOptions.value.length === 0) {
    try {
      sharedUnitOptions.value = await fmeaApi.listSharedUnits()
    } catch {
      sharedUnitOptions.value = []
    }
  }
}

const filteredSharedUnits = computed(() => {
  const kw = nodeMenuSearch.value.trim().toLowerCase()
  if (!kw) return sharedUnitOptions.value
  return sharedUnitOptions.value.filter(
    (u) => u.unit_code.toLowerCase().includes(kw) || u.title.toLowerCase().includes(kw)
  )
})

const filteredCandidateSubBoards = computed(() => {
  const excluded = new Set<number>([
    ...(props.boardId ? [props.boardId] : []),
    ...(props.ancestorBoardIds || [])
  ])
  const kw = nodeMenuSearch.value.trim().toLowerCase()
  return (props.allBoards || []).filter((b) => {
    if (excluded.has(b.id)) return false
    if (!kw) return true
    return (
      b.name.toLowerCase().includes(kw) ||
      b.group_name.toLowerCase().includes(kw) ||
      b.board_code.toLowerCase().includes(kw)
    )
  })
})

function addPlainModuleNode() {
  const pos = getSpawnCoords()
  const newNode: CanvasModuleNode = {
    id: `nd_${Date.now().toString(36)}`,
    title: `新建模块单元 ${props.canvasData.nodes.length + 1}`,
    sub: '',
    x: pos.x,
    y: pos.y
  }
  nodeMenuOpen.value = false
  emit('before-mutate')
  props.canvasData.nodes.push(newNode)
  toolMode.value = 'select'
  emit('change', true)
  emit('select', { kind: 'node', id: newNode.id })
}

function insertSharedUnitNode(unit: { unit_code: string; title: string }) {
  const pos = getSpawnCoords()
  const newNode: CanvasModuleNode = {
    id: `nd_${Date.now().toString(36)}`,
    title: unit.title || unit.unit_code,
    sub: unit.unit_code,
    unit_code: unit.unit_code,
    x: pos.x,
    y: pos.y
  }
  nodeMenuOpen.value = false
  emit('before-mutate')
  props.canvasData.nodes.push(newNode)
  toolMode.value = 'select'
  emit('change', true)
  emit('select', { kind: 'node', id: newNode.id })
  ElMessage.success(`已引用共用单元「${unit.unit_code}」，其本体机理卡已自动同步`)
}

function insertSubBoardNode(sb: FmeaBoardSummary, customPos?: { x: number; y: number }) {
  if (sb.id === props.boardId) {
    ElMessage.warning('不能将当前画板自身嵌套为子模块')
    return
  }
  if ((props.ancestorBoardIds || []).includes(sb.id)) {
    ElMessage.warning('不能嵌入当前画板的上级父画板（防止循环嵌套）')
    return
  }
  const pos = customPos || getSpawnCoords()
  const newNode: CanvasModuleNode = {
    id: `nd_${Date.now().toString(36)}`,
    title: sb.name,
    sub: sb.board_code,
    sub_board_id: sb.id,
    x: pos.x,
    y: pos.y
  }
  nodeMenuOpen.value = false
  emit('before-mutate')
  props.canvasData.nodes.push(newNode)
  toolMode.value = 'select'
  emit('change', true)
  emit('select', { kind: 'node', id: newNode.id })
  ElMessage.success(`已嵌入子模块「${sb.name}」，双击该节点即可下钻进入`)
}

function onNodeMenuSearchEnter() {
  if (nodeMenuTab.value === 'shared') {
    if (filteredSharedUnits.value.length > 0) {
      insertSharedUnitNode(filteredSharedUnits.value[0])
    } else if (nodeMenuSearch.value.trim()) {
      const code = nodeMenuSearch.value.trim().toUpperCase()
      insertSharedUnitNode({ unit_code: code, title: code })
    }
  } else if (filteredCandidateSubBoards.value.length > 0) {
    insertSubBoardNode(filteredCandidateSubBoards.value[0])
  }
}

function getStageDimensions() {
  const rect = stageRef.value?.getBoundingClientRect()
  return {
    width: rect?.width || 1000,
    height: rect?.height || 680
  }
}

defineExpose({
  createBlueprintFromFile,
  insertSubBoardNode,
  getStageDimensions,
  setToolMode: (m: CanvasToolMode) => {
    toolMode.value = m
  }
})
</script>

<style scoped>
.fmea-canvas-stage {
  position: relative;
  flex: 1;
  height: 100%;
  overflow: hidden;
  background-color: #f8fafc;
  background-image: radial-gradient(#cbd5e1 1.15px, transparent 1.15px);
  cursor: grab;
  user-select: none;
}

.fmea-canvas-stage.is-panning {
  cursor: grabbing;
}

.fmea-canvas-stage.is-linking {
  cursor: crosshair;
}

.drop-overlay {
  position: absolute;
  inset: 12px;
  border-radius: 12px;
  border: 2px dashed #2563eb;
  background: rgba(239, 246, 255, 0.78);
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.drop-card {
  padding: 10px 18px;
  border-radius: 8px;
  background: #0f172a;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
}

.canvas-world {
  position: absolute;
  left: 0;
  top: 0;
  width: 1px;
  height: 1px;
  transform-origin: 0 0;
}

.canvas-world.is-smooth {
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

/* ==================== 1. 图纸底板 ==================== */
.blueprint-board {
  position: absolute;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2;
}

.bp-header {
  height: 30px;
  padding: 0 8px 0 10px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: move;
  flex-shrink: 0;
}

.bp-ico {
  width: 13px;
  height: 13px;
  color: #64748b;
  flex-shrink: 0;
}

.bp-title {
  flex: 1;
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bp-title-input {
  flex: 1;
  height: 22px;
  padding: 0 6px;
  font-size: 11.5px;
  border: 1px solid #2563eb;
  border-radius: 4px;
  outline: none;
}

.bp-pin-hint {
  font-size: 10.5px;
  color: #2563eb;
  background: #eff6ff;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.bp-del-btn {
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 15px;
  line-height: 1;
  border-radius: 4px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}

.blueprint-board:hover .bp-del-btn {
  opacity: 1;
}

.bp-del-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.bp-body {
  position: relative;
  flex: 1;
  background: #0f172a;
  overflow: hidden;
}

.bp-body.pin-cursor {
  cursor: crosshair;
}

.bp-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.risk-pin {
  position: absolute;
  width: 24px;
  height: 24px;
  margin-left: -12px;
  margin-top: -12px;
  border-radius: 50%;
  background: #dc2626;
  color: #ffffff;
  font-size: 11.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.36);
  cursor: pointer;
  transition: transform 0.14s, opacity 0.15s;
  z-index: 5;
}

.risk-pin.risk-med {
  background: #d97706;
}

.risk-pin.risk-low {
  background: #059669;
}

.risk-pin.risk-none {
  background: #475569;
}

.risk-pin:hover,
.risk-pin.selected {
  transform: scale(1.18);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.45), 0 4px 10px rgba(15, 23, 42, 0.35);
}

.risk-pin.is-limit {
  border-color: #fef08a;
  box-shadow: 0 0 0 2.5px #f59e0b, 0 3px 8px rgba(245, 158, 11, 0.45);
}

.pin-limit-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 11px;
  line-height: 1;
  background: #ffffff;
  border-radius: 50%;
  padding: 1px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  pointer-events: none;
}

/* 图纸热点连线端口微把手 */
.pin-port {
  position: absolute;
  right: -6px;
  top: calc(50% - 5px);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #2563eb;
  z-index: 10;
  cursor: crosshair;
  opacity: 0;
  transition: opacity 0.14s, transform 0.14s;
}

.risk-pin:hover .pin-port,
.fmea-canvas-stage.is-linking .pin-port {
  opacity: 1;
}

.pin-port:hover {
  transform: scale(1.35);
  background: #2563eb;
}

.bp-resize-grip {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 14px;
  height: 14px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, #94a3b8 50%);
  opacity: 0.55;
  z-index: 6;
}

/* ==================== 2. 贝塞尔接口连线 ==================== */
.edges-svg-layer {
  position: absolute;
  left: 0;
  top: 0;
  width: 4000px;
  height: 3000px;
  overflow: visible;
  pointer-events: none;
  z-index: 3;
}

.edge-group {
  pointer-events: stroke;
  cursor: pointer;
}

.edge-hit-path {
  fill: none;
  stroke: transparent;
  stroke-width: 14px;
}

.edge-vis-path {
  fill: none;
  stroke: #94a3b8;
  stroke-width: 1.75px;
  transition: stroke 0.15s, stroke-width 0.15s, opacity 0.15s;
}

.edge-group.is-high .edge-vis-path {
  stroke: #f87171;
}

.edge-group.is-challenge .edge-vis-path {
  stroke: #f97316;
  stroke-width: 2.1px;
  stroke-dasharray: 6 4;
  animation: challengeFlow 1.2s linear infinite;
}

@keyframes challengeFlow {
  to {
    stroke-dashoffset: -10;
  }
}

.edge-group:hover .edge-vis-path,
.edge-group.selected .edge-vis-path {
  stroke: #2563eb;
  stroke-width: 2.3px;
}

.edge-linking-preview {
  fill: none;
  stroke: #2563eb;
  stroke-width: 1.8px;
  stroke-dasharray: 5 4;
}

.edge-short-pill {
  position: absolute;
  transform: translate(-50%, -50%);
  height: 22px;
  padding: 0 8px;
  border-radius: 11px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  z-index: 4;
  transition: all 0.14s;
}

.edge-short-pill.has-high {
  border-color: #fecaca;
  color: #b91c1c;
}

.edge-short-pill.is-challenge {
  border-color: #fdba74;
  background: #fff7ed;
  color: #c2410c;
  font-weight: 600;
}

.edge-short-pill.is-challenge:hover,
.edge-short-pill.is-challenge.selected {
  border-color: #ea580c;
  background: #ffedd5;
  color: #9a3412;
  box-shadow: 0 0 0 2px rgba(234, 88, 12, 0.2);
}

.challenge-pill-icon {
  font-size: 11px;
  line-height: 1;
}

.edge-short-pill:hover,
.edge-short-pill.selected {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.14);
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.pill-dot.high {
  background: #ef4444;
}

.pill-dot.med {
  background: #f59e0b;
}

/* ==================== 3. 184px 极简模块节点（含子模块黑盒与共用单元） ==================== */
.module-node {
  position: absolute;
  width: 184px;
  min-height: 76px;
  padding: 9px 11px 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 9px;
  cursor: pointer;
  z-index: 5;
  transition: border-color 0.14s, box-shadow 0.14s, opacity 0.15s;
}

.module-node.is-sub-board {
  border-color: #c7d2fe;
  border-top: 2.5px solid #4f46e5;
  background: linear-gradient(180deg, #f8faff 0%, #ffffff 48%);
  box-shadow: 0 3px 0 #e0e7ff, 0 4px 12px rgba(15, 23, 42, 0.06);
}

.module-node.is-shared-unit {
  border-left: 2.5px solid #0284c7;
}

.module-node:hover {
  border-color: #94a3b8;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.module-node.is-sub-board:hover {
  border-color: #818cf8;
  border-top-color: #4f46e5;
}

.module-node.selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 2.5px rgba(37, 99, 235, 0.18), 0 6px 16px rgba(15, 23, 42, 0.08);
}

.dimmed {
  opacity: 0.24 !important;
}

.node-head {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.node-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 5px;
}

.node-title {
  flex: 1;
  font-size: 12.5px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-sub-row {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.node-sub {
  font-size: 10.5px;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bom-micro-badge {
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  line-height: 1.25;
  flex-shrink: 0;
}

.bom-micro-badge.sub {
  background: #eef2ff;
  color: #4338ca;
  border: 1px solid #c7d2fe;
}

.bom-micro-badge.shared {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.drill-chip-btn {
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  color: #4338ca;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.12s;
}

.drill-chip-btn:hover {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #ffffff;
}

.node-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.node-risk-summary {
  display: flex;
  align-items: center;
  gap: 6px;
}

.r-chip {
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.r-chip .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.r-chip.high {
  color: #dc2626;
}

.r-chip.high .dot {
  background: #ef4444;
}

.r-chip.normal {
  color: #475569;
}

.r-chip.normal .dot {
  background: #f59e0b;
}

.r-empty {
  font-size: 11px;
  color: #94a3b8;
}

.photo-cnt {
  font-size: 11px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.photo-cnt svg {
  width: 12.5px;
  height: 12.5px;
}

/* 四向连线微端口 */
.node-port {
  position: absolute;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ffffff;
  border: 1.75px solid #2563eb;
  opacity: 0;
  transition: opacity 0.14s, transform 0.14s;
  cursor: crosshair;
  z-index: 7;
}

.module-node:hover .node-port,
.fmea-canvas-stage.is-linking .node-port {
  opacity: 1;
}

.node-port:hover {
  transform: scale(1.35);
  background: #2563eb;
}

.port-top {
  top: -5px;
  left: calc(50% - 4.5px);
}

.port-bottom {
  bottom: -5px;
  left: calc(50% - 4.5px);
}

.port-left {
  left: -5px;
  top: calc(50% - 4.5px);
}

.port-right {
  right: -5px;
  top: calc(50% - 4.5px);
}

/* ==================== 4. 底部三合一节点插入上浮菜单 ==================== */
.node-insert-popover {
  position: absolute;
  left: 50%;
  bottom: 62px;
  transform: translateX(-50%);
  width: 288px;
  padding: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 11px;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14);
  display: flex;
  flex-direction: column;
  gap: 7px;
  z-index: 30;
}

.ni-quick-create {
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  gap: 9px;
  text-align: left;
  cursor: pointer;
  transition: all 0.13s;
}

.ni-quick-create:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.ni-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #0f172a;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ni-main {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.ni-sub {
  font-size: 10.5px;
  color: #64748b;
}

.ni-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 2px;
  border-radius: 7px;
  background: #f1f5f9;
}

.ni-tab {
  height: 24px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.ni-tab.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.ni-search {
  height: 27px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 11.5px;
  color: #0f172a;
  outline: none;
}

.ni-search:focus {
  border-color: #2563eb;
}

.ni-list {
  max-height: 156px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ni-empty {
  padding: 12px 6px;
  text-align: center;
  font-size: 11px;
  color: #94a3b8;
}

.ni-option {
  padding: 5px 7px;
  border: none;
  border-radius: 6px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  cursor: pointer;
  text-align: left;
}

.ni-option:hover {
  background: #f1f5f9;
}

.nio-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.nio-code {
  font-size: 10px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  padding: 1px 5px;
  border-radius: 4px;
  background: #e0f2fe;
  color: #0369a1;
  flex-shrink: 0;
}

.nio-code.sub {
  background: #eef2ff;
  color: #4338ca;
}

.nio-title {
  font-size: 12px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nio-meta {
  font-size: 10.5px;
  color: #94a3b8;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ==================== 5. 底部极简悬浮短工具坞 ==================== */
.bottom-short-dock {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  height: 38px;
  padding: 0 6px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  gap: 3px;
  z-index: 20;
}

.dock-btn {
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.14s;
}

.dock-btn svg {
  width: 14px;
  height: 14px;
}

.dock-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.dock-btn.active {
  background: #0f172a;
  color: #ffffff;
}

.dock-sep {
  width: 1px;
  height: 16px;
  background: #e2e8f0;
  margin: 0 3px;
}

/* ==================== 6. 右下角微缩撤销缩放条 ==================== */
.zoom-undo-bar {
  position: absolute;
  right: 16px;
  bottom: 16px;
  height: 32px;
  padding: 0 5px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
  display: flex;
  align-items: center;
  gap: 2px;
  z-index: 18;
}

.micro-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #475569;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.micro-btn:hover:not(:disabled) {
  background: #f1f5f9;
  color: #0f172a;
}

.micro-btn:disabled {
  opacity: 0.32;
  cursor: not-allowed;
}

.micro-btn svg {
  width: 13.5px;
  height: 13.5px;
}

.micro-sep {
  width: 1px;
  height: 14px;
  background: #e2e8f0;
  margin: 0 2px;
}

.zoom-pct-btn {
  min-width: 44px;
  height: 24px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #334155;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}

.zoom-pct-btn:hover {
  background: #f1f5f9;
}

/* 节点悬停快捷删除按钮 (【信标 1】快捷删除) */
.node-del-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  line-height: 14px;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  transition: all 0.12s ease;
  z-index: 5;
}

.module-node:hover .node-del-btn {
  display: inline-flex;
}

.node-del-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* 画布右键上下文菜单 */
.canvas-ctx-menu {
  position: fixed;
  z-index: 9999;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15), 0 4px 6px -2px rgba(15, 23, 42, 0.05);
  min-width: 175px;
  padding: 4px;
  user-select: none;
  animation: ctxFadeIn 0.1s ease;
}

@keyframes ctxFadeIn {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.canvas-ctx-menu .ctx-header {
  padding: 6px 8px 4px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 2px;
}

.canvas-ctx-menu .ctx-type {
  font-size: 9.5px;
  color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  display: block;
}

.canvas-ctx-menu .ctx-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.canvas-ctx-menu .ctx-item {
  height: 28px;
  padding: 0 8px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #334155;
  cursor: pointer;
  transition: background 0.12s;
}

.canvas-ctx-menu .ctx-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.canvas-ctx-menu .ctx-item.danger {
  color: #e11d48;
}

.canvas-ctx-menu .ctx-item.danger:hover {
  background: #fff1f2;
  color: #be123c;
}

.canvas-ctx-menu .ctx-ico {
  font-size: 12px;
  width: 14px;
  display: inline-flex;
  justify-content: center;
}

.canvas-ctx-menu .ctx-shortcut {
  margin-left: auto;
  font-size: 10px;
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.canvas-ctx-menu .ctx-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 3px 0;
}
</style>
