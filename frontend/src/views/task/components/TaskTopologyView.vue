<template>
  <div class="task-topology-view">
    <!-- 拓扑顶栏工具条 -->
    <div class="topology-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">🕸️ SQM 质量任务拓扑依赖与工序流向图</span>
        <span class="toolbar-subtitle">直观识别前后置阻断红线，监控各环节交期交付链</span>
      </div>

      <div class="toolbar-right">
        <div class="topology-legend">
          <span class="legend-item"><span class="legend-line solid-green"></span>前置已就绪</span>
          <span class="legend-item"><span class="legend-line dashed-red"></span>前置未结阻断</span>
          <span class="legend-item"><span class="legend-badge blocked">⚠️ 受阻节点</span></span>
        </div>
      </div>
    </div>

    <!-- 拓扑主画布区域 (自适应 SVG 连接线与 HTML 节点) -->
    <div class="topology-stage" ref="stageRef">
      <!-- 泳道分组列 (按制造质量阶段划分流向) -->
      <div class="topology-lanes">
        <!-- 阶段 1: 供应商准备与开模 -->
        <div class="stage-lane">
          <div class="stage-lane-header">
            <span class="lane-stage-badge">阶段一</span>
            <span class="lane-stage-name">🏢 供应商商务与模具</span>
          </div>
          <div class="stage-nodes-box">
            <div
              v-for="node in supplierNodes"
              :key="node.id"
              class="dag-node-card"
              :class="[
                node.status.toLowerCase(),
                {
                  'is-active': selectedNodeId === node.id,
                  'is-blocked': isNodeBlocked(node)
                }
              ]"
              :ref="(el) => registerNodeEl(node.id, el)"
              @click="handleSelectNode(node.id)"
            >
              <div class="node-top-row">
                <span class="node-code">{{ node.task_code }}</span>
                <span v-if="isNodeBlocked(node)" class="node-blocked-tag">⚠️ 依赖阻塞</span>
                <span v-else class="node-status-tag" :class="node.status.toLowerCase()">
                  {{ getStatusText(node.status) }}
                </span>
              </div>
              <div class="node-title" :title="node.title">{{ node.title }}</div>
              <div class="node-footer-row">
                <span class="node-user">👤 {{ node.assignee_name || '待定' }}</span>
                <span class="node-date">📅 {{ node.due_date || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 流向箭头指示 -->
        <div class="stage-arrow-col">➔</div>

        <!-- 阶段 2: 零件样品开发与送样 -->
        <div class="stage-lane">
          <div class="stage-lane-header">
            <span class="lane-stage-badge">阶段二</span>
            <span class="lane-stage-name">⚙️ 零件送样与试产</span>
          </div>
          <div class="stage-nodes-box">
            <div
              v-for="node in partNodes"
              :key="node.id"
              class="dag-node-card"
              :class="[
                node.status.toLowerCase(),
                {
                  'is-active': selectedNodeId === node.id,
                  'is-blocked': isNodeBlocked(node)
                }
              ]"
              :ref="(el) => registerNodeEl(node.id, el)"
              @click="handleSelectNode(node.id)"
            >
              <div class="node-top-row">
                <span class="node-code">{{ node.task_code }}</span>
                <span v-if="isNodeBlocked(node)" class="node-blocked-tag">⚠️ 依赖阻塞</span>
                <span v-else class="node-status-tag" :class="node.status.toLowerCase()">
                  {{ getStatusText(node.status) }}
                </span>
              </div>
              <div class="node-title" :title="node.title">{{ node.title }}</div>
              <div class="node-footer-row">
                <span class="node-user">👤 {{ node.assignee_name || '待定' }}</span>
                <span class="node-date">📅 {{ node.due_date || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 流向箭头指示 -->
        <div class="stage-arrow-col">➔</div>

        <!-- 阶段 3: CTQ 关键质量检验与量产 -->
        <div class="stage-lane">
          <div class="stage-lane-header">
            <span class="lane-stage-badge">阶段三</span>
            <span class="lane-stage-name">🎯 CTQ 特性与全尺寸</span>
          </div>
          <div class="stage-nodes-box">
            <div
              v-for="node in ctqNodes"
              :key="node.id"
              class="dag-node-card"
              :class="[
                node.status.toLowerCase(),
                {
                  'is-active': selectedNodeId === node.id,
                  'is-blocked': isNodeBlocked(node)
                }
              ]"
              :ref="(el) => registerNodeEl(node.id, el)"
              @click="handleSelectNode(node.id)"
            >
              <div class="node-top-row">
                <span class="node-code">{{ node.task_code }}</span>
                <span v-if="isNodeBlocked(node)" class="node-blocked-tag">⚠️ 依赖阻塞</span>
                <span v-else class="node-status-tag" :class="node.status.toLowerCase()">
                  {{ getStatusText(node.status) }}
                </span>
              </div>
              <div class="node-title" :title="node.title">{{ node.title }}</div>
              <div class="node-footer-row">
                <span class="node-user">👤 {{ node.assignee_name || '待定' }}</span>
                <span class="node-date">📅 {{ node.due_date || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 流向箭头指示 -->
        <div class="stage-arrow-col">➔</div>

        <!-- 阶段 4: 规程归档与协同闭环 -->
        <div class="stage-lane">
          <div class="stage-lane-header">
            <span class="lane-stage-badge">阶段四</span>
            <span class="lane-stage-name">📑 规程归档与持续改进</span>
          </div>
          <div class="stage-nodes-box">
            <div
              v-for="node in otherNodes"
              :key="node.id"
              class="dag-node-card"
              :class="[
                node.status.toLowerCase(),
                {
                  'is-active': selectedNodeId === node.id,
                  'is-blocked': isNodeBlocked(node)
                }
              ]"
              :ref="(el) => registerNodeEl(node.id, el)"
              @click="handleSelectNode(node.id)"
            >
              <div class="node-top-row">
                <span class="node-code">{{ node.task_code }}</span>
                <span v-if="isNodeBlocked(node)" class="node-blocked-tag">⚠️ 依赖阻塞</span>
                <span v-else class="node-status-tag" :class="node.status.toLowerCase()">
                  {{ getStatusText(node.status) }}
                </span>
              </div>
              <div class="node-title" :title="node.title">{{ node.title }}</div>
              <div class="node-footer-row">
                <span class="node-user">👤 {{ node.assignee_name || '待定' }}</span>
                <span class="node-date">📅 {{ node.due_date || '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部选中节点详情快速条 -->
    <div v-if="selectedTask" class="node-detail-banner">
      <div class="banner-left">
        <span class="banner-code">{{ selectedTask.task_code }}</span>
        <span class="banner-title">{{ selectedTask.title }}</span>
        <el-tag size="small" :type="selectedTask.status === 'DONE' ? 'success' : 'warning'">
          {{ selectedTask.status }}
        </el-tag>
      </div>
      <div class="banner-right">
        <span class="banner-info">责任人: {{ selectedTask.assignee_name || '未指派' }}</span>
        <span class="banner-info">截止日期: {{ selectedTask.due_date || '未设置' }}</span>
        <el-button type="primary" size="small" @click="emit('open-detail', selectedTask.id)">
          查看完整工单与附件
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { TaskItem } from '@/types/task'

const props = defineProps<{
  tasks: TaskItem[]
}>()

const emit = defineEmits<{
  (e: 'open-detail', id: number): void
}>()

const selectedNodeId = ref<number | null>(null)
const nodeElements = new Map<number, HTMLElement>()

const registerNodeEl = (id: number, el: any) => {
  if (el) {
    nodeElements.set(id, el)
  } else {
    nodeElements.delete(id)
  }
}

// 分流节点到制造阶段
const supplierNodes = computed(() => {
  return props.tasks.filter(t => t.source_type === 'SUPPLIER')
})

const partNodes = computed(() => {
  return props.tasks.filter(t => t.source_type === 'PART')
})

const ctqNodes = computed(() => {
  return props.tasks.filter(t => t.source_type === 'CTQ')
})

const otherNodes = computed(() => {
  return props.tasks.filter(t => !['SUPPLIER', 'PART', 'CTQ'].includes(t.source_type))
})

const taskMap = computed(() => {
  const map = new Map<number, TaskItem>()
  props.tasks.forEach(t => map.set(t.id, t))
  return map
})

// 检查该节点是否被前置任务阻塞 (如果前置未完成，则阻塞)
const isNodeBlocked = (node: TaskItem) => {
  if (node.status === 'DONE') return false
  if (node.status === 'BLOCKED') return true

  // 如果有前置任务 ID 列表
  if (node.predecessor_ids && Array.isArray(node.predecessor_ids) && node.predecessor_ids.length > 0) {
    for (const pid of node.predecessor_ids) {
      const pred = taskMap.value.get(pid)
      if (pred && pred.status !== 'DONE') {
        return true
      }
    }
  }

  // 跨阶段仿真拓扑推导：若零件开发有对应供应商任务且供应商未闭环
  if (node.source_type === 'PART') {
    const hasUnfinishedSupplier = supplierNodes.value.some(s => s.status !== 'DONE')
    if (hasUnfinishedSupplier && supplierNodes.value.length > 0) return true
  }

  // 若 CTQ 检验中，存在未闭环的送样任务
  if (node.source_type === 'CTQ') {
    const hasUnfinishedPart = partNodes.value.some(p => p.status !== 'DONE')
    if (hasUnfinishedPart && partNodes.value.length > 0) return true
  }

  return false
}

const selectedTask = computed(() => {
  if (!selectedNodeId.value) return null
  return taskMap.value.get(selectedNodeId.value) || null
})

const handleSelectNode = (id: number) => {
  selectedNodeId.value = id
}

const getStatusText = (s: string) => {
  switch (s) {
    case 'TODO': return '待办'
    case 'IN_PROGRESS': return '进行中'
    case 'PENDING_REVIEW': return '待验收'
    case 'DONE': return '已闭环'
    case 'BLOCKED': return '已阻塞'
    default: return s
  }
}
</script>

<style scoped>
.task-topology-view {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
  min-height: 520px;
}

.topology-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #ebeef5;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toolbar-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.toolbar-subtitle {
  font-size: 12px;
  color: #909399;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.topology-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 11px;
  color: #606266;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-line {
  width: 18px;
  height: 2px;
  display: inline-block;
}
.legend-line.solid-green {
  background: #67c23a;
}
.legend-line.dashed-red {
  border-top: 2px dashed #f56c6c;
}
.legend-badge.blocked {
  background: #fef0f0;
  color: #f56c6c;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.topology-stage {
  flex: 1;
  padding: 24px 16px;
  background: #f8fafc;
  overflow-x: auto;
  position: relative;
}

.topology-lanes {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  min-width: 980px;
}

.stage-lane {
  flex: 1;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.stage-lane-header {
  padding: 10px 12px;
  background: #edf2f7;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.lane-stage-badge {
  font-size: 10px;
  font-weight: 700;
  background: #cbd5e1;
  color: #334155;
  padding: 1px 5px;
  border-radius: 4px;
}

.lane-stage-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.stage-arrow-col {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #94a3b8;
  height: 200px;
  font-weight: bold;
}

.stage-nodes-box {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 280px;
}

.dag-node-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dag-node-card:hover {
  transform: translateY(-2px);
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
}

.dag-node-card.is-active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

.dag-node-card.is-blocked {
  border-left: 4px solid #ef4444;
  background: #fff5f5;
}

.dag-node-card.done {
  border-left: 4px solid #10b981;
}

.node-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.node-code {
  font-family: monospace;
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

.node-blocked-tag {
  font-size: 10px;
  font-weight: 700;
  color: #ef4444;
  background: #fee2e2;
  padding: 1px 5px;
  border-radius: 4px;
}

.node-status-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
}
.node-status-tag.in_progress {
  background: #dbeafe;
  color: #1d4ed8;
}
.node-status-tag.done {
  background: #d1fae5;
  color: #047857;
}

.node-title {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.node-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  border-top: 1px dashed #e2e8f0;
  padding-top: 4px;
}

.node-detail-banner {
  padding: 12px 16px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.banner-code {
  font-family: monospace;
  font-weight: bold;
  color: #475569;
}

.banner-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.banner-right {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  color: #64748b;
}
</style>
