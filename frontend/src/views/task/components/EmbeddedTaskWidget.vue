<template>
  <div class="embedded-task-widget">
    <!-- 头部工具与摘要条 -->
    <div class="widget-header">
      <div class="header-left">
        <span class="widget-title">📋 关联质量协同任务</span>
        <div class="mini-stats">
          <span class="stat-pill total">共 {{ taskList.length }} 项</span>
          <span class="stat-pill doing" v-if="inProgressCount > 0">{{ inProgressCount }} 项进行中</span>
          <span class="stat-pill done" v-if="doneCount > 0">{{ doneCount }} 项已闭环</span>
          <span class="stat-pill overdue" v-if="overdueCount > 0">⚠️ {{ overdueCount }} 项已超期</span>
        </div>
      </div>

      <div class="header-right">
        <el-radio-group v-model="statusFilter" size="small" class="mini-filter-group">
          <el-radio-button value="ALL">全部</el-radio-button>
          <el-radio-button value="ACTIVE">跟进中</el-radio-button>
          <el-radio-button value="DONE">已完成</el-radio-button>
        </el-radio-group>

        <el-button
          type="primary"
          size="small"
          :icon="Plus"
          @click="openCreateModal"
        >
          新建关联任务
        </el-button>
      </div>
    </div>

    <!-- 任务清单区域 -->
    <div v-loading="loading" class="widget-body">
      <div v-if="filteredTasks.length > 0" class="task-items-list">
        <div
          v-for="item in filteredTasks"
          :key="item.id"
          class="task-row-card"
          :class="{
            'is-done': item.status === 'DONE',
            'is-overdue': item.is_overdue
          }"
          @click="openDetailDrawer(item.id)"
        >
          <!-- 快捷状态勾选框 -->
          <div class="check-box-col" @click.stop>
            <el-checkbox
              :model-value="item.status === 'DONE'"
              @change="(checked: boolean) => handleToggleDone(item, checked)"
            />
          </div>

          <!-- 优先级徽标 -->
          <div class="priority-col">
            <el-tag
              :type="getPriorityTagType(item.priority)"
              size="small"
              effect="light"
            >
              {{ getPriorityLabel(item.priority) }}
            </el-tag>
          </div>

          <!-- 任务主体信息 -->
          <div class="main-info-col">
            <div class="task-title-row">
              <span class="task-code-badge">{{ item.task_code }}</span>
              <span class="task-title-text" :class="{ 'strike': item.status === 'DONE' }">
                {{ item.title }}
              </span>
            </div>
            <div class="task-meta-row">
              <span class="meta-item assignee">
                👤 {{ item.assignee_name || '待指派' }}
              </span>
              <span class="meta-dot">·</span>
              <span class="meta-item schedule" :class="{ 'text-danger': item.is_overdue }">
                📅 截止: {{ item.due_date || '未设' }}
                <span v-if="item.is_overdue" class="overdue-inline">已超期</span>
              </span>
              <span v-if="item.attachment_count" class="meta-item attachments">
                <span class="meta-dot">·</span>
                📎 {{ item.attachment_count }} 份附件
              </span>
            </div>
          </div>

          <!-- 状态标签与快捷操作 -->
          <div class="status-col" @click.stop>
            <el-dropdown trigger="click" @command="(cmd: any) => handleQuickStatus(item, cmd)">
              <span class="status-pill" :class="(item.status || 'TODO').toLowerCase()">
                {{ getStatusLabel(item.status) }} ▾
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
          </div>

          <!-- 操作按钮 -->
          <div class="actions-col" @click.stop>
            <el-button link type="primary" size="small" @click="openDetailDrawer(item.id)">
              详情
            </el-button>
            <el-popconfirm
              title="确定解除或删除此关联任务？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              confirm-button-type="danger"
              @confirm="handleDelete(item.id)"
            >
              <template #reference>
                <el-button link type="danger" size="small">
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state-box">
        <el-empty
          :image-size="70"
          :description="statusFilter === 'ALL' ? '当前业务对象暂无协同任务' : '无符合状态的任务'"
        >
          <el-button
            type="primary"
            plain
            size="small"
            :icon="Plus"
            @click="openCreateModal"
          >
            立即创建关联任务
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- 统一 70% 宽幅可拖拽协同任务抽屉 (兼顾查看与编辑) -->
    <TaskEditModal
      v-model="createModalVisible"
      :task="draftTask"
      @saved="handleTaskSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '@/api/task'
import type { TaskItem, TaskSourceType, TaskStatus, TaskPriority } from '@/types/task'
import TaskEditModal from '@/views/task/components/TaskEditModal.vue'

const props = defineProps<{
  sourceType: TaskSourceType
  sourceId: string | number
  sourceTitle?: string
  sourceUrl?: string
}>()

const emit = defineEmits<{
  (e: 'change', count: number): void
}>()

const loading = ref(false)
const taskList = ref<TaskItem[]>([])
const statusFilter = ref<'ALL' | 'ACTIVE' | 'DONE'>('ALL')
const createModalVisible = ref(false)
const draftTask = ref<Partial<TaskItem> | null>(null)

// 统计信息
const inProgressCount = computed(() => {
  return taskList.value.filter(t => ['TODO', 'IN_PROGRESS', 'PENDING_REVIEW'].includes(t.status)).length
})

const doneCount = computed(() => {
  return taskList.value.filter(t => t.status === 'DONE').length
})

