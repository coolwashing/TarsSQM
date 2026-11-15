<template>
  <div class="page-container">
    <DataTable
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      storage-key="mrb_list"
      import-key="mrb"
      import-title="MRB 审理台账"
      show-actions
      action-width="190px"
      entity-label="MRB 评审单"
      :row-label-key="(r: MrbRow) => `${r.mrb_no}${r.supplier_name ? ` (${r.supplier_name})` : ''}`"
      allow-quick-add
      quick-add-placeholder="快速登记新 MRB 缺陷概述..."
      :quick-add-defaults="{ mrb_source: filters.mrb_source !== 'ALL' ? filters.mrb_source : 'IQC来料', defect_qty: 1, status: '待审理', mrb_decision: '待审理', occurred_date: new Date().toISOString().slice(0, 10) }"
      @refresh="fetchData"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
      @cell-change="handleCellChange"
      @quick-add="handleQuickAdd"
      @edit="handleEdit"
      @delete="handleDelete"
    >
      <!-- 检索工具栏插槽 -->
      <template #search>
        <div class="search-toolbar">
          <div class="filter-inputs">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索 MRB单号 / 供应商 / 物料编码 / 缺陷描述 / 责任人..."
              clearable
              size="small"
              :prefix-icon="Search"
              class="filter-item-input"
              style="width: 280px"
              @keyup.enter="handleSearch"
            />

            <el-select
              v-model="filters.mrb_source"
              placeholder="来源环节"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部来源" value="ALL" />
              <el-option label="IQC来料" value="IQC来料" />
              <el-option label="制程装配" value="制程装配" />
              <el-option label="研发试制" value="研发试制" />
              <el-option label="售后客诉" value="售后客诉" />
            </el-select>

            <el-select
              v-model="filters.mrb_decision"
              placeholder="审理判定"
              clearable
              size="small"
              class="filter-item-select"
              @change="handleSearch"
            >
              <el-option label="全部判定" value="ALL" />
              <el-option label="退货" value="退货" />
              <el-option label="让步接收" value="让步接收" />
              <el-option label="让步" value="让步" />
              <el-option label="内部返修" value="内部返修" />
              <el-option label="挑选" value="挑选" />
              <el-option label="报废" value="报废" />
              <el-option label="待审理" value="待审理" />
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
              <el-option label="待审理" value="待审理" />
              <el-option label="改善中" value="改善中" />
              <el-option label="已验证" value="已验证" />
              <el-option label="已结案" value="已结案" />
            </el-select>

            <el-button type="primary" size="small" :icon="Search" @click="handleSearch">查询</el-button>
            <el-tooltip content="重置检索条件" placement="top" :show-after="500">
              <el-button size="small" :icon="Refresh" circle @click="handleReset" />
            </el-tooltip>
          </div>
        </div>
      </template>

      <!-- 工具栏按钮插槽 -->
      <template #toolbar>
        <el-button type="primary" size="small" :icon="Plus" @click="handleCreate">
          登记新 MRB
        </el-button>
      </template>

      <!-- 操作栏前缀：会签审理插槽 -->
      <template #action-prefix="{ row }">
        <el-button
          link
          type="primary"
          size="small"
          @click.stop="openJudge(row)"
        >
          会签审理
        </el-button>
      </template>

      <!-- 空状态插槽 -->
      <template #empty>
        <el-empty description="未检索到符合条件的 MRB 审理单据">
          <el-button type="primary" plain :icon="Plus" @click="handleCreate">
            立即登记首个 MRB 异常单
          </el-button>
        </el-empty>
      </template>
    </DataTable>

    <!-- 详情/审理/编辑抽屉 -->
    <MrbDetailDrawer ref="mrbDetailDrawerRef" @success="handleDrawerSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn } from '@/components/common/DataTable/types'
import { getStoredTablePageSize } from '@/components/common/DataTable/types'
import MrbDetailDrawer from './components/MrbDetailDrawer.vue'

interface MrbRow {
  id: number
  mrb_no: string
  mrb_source: string
  occurred_date?: string
  supplier_name?: string
  material_type?: string
  part_no?: string
  part_name?: string
  version?: string
  batch_no?: string
  batch_qty?: number
  sample_qty?: number
  defect_qty: number
  defect_rate?: string
  defect_type?: string
  defect_desc?: string
  attachments?: any
  mrb_decision?: string
  duty_attribution?: string
  reporter?: string
  owner?: string
  status: string
  is_closed?: string
  created_at: string
}

const mrbDetailDrawerRef = ref<InstanceType<typeof MrbDetailDrawer>>()
const loading = ref(false)
const tableData = ref<MrbRow[]>([])

const filters = reactive({
  keyword: '',
  mrb_source: 'ALL',
  mrb_decision: 'ALL',
  status: 'ALL'
})

const pagination = reactive({
  page: 1,
  pageSize: getStoredTablePageSize('mrb_list', 15),
  total: 0
})

