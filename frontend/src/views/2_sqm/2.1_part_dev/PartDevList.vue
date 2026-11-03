<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="part_dev_list"
      import-key="part_dev"
      import-title="零件开发台账"
      allow-quick-add
      quick-add-placeholder="快速绑定新零件开发关系..."
      @refresh="fetchData"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
      @cell-change="handleCellChange"
      @quick-add="handleQuickAdd"
    >
      <!-- 顶部检索插槽 -->
      <template #search>
        <div class="search-toolbar">
          <div class="filter-inputs">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索零件图号 / 零件名称 / 供应商 / SQE..."
              clearable
              size="small"
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.dev_phase"
              placeholder="开发阶段"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部阶段" value="ALL" />
              <el-option label="OTS" value="OTS" />
              <el-option label="工装样件" value="工装样件" />
              <el-option label="PPAP" value="PPAP" />
              <el-option label="SOP" value="SOP" />
            </el-select>

            <el-select
              v-model="filters.status"
              placeholder="审批状态"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部状态" value="ALL" />
              <el-option label="进行中" value="进行中" />
              <el-option label="待评审" value="待评审" />
              <el-option label="已批准" value="已批准" />
              <el-option label="已冻结" value="已冻结" />
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
          绑定零件开发
        </el-button>
      </template>

      <!-- 供应商复合展示插槽 -->
      <template #supplier="{ row }">
        <div class="supplier-box">
          <span class="sup-code">{{ row.supplier_code }}</span>
          <span class="sup-name">{{ row.supplier_name }}</span>
        </div>
      </template>

      <!-- 所属车型/项目复合展示插槽 -->
      <template #project="{ row }">
        <el-tag v-if="row.project_code" size="small" type="info" effect="plain">
          {{ row.project_code }} {{ row.project_name ? `(${row.project_name})` : '' }}
        </el-tag>
        <span v-else class="text-muted">-</span>
      </template>

      <!-- 操作列 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-popconfirm
          title="确认解除该零件与供应商的开发绑定关系？"
          confirm-button-text="解绑删除"
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
        <el-empty description="未检索到符合条件的零件开发看板记录">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即绑定首个零件开发关系
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式抽屉表单 -->
    <PartDevForm ref="partDevFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import PartDevForm from './PartDevForm.vue'

interface PartDevRow {
  id: number
  part_id: number
  supplier_id: number
  part_no: string
  part_name: string
  supplier_code: string
  supplier_name: string
  project_code?: string
  project_name?: string
  dev_phase: string
  status: string
  target_date?: string
  sample_qty: number
  responsible?: string
  remark?: string
  created_at: string
}

const partDevFormRef = ref<InstanceType<typeof PartDevForm>>()

const loading = ref(false)
const tableData = ref<PartDevRow[]>([])

const filters = reactive({
  keyword: '',
  dev_phase: 'ALL',
  status: 'ALL'
})

const getStoredPageSize = (storageKey: string, fallback = 10) => {
  try {
    const v = localStorage.getItem(`${storageKey}_pagesize`)
    return v ? Number(v) || fallback : fallback
  } catch {
    return fallback
  }
}

const pagination = reactive({
  page: 1,
  pageSize: getStoredPageSize('part_dev_list', 10),
  total: 0
})

