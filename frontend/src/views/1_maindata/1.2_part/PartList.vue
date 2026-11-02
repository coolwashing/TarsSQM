<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="part_list"
      import-key="part"
      import-title="零件主数据"
      unique-key="part_no"
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
              placeholder="搜索图号/名称..."
              size="small"
              clearable
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.projectId"
              placeholder="所属项目"
              size="small"
              clearable
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option
                v-for="item in projectOptions"
                :key="item.id"
                :label="`${item.project_code} (${item.name})`"
                :value="item.id"
              />
            </el-select>

            <el-select
              v-model="filters.category"
              placeholder="物料大类"
              size="small"
              clearable
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部分类" value="ALL" />
              <el-option label="机械结构件" value="机械结构件" />
              <el-option label="驱动执行器" value="驱动执行器" />
              <el-option label="传感器件" value="传感器件" />
              <el-option label="电子电气" value="电子电气" />
              <el-option label="动力电池/电源" value="动力电池/电源" />
              <el-option label="线束接插件" value="线束接插件" />
              <el-option label="紧固标准件" value="紧固标准件" />
              <el-option label="流体气动件" value="流体气动件" />
              <el-option label="外观注塑件" value="外观注塑件" />
              <el-option label="其他" value="其他" />
            </el-select>

            <el-button type="primary" size="small" :icon="Search" @click="handleSearch">查询</el-button>
            <el-tooltip content="重置检索条件" placement="top" :show-after="500">
              <el-button circle size="small" :icon="Refresh" @click="handleReset" />
            </el-tooltip>
          </div>
        </div>
      </template>

      <!-- 工具栏按钮 -->
      <template #toolbar>
        <el-button type="primary" size="small" :icon="Plus" @click="handleCreate">
          新建零件
        </el-button>
      </template>

      <!-- 零件编码/图号 -->
      <template #part_no="{ row }">
        <span class="part-badge">{{ row.part_no }}</span>
      </template>

      <!-- 零件名称 -->
      <template #name="{ row }">
        <strong>{{ row.name }}</strong>
      </template>

      <!-- 所属项目 -->
      <template #project="{ row }">
        <div v-if="row.project_code" class="project-tag-box">
          <el-tag size="small" type="info" effect="plain" class="prj-code">
            {{ row.project_code }}
          </el-tag>
          <span class="prj-name">{{ row.project_name }}</span>
        </div>
        <span v-else class="text-muted">未绑定</span>
      </template>

      <!-- 图纸版本 -->
      <template #drawing_version="{ row }">
        <span class="version-badge">v{{ row.drawing_version || 'A.0' }}</span>
      </template>

      <!-- 登记时间 -->
      <template #created_at="{ row }">
        {{ formatDateTime(row.created_at) }}
      </template>

      <!-- 操作列 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-popconfirm
          title="确认删除该零件主数据？"
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
        <el-empty description="未检索到符合条件的零件规格数据">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即新建首个零件
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式抽屉表单 -->
    <PartForm ref="partFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import PartForm from './PartForm.vue'

interface ProjectOption {
  id: number
  project_code: string
  name: string
}

interface PartRow {
  id: number
  part_no: string
  name: string
  project_id?: number
  project_code?: string
  project_name?: string
  category?: string
  drawing_version: string
  engineer?: string
  remark?: string
  created_at: string
}

const partFormRef = ref<InstanceType<typeof PartForm>>()

const loading = ref(false)
const tableData = ref<PartRow[]>([])
const projectOptions = ref<ProjectOption[]>([])

const filters = reactive({
  keyword: '',
  projectId: undefined as number | undefined,
  category: 'ALL'
})

