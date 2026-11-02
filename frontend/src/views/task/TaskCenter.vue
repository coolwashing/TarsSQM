<template>
  <div class="task-center-page">
    <!-- 传送至 WorkspaceHeader 的视图切换与详细立项按钮 (信标 3 -> 信标 4，消除信标 5 & 6 重复加号) -->
    <Teleport to="#workspace-header-actions" v-if="isHeaderMounted">
      <div class="task-header-teleport-actions">
        <el-radio-group v-model="viewMode" size="small" class="view-mode-toggle">
          <el-radio-button value="grid">📋 任务总表</el-radio-button>
          <el-radio-button value="kanban">🗂️ 状态看板</el-radio-button>
          <el-radio-button value="calendar">📅 任务日历</el-radio-button>
          <el-radio-button value="dag">🕸️ 依赖拓扑</el-radio-button>
        </el-radio-group>

        <el-button
          v-if="stats.total === 0"
          size="small"
          type="warning"
          plain
          @click="handleSeedDemo"
        >
          ⚡ 预置仿真任务
        </el-button>

        <!-- 信标 5 & 6：去除重复加号，只保留加号图标与清晰文字 -->
        <el-button
          size="small"
          type="primary"
          :icon="Plus"
          @click="openCreateModal"
        >
          详细立项
        </el-button>
      </div>
    </Teleport>

    <!-- 主视图展示区 (Grid / Kanban / Calendar / DAG) -->
    <main class="task-view-container">
      <!-- 视图 A：总任务表 (集成 AI 录入、列配置、就地加行、紧凑内边距与底部状态胶囊) -->
      <div v-show="viewMode === 'grid'" class="grid-view-wrapper">
        <DataTable
          :columns="columns"
          :data="tableData"
          :loading="loading"
          :pagination="pagination"
          action-width="150px"
          storage-key="sqm_task_center_v3"
          import-key="task"
          import-title="协同待办任务"
          unique-key="task_code"
          @refresh="fetchData"
          @page-change="handlePageChange"
          @size-change="handleSizeChange"
          @cell-change="handleCellChange"
        >
          <!-- 统一紧凑检索插槽 (单行排布、不换行) -->
          <template #search>
            <div class="task-search-toolbar">
              <el-input
                v-model="filters.keyword"
                placeholder="搜索标题 / 编码 / 责任人..."
                clearable
                size="small"
                :prefix-icon="Search"
                class="search-input"
                @keyup.enter="handleSearch"
              />

              <el-select
                v-model="filters.source_type"
                placeholder="业务源头"
                clearable
                size="small"
                class="filter-select source-select"
                @change="handleSourceChange"
              >
                <el-option label="全部源头" value="ALL" />
                <el-option label="🏢 供应商" value="SUPPLIER" />
                <el-option label="⚙️ 零件" value="PART" />
                <el-option label="🎯 CTQ" value="CTQ" />
                <el-option label="📑 规程" value="DOC_KB" />
                <el-option label="📋 自建" value="CUSTOM" />
              </el-select>

              <el-select
                v-model="filters.status"
                placeholder="状态"
                clearable
                size="small"
                class="filter-select status-select"
                @change="handleSearch"
              >
                <el-option label="全部状态" value="ALL" />
                <el-option label="待办" value="TODO" />
                <el-option label="进行中" value="IN_PROGRESS" />
                <el-option label="待复核" value="PENDING_REVIEW" />
                <el-option label="已闭环" value="DONE" />
                <el-option label="已阻塞" value="BLOCKED" />
              </el-select>

              <el-select
                v-model="filters.priority"
                placeholder="优先级"
                clearable
                size="small"
                class="filter-select priority-select"
                @change="handleSearch"
              >
                <el-option label="全部优先级" value="ALL" />
                <el-option label="🔴 紧急红线" value="URGENT" />
                <el-option label="🟡 重点关注" value="HIGH" />
                <el-option label="🟢 普通" value="MEDIUM" />
                <el-option label="⚪ 低优先级" value="LOW" />
              </el-select>

              <el-select
                v-model="filters.due_filter"
                placeholder="排期"
                clearable
                size="small"
                class="filter-select due-select"
                @change="handleSearch"
              >
                <el-option label="全部排期" value="all" />
                <el-option label="今日到期" value="today" />
                <el-option label="本周到期" value="this_week" />
                <el-option label="已超期红线" value="overdue" />
              </el-select>

              <el-button type="primary" size="small" :icon="Search" class="query-btn" @click="handleSearch">
                查询
              </el-button>
              <el-tooltip content="重置检索条件" placement="top" :show-after="500">
                <el-button size="small" :icon="Refresh" circle class="reset-btn" @click="handleReset" />
              </el-tooltip>
            </div>
          </template>

          <!-- 移入底部分页栏的指标胶囊群 (信标 7 ~ 11 -> 信标 13) -->
          <template #footer-left>
            <div class="task-footer-stats">
              <div
                class="stat-pill total"
                :class="{ 'is-active': filters.status === 'ALL' && filters.due_filter === 'all' }"
                @click="quickFilterByStatus('ALL')"
                title="全部任务池"
              >
                <span class="stat-num">{{ stats.total }}</span>
                <span class="stat-label">总任务池</span>
              </div>
              <div
                class="stat-pill todo"
                :class="{ 'is-active': filters.status === 'TODO' }"
                @click="quickFilterByStatus('TODO')"
                title="过滤待办"
              >
                <span class="stat-num">{{ stats.todo }}</span>
                <span class="stat-label">待办任务</span>
              </div>
              <div
                class="stat-pill in-progress"
                :class="{ 'is-active': filters.status === 'IN_PROGRESS' }"
                @click="quickFilterByStatus('IN_PROGRESS')"
                title="过滤进行中"
              >
                <span class="stat-num">{{ stats.in_progress }}</span>
                <span class="stat-label">进行中</span>
              </div>
              <div
                class="stat-pill pending-review"
                :class="{ 'is-active': filters.status === 'PENDING_REVIEW' }"
                @click="quickFilterByStatus('PENDING_REVIEW')"
                title="过滤待验收"
              >
                <span class="stat-num">{{ stats.pending_review }}</span>
                <span class="stat-label">待验收</span>
              </div>
              <div
                class="stat-pill done"
                :class="{ 'is-active': filters.status === 'DONE' }"
                @click="quickFilterByStatus('DONE')"
                title="过滤已闭环"
              >
                <span class="stat-num">{{ stats.done }}</span>
                <span class="stat-label">已闭环</span>
              </div>
              <div
                v-if="stats.overdue > 0"
                class="stat-pill overdue"
                :class="{ 'is-active': filters.due_filter === 'overdue' }"
                @click="quickFilterDue('overdue')"
                title="过滤已超期红线"
              >
                <span class="stat-num">{{ stats.overdue }}</span>
                <span class="stat-label">⚠️ 已超期</span>
              </div>
            </div>
          </template>
          <!-- 任务标题列插槽 (可直接点击呼出侧拉抽屉) -->
          <template #title="{ row }">
            <div class="task-title-cell" @click="openEditModal(row)">
              <span class="task-title-text" :title="row.title">{{ row.title }}</span>
              <el-tag v-if="row.is_overdue" size="small" type="danger" effect="dark" class="mini-tag">
                超期
              </el-tag>
            </div>
          </template>

          <!-- 业务源头列插槽 (带徽标与一键直跳原业务路由) -->
          <template #source="{ row }">
            <div class="source-cell">
              <span class="source-icon">{{ getSourceIcon(row.source_type) }}</span>
              <span
                v-if="row.source_url"
                class="source-link"
                :title="`直跳: ${row.source_title || '详情'}`"
                @click.stop="jumpToSource(row.source_url)"
              >
                {{ row.source_title || getSourceName(row.source_type) }}
              </span>
              <span v-else class="source-plain">
                {{ row.source_title || getSourceName(row.source_type) }}
              </span>
            </div>
          </template>

          <!-- 优先级列插槽 -->
          <template #priority="{ row }">
            <el-tag :type="getPriorityTagType(row.priority)" size="small" effect="light">
              {{ getPriorityLabel(row.priority) }}
            </el-tag>
          </template>

          <!-- 计划起止列插槽 -->
          <template #schedule="{ row }">
            <div class="schedule-cell" :class="{ 'is-overdue': row.is_overdue }">
              <span>{{ row.due_date || '未设止期' }}</span>
            </div>
          </template>

          <!-- 状态列插槽 (支持就地下拉快速流转) -->
          <template #status="{ row }">
            <el-dropdown v-if="row" trigger="click" @command="(cmd: any) => handleQuickStatusChange(row, cmd)">
              <span class="status-dropdown-pill" :class="(row.status || 'TODO').toLowerCase()">
                {{ getStatusLabel(row.status || 'TODO') }} ▾
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="TODO">待办</el-dropdown-item>
                  <el-dropdown-item command="IN_PROGRESS">进行中</el-dropdown-item>
                  <el-dropdown-item command="PENDING_REVIEW">待复核</el-dropdown-item>
                  <el-dropdown-item command="DONE">已闭环</el-dropdown-item>
                  <el-dropdown-item command="BLOCKED" divided>已阻塞</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>

          <!-- 附件数列插槽 -->
          <template #attachment_count="{ row }">
            <span v-if="row.attachment_count" class="att-count-badge">
              📎 {{ row.attachment_count }}
            </span>
            <span v-else class="text-dim">-</span>
          </template>

          <!-- 操作列插槽 -->
          <template #action="{ row }">
            <el-button link type="primary" size="small" @click="openEditModal(row)">
              编辑详情
            </el-button>
            <el-popconfirm
              title="确定删除此协同任务？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="handleDeleteTask(row.id)"
            >
              <template #reference>
                <el-button link type="danger" size="small">
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>

          <!-- 飞书多维表格风格：表格行底极速行内录入插槽 -->
          <template #append>
            <div class="feishu-table-append-zone">
              <!-- 未激活态：飞书多维表格经典底栏 "+ 添加新任务" -->
              <div
                v-if="!isAddingInlineRow"
                class="feishu-add-row-placeholder"
                tabindex="0"
                @click="startInlineAdd"
                @keydown.enter="startInlineAdd"
              >
                <div class="add-btn-inner">
                  <el-icon class="add-icon"><Plus /></el-icon>
                  <span class="add-title">添加新任务</span>
                  <span class="add-tip">点击或按回车快速加行，支持连续录入</span>
                </div>
              </div>

              <!-- 激活态：行内直接录入行 (完全融入表格网格与各列) -->
              <div
                v-else
                class="feishu-inline-editor-row"
                @keyup.esc="cancelInlineAdd"
              >
                <div class="inline-cell cell-code">
                  <span class="new-row-badge">+ 新行</span>
                </div>

                <div class="inline-cell cell-title">
                  <el-input
                    ref="inlineTitleInputRef"
                    v-model="quickRow.title"
                    placeholder="输入新任务标题，按回车立即创建并自动开启下一行..."
                    size="small"
                    clearable
                    @keyup.enter="handleAutoAddRow"
                  >
                    <template #suffix>
                      <span class="enter-badge" title="回车即刻自动创建下一行">Enter ↵</span>
                    </template>
                  </el-input>
                </div>

                <div class="inline-cell cell-source">
                  <el-select
                    v-model="quickRow.source_type"
                    placeholder="业务源头"
                    size="small"
                    class="inline-select"
                  >
                    <el-option label="📋 协同待办" value="CUSTOM" />
                    <el-option label="🏢 供应商" value="SUPPLIER" />
                    <el-option label="⚙️ 零件试产" value="PART" />
                    <el-option label="🎯 CTQ 特性" value="CTQ" />
                    <el-option label="📑 规程知识" value="DOC_KB" />
                  </el-select>
                </div>

                <div class="inline-cell cell-priority">
                  <el-select
                    v-model="quickRow.priority"
                    placeholder="优先级"
                    size="small"
                    class="inline-select"
                  >
                    <el-option label="🟢 普通" value="MEDIUM" />
                    <el-option label="🟡 重点关注" value="HIGH" />
                    <el-option label="🔴 紧急红线" value="URGENT" />
                    <el-option label="⚪ 低" value="LOW" />
                  </el-select>
                </div>

                <div class="inline-cell cell-assignee">
                  <el-input
                    v-model="quickRow.assignee_name"
                    placeholder="责任人"
                    size="small"
                    class="inline-input"
                    @keyup.enter="handleAutoAddRow"
                  />
                </div>

                <div class="inline-cell cell-due">
                  <el-date-picker
                    v-model="quickRow.due_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                    placeholder="截止日期"
                    size="small"
                    class="inline-date-picker"
                  />
                </div>

                <div class="inline-cell cell-actions">
                  <el-button
                    type="primary"
                    size="small"
                    :loading="quickAdding"
                    class="save-btn"
                    @click="handleAutoAddRow"
                  >
                    保存 ↵
                  </el-button>
                  <el-button
                    size="small"
                    class="cancel-btn"
                    @click="cancelInlineAdd"
                  >
                    收起
                  </el-button>
                </div>
              </div>
            </div>
          </template>
        </DataTable>
      </div>

      <!-- 视图 B：敏捷泳道看板 (Kanban) - 支持 HTML5 平滑跨列拖拽 -->
      <div v-show="viewMode === 'kanban'" class="kanban-view-wrapper">
        <div class="kanban-lane-board">
          <!-- 泳道 1: 待办 -->
          <div
            class="kanban-column todo"
            :class="{ 'lane-drag-over': dragOverLane === 'TODO' }"
            @dragover.prevent="dragOverLane = 'TODO'"
            @dragleave="handleLaneDragLeave('TODO')"
            @drop="handleLaneDrop('TODO')"
          >
            <div class="lane-header">
              <div class="lane-title-box">
                <span class="lane-dot"></span>
                <span class="lane-title">待办事项</span>
              </div>
              <span class="lane-count">{{ kanbanTasks.todo.length }}</span>
            </div>
            <div class="lane-cards-scroll">
              <div
                v-for="item in kanbanTasks.todo"
                :key="item.id"
                class="kanban-task-card"
                draggable="true"
                @dragstart="handleKanbanDragStart($event, item)"
                @dragend="handleKanbanDragEnd"
                @click="openEditModal(item)"
              >
                <div class="card-top-row">
                  <span class="card-code">{{ item.task_code }}</span>
                  <el-tag :type="getPriorityTagType(item.priority)" size="small">
                    {{ getPriorityLabel(item.priority) }}
                  </el-tag>
                </div>
                <div class="card-title">{{ item.title }}</div>
                <div class="card-source-tag">
                  {{ getSourceIcon(item.source_type) }} {{ item.source_title || getSourceName(item.source_type) }}
                </div>
                <div class="card-footer-row">
                  <span class="card-assignee">👤 {{ item.assignee_name || '待指派' }}</span>
                  <span class="card-due" :class="{ 'is-overdue': item.is_overdue }">
                    📅 {{ item.due_date || '无止期' }}
                  </span>
                </div>
                <div class="card-actions-quick" @click.stop>
                  <button type="button" class="lane-move-btn" @click="handleQuickStatusChange(item, 'IN_PROGRESS')">
                    开始跟进 ➔
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 泳道 2: 进行中 -->
          <div
            class="kanban-column in-progress"
            :class="{ 'lane-drag-over': dragOverLane === 'IN_PROGRESS' }"
            @dragover.prevent="dragOverLane = 'IN_PROGRESS'"
            @dragleave="handleLaneDragLeave('IN_PROGRESS')"
            @drop="handleLaneDrop('IN_PROGRESS')"
          >
            <div class="lane-header">
              <div class="lane-title-box">
                <span class="lane-dot"></span>
                <span class="lane-title">进行中</span>
              </div>
              <span class="lane-count">{{ kanbanTasks.inProgress.length }}</span>
            </div>
            <div class="lane-cards-scroll">
              <div
                v-for="item in kanbanTasks.inProgress"
                :key="item.id"
                class="kanban-task-card"
                draggable="true"
                @dragstart="handleKanbanDragStart($event, item)"
                @dragend="handleKanbanDragEnd"
                @click="openEditModal(item)"
              >
                <div class="card-top-row">
                  <span class="card-code">{{ item.task_code }}</span>
                  <el-tag :type="getPriorityTagType(item.priority)" size="small">
                    {{ getPriorityLabel(item.priority) }}
                  </el-tag>
                </div>
                <div class="card-title">{{ item.title }}</div>
                <div class="card-source-tag">
                  {{ getSourceIcon(item.source_type) }} {{ item.source_title || getSourceName(item.source_type) }}
                </div>
                <div class="card-footer-row">
                  <span class="card-assignee">👤 {{ item.assignee_name || '待指派' }}</span>
                  <span class="card-due" :class="{ 'is-overdue': item.is_overdue }">
                    📅 {{ item.due_date || '无止期' }}
                  </span>
                </div>
                <div class="card-actions-quick" @click.stop>
                  <button type="button" class="lane-move-btn" @click="handleQuickStatusChange(item, 'PENDING_REVIEW')">
                    提检验收 ➔
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 泳道 3: 待验收 -->
          <div
            class="kanban-column pending-review"
            :class="{ 'lane-drag-over': dragOverLane === 'PENDING_REVIEW' }"
            @dragover.prevent="dragOverLane = 'PENDING_REVIEW'"
            @dragleave="handleLaneDragLeave('PENDING_REVIEW')"
            @drop="handleLaneDrop('PENDING_REVIEW')"
          >
            <div class="lane-header">
              <div class="lane-title-box">
                <span class="lane-dot"></span>
                <span class="lane-title">待复核验收</span>
              </div>
              <span class="lane-count">{{ kanbanTasks.pendingReview.length }}</span>
            </div>
            <div class="lane-cards-scroll">
              <div
                v-for="item in kanbanTasks.pendingReview"
                :key="item.id"
                class="kanban-task-card"
                draggable="true"
                @dragstart="handleKanbanDragStart($event, item)"
                @dragend="handleKanbanDragEnd"
                @click="openEditModal(item)"
              >
                <div class="card-top-row">
                  <span class="card-code">{{ item.task_code }}</span>
                  <el-tag :type="getPriorityTagType(item.priority)" size="small">
                    {{ getPriorityLabel(item.priority) }}
                  </el-tag>
                </div>
                <div class="card-title">{{ item.title }}</div>
                <div class="card-source-tag">
                  {{ getSourceIcon(item.source_type) }} {{ item.source_title || getSourceName(item.source_type) }}
                </div>
                <div class="card-footer-row">
                  <span class="card-assignee">👤 {{ item.assignee_name || '待指派' }}</span>
                  <span class="card-due" :class="{ 'is-overdue': item.is_overdue }">
                    📅 {{ item.due_date || '无止期' }}
                  </span>
                </div>
                <div class="card-actions-quick" @click.stop>
                  <button type="button" class="lane-move-btn success" @click="handleQuickStatusChange(item, 'DONE')">
                    验收闭环 ✓
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 泳道 4: 已闭环 -->
          <div
            class="kanban-column done"
            :class="{ 'lane-drag-over': dragOverLane === 'DONE' }"
            @dragover.prevent="dragOverLane = 'DONE'"
            @dragleave="handleLaneDragLeave('DONE')"
            @drop="handleLaneDrop('DONE')"
          >
            <div class="lane-header">
              <div class="lane-title-box">
                <span class="lane-dot"></span>
                <span class="lane-title">已闭环</span>
              </div>
              <span class="lane-count">{{ kanbanTasks.done.length }}</span>
            </div>
            <div class="lane-cards-scroll">
              <div
                v-for="item in kanbanTasks.done"
                :key="item.id"
                class="kanban-task-card is-completed"
                draggable="true"
                @dragstart="handleKanbanDragStart($event, item)"
                @dragend="handleKanbanDragEnd"
                @click="openEditModal(item)"
              >
                <div class="card-top-row">
                  <span class="card-code">{{ item.task_code }}</span>
                  <span class="done-tag">✓ 已闭环</span>
                </div>
                <div class="card-title strike">{{ item.title }}</div>
                <div class="card-footer-row">
                  <span class="card-assignee">👤 {{ item.assignee_name || '无' }}</span>
                  <span class="card-done-time">已归档</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 视图 C：任务日历排期 (Calendar) -->
      <div v-if="viewMode === 'calendar'" class="calendar-view-wrapper">
        <TaskCalendarView
          :tasks="allTasksList"
          @open-detail="openDetailDrawer"
          @update-date="handleCalendarDateUpdate"
          @create-on-date="handleCalendarCreateOnDate"
        />
      </div>

      <!-- 视图 D：质量拓扑依赖图 (DAG) -->
      <div v-if="viewMode === 'dag'" class="dag-view-wrapper">
        <TaskTopologyView
          :tasks="allTasksList"
          @open-detail="openDetailDrawer"
        />
      </div>
    </main>

    <!-- 4. 统一 70% 宽幅可拖拽协同任务抽屉 (兼顾查看与编辑，无多余冗余弹窗) -->
    <TaskEditModal
      v-if="editModalMounted"
      v-model="editModalVisible"
      :task="editingTask"
      @saved="fetchData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onActivated, onDeactivated, nextTick, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import { taskApi } from '@/api/task'
