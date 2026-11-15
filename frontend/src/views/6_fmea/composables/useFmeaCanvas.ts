import { ref, computed } from 'vue'
import type {
  BoardCanvasData,
  CanvasModuleNode,
  PortSide,
  CanvasSelection
} from '@/views/6_fmea/types'

export const NODE_WIDTH = 184
export const NODE_HEIGHT = 76
export const RIGHT_PANEL_WIDTH = 368

export function cloneCanvasData(data: BoardCanvasData): BoardCanvasData {
  return JSON.parse(JSON.stringify(data))
}

export function getPortPoint(node: CanvasModuleNode, port: PortSide): { x: number; y: number } {
  switch (port) {
    case 'top':
      return { x: node.x + NODE_WIDTH / 2, y: node.y }
    case 'bottom':
      return { x: node.x + NODE_WIDTH / 2, y: node.y + NODE_HEIGHT }
    case 'left':
      return { x: node.x, y: node.y + NODE_HEIGHT / 2 }
    case 'right':
    default:
      return { x: node.x + NODE_WIDTH, y: node.y + NODE_HEIGHT / 2 }
  }
}

export function buildBezierEdgePath(
  p1: { x: number; y: number },
  fromPort: PortSide,
  p2: { x: number; y: number },
  toPort: PortSide
): { path: string; midX: number; midY: number } {
  const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y)
  const offset = Math.max(44, Math.min(140, dist * 0.42))

  const dirVec = (side: PortSide) => {
    if (side === 'left') return { dx: -offset, dy: 0 }
    if (side === 'right') return { dx: offset, dy: 0 }
    if (side === 'top') return { dx: 0, dy: -offset }
    return { dx: 0, dy: offset }
  }

  const v1 = dirVec(fromPort)
  const v2 = dirVec(toPort)
  const c1x = p1.x + v1.dx
  const c1y = p1.y + v1.dy
  const c2x = p2.x + v2.dx
  const c2y = p2.y + v2.dy

  // t = 0.5 处的三次贝塞尔精确中点，确保 4 字短标签严丝合缝骑在线中央
  const midX = 0.125 * p1.x + 0.375 * c1x + 0.375 * c2x + 0.125 * p2.x
  const midY = 0.125 * p1.y + 0.375 * c1y + 0.375 * c2y + 0.125 * p2.y

  return {
    path: `M ${p1.x} ${p1.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`,
    midX,
    midY
  }
}