const getStoredPageSize = () => {
  try {
    const saved = localStorage.getItem('sqm_table_pagesize_part_list')
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
  { prop: 'part_no', label: '零件物料编码/图号', width: 160, fixed: 'left', sortable: true },
  { prop: 'name', label: '零件中文名称', minWidth: 180, sortable: true, editable: true },
  { prop: 'project', label: '所属车型/项目', minWidth: 180, slotName: 'project' },
  {
    prop: 'category',
    label: '物料分类',
    width: 140,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    allowCreate: true,
    options: [
      { label: '机械结构件', value: '机械结构件', color: 'primary' },
      { label: '驱动执行器', value: '驱动执行器', color: 'warning' },
      { label: '传感器件', value: '传感器件', color: 'success' },
      { label: '电子电气', value: '电子电气', color: 'danger' },
      { label: '动力电池/电源', value: '动力电池/电源', color: 'warning' },
      { label: '线束接插件', value: '线束接插件', color: 'primary' },
      { label: '紧固标准件', value: '紧固标准件', color: 'info' },
      { label: '流体气动件', value: '流体气动件', color: 'info' },
      { label: '外观注塑件', value: '外观注塑件', color: 'primary' },
      { label: '其他', value: '其他', color: 'info' }
    ]
  },
  { prop: 'drawing_version', label: '图纸版本', width: 110, align: 'center', sortable: true, editable: true },
  {
    prop: 'engineer',
    label: '责任工程师',
    width: 130,
    sortable: true,
    editable: true,
    editType: 'select',
    allowCreate: true,
    options: ['张工', '李工', '王工', '赵工', '陈工', '刘工']
  },
  { prop: 'remark', label: '工艺说明与备注', minWidth: 160, editable: true },
  { prop: 'created_at', label: '登记时间', width: 160, sortable: true }
]

// 单元格行内编辑与拖拽复制持久化
const handleCellChange = async ({ row, prop, value, oldValue }: CellChangeEvent) => {
  try {
    await axios.put(`/api/maindata/parts/${row.id}`, { [prop]: value })
  } catch (err: any) {
    row[prop] = oldValue
    ElMessage.error(err.response?.data?.detail || '保存零件修改失败，已还原')
  }
}

const getCategoryTagType = (cat?: string) => {
  switch (cat) {
    case '机械结构件':
      return 'primary'
    case '驱动执行器':
      return 'warning'
    case '传感器件':
      return 'success'
    case '电子电气':
      return 'danger'
    default:
      return 'info'
  }
}

const formatDateTime = (val?: string) => {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 19)
}

const fetchProjectOptions = async () => {
  try {
    const res = await axios.get('/api/maindata/projects/options')
    projectOptions.value = res.data || []
  } catch (err: any) {
    console.error('加载项目候选项失败:', err)
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.projectId) params.project_id = filters.projectId
    if (filters.category && filters.category !== 'ALL') params.category = filters.category

    const res = await axios.get('/api/maindata/parts', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取零件列表失败: ${err.response?.data?.detail || err.message}`)
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
  filters.projectId = undefined
  filters.category = 'ALL'
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
  partFormRef.value?.openCreate()
}

const handleEdit = (row: PartRow) => {
  partFormRef.value?.openEdit(row.id)
}

const handleDelete = async (row: PartRow) => {
  try {
    await axios.delete(`/api/maindata/parts/${row.id}`)
    ElMessage.success(`零件 "${row.name}" (${row.part_no}) 已成功删除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除零件失败: ${err.response?.data?.detail || err.message}`)
  }
}

onMounted(() => {
  fetchProjectOptions()
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
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.filter-item-input {
  width: 160px;
  min-width: 120px;
}

.filter-item-select {
  width: 115px;
}

.filter-item-select {
  width: 170px;
}

.part-badge {
  font-family: monospace;
  font-weight: 700;
  color: #0284c7;
  background-color: #f0f9ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.project-tag-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.prj-code {
  font-family: monospace;
}

.prj-name {
  color: #374151;
  font-size: 13px;
}

.version-badge {
  font-family: monospace;
  font-size: 11px;
  font-weight: 600;
  color: #4b5563;
  background: #f3f4f6;
  padding: 2px 5px;
  border-radius: 3px;
}

.text-muted {
  color: #9ca3af;
}
</style>