import type { TaskItem, TaskSummaryStats, TaskStatus, TaskPriority, TaskSourceType } from '@/types/task'

const TaskEditModal = defineAsyncComponent(() => import('./components/TaskEditModal.vue'))
const TaskCalendarView = defineAsyncComponent(() => import('./components/TaskCalendarView.vue'))
const TaskTopologyView = defineAsyncComponent(() => import('./components/TaskTopologyView.vue'))

const router = useRouter()

const viewMode = ref<'grid' | 'kanban' | 'calendar' | 'dag'>('grid')
const isHeaderMounted = ref(false)
const loading = ref(false)
const tableData = ref<TaskItem[]>([])
const allTasksList = ref<TaskItem[]>([])

// 快捷自动加行状态 (飞书多维表格风格：默认就绪于最后一行底部)
const isAddingInlineRow = ref(true)
const inlineTitleInputRef = ref<any>(null)
const quickAdding = ref(false)
const quickRow = reactive({
  title: '',
  source_type: 'CUSTOM' as TaskSourceType,
  assignee_name: '',
  due_date: null as string | null,
  priority: 'MEDIUM' as TaskPriority,
  status: 'TODO' as TaskStatus
})

const startInlineAdd = () => {
  isAddingInlineRow.value = true
  nextTick(() => {
    inlineTitleInputRef.value?.focus()
  })
}