const columns: TableColumn[] = [
  { prop: 'part_no', label: '零件图号/编码', width: 160, fixed: 'left', sortable: true, dataType: 'code' },
  { prop: 'part_name', label: '零件中文名称', minWidth: 180, sortable: true },
  { prop: 'supplier', label: '承制供应商', minWidth: 200, slotName: 'supplier' },
  { prop: 'project', label: '所属车型/项目', minWidth: 160, slotName: 'project' },
  {
    prop: 'dev_phase',
    label: '试制阶段',
    width: 120,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    options: ['OTS', '工装样件', 'PPAP', 'SOP'],
    filters: [
      { text: 'OTS', value: 'OTS' },
      { text: '工装样件', value: '工装样件' },
      { text: 'PPAP', value: 'PPAP' },
      { text: 'SOP', value: 'SOP' }
    ]
  },
  {
    prop: 'status',
    label: '审批状态',
    width: 120,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    options: ['进行中', '待评审', '已批准', '已冻结'],
    filters: [
      { text: '进行中', value: '进行中' },
      { text: '待评审', value: '待评审' },
      { text: '已批准', value: '已批准' },
      { text: '已冻结', value: '已冻结' }
    ]
  },
  {
    prop: 'target_date',
    label: '计划达成节点',
    width: 140,
    align: 'center',
    sortable: true,
    dataType: 'date',
    editable: true,
    editType: 'date'
  },
  {
    prop: 'sample_qty',
    label: '送样数量',
    width: 110,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'number'
  },
  {
    prop: 'responsible',
    label: 'SQE责任人',
    width: 130,
    sortable: true,
    editable: true,
    editType: 'select',
    allowCreate: true,
    options: ['张工', '李工', '王工', '丁工', '叶工', '林工']
  },
  {
    prop: 'remark',
    label: '阶段备忘与评审说明',
    minWidth: 180,
    editable: true,
    editType: 'input'
  }
]

const fetchData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.dev_phase && filters.dev_phase !== 'ALL') params.dev_phase = filters.dev_phase
    if (filters.status && filters.status !== 'ALL') params.status = filters.status

    const res = await axios.get('/api/sqm/part-devs', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取零件开发看板失败: ${err.response?.data?.detail || err.message}`)
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
  filters.dev_phase = 'ALL'
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
  partDevFormRef.value?.openCreate()
}

const handleEdit = (row: PartDevRow) => {
  partDevFormRef.value?.openEdit(row.id)
}

const handleDelete = async (row: PartDevRow) => {
  try {
    await axios.delete(`/api/sqm/part-devs/${row.id}`)
    ElMessage.success(`零件 "${row.part_no}" 开发绑定关系已解除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

const handleCellChange = async (event: CellChangeEvent) => {
  try {
    let val = event.value
    if (event.prop === 'sample_qty') {
      val = val ? Number(val) : 0
    }
    await axios.put(`/api/sqm/part-devs/${event.row.id}`, {
      [event.prop]: val
    })
    ElMessage.success({
      message: `已自动更新 [${event.prop}]`,
      duration: 1500
    })
  } catch (err: any) {
    ElMessage.error(`单元格更新失败: ${err.response?.data?.detail || err.message}`)
    fetchData()
  }
}

const handleQuickAdd = async (payload: Record<string, any>, done: () => void) => {
  if (payload.part_id && payload.supplier_id) {
    try {
      await axios.post('/api/sqm/part-devs', payload)
      ElMessage.success('新零件开发关系绑定成功')
      done()
      fetchData()
    } catch (err: any) {
      ElMessage.error(`添加失败: ${err.response?.data?.detail || err.message}`)
    }
  } else {
    ElMessage.info('正在开启详细绑定抽屉以选定零件与承制供应商...')
    partDevFormRef.value?.openCreate(payload)
    done()
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

.part-badge {
  font-family: monospace;
  font-weight: 700;
  color: #0284c7;
  background-color: #f0f9ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.supplier-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sup-code {
  font-family: monospace;
  font-size: 11px;
  color: #6366f1;
}

.sup-name {
  color: #1f2937;
  font-weight: 500;
}

.phase-tag {
  font-weight: 600;
  letter-spacing: 0.5px;
}

.status-tag {
  font-weight: 600;
}

.date-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #4b5563;
  font-family: monospace;
}

.date-icon {
  color: #6366f1;
}

.qty-badge {
  font-family: monospace;
  font-weight: 600;
  color: #374151;
}

.text-muted {
  color: #9ca3af;
}
</style>
