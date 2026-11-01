<template>
  <div class="task-calendar-view">
    <!-- 日历顶栏工具与导航 -->
    <div class="calendar-toolbar">
      <div class="nav-cluster">
        <el-button-group size="small">
          <el-button :icon="ArrowLeft" @click="prevMonth">上月</el-button>
          <el-button @click="jumpToToday">今天</el-button>
          <el-button :icon="ArrowRight" @click="nextMonth">下月</el-button>
        </el-button-group>
        <span class="current-month-label">{{ currentYear }} 年 {{ currentMonth + 1 }} 月 质量协同日程</span>
      </div>

      <div class="toolbar-right">
        <!-- 图例解释 -->
        <div class="calendar-legend">
          <span class="legend-item"><span class="legend-dot urgent"></span>CTQ紧急</span>
          <span class="legend-item"><span class="legend-dot high"></span>重点关注</span>
          <span class="legend-item"><span class="legend-dot medium"></span>普通</span>
          <span class="legend-item"><span class="legend-dot done"></span>已闭环</span>
        </div>

        <el-radio-group v-model="dateField" size="small" class="field-toggle">
          <el-radio-button value="due_date">按截止日</el-radio-button>
          <el-radio-button value="start_date">按起始日</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 星期表头 -->
    <div class="calendar-week-header">
      <div v-for="(day, idx) in weekDays" :key="idx" class="week-day-cell" :class="{ 'is-weekend': idx >= 5 }">
        {{ day }}
      </div>
    </div>

    <!-- 7x6 / 7x5 日历格 -->
    <div class="calendar-grid-body">
      <div
        v-for="cell in calendarCells"
        :key="cell.dateStr"
        class="calendar-day-cell"
        :class="{
          'not-current-month': !cell.isCurrentMonth,
          'is-today': cell.isToday,
          'is-drag-over': dragOverDate === cell.dateStr
        }"
        @dragover.prevent="handleDragOver(cell.dateStr)"
        @dragleave="handleDragLeave(cell.dateStr)"
        @drop="handleDrop(cell.dateStr)"
        @click="emit('create-on-date', cell.dateStr)"
      >
        <!-- 日期数字与快捷加行按钮 -->
        <div class="cell-header">
          <div class="cell-header-left">
            <span class="day-number">{{ cell.dayNumber }}</span>
            <span v-if="cell.tasks.length > 0" class="day-count-badge">
              {{ cell.tasks.length }} 项
            </span>
          </div>
          <button
            type="button"
            class="day-quick-create-btn"
            title="在此日期新建协同任务"
            @click.stop="emit('create-on-date', cell.dateStr)"
          >
            +
          </button>
        </div>

        <!-- 任务事件条列表 -->
        <div class="cell-tasks-scroll">
          <div
            v-for="task in cell.tasks"
            :key="task.id"
            class="calendar-task-bar"
            :class="[
              (task.priority || 'medium').toLowerCase(),
              {
                'is-closed': task.status === 'DONE',
                'is-overdue': task.is_overdue
              }
            ]"
            draggable="true"
            @dragstart="handleDragStart($event, task)"
            @dragend="handleDragEnd"
            @click.stop="emit('open-detail', task.id)"
          >
            <span class="task-prio-dot"></span>
            <span class="task-bar-code">{{ task.task_code }}</span>
            <span class="task-bar-title" :title="task.title">{{ task.title }}</span>
            <span v-if="task.assignee_name" class="task-bar-user">{{ task.assignee_name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import type { TaskItem } from '@/types/task'

const props = defineProps<{
  tasks: TaskItem[]
}>()

const emit = defineEmits<{
  (e: 'open-detail', id: number): void
  (e: 'update-date', id: number, dateStr: string): void
  (e: 'create-on-date', dateStr: string): void
}>()

const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth()) // 0-indexed
const dateField = ref<'due_date' | 'start_date'>('due_date')

// 拖拽日期状态
const draggingTask = ref<TaskItem | null>(null)
const dragOverDate = ref<string | null>(null)

const prevMonth = () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11
    currentYear.value -= 1
  } else {
    currentMonth.value -= 1
  }
}

const nextMonth = () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0
    currentYear.value += 1
  } else {
    currentMonth.value += 1
  }
}

const jumpToToday = () => {
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth()
}