const columns: TableColumn[] = [
  {
    prop: 'mrb_no',
    label: 'MRB 单号',
    width: 155,
    fixed: 'left',
    sortable: true,
    dataType: 'code',
    editable: true,
    editType: 'input'
  },
  {
    prop: 'mrb_source',
    label: '来源环节',
    width: 105,
    align: 'center',
    sortable: true,
    dataType: 'badge',
    editable: true,
    editType: 'select',
    options: ['IQC来料', '制程装配', '研发试制', '售后客诉'],
    colorMap: {
      IQC来料: 'primary',
      制程装配: 'warning',
      研发试制: 'info',
      售后客诉: 'danger'
    }
  },
  {
    prop: 'occurred_date',
    label: '发生日期',
    width: 115,
    align: 'center',
    sortable: true,
    dataType: 'date',
    editable: true,
    editType: 'date'
  },
  {
    prop: 'supplier_name',
    label: '供应商',
    width: 130,
    sortable: true,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'part_no',
    label: '物料编码',
    width: 130,
    sortable: true,
    dataType: 'code',
    editable: true,
    editType: 'input'
  },
  {
    prop: 'part_name',
    label: '物料名称（型号）',
    minWidth: 160,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'defect_qty',
    label: '不合格数',
    width: 95,
    align: 'center',
    sortable: true,
    editable: true,
    editType: 'number'
  },
  {
    prop: 'defect_rate',
    label: '不良率',
    width: 90,
    align: 'center',
    editable: true,
    editType: 'input'
  },
  {
    prop: 'attachments',
    label: '现场照片',
    width: 140,
    align: 'center',
    dataType: 'image',
    editable: true
  },
  {
    prop: 'defect_type',
    label: '不合格类型',
    width: 135,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'defect_desc',
    label: '不合格描述',
    minWidth: 200,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'mrb_decision',
    label: '审理意见',
    width: 110,
    align: 'center',
    sortable: true,
    dataType: 'badge',
    editable: true,
    editType: 'select',
    options: ['退货', '让步接收', '让步', '内部返修', '挑选', '报废', '待审理'],
    colorMap: {
      退货: 'danger',
      报废: 'danger',
      让步接收: 'warning',
      让步: 'warning',
      内部返修: 'primary',
      挑选: 'info',
      待审理: 'info'
    }
  },
  {
    prop: 'duty_attribution',
    label: '责任归属',
    width: 120,
    align: 'center',
    editable: true,
    editType: 'select',
    options: ['供应商责任', '生产责任', '研发设计责任', '待定'],
    colorMap: {
      供应商责任: 'danger',
      生产责任: 'warning',
      研发设计责任: 'info',
      待定: 'info'
    }
  },
  {
    prop: 'status',
    label: '闭环状态',
    width: 100,
    align: 'center',
    sortable: true,
    dataType: 'badge',
    editable: true,
    editType: 'select',
    options: ['待审理', '改善中', '已验证', '已结案'],
    colorMap: {
      待审理: 'info',
      改善中: 'warning',
      已验证: 'primary',
      已结案: 'success'
    }
  },
  {
    prop: 'reporter',
    label: '反馈人',
    width: 100,
    editable: true,
    editType: 'input'
  },
  {
    prop: 'owner',
    label: '物料归属人',
    width: 100,
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
    if (filters.mrb_source && filters.mrb_source !== 'ALL') params.mrb_source = filters.mrb_source
    if (filters.mrb_decision && filters.mrb_decision !== 'ALL') params.mrb_decision = filters.mrb_decision
    if (filters.status && filters.status !== 'ALL') params.status = filters.status

    const res = await axios.get('/api/sqm/mrb/list', { params })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取 MRB 审理台账失败: ${err.response?.data?.detail || err.message}`)
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
  filters.mrb_source = 'ALL'
  filters.mrb_decision = 'ALL'
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

const handleCellChange = async (payload: { row: MrbRow; prop: string; value: any }) => {
  try {
    await axios.put(`/api/sqm/mrb/${payload.row.id}`, { [payload.prop]: payload.value })
    ElMessage.success('已自动保存')
  } catch (err: any) {
    ElMessage.error(`保存失败: ${err.response?.data?.detail || err.message}`)
    fetchData()
  }
}

const handleQuickAdd = async (payload: Record<string, any>, done: () => void) => {
  try {
    await axios.post('/api/sqm/mrb', {
      defect_desc: payload.defect_desc || '快捷登记异常',
      mrb_source: payload.mrb_source || (filters.mrb_source !== 'ALL' ? filters.mrb_source : 'IQC来料'),
      defect_qty: payload.defect_qty || 1,
      occurred_date: payload.occurred_date || new Date().toISOString().slice(0, 10),
      mrb_decision: payload.mrb_decision || '待审理',
      status: payload.status || '待审理'
    })
    ElMessage.success('已快速登记新 MRB 审理单')
    fetchData()
    done()
  } catch (err: any) {
    ElMessage.error(`登记失败: ${err.response?.data?.detail || err.message}`)
  }
}

const handleCreate = () => {
  mrbDetailDrawerRef.value?.openCreate(filters.mrb_source !== 'ALL' ? filters.mrb_source : 'IQC来料')
}

const handleEdit = (row: MrbRow) => {
  mrbDetailDrawerRef.value?.openEdit(row.id, false)
}

const openJudge = (row: MrbRow) => {
  mrbDetailDrawerRef.value?.openEdit(row.id, true)
}

const handleDelete = async (row: MrbRow) => {
  try {
    await axios.delete(`/api/sqm/mrb/${row.id}`)
    ElMessage.success(`MRB 单据 "${row.mrb_no}" 已删除`)
    fetchData()
  } catch (err: any) {
    ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
  }
}

const handleDrawerSuccess = () => {
  fetchData()
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
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
