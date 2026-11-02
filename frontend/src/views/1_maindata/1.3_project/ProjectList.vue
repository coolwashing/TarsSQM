<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="project_list"
      import-key="project"
      import-title="新产品项目"
      unique-key="project_code"
      @refresh="fetchData"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
      @cell-change="handleCellChange"
    >
      <!-- 顶部检索插槽 -->
      <template #search>
        <div class="search-toolbar">
          <div class="filter-inputs">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索项目代号 / 名称 / 平台..."
              clearable
              size="small"
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.status"
              placeholder="状态"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部状态" value="ALL" />
              <el-option label="立项" value="立项" />
              <el-option label="开发中" value="开发中" />
              <el-option label="量产" value="量产" />
              <el-option label="结束" value="结束" />
            </el-select>

            <el-button type="primary" size="small" :icon="Search" @click="handleSearch">查询</el-button>
            <el-tooltip content="重置检索条件" placement="top" :show-after="500">
              <el-button size="small" :icon="Refresh" circle @click="handleReset" />
            </el-tooltip>
          </div>
        </div>
      </template>

      <!-- 工具栏按钮 -->
      <template #toolbar>
        <el-button type="primary" size="small" :icon="Plus" @click="handleCreate">
          新建项目
        </el-button>
      </template>

      <!-- 项目唯一代号 -->
      <template #project_code="{ row }">
        <span class="project-badge">{{ row.project_code }}</span>
      </template>

      <!-- 项目名称 -->
      <template #name="{ row }">
        <strong>{{ row.name }}</strong>
      </template>

      <!-- 所属平台 -->
      <template #platform="{ row }">
        <el-tag v-if="row.platform" size="small" type="info" effect="light">
          {{ row.platform }}
        </el-tag>
        <span v-else class="text-muted">-</span>
      </template>

      <!-- SOP 日期 -->
      <template #sop_date="{ row }">
        <div v-if="row.sop_date" class="sop-cell">
          <el-icon class="sop-icon"><Calendar /></el-icon>
          <span>{{ row.sop_date }}</span>
        </div>
        <span v-else class="text-muted">待排期</span>
      </template>


      <!-- 操作列 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-popconfirm
          title="确认删除该产品项目主数据？"
          confirm-button-text="删除"
          cancel-button-text="取消"
          confirm-button-type="danger"
          @confirm="handleDelete(row)"
        >
          <template #reference>
            <el-button link type="danger" :icon="Delete">
              删除
            </el-button>
          </template>
        </el-popconfirm>
      </template>

      <!-- 空状态 -->
      <template #empty>
        <el-empty description="未检索到符合条件的新产品项目数据">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即新建首个项目
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式滑出抽屉表单 -->
    <ProjectForm ref="projectFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete, Calendar } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import ProjectForm from './ProjectForm.vue'

interface ProjectRow {
  id: number
  project_code: string
  name: string
  platform?: string
  sop_date?: string
  status: string
  remark?: string
  created_at: string
}

const projectFormRef = ref<InstanceType<typeof ProjectForm>>()

const loading = ref(false)
const tableData = ref<ProjectRow[]>([])

const filters = reactive({
  keyword: '',
  status: 'ALL'
})

const getStoredPageSize = () => {
  try {
    const saved = localStorage.getItem('sqm_table_pagesize_project_list')
    if (saved) {
      const num = parseInt(saved, 10)
      if (num && !isNaN(num)) return num
    }
  } catch {}
  return 10
}

const pagination = reactive({
  page: 1,
  pageSize: getStoredPageSize(),
  total: 0
})

const columns: TableColumn[] = [
  { prop: 'project_code', label: '项目唯一代号', width: 160, fixed: 'left', sortable: true },
  { prop: 'name', label: '项目名称', minWidth: 200, sortable: true, editable: true },
  { prop: 'platform', label: '所属平台/车型', width: 160, sortable: true, editable: true },
  { prop: 'sop_date', label: '量产节点 (SOP)', width: 150, align: 'center', sortable: true, editable: true },
  {
    prop: 'status',
    label: '项目状态',
    width: 120,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    options: [
      { label: '立项', value: '立项', color: 'info' },
      { label: '开发中', value: '开发中', color: 'primary' },
      { label: '量产', value: '量产', color: 'success' },
      { label: '结束', value: '结束', color: 'danger' }
    ]
  },
  { prop: 'remark', label: '项目备忘说明', minWidth: 180, editable: true },
  { prop: 'created_at', label: '创建时间', width: 140, sortable: true, dataType: 'datetime' }
]

// 单元格行内编辑与拖拽复制持久化
const handleCellChange = async ({ row, prop, value, oldValue }: CellChangeEvent) => {
  try {
    await axios.put(`/api/maindata/projects/${row.id}`, { [prop]: value })
  } catch (err: any) {
    row[prop] = oldValue
    ElMessage.error(err.response?.data?.detail || '保存项目修改失败，已还原')
  }
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case '立项':
      return 'info'
    case '开发中':
      return 'primary'
    case '量产':
      return 'success'
    case '结束':
      return 'danger'
    default:
      return 'info'
  }
}

const formatDateTime = (val?: string) => {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 19)
}

const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.status && filters.status !== 'ALL') params.status = filters.status

    const res = await axios.get('/api/maindata/projects', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取项目列表失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  filters.keyword = ''
  filters.status = 'ALL'
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

const handleCreate = () => {
  projectFormRef.value?.openCreate()
}

const handleEdit = (row: ProjectRow) => {
  projectFormRef.value?.openEdit(row.id)
}

const handleDelete = async (row: ProjectRow) => {
  try {
    await axios.delete(`/api/maindata/projects/${row.id}`)
    ElMessage.success(`项目 "${row.name}" 已成功删除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.filter-item-input {
  width: 180px;
}

.filter-item-select {
  width: 110px;
}

.project-badge {
  font-family: monospace;
  font-weight: 700;
  color: #2563eb;
  background-color: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.sop-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #4b5563;
  font-family: monospace;
}

.sop-icon {
  color: #3b82f6;
}

.status-tag {
  font-weight: 600;
}

.text-muted {
  color: #9ca3af;
}
</style>
