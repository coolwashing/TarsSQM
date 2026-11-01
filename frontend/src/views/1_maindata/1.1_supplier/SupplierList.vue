<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="supplier_list"
      import-key="supplier"
      import-title="供应商主数据"
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
              placeholder="搜索编码 / 全称 / 简称 / 产品类型 / 城市..."
              clearable
              :prefix-icon="Search"
              class="filter-item-input"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.status"
              placeholder="准入状态"
              clearable
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部准入状态" value="ALL" />
              <el-option label="合格" value="合格" />
              <el-option label="考察" value="考察" />
              <el-option label="潜在" value="潜在" />
              <el-option label="冻结" value="冻结" />
            </el-select>

            <el-select
              v-model="filters.supply_tier"
              placeholder="供应层级"
              clearable
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部供应层级" value="ALL" />
              <el-option label="1供" value="1供" />
              <el-option label="2供开发中" value="2供开发中" />
              <el-option label="在开发" value="在开发" />
              <el-option label="潜在供应商" value="潜在供应商" />
            </el-select>

            <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </div>
        </div>
      </template>

      <!-- 顶部工具栏右侧按钮 -->
      <template #toolbar>
        <el-button type="primary" :icon="Plus" @click="handleCreate">
          新建供应商
        </el-button>
      </template>

      <!-- 列自定义插槽 -->
      <template #code="{ row }">
        <span class="code-badge">{{ row.code }}</span>
      </template>

      <template #name="{ row }">
        <div class="name-cell">
          <span class="main-name">{{ row.name }}</span>
          <el-tag
            v-if="row.short_name && row.short_name !== row.name"
            size="small"
            type="info"
            effect="plain"
            class="short-tag"
          >
            {{ row.short_name }}
          </el-tag>
        </div>
      </template>

      <template #supply_tier="{ row }">
        <el-tag
          v-if="row.supply_tier"
          :type="getTierTagType(row.supply_tier)"
          effect="light"
          class="status-tag"
        >
          {{ row.supply_tier }}
        </el-tag>
        <span v-else class="text-dim">-</span>
      </template>

      <template #status="{ row }">
        <el-tag :type="getStatusTagType(row.status)" effect="plain" class="status-tag">
          {{ row.status }}
        </el-tag>
      </template>

      <template #cooperation_rate="{ row }">
        <el-tag
          v-if="row.cooperation_rate"
          :type="getCoopTagType(row.cooperation_rate)"
          effect="plain"
          size="small"
        >
          {{ row.cooperation_rate }}
        </el-tag>
        <span v-else class="text-dim">-</span>
      </template>

      <template #product_type="{ row }">
        <span v-if="row.product_type" class="product-type-text" :title="row.product_type">
          {{ row.product_type }}
        </span>
        <span v-else class="text-dim">-</span>
      </template>

      <!-- 图文档案列插槽 -->
      <template #profile_html="{ row }">
        <el-button
          v-if="row.profile_html && row.profile_html.trim()"
          link
          type="primary"
          :icon="Document"
          size="small"
          class="profile-action-btn has-content"
          @click="handleEdit(row, 'profile')"
        >
          查看档案
        </el-button>
        <el-button
          v-else
          link
          type="info"
          size="small"
          class="profile-action-btn empty"
          @click="handleEdit(row, 'profile')"
        >
          + 录入档案
        </el-button>
      </template>

      <template #created_at="{ row }">
        {{ formatDateTime(row.created_at) }}
      </template>

      <!-- 操作列插槽 -->
      <template #action="{ row }">
        <el-button link type="primary" :icon="Edit" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-popconfirm
          title="确认删除该供应商主数据？"
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

      <!-- 空状态插槽 -->
      <template #empty>
        <el-empty description="未检索到符合条件的供应商主数据">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即新建首个供应商
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 70% 宽幅沉浸式滑出抽屉表单 -->
    <SupplierForm ref="supplierFormRef" @success="fetchData" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import SupplierForm from './SupplierForm.vue'

interface SupplierRow {
  id: number
  code: string
  name: string
  short_name?: string
  pinyin?: string
  status: string
  supply_tier?: string
  product_type?: string
  cooperation_rate?: string
  quality_system?: string
  region?: string
  city?: string
  company_type?: string
  importance?: string
  urgency?: string
  purchasing_status?: string
  contact?: string
  phone?: string
  email?: string
  address?: string
  remark?: string
  profile_html?: string
  created_at: string
}

const supplierFormRef = ref<InstanceType<typeof SupplierForm>>()

const loading = ref(false)
const tableData = ref<SupplierRow[]>([])

const filters = reactive({
  keyword: '',
  status: 'ALL',
  supply_tier: 'ALL'
})

const getStoredPageSize = () => {
  const saved = localStorage.getItem('sqm_table_pagesize_supplier_list')
  if (saved) {
    const num = parseInt(saved, 10)
    if (num && !isNaN(num)) return num
  }
  return 10
}