// 格式化为 YYYY-MM-DD
const formatDateStr = (year: number, month: number, day: number) => {
  const m = String(month + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${year}-${m}-${d}`
}

const todayStr = formatDateStr(today.getFullYear(), today.getMonth(), today.getDate())

// 按日期聚合任务字典
const tasksByDate = computed(() => {
  const map: Record<string, TaskItem[]> = {}
  for (const t of props.tasks) {
    const d = dateField.value === 'due_date' ? t.due_date : t.start_date
    if (d) {
      if (!map[d]) map[d] = []
      map[d].push(t)
    }
  }
  return map
})

// 计算日历网格所有格子 (包括上月尾巴与下月开头，保证整齐周对齐)
const calendarCells = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()

  // 星期一 = 1, ..., 星期日 = 0
  let startDayOfWeek = firstDay.getDay()
  if (startDayOfWeek === 0) startDayOfWeek = 7 // 转换周一为 1，周日为 7

  const cells: Array<{
    dateStr: string
    dayNumber: number
    isCurrentMonth: boolean
    isToday: boolean
    tasks: TaskItem[]
  }> = []

  // 填充上月末尾几天
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startDayOfWeek - 1; i > 0; i--) {
    const d = prevMonthLastDay - i + 1
    const prevMonthIdx = month === 0 ? 11 : month - 1
    const prevYear = month === 0 ? year - 1 : year
    const dStr = formatDateStr(prevYear, prevMonthIdx, d)
    cells.push({
      dateStr: dStr,
      dayNumber: d,
      isCurrentMonth: false,
      isToday: dStr === todayStr,
      tasks: tasksByDate.value[dStr] || []
    })
  }

  // 填充当月
  for (let d = 1; d <= daysInMonth; d++) {
    const dStr = formatDateStr(year, month, d)
    cells.push({
      dateStr: dStr,
      dayNumber: d,
      isCurrentMonth: true,
      isToday: dStr === todayStr,
      tasks: tasksByDate.value[dStr] || []
    })
  }

  // 填充下月初几天补齐至 35 或 42 格
  const totalSlots = cells.length > 35 ? 42 : 35
  const remaining = totalSlots - cells.length
  for (let d = 1; d <= remaining; d++) {
    const nextMonthIdx = month === 11 ? 0 : month + 1
    const nextYear = month === 11 ? year + 1 : year
    const dStr = formatDateStr(nextYear, nextMonthIdx, d)
    cells.push({
      dateStr: dStr,
      dayNumber: d,
      isCurrentMonth: false,
      isToday: dStr === todayStr,
      tasks: tasksByDate.value[dStr] || []
    })
  }

  return cells
})

// 拖拽事件处理
const handleDragStart = (e: DragEvent, task: TaskItem) => {
  draggingTask.value = task
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', String(task.id))
    e.dataTransfer.effectAllowed = 'move'
  }
}

const handleDragEnd = () => {
  draggingTask.value = null
  dragOverDate.value = null
}

const handleDragOver = (dateStr: string) => {
  dragOverDate.value = dateStr
}

const handleDragLeave = (dateStr: string) => {
  if (dragOverDate.value === dateStr) {
    dragOverDate.value = null
  }
}

const handleDrop = (targetDateStr: string) => {
  if (!draggingTask.value) return
  const currentVal = dateField.value === 'due_date' ? draggingTask.value.due_date : draggingTask.value.start_date
  if (currentVal !== targetDateStr) {
    emit('update-date', draggingTask.value.id, targetDateStr)
  }
  draggingTask.value = null
  dragOverDate.value = null
}
</script>

<style scoped>
.task-calendar-view {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fafbfc;
  border-bottom: 1px solid #ebeef5;
  flex-wrap: wrap;
  gap: 12px;
}

.nav-cluster {
  display: flex;
  align-items: center;
  gap: 14px;
}

.current-month-label {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  letter-spacing: 0.5px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.calendar-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: #606266;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.legend-dot.urgent { background: #f56c6c; }
.legend-dot.high { background: #e6a23c; }
.legend-dot.medium { background: #409eff; }
.legend-dot.done { background: #67c23a; }

.calendar-week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.week-day-cell {
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  border-right: 1px solid #ebeef5;
}
.week-day-cell:last-child {
  border-right: none;
}
.week-day-cell.is-weekend {
  color: #909399;
  background: #fbfbfc;
}

.calendar-grid-body {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: minmax(110px, 1fr);
}

.calendar-day-cell {
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  position: relative;
  transition: background-color 0.15s ease;
}
.calendar-day-cell:nth-child(7n) {
  border-right: none;
}

.calendar-day-cell.not-current-month {
  background: #fafafa;
  opacity: 0.55;
}

.calendar-day-cell.is-today {
  background: #f0f7ff;
}
.calendar-day-cell.is-today .day-number {
  background: #1890ff;
  color: #ffffff;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.calendar-day-cell.is-drag-over {
  background: #e6f7ff !important;
  outline: 2px dashed #1890ff;
  outline-offset: -2px;
}

.cell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.cell-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.day-number {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}

.day-count-badge {
  font-size: 10px;
  color: #909399;
  background: #f0f2f5;
  padding: 1px 5px;
  border-radius: 8px;
}

.day-quick-create-btn {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1px solid #dcdfe6;
  background: #ffffff;
  color: #409eff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  opacity: 0;
  transition: all 0.15s ease;
  line-height: 1;
  padding: 0;
}

.calendar-day-cell:hover .day-quick-create-btn {
  opacity: 1;
}

.day-quick-create-btn:hover {
  background: #409eff;
  color: #ffffff;
  border-color: #409eff;
  transform: scale(1.15);
}

.cell-tasks-scroll {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  max-height: 120px;
  padding-right: 2px;
}

.calendar-task-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border-radius: 4px;
  background: #ecf5ff;
  border-left: 3px solid #409eff;
  font-size: 11px;
  cursor: grab;
  user-select: none;
  transition: all 0.15s ease;
}
.calendar-task-bar:hover {
  filter: brightness(0.96);
  transform: translateY(-1px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.calendar-task-bar:active {
  cursor: grabbing;
}

.calendar-task-bar.urgent {
  background: #fef0f0;
  border-left-color: #f56c6c;
}
.calendar-task-bar.high {
  background: #fdf6ec;
  border-left-color: #e6a23c;
}
.calendar-task-bar.is-closed {
  background: #f0f9eb;
  border-left-color: #67c23a;
  opacity: 0.7;
}
.calendar-task-bar.is-closed .task-bar-title {
  text-decoration: line-through;
  color: #909399;
}

.calendar-task-bar.is-overdue:not(.is-closed) {
  border: 1px solid #f56c6c;
  border-left-width: 3px;
}

.task-prio-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.task-bar-code {
  font-family: monospace;
  font-size: 10px;
  color: #909399;
  flex-shrink: 0;
}

.task-bar-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
  font-weight: 500;
}

.task-bar-user {
  font-size: 10px;
  color: #909399;
  background: rgba(255, 255, 255, 0.7);
  padding: 0 3px;
  border-radius: 2px;
  flex-shrink: 0;
}
</style>