const overdueCount = computed(() => {
  return taskList.value.filter(t => t.is_overdue && t.status !== 'DONE').length
})

// 过滤后的任务列表
const filteredTasks = computed(() => {
  if (statusFilter.value === 'ACTIVE') {
    return taskList.value.filter(t => t.status !== 'DONE')
  }
  if (statusFilter.value === 'DONE') {
    return taskList.value.filter(t => t.status === 'DONE')
  }
  return taskList.value
})

const fetchTasks = async () => {
  if (!props.sourceId) return
  try {
    loading.value = true
    const res = await taskApi.getTasksBySource(props.sourceType, props.sourceId)
    taskList.value = res || []
    emit('change', taskList.value.length)
  } catch (err: any) {
    console.error('获取关联任务失败:', err)
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.sourceType, props.sourceId],
  () => {
    fetchTasks()
  }
)

onMounted(() => {
  fetchTasks()
})

const openDetailDrawer = (id: number) => {
  const found = taskList.value.find(t => t.id === id)
  if (found) {
    draftTask.value = found
  } else {
    draftTask.value = { id } as any
  }
  createModalVisible.value = true
}

const openCreateModal = () => {
  draftTask.value = {
    source_type: props.sourceType,
    source_id: props.sourceId,
    source_title: props.sourceTitle || '',
    source_url: props.sourceUrl || '',
    priority: 'MEDIUM',
    status: 'TODO'
  }
  createModalVisible.value = true
}

const handleTaskSaved = () => {
  createModalVisible.value = false
  fetchTasks()
}

const handleToggleDone = async (item: TaskItem, checked: boolean) => {
  const newStatus: TaskStatus = checked ? 'DONE' : 'IN_PROGRESS'
  try {
    await taskApi.updateStatus(item.id, newStatus)
    item.status = newStatus
    ElMessage.success(checked ? '任务已闭环' : '任务已重新激活为跟进中')
    fetchTasks()
  } catch {
    ElMessage.error('状态更新失败')
  }
}

const handleQuickStatus = async (item: TaskItem, status: TaskStatus) => {
  try {
    await taskApi.updateStatus(item.id, status)
    item.status = status
    ElMessage.success('状态已更新')
    fetchTasks()
  } catch {
    ElMessage.error('状态更新失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await taskApi.deleteTask(id)
    ElMessage.success('任务删除成功')
    fetchTasks()
  } catch {
    ElMessage.error('删除任务失败')
  }
}

const getPriorityLabel = (p: TaskPriority) => {
  switch (p) {
    case 'URGENT': return '🔴 紧急红线'
    case 'HIGH': return '🟡 重点关注'
    case 'MEDIUM': return '🟢 普通'
    case 'LOW': return '⚪ 低'
    default: return p
  }
}

const getPriorityTagType = (p: TaskPriority) => {
  switch (p) {
    case 'URGENT': return 'danger'
    case 'HIGH': return 'warning'
    case 'MEDIUM': return 'success'
    default: return 'info'
  }
}

const getStatusLabel = (s: TaskStatus) => {
  switch (s) {
    case 'TODO': return '待办'
    case 'IN_PROGRESS': return '进行中'
    case 'PENDING_REVIEW': return '待验收'
    case 'DONE': return '已闭环'
    case 'BLOCKED': return '已阻塞'
    default: return s
  }
}

defineExpose({
  fetchTasks
})
</script>

<style scoped>
.embedded-task-widget {
  background: var(--el-bg-color, #ffffff);
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.widget-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
}

.mini-stats {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}
.stat-pill.total {
  background: #f0f2f5;
  color: #606266;
}
.stat-pill.doing {
  background: #e6f7ff;
  color: #1890ff;
}
.stat-pill.done {
  background: #f6ffed;
  color: #52c41a;
}
.stat-pill.overdue {
  background: #fff2f0;
  color: #ff4d4f;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-row-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.task-row-card:hover {
  background: #f0f7ff;
  border-color: #b3d8ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.task-row-card.is-done {
  background: #fdfdfd;
  opacity: 0.75;
}

.task-row-card.is-overdue:not(.is-done) {
  border-left: 3px solid #f56c6c;
  background: #fff9f9;
}

.check-box-col {
  display: flex;
  align-items: center;
}

.priority-col {
  flex-shrink: 0;
}

.main-info-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-code-badge {
  font-size: 11px;
  font-family: monospace;
  color: #909399;
  background: #eef1f6;
  padding: 1px 6px;
  border-radius: 4px;
}

.task-title-text {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-title-text.strike {
  text-decoration: line-through;
  color: #909399;
}

.task-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #909399;
}

.meta-dot {
  color: #dcdfe6;
}

.overdue-inline {
  color: #f56c6c;
  font-weight: bold;
  margin-left: 4px;
}

.text-danger {
  color: #f56c6c;
}

.status-col {
  flex-shrink: 0;
}

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}

.status-pill.todo {
  background: #f4f4f5;
  color: #909399;
}
.status-pill.in_progress {
  background: #ecf5ff;
  color: #409eff;
}
.status-pill.pending_review {
  background: #fdf6ec;
  color: #e6a23c;
}
.status-pill.done {
  background: #f0f9eb;
  color: #67c23a;
}
.status-pill.blocked {
  background: #fef0f0;
  color: #f56c6c;
}

.actions-col {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.empty-state-box {
  padding: 16px 0;
}
</style>