const pagination = reactive({
  page: 1,
  pageSize: getStoredPageSize(),
  total: 0
})

// 列配置定义 (支持拖拽列宽、排序、表头过滤、列显隐重排)
const columns: TableColumn[] = [
  { prop: 'code', label: '供应商简称', width: 120, fixed: 'left', sortable: true, align: 'center' },
  { prop: 'name', label: '企业全称', minWidth: 220, sortable: true },
  {
    prop: 'supply_tier',
    label: '供应层级',
    width: 125,
    align: 'center',
    sortable: true,
    filters: [
      { text: '1供', value: '1供' },
      { text: '2供开发中', value: '2供开发中' },
      { text: '在开发', value: '在开发' },
      { text: '潜在供应商', value: '潜在供应商' }
    ]
  },
  {
    prop: 'status',
    label: '准入状态',
    width: 105,
    align: 'center',
    sortable: true,
    filters: [
      { text: '合格', value: '合格' },
      { text: '考察', value: '考察' },
      { text: '潜在', value: '潜在' },
      { text: '冻结', value: '冻结' }
    ]
  },
  { prop: 'profile_html', label: '图文档案', width: 115, align: 'center' },
  { prop: 'product_type', label: '主营产品类型', minWidth: 170, sortable: true },
  {
    prop: 'cooperation_rate',
    label: '配合度',
    width: 95,
    align: 'center',
    sortable: true,
    filters: [
      { text: '高', value: '高' },
      { text: '中', value: '中' },
      { text: '低', value: '低' }
    ]
  },
  { prop: 'city', label: '城市', width: 95, sortable: true, editable: true },
  { prop: 'quality_system', label: '质量体系', width: 140 },
  { prop: 'contact', label: '联络人', width: 110, sortable: true, editable: true },
  { prop: 'phone', label: '联系电话', width: 130, editable: true },
  { prop: 'address', label: '办公/工厂地址', minWidth: 200, editable: true },
  { prop: 'created_at', label: '登记时间', width: 130, sortable: true, dataType: 'date' }
]

const getStatusTagType = (status: string) => {
  switch (status) {
    case '合格':
      return 'success'
    case '考察':
      return 'warning'
    case '冻结':
      return 'danger'
    default:
      return 'info'
  }
}

const getTierTagType = (tier: string) => {
  switch (tier) {
    case '1供':
      return 'success'
    case '2供开发中':
      return 'primary'
    case '在开发':
      return 'warning'
    case '潜在供应商':
      return 'info'
    default:
      return 'info'
  }
}

const getCoopTagType = (rate: string) => {
  switch (rate) {
    case '高':
      return 'success'
    case '中':
      return 'warning'
    case '低':
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
    if (filters.supply_tier && filters.supply_tier !== 'ALL') params.supply_tier = filters.supply_tier

    const res = await axios.get('/api/maindata/suppliers', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取供应商列表失败: ${err.response?.data?.detail || err.message}`)
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
  filters.supply_tier = 'ALL'
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
  supplierFormRef.value?.openCreate()
}

const handleEdit = (row: SupplierRow, tab: 'basic' | 'profile' = 'basic') => {
  supplierFormRef.value?.openEdit(row.id, tab)
}

const handleDelete = async (row: SupplierRow) => {
  try {
    await axios.delete(`/api/maindata/suppliers/${row.id}`)
    ElMessage.success(`供应商 ${row.name} 删除成功`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

const handleCellChange = async ({ row, prop, value, oldValue }: CellChangeEvent) => {
  try {
    await axios.put(`/api/maindata/suppliers/${row.id}`, { [prop]: value })
  } catch (err: any) {
    row[prop] = oldValue
    ElMessage.error(`行内修改保存失败: ${err.response?.data?.detail || err.message}`)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.search-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  gap: 12px;
}

.filter-inputs {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 10px;
  white-space: nowrap;
}

.filter-item-input {
  width: 250px;
  flex-shrink: 0;
}

.filter-item-select {
  width: 135px;
  flex-shrink: 0;
}

.code-badge {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.main-name {
  font-weight: 600;
  color: #1e293b;
}

.short-tag {
  font-size: 11px;
  padding: 0 6px;
  height: 20px;
  line-height: 18px;
}

.product-type-text {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #475569;
  font-size: 13px;
}

.status-tag {
  font-weight: 500;
  border-radius: 6px;
}

.text-dim {
  color: #94a3b8;
  font-size: 12px;
}

.profile-action-btn {
  font-size: 12px;
}

.profile-action-btn.empty {
  color: #94a3b8;
}

.profile-action-btn.empty:hover {
  color: #6366f1;
}

.profile-action-btn.has-content {
  font-weight: 600;
}
</style>