const cancelInlineAdd = () => {
  isAddingInlineRow.value = false
  quickRow.title = ''
}

// 看板拖拽状态
const draggingKanbanTask = ref<TaskItem | null>(null)
const dragOverLane = ref<TaskStatus | null>(null)

const stats = reactive<TaskSummaryStats>({
  total: 0,
  todo: 0,
  in_progress: 0,
  pending_review: 0,
  done: 0,
  blocked: 0,
  overdue: 0
})

const filters = reactive({
  keyword: '',
  source_type: 'ALL',
  status: 'ALL',
  priority: 'ALL',
  due_filter: 'all'
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 抽屉与弹窗状态 (懒加载挂载，首次点击前 0 内存开销)
const detailDrawerVisible = ref(false)
const activeTaskId = ref<number | null>(null)
const editModalMounted = ref(false)
const editModalVisible = ref(false)
const editingTask = ref<Partial<TaskItem> | null>(null)

// 列定义配置 (支持双击快编与防御性排版)
const columns: TableColumn[] = [
  { prop: 'task_code', label: '流水编号', width: '135px', sortable: true },
  { prop: 'title', label: '任务标题 / 验收主题', minWidth: '220px', sortable: true, editable: true },
  { prop: 'source', label: '业务源头', minWidth: '180px' },
  {
    prop: 'priority',
    label: '优先级',
    width: '110px',
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    editOptions: [
      { label: '🔴 紧急红线', value: 'URGENT' },
      { label: '🟡 重点关注', value: 'HIGH' },
      { label: '🟢 普通', value: 'MEDIUM' },
      { label: '⚪ 低', value: 'LOW' }
    ]
  },
  { prop: 'assignee_name', label: '责任人', width: '120px', sortable: true, editable: true },
  { prop: 'schedule', label: '计划截止日', width: '130px', align: 'center', sortable: true },
  { prop: 'status', label: '流转状态', width: '120px', align: 'center' },
  { prop: 'attachment_count', label: '附件', width: '75px', align: 'center' }
]

// 看板分类计算
const kanbanTasks = computed(() => {
  return {
    todo: allTasksList.value.filter(t => t.status === 'TODO'),
    inProgress: allTasksList.value.filter(t => t.status === 'IN_PROGRESS'),
    pendingReview: allTasksList.value.filter(t => t.status === 'PENDING_REVIEW'),
    done: allTasksList.value.filter(t => t.status === 'DONE' || t.status === 'BLOCKED')
  }
})

// 加载数据
const fetchData = async () => {
  try {
    loading.value = true
    const queryParams = {
      keyword: filters.keyword,
      source_type: filters.source_type,
      status: filters.status,
      priority: filters.priority,
      due_filter: filters.due_filter as any,
      page: pagination.page,
      page_size: pagination.pageSize
    }
    console.log('[TaskCenter] fetching tasks with queryParams:', queryParams)

    const [statsRes, listRes] = await Promise.all([
      taskApi.getStats(),
      taskApi.listTasks(queryParams)
    ])

    console.log('[TaskCenter] statsRes:', statsRes, 'listRes:', listRes)

    Object.assign(stats, statsRes)
    tableData.value = listRes?.items || []
    pagination.total = listRes?.total || 0

    console.log('[TaskCenter] after assignment, tableData count:', tableData.value.length, 'pagination.total:', pagination.total)

    // 同时拉取全部列表填充看板 (上限 200)
    const allRes = await taskApi.listTasks({
      source_type: filters.source_type,
      priority: filters.priority,
      page: 1,
      page_size: 200
    })
    allTasksList.value = allRes.items
  } catch (err: any) {
    ElMessage.error(`加载任务列表异常: ${err.message || '服务响应失败'}`)
  } finally {
    loading.value = false
  }
}

const checkHeaderTarget = () => {
  if (typeof document !== 'undefined' && document.getElementById('workspace-header-actions')) {
    isHeaderMounted.value = true
  }
}

onMounted(() => {
  fetchData()
  checkHeaderTarget()
  nextTick(checkHeaderTarget)
  setTimeout(checkHeaderTarget, 100)
  setTimeout(checkHeaderTarget, 300)
})

onActivated(() => {
  checkHeaderTarget()
  nextTick(checkHeaderTarget)
  setTimeout(checkHeaderTarget, 100)
})

onDeactivated(() => {
  isHeaderMounted.value = false
})

// 就地单元格编辑保存 (双击/回车修改后静默持久化，符合 data-table.md)
const handleCellChange = async (event: CellChangeEvent) => {
  const { row, prop, value, oldValue } = event
  try {
    if (prop === 'status') {
      await taskApi.updateStatus(row.id, value)
    } else {
      await taskApi.updateTask(row.id, { [prop]: value })
    }
    row[prop] = value
    const statsRes = await taskApi.getStats()
    Object.assign(stats, statsRes)
  } catch (err: any) {
    row[prop] = oldValue
    ElMessage.error(`任务属性修改失败: ${err.message || '请检查输入'}`)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  filters.keyword = ''
  filters.source_type = 'ALL'
  filters.status = 'ALL'
  filters.priority = 'ALL'
  filters.due_filter = 'all'
  pagination.page = 1
  fetchData()
}

const handleSourceChange = () => {
  if (filters.source_type && filters.source_type !== 'ALL') {
    quickRow.source_type = filters.source_type as TaskSourceType
  }
  handleSearch()
}

const setSourceType = (type: string) => {
  filters.source_type = type
  handleSourceChange()
}

const quickFilterByStatus = (statusStr: string) => {
  filters.status = statusStr
  filters.due_filter = 'all'
  pagination.page = 1
  fetchData()
}

const quickFilterDue = (dueStr: string) => {
  filters.due_filter = dueStr
  pagination.page = 1
  fetchData()
}

const handlePageChange = (p: number) => {
  pagination.page = p
  fetchData()
}

const handleSizeChange = (s: number) => {
  pagination.pageSize = s
  pagination.page = 1
  fetchData()
}

// 快速状态变更
const handleQuickStatusChange = async (row: TaskItem, newStatus: TaskStatus) => {
  try {
    await taskApi.updateStatus(row.id, newStatus)
    ElMessage.success(`任务 ${row.task_code} 状态已流转`)
    fetchData()
  } catch {
    ElMessage.error('状态变更失败')
  }
}

// 看板拖拽流转交互
const handleKanbanDragStart = (e: DragEvent, item: TaskItem) => {
  draggingKanbanTask.value = item
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', String(item.id))
    e.dataTransfer.effectAllowed = 'move'
  }
}

const handleKanbanDragEnd = () => {
  draggingKanbanTask.value = null
  dragOverLane.value = null
}

const handleLaneDragLeave = (status: TaskStatus) => {
  if (dragOverLane.value === status) {
    dragOverLane.value = null
  }
}

const handleLaneDrop = async (targetStatus: TaskStatus) => {
  if (!draggingKanbanTask.value) return
  if (draggingKanbanTask.value.status !== targetStatus) {
    try {
      await taskApi.updateStatus(draggingKanbanTask.value.id, targetStatus)
      ElMessage.success(`任务 ${draggingKanbanTask.value.task_code} 状态已流转至【${getStatusLabel(targetStatus)}】`)
      fetchData()
    } catch {
      ElMessage.error('状态流转失败')
    }
  }
  draggingKanbanTask.value = null
  dragOverLane.value = null
}

// 日历拖拽改期交互
const handleCalendarDateUpdate = async (id: number, dateStr: string) => {
  try {
    await taskApi.updateDates(id, { due_date: dateStr })
    ElMessage.success(`任务计划截止日已调整至 ${dateStr}`)
    fetchData()
  } catch {
    ElMessage.error('更新排期失败')
  }
}

// 快速自动加行处理 (回车即刻自动生成并就绪下一行，实现飞书多维表格行底连续录入体验)
const handleAutoAddRow = async () => {
  const title = quickRow.title.trim()
  if (!title) {
    ElMessage.warning('请输入任务标题')
    inlineTitleInputRef.value?.focus()
    return
  }

  try {
    quickAdding.value = true
    await taskApi.createTask({
      title,
      source_type: quickRow.source_type,
      assignee_name: quickRow.assignee_name.trim() || undefined,
      due_date: quickRow.due_date || undefined,
      priority: quickRow.priority,
      status: quickRow.status || 'TODO'
    })
    ElMessage.success('已新建任务，自动就绪下一行')
    quickRow.title = ''
    await fetchData()
    // 保持行底激活态并再次自动对焦输入框，支持像飞书一样连续回车极速加行
    isAddingInlineRow.value = true
    nextTick(() => {
      inlineTitleInputRef.value?.focus()
    })
  } catch (err: any) {
    ElMessage.error(`添加行失败: ${err.message || '网络异常'}`)
  } finally {
    quickAdding.value = false
  }
}

// 日历网格点击直接创建任务
const handleCalendarCreateOnDate = (dateStr: string) => {
  editingTask.value = {
    due_date: dateStr,
    priority: 'MEDIUM',
    status: 'TODO',
    source_type: 'CUSTOM'
  }
  editModalVisible.value = true
}



// 删除任务
const handleDeleteTask = async (id: number) => {
  try {
    await taskApi.deleteTask(id)
    ElMessage.success('任务已成功删除')
    fetchData()
  } catch {
    ElMessage.error('删除失败')
  }
}

// 统一的弹窗与抽屉控制 (合并详情与编辑为单一 70% 可拖拽抽屉)
const openDetailDrawer = (id: number) => {
  const found = allTasksList.value.find(t => t.id === id) || tableData.value.find(t => t.id === id)
  if (found) {
    openEditModal(found)
  } else {
    taskApi.getTask(id).then(t => openEditModal(t)).catch(() => {
      openEditModal({ id } as any)
    })
  }
}

const openCreateModal = () => {
  editingTask.value = null
  editModalMounted.value = true
  editModalVisible.value = true
}

const openEditModal = (row: TaskItem) => {
  editingTask.value = row
  editModalMounted.value = true
  editModalVisible.value = true
}

// 预置演示数据
const handleSeedDemo = async () => {
  try {
    loading.value = true
    await taskApi.seedDemoTasks()
    ElMessage.success('已预置 5 条制造质量协同仿真任务')
    fetchData()
  } catch {
    ElMessage.error('预置失败')
  } finally {
    loading.value = false
  }
}

const jumpToSource = (url: string) => {
  router.push(url)
}

// 标签与图标工具
const getSourceIcon = (type: string) => {
  const map: Record<string, string> = {
    SUPPLIER: '🏢',
    PART: '⚙️',
    CTQ: '🎯',
    DOC_KB: '📑',
    CUSTOM: '📋'
  }
  return map[type] || '📌'
}

const getSourceName = (type: string) => {
  const map: Record<string, string> = {
    SUPPLIER: '供应商',
    PART: '零件试产',
    CTQ: 'CTQ特性',
    DOC_KB: '规程文档',
    CUSTOM: '自建待办'
  }
  return map[type] || type
}

const getStatusLabel = (s: string) => {
  const map: Record<string, string> = {
    TODO: '待办',
    IN_PROGRESS: '进行中',
    PENDING_REVIEW: '待验收',
    DONE: '已闭环',
    BLOCKED: '阻塞'
  }
  return map[s] || s
}

const getPriorityLabel = (p: string) => {
  const map: Record<string, string> = {
    URGENT: 'CTQ红线',
    HIGH: '重点关注',
    MEDIUM: '普通',
    LOW: '低'
  }
  return map[p] || p
}

const getPriorityTagType = (p: string) => {
  if (p === 'URGENT') return 'danger'
  if (p === 'HIGH') return 'warning'
  if (p === 'MEDIUM') return 'primary'
  return 'info'
}
</script>

<style scoped>
.task-center-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: transparent;
  overflow: hidden;
  padding: 0;
  gap: 0;
}

.task-header-teleport-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 顶部检索栏 (嵌入 DataTable #search 插槽内，单行紧凑排布) */
.task-search-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.task-search-toolbar .search-input {
  width: 165px;
}

.task-search-toolbar .filter-select {
  width: 90px;
}

.task-search-toolbar .filter-select.source-select {
  width: 105px;
}

.task-search-toolbar .filter-select.priority-select {
  width: 95px;
}

.task-search-toolbar .filter-select.due-select {
  width: 95px;
}

.task-search-toolbar .query-btn,
.task-search-toolbar .reset-btn {
  flex-shrink: 0;
}

/* 底部状态胶囊指标群 (嵌入 DataTable #footer-left 插槽内，单行水平紧凑排布，杜绝垂直折叠) */
.task-footer-stats {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap !important;
  white-space: nowrap !important;
  flex-shrink: 0;
}

.task-footer-stats .stat-pill {
  display: inline-flex !important;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
  line-height: 1.2;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
}

.task-footer-stats .stat-pill:hover {
  transform: translateY(-1px);
  filter: brightness(0.95);
}

.task-footer-stats .stat-pill.is-active {
  box-shadow: 0 0 0 1.5px currentColor;
  font-weight: 700;
}

.task-footer-stats .stat-pill .stat-num {
  font-weight: 700;
}

.task-footer-stats .stat-pill .stat-label {
  font-size: 11px;
}

.task-footer-stats .stat-pill.total {
  background: #f1f5f9;
  color: #334155;
}
.task-footer-stats .stat-pill.todo {
  background: #eff6ff;
  color: #2563eb;
}
.task-footer-stats .stat-pill.in-progress {
  background: #fffbeb;
  color: #d97706;
}
.task-footer-stats .stat-pill.pending-review {
  background: #faf5ff;
  color: #9333ea;
}
.task-footer-stats .stat-pill.done {
  background: #f0fdf4;
  color: #16a34a;
}
.task-footer-stats .stat-pill.overdue {
  background: #fef2f2;
  color: #dc2626;
  font-weight: 600;
}

/* 主内容视图容器与 Grid 包装器 */
.task-view-container {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.grid-view-wrapper {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

/* Grid 单元格定制 */
.task-title-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.task-title-text {
  font-weight: 600;
  color: #0f172a;
  transition: color 0.12s ease;
}
.task-title-cell:hover .task-title-text {
  color: #2563eb;
}
.mini-tag {
  font-size: 10px;
  height: 18px;
  padding: 0 4px;
}

.source-cell {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}
.source-link {
  color: #2563eb;
  cursor: pointer;
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.source-link:hover {
  color: #1d4ed8;
}
.source-plain {
  color: #334155;
}

.schedule-cell {
  font-size: 12px;
  color: #475569;
}
.schedule-cell.is-overdue {
  color: #ef4444;
  font-weight: 600;
}

.status-dropdown-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}
.status-dropdown-pill.todo {
  background: #eff6ff;
  color: #2563eb;
}
.status-dropdown-pill.in_progress {
  background: #fffbeb;
  color: #d97706;
}
.status-dropdown-pill.pending_review {
  background: #faf5ff;
  color: #9333ea;
}
.status-dropdown-pill.done {
  background: #f0fdf4;
  color: #16a34a;
}
.status-dropdown-pill.blocked {
  background: #fef2f2;
  color: #dc2626;
}

.att-count-badge {
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 10px;
}

/* 看板模式 */
.kanban-view-wrapper {
  flex: 1;
  min-height: 0;
  padding: 14px;
  overflow-x: auto;
  overflow-y: hidden;
  background: #f8fafc;
}

.kanban-lane-board {
  display: flex;
  gap: 14px;
  height: 100%;
}

.kanban-column {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.lane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
}
.lane-title-box {
  display: flex;
  align-items: center;
  gap: 6px;
}
.lane-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}
.kanban-column.todo .lane-dot { background: #3b82f6; }
.kanban-column.in-progress .lane-dot { background: #f59e0b; }
.kanban-column.pending-review .lane-dot { background: #a855f7; }
.kanban-column.done .lane-dot { background: #10b981; }

.lane-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.lane-count {
  font-size: 11px;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
  padding: 1px 6px;
  border-radius: 10px;
}

.lane-cards-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kanban-task-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: all 0.12s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.kanban-task-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
  transform: translateY(-1px);
}
.kanban-task-card.is-completed {
  opacity: 0.7;
}

.card-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-code {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}
.done-tag {
  font-size: 10px;
  font-weight: bold;
  color: #16a34a;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
}
.card-title.strike {
  text-decoration: line-through;
  color: #64748b;
}

.card-source-tag {
  font-size: 11px;
  color: #475569;
  background: #f8fafc;
  padding: 2px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed #f1f5f9;
}
.card-due.is-overdue {
  color: #ef4444;
  font-weight: bold;
}

.card-actions-quick {
  display: flex;
  justify-content: flex-end;
  margin-top: 2px;
}
.lane-move-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  color: #2563eb;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  cursor: pointer;
  transition: all 0.12s ease;
}
.lane-move-btn:hover {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}
.lane-move-btn.success {
  color: #16a34a;
}
.lane-move-btn.success:hover {
  background: #16a34a;
  color: #ffffff;
  border-color: #16a34a;
}

.kanban-column.lane-drag-over {
  outline: 2px dashed #3b82f6 !important;
  outline-offset: -2px;
  background: #eff6ff !important;
}

.calendar-view-wrapper,
.dag-view-wrapper {
  margin-top: 4px;
}

/* 飞书多维表格风格：表格底部行内极速录入区 */
.feishu-table-append-zone {
  width: 100%;
  border-top: 1px solid var(--el-border-color-lighter, #ebeef5);
  background: #ffffff;
}

.feishu-add-row-placeholder {
  display: flex;
  align-items: center;
  height: 42px;
  padding: 0 16px;
  cursor: pointer;
  user-select: none;
  color: #64748b;
  font-size: 13px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.feishu-add-row-placeholder:hover,
.feishu-add-row-placeholder:focus-visible {
  background: #f0f7ff;
  color: #2563eb;
}

.add-btn-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.add-btn-inner .add-icon {
  font-size: 14px;
  font-weight: 700;
  transition: transform 0.2s ease;
}

.feishu-add-row-placeholder:hover .add-icon {
  transform: rotate(90deg) scale(1.1);
}

.add-btn-inner .add-title {
  font-weight: 500;
}

.add-btn-inner .add-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 8px;
}

/* 激活态：行内直接录入行 */
.feishu-inline-editor-row {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 6px 12px;
  gap: 8px;
  background: #f8fafc;
  border-left: 3px solid #2563eb;
  animation: feishuFadeIn 0.18s cubic-bezier(0, 0, 0.2, 1);
}

@keyframes feishuFadeIn {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feishu-inline-editor-row .inline-cell {
  display: flex;
  align-items: center;
}

.feishu-inline-editor-row .cell-code {
  width: 75px;
  flex-shrink: 0;
  justify-content: center;
}

.new-row-badge {
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
}

.feishu-inline-editor-row .cell-title {
  flex: 1;
  min-width: 240px;
}

.feishu-inline-editor-row .cell-source {
  width: 130px;
  flex-shrink: 0;
}

.feishu-inline-editor-row .cell-priority {
  width: 115px;
  flex-shrink: 0;
}

.feishu-inline-editor-row .cell-assignee {
  width: 100px;
  flex-shrink: 0;
}

.feishu-inline-editor-row .cell-due {
  width: 135px;
  flex-shrink: 0;
}

.feishu-inline-editor-row .cell-actions {
  width: 125px;
  flex-shrink: 0;
  display: flex;
  gap: 6px;
}

.enter-badge {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  font-family: inherit;
  user-select: none;
}

.feishu-inline-editor-row .save-btn {
  font-weight: 500;
}

.feishu-inline-editor-row .cancel-btn {
  color: #64748b;
}
.feishu-inline-editor-row .cancel-btn:hover {
  color: #0f172a;
}
</style>
