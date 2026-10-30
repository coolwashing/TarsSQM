<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="ctq_list"
      import-key="ctq"
      import-title="CTQ关键质量特性"
      @refresh="fetchData"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
    >
      <!-- 顶部检索插槽 -->
      <template #search>
        <div class="search-toolbar">
          <div class="filter-inputs">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索特征代号 / 特性名称 / 零件图号 / 检验量具..."
              clearable
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.featureType"
              placeholder="特性分类"
              clearable
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部特性类别" value="ALL" />
              <el-option label="KPC (产品关键特性)" value="KPC" />
              <el-option label="KCC (过程关键特性)" value="KCC" />
            </el-select>

            <el-select
              v-model="filters.partId"
              placeholder="筛选零部件"
              clearable
              filterable
              class="filter-item-select-part"
              @change="handleSearch"
            >
              <el-option
                v-for="p in partOptions"
                :key="p.id"
                :label="`[${p.part_no}] ${p.name}`"
                :value="p.id"
              />
            </el-select>

            <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </div>
        </div>
      </template>

      <!-- 工具栏按钮 -->
      <template #toolbar>
        <el-button type="primary" :icon="Plus" @click="handleCreate">
          新增 CTQ 特征
        </el-button>
      </template>

      <!-- 特征代号 -->
      <template #feature_code="{ row }">
        <span class="code-badge">{{ row.feature_code }}</span>
      </template>

      <!-- 特性类别 -->
      <template #feature_type="{ row }">
        <el-tag
          :type="row.feature_type === 'KPC' ? 'primary' : 'warning'"
          effect="dark"
          class="type-tag"
        >
          {{ row.feature_type }}
        </el-tag>
      </template>

      <!-- 特性中文名称 -->
      <template #feature_name="{ row }">
        <strong>{{ row.feature_name }}</strong>
      </template>

      <!-- 关联零部件 -->
      <template #part="{ row }">
        <div class="part-box">
          <span class="part-badge">{{ row.part_no }}</span>
          <span class="part-name">{{ row.part_name }}</span>
        </div>
      </template>

      <!-- 标称值 -->
      <template #standard_value="{ row }">
        <span v-if="row.standard_value" class="nominal-val">{{ row.standard_value }}</span>
        <span v-else class="text-muted">-</span>
      </template>

      <!-- 公差/控制规格 -->
      <template #tolerance="{ row }">
        <span class="tolerance-badge">{{ row.tolerance }}</span>
      </template>

      <!-- 检验频次 -->
      <template #frequency="{ row }">
        <el-tag size="small" type="info" effect="plain">
          {{ row.frequency }}
        </el-tag>
      </template>

      <!-- 操作列 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-popconfirm
          title="确认删除该关键质量特性配置？"
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
        <el-empty description="未检索到符合条件的 CTQ 关键质量特性配置">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即新建首个 CTQ 特征
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式抽屉表单 -->
    <CTQForm ref="ctqFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn } from '@/components/common/DataTable/types'
import CTQForm from './CTQForm.vue'

interface PartOption {
  id: number
  part_no: string
  name: string
}

interface CtqRow {
  id: number
  part_id: number
  part_no: string
  part_name: string
  project_code?: string
  project_name?: string
  feature_code: string
  feature_name: string
  feature_type: string
  standard_value?: string
  tolerance: string
  inspection_tool?: string
  frequency: string
  control_method?: string
  remark?: string
  created_at: string
}

const ctqFormRef = ref<InstanceType<typeof CTQForm>>()

const loading = ref(false)
const tableData = ref<CtqRow[]>([])
const partOptions = ref<PartOption[]>([])

const filters = reactive({
  keyword: '',
  featureType: 'ALL',
  partId: undefined as number | undefined
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const columns: TableColumn[] = [
  { prop: 'feature_code', label: '特征代号', width: 130, fixed: 'left', sortable: true },
  {
    prop: 'feature_type',
    label: '特性类别',
    width: 110,
    align: 'center',
    sortable: true,
    filters: [
      { text: 'KPC (产品关键特性)', value: 'KPC' },
      { text: 'KCC (过程关键特性)', value: 'KCC' }
    ]
  },
  { prop: 'feature_name', label: '特性中文名称', minWidth: 180, sortable: true },
  { prop: 'part', label: '关联零部件', minWidth: 180, slotName: 'part' },
  { prop: 'standard_value', label: '标称值', width: 120, align: 'center', sortable: true },
  { prop: 'tolerance', label: '公差/控制规格', minWidth: 160 },
  { prop: 'inspection_tool', label: '测量量具', width: 160, sortable: true },
  { prop: 'frequency', label: '检验频次', width: 160 }
]

const loadPartOptions = async () => {
  try {
    const res = await axios.get('/api/maindata/parts', { params: { page_size: 200 } })
    partOptions.value = res.data.items || []
  } catch (err: any) {
    console.error('加载零件候选项失败:', err)
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
    if (filters.featureType && filters.featureType !== 'ALL') params.feature_type = filters.featureType
    if (filters.partId) params.part_id = filters.partId

    const res = await axios.get('/api/ctq', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取 CTQ 关键特性列表失败: ${err.response?.data?.detail || err.message}`)
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
  filters.featureType = 'ALL'
  filters.partId = undefined
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
  ctqFormRef.value?.openCreate()
}

const handleEdit = (row: CtqRow) => {
  ctqFormRef.value?.openEdit(row.id)
}

const handleDelete = async (row: CtqRow) => {
  try {
    await axios.delete(`/api/ctq/${row.id}`)
    ElMessage.success(`关键特性 "${row.feature_code}" 已成功删除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

onMounted(() => {
  loadPartOptions()
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
  gap: 12px;
  flex-wrap: wrap;
}

.filter-item-input {
  width: 260px;
}

.filter-item-select {
  width: 170px;
}

.filter-item-select-part {
  width: 220px;
}

.code-badge {
  font-family: monospace;
  font-weight: 700;
  color: #d97706;
  background-color: #fffbeb;
  padding: 2px 6px;
  border-radius: 4px;
}

.type-tag {
  font-weight: 700;
  letter-spacing: 0.5px;
}

.part-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.part-badge {
  font-family: monospace;
  font-size: 11px;
  color: #0284c7;
  background: #f0f9ff;
  padding: 1px 5px;
  border-radius: 3px;
}

.part-name {
  color: #374151;
}

.nominal-val {
  font-family: monospace;
  font-weight: 600;
  color: #1e293b;
}

.tolerance-badge {
  font-family: monospace;
  font-weight: 600;
  color: #4338ca;
  background-color: #eef2ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.text-muted {
  color: #9ca3af;
}
</style>