export function useFmeaCanvas(onPersist: (canvas: BoardCanvasData) => void) {
  const canvasData = ref<BoardCanvasData>({
    viewport: { panX: 40, panY: 36, zoom: 1 },
    image_boards: [],
    nodes: [],
    edges: []
  })

  const undoStack = ref<BoardCanvasData[]>([])
  const redoStack = ref<BoardCanvasData[]>([])
  const isSmoothFocusing = ref(false)
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  let smoothTimer: ReturnType<typeof setTimeout> | null = null

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  function loadCanvas(initial: BoardCanvasData) {
    canvasData.value = cloneCanvasData({
      viewport: initial?.viewport || { panX: 40, panY: 36, zoom: 1 },
      image_boards: initial?.image_boards || [],
      nodes: initial?.nodes || [],
      edges: initial?.edges || []
    })
    undoStack.value = []
    redoStack.value = []
  }

  function pushHistorySnapshot() {
    undoStack.value.push(cloneCanvasData(canvasData.value))
    if (undoStack.value.length > 35) {
      undoStack.value.shift()
    }
    redoStack.value = []
  }

  function schedulePersist(immediate = false) {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
    if (immediate) {
      onPersist(cloneCanvasData(canvasData.value))
      return
    }
    saveTimer = setTimeout(() => {
      onPersist(cloneCanvasData(canvasData.value))
    }, 420)
  }

  function undo() {
    if (!undoStack.value.length) return
    const prev = undoStack.value.pop()!
    redoStack.value.push(cloneCanvasData(canvasData.value))
    canvasData.value = prev
    schedulePersist()
  }

  function redo() {
    if (!redoStack.value.length) return
    const next = redoStack.value.pop()!
    undoStack.value.push(cloneCanvasData(canvasData.value))
    canvasData.value = next
    schedulePersist()
  }

  function setZoom(nextZoom: number, pivotScreenX?: number, pivotScreenY?: number) {
    const vp = canvasData.value.viewport
    const clamped = Math.min(2.0, Math.max(0.45, Number(nextZoom.toFixed(2))))
    if (pivotScreenX !== undefined && pivotScreenY !== undefined) {
      const worldX = (pivotScreenX - vp.panX) / vp.zoom
      const worldY = (pivotScreenY - vp.panY) / vp.zoom
      vp.panX = Math.round(pivotScreenX - worldX * clamped)
      vp.panY = Math.round(pivotScreenY - worldY * clamped)
    }
    vp.zoom = clamped
    schedulePersist()
  }

  function resetViewport() {
    canvasData.value.viewport = { panX: 40, panY: 36, zoom: 1 }
    schedulePersist()
  }

  // 一键整齐理线排版：左放图纸底板，右侧网格整齐排列模块节点，并根据相对方位优化端口朝向
  function tidyLayout() {
    pushHistorySnapshot()
    let startX = 72
    const ibs = canvasData.value.image_boards
    if (ibs.length > 0) {
      let curY = 56
      for (const ib of ibs) {
        ib.x = 44
        ib.y = curY
        curY += ib.h + 36
        startX = Math.max(startX, ib.x + ib.w + 88)
      }
    }

    const nodes = canvasData.value.nodes
    const cols = nodes.length <= 3 ? nodes.length || 1 : 2
    nodes.forEach((nd, idx) => {
      const col = idx % cols
      const row = Math.floor(idx / cols)
      nd.x = startX + col * 264
      nd.y = 56 + row * 132
    })

    const nodeMap = new Map(nodes.map((n) => [n.id, n]))
    for (const ed of canvasData.value.edges) {
      const n1 = nodeMap.get(ed.from)
      const n2 = nodeMap.get(ed.to)
      if (!n1 || !n2) continue
      const dx = n2.x - n1.x
      const dy = n2.y - n1.y
      if (Math.abs(dx) >= Math.abs(dy)) {
        ed.fromPort = dx >= 0 ? 'right' : 'left'
        ed.toPort = dx >= 0 ? 'left' : 'right'
      } else {
        ed.fromPort = dy >= 0 ? 'bottom' : 'top'
        ed.toPort = dy >= 0 ? 'top' : 'bottom'
      }
    }
    schedulePersist()
  }

  // 点击大纲或从图鉴/台账跳转时：将目标元素平滑移至可视区中心（扣除右侧 368px 悬浮面板遮挡）
  function focusSelectionInStage(
    sel: CanvasSelection,
    stageWidth: number,
    stageHeight: number,
    ensureVisibleOnly = false
  ) {
    let worldX: number | null = null
    let worldY: number | null = null

    if (sel.kind === 'node') {
      const nd = canvasData.value.nodes.find((n) => n.id === sel.id)
      if (nd) {
        worldX = nd.x + NODE_WIDTH / 2
        worldY = nd.y + NODE_HEIGHT / 2
      }
    } else if (sel.kind === 'pin') {
      for (const ib of canvasData.value.image_boards) {
        const pin = ib.pins.find((p) => p.id === sel.id)
        if (pin) {
          worldX = ib.x + ib.w * pin.rx
          worldY = ib.y + ib.h * pin.ry
          break
        }
      }
    } else if (sel.kind === 'edge') {
      const ed = canvasData.value.edges.find((e) => e.id === sel.id)
      if (ed) {
        const n1 = canvasData.value.nodes.find((n) => n.id === ed.from)
        const n2 = canvasData.value.nodes.find((n) => n.id === ed.to)
        if (n1 && n2) {
          const bz = buildBezierEdgePath(
            getPortPoint(n1, ed.fromPort),
            ed.fromPort,
            getPortPoint(n2, ed.toPort),
            ed.toPort
          )
          worldX = bz.midX
          worldY = bz.midY
        }
      }
    }

    if (worldX === null || worldY === null) return

    const vp = canvasData.value.viewport
    const safeWidth = Math.max(280, stageWidth - RIGHT_PANEL_WIDTH - 24)
    const screenX = worldX * vp.zoom + vp.panX
    const screenY = worldY * vp.zoom + vp.panY

    if (ensureVisibleOnly) {
      // 若当前已经在安全可视区内，仅在被右侧悬浮面板遮挡时轻微左移
      if (screenX > safeWidth - 70) {
        vp.panX -= Math.round(screenX - (safeWidth - 110))
      } else if (screenX < 70) {
        vp.panX += Math.round(110 - screenX)
      }
      if (screenY < 60 || screenY > stageHeight - 80) {
        vp.panY = Math.round(stageHeight * 0.45 - worldY * vp.zoom)
      }
      return
    }

    if (smoothTimer) clearTimeout(smoothTimer)
    isSmoothFocusing.value = true
    smoothTimer = setTimeout(() => {
      isSmoothFocusing.value = false
    }, 250)

    vp.panX = Math.round(safeWidth * 0.5 - worldX * vp.zoom)
    vp.panY = Math.round(stageHeight * 0.46 - worldY * vp.zoom)
  }

  return {
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
  }
}

