<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="quality_issue_list"
      import-key="quality_issue"
      import-title="质量问题台账"
      allow-quick-add
      quick-add-placeholder="快速登记新质量问题简述..."
      :quick-add-defaults="{ severity: '一般', status: '登记', occurred_date: new Date().toISOString().slice(0, 10) }"
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
              placeholder="搜索问题单号 / 标题 / 零件 / 供应商..."
              clearable
              size="small"
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.severity"
              placeholder="严重等级"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部等级" value="ALL" />
              <el-option label="致命" value="致命" />
              <el-option label="严重" value="严重" />
              <el-option label="一般" value="一般" />
              <el-option label="微小" value="微小" />
            </el-select>

            <el-select
              v-model="filters.status"
              placeholder="闭环状态"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部状态" value="ALL" />
              <el-option label="登记" value="登记" />
              <el-option label="已提改善" value="已提改善" />
              <el-option label="已验证" value="已验证" />
              <el-option label="闭环" value="闭环" />
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
        <el-button type="primary" :icon="Plus" @click="handleCreate">
          登记新问题
        </el-button>
      </template>

      <!-- 关联零部件复合展示插槽 -->
      <template #part="{ row }">
        <div v-if="row.part_no" class="part-cell">
          <span class="part-code">{{ row.part_no }}</span>
          <span class="part-name">{{ row.part_name }}</span>
        </div>
        <span v-else class="text-muted">-</span>
      </template>

      <!-- 操作列 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          处理/编辑
        </el-button>
        <el-popconfirm
          title="确认删除该质量问题记录？"
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
        <el-empty description="未检索到符合条件的质量异常单据记录">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即登记首个质量问题
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式抽屉表单 -->
    <QualityIssueForm ref="qualityIssueFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import QualityIssueForm from './QualityIssueForm.vue'

interface QualityIssueRow {
  id: number
  issue_no: string
  title: string
  severity: string
  status: string
  part_id?: number
  part_no?: string
  part_name?: string
  supplier_id?: number
  supplier_name?: string
  occurred_date?: string
  closed_date?: string
  responsible?: string
  description?: string
  containment_action?: string
  created_at: string
}

const qualityIssueFormRef = ref<InstanceType<typeof QualityIssueForm>>()

const loading = ref(false)
const tableData = ref<QualityIssueRow[]>([])

const filters = reactive({
  keyword: '',
  severity: 'ALL',
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
  pageSize: getStoredPageSize('quality_issue_list', 10),
  total: 0
})

const columns: TableColumn[] = [
  {
    prop: 'issue_no',
    label: '问题单号',
    width: 160,
    fixed: 'left',
    sortable: true,
    dataType: 'code',
    editable: true,
    editType: 'input'
  },
  {
    prop: 'title',
    label: '质量问题主题简述',
    minWidth: 220,
    sortable: true,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'severity',
    label: '严重等级',
    width: 110,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    options: ['致命', '严重', '一般', '微小'],
    colorMap: {
      致命: 'danger',
      严重: 'warning',
      一般: 'primary',
      微小: 'info'
    },
    filters: [
      { text: '致命', value: '致命' },
      { text: '严重', value: '严重' },
      { text: '一般', value: '一般' },
      { text: '微小', value: '微小' }
    ]
  },
  {
    prop: 'status',
    label: '闭环状态',
    width: 120,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'select',
    options: ['登记', '已提改善', '已验证', '闭环'],
    colorMap: {
      闭环: 'success',
      已验证: 'primary',
      已提改善: 'warning',
      登记: 'danger'
    },
    filters: [
      { text: '登记', value: '登记' },
      { text: '已提改善', value: '已提改善' },
      { text: '已验证', value: '已验证' },
      { text: '闭环', value: '闭环' }
    ]
  },
  {
    prop: 'part',
    label: '关联零部件',
    minWidth: 180,
    slotName: 'part',
    quickAddDisabled: true
  },
  {
    prop: 'supplier_name',
    label: '责任供应商',
    minWidth: 180,
    sortable: true,
    quickAddDisabled: true
  },
  {
    prop: 'responsible',
    label: '跟进人',
    width: 120,
    sortable: true,
    editable: true,
    editType: 'select',
    allowCreate: true,
    options: ['张工', '李工', '王工', '丁工', '叶工', '林工']
  },
  {
    prop: 'occurred_date',
    label: '发现日期',
    width: 130,
    align: 'center',
    sortable: true,
    dataType: 'date',
    editable: true,
    editType: 'date'
  },
  {
    prop: 'closed_date',
    label: '闭环日期',
    width: 130,
    align: 'center',
    sortable: true,
    dataType: 'date',
    editable: true,
    editType: 'date'
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
    if (filters.severity && filters.severity !== 'ALL') params.severity = filters.severity
    if (filters.status && filters.status !== 'ALL') params.status = filters.status

    const res = await axios.get('/api/sqm/quality-issues', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取质量问题列表失败: ${err.response?.data?.detail || err.message}`)
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
  filters.severity = 'ALL'
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
  qualityIssueFormRef.value?.openCreate()
}

const handleEdit = (row: QualityIssueRow) => {
  qualityIssueFormRef.value?.openEdit(row.id)
}

const handleDelete = async (row: QualityIssueRow) => {
  try {
    await axios.delete(`/api/sqm/quality-issues/${row.id}`)
    ElMessage.success(`质量问题单 "${row.issue_no}" 已成功删除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

const handleCellChange = async (event: CellChangeEvent) => {
  try {
    await axios.put(`/api/sqm/issues/${event.row.id}`, {
      [event.prop]: event.value
    })
    ElMessage.success({
      message: `已自动更新 [${event.prop}]`,
      duration: 1500
    })
  } catch (err: any) {
    ElMessage.error(`更新失败: ${err.response?.data?.detail || err.message}`)
    fetchData()
  }
}

const handleQuickAdd = async (payload: Record<string, any>, done: () => void) => {
  if (payload.title && payload.title.trim()) {
    try {
      await axios.post('/api/sqm/issues', payload)
      ElMessage.success('质量问题单创建成功')
      done()
      fetchData()
    } catch (err: any) {
      ElMessage.error(`快速创建失败: ${err.response?.data?.detail || err.message}`)
    }
  } else {
    ElMessage.info('正在开启详细登记抽屉以输入完整问题简述...')
    qualityIssueFormRef.value?.openCreate(payload)
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

.issue-badge {
  font-family: monospace;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.severity-致命 {
  background-color: #fee2e2;
  color: #dc2626;
}

.severity-严重 {
  background-color: #ffedd5;
  color: #ea580c;
}

.severity-一般 {
  background-color: #e0e7ff;
  color: #4f46e5;
}

.severity-微小 {
  background-color: #f3f4f6;
  color: #4b5563;
}

.severity-tag,
.status-tag {
  font-weight: 600;
}

.part-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.part-code {
  font-family: monospace;
  font-size: 11px;
  color: #0284c7;
}

.part-name {
  color: #374151;
}

.closed-date {
  color: #10b981;
  font-weight: 500;
}

.text-muted {
  color: #9ca3af;
}
</style>
