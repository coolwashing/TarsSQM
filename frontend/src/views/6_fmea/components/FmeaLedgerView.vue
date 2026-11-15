<template>
  <div class="fmea-ledger-view">
    <DataTable
      :columns="columns"
      :data="rows"
      :loading="loading"
      :pagination="pagination"
      storage-key="fmea_global_ledger"
      import-key="fmea_item"
      import-title="FMEA风险与防错经验台账"
      show-actions
      action-width="165px"
      entity-label="FMEA机理卡"
      :row-label-key="(r: FmeaItem) => `${r.fmea_code} (${r.failure_mode})`"
      allow-quick-add
      quick-add-placeholder="极速记一条潜在失效模式（回车直接入库，无需先填S/O/D）..."
      :quick-add-defaults="{ fmea_type: 'DFMEA', risk_level: 'MED' }"
      @refresh="fetchLedger"
      @page-change="onPageChange"
      @size-change="onSizeChange"
      @cell-change="onCellChange"
      @quick-add="onQuickAdd"
      @edit="$emit('edit-item', $event)"
      @delete="onDeleteRow"
    >
      <template #search>
        <div class="ledger-filters">
          <el-select
            v-model="localBoardFilter"
            placeholder="全部模块画板"
            clearable
            size="small"
            style="width: 176px"
            @change="onFilterChange"
          >
            <el-option
              v-for="b in boards"
              :key="b.id"
              :label="`${b.group_name} / ${b.name}`"
              :value="b.id"
            />
          </el-select>

          <el-select
            v-model="localTypeFilter"
            placeholder="全部类型"
            clearable
            size="small"
            style="width: 128px"
            @change="onFilterChange"
          >
            <el-option label="DFMEA 设计" value="DFMEA" />
            <el-option label="PFMEA 工艺" value="PFMEA" />
            <el-option label="历史教训" value="LESSON" />
          </el-select>
        </div>
      </template>

      <template #toolbar>
        <el-button type="primary" size="small" @click="$emit('create-global-item')">
          + 新建 FMEA 条目
        </el-button>
      </template>

      <template #board_spot="{ row }">
        <div class="spot-cell">
          <span v-if="row.target_kind === 'shared_unit'" class="spot-shared-pill">
            共用本体 · {{ row.target_id }}
          </span>
          <span v-else class="spot-board">{{ row.board_name || '未分配画板' }}</span>
          <span v-if="row.target_title_snapshot" class="spot-sub">· {{ row.target_title_snapshot }}</span>
        </div>
      </template>

      <template #risk_slot="{ row }">
        <span class="ledger-risk-pill" :class="`rk-${(row.risk_level || 'MED').toLowerCase()}`">
          <i class="dot" />
          {{ row.risk_level === 'HIGH' ? '高危' : row.risk_level === 'LOW' ? '低危' : '中危' }}
          <span v-if="row.rpn" class="rpn-num">({{ row.rpn }})</span>
        </span>
      </template>

      <template #refs_slot="{ row }">
        <div v-if="row.linked_refs?.length" class="refs-cell">
          <SoftRefChip
            v-for="(rf, idx) in row.linked_refs.slice(0, 3)"
            :key="idx"
            :item="rf"
          />
          <span v-if="row.linked_refs.length > 3" class="more-cnt">+{{ row.linked_refs.length - 3 }}</span>
        </div>
        <span v-else class="muted">-</span>
      </template>

      <template #photos_slot="{ row }">
        <span v-if="row.photos?.length" class="photo-badge">{{ row.photos.length }} 张图</span>
        <span v-else class="muted">-</span>
      </template>

      <template #action-prefix="{ row }">
        <el-button
          v-if="row.board_id || (row.target_kind === 'shared_unit' && row.target_id)"
          link
          type="primary"
          size="small"
          @click.stop="$emit('locate', row)"
        >
          定位画板
        </el-button>
      </template>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import DataTable from '@/components/common/DataTable/index.vue'
import { getStoredTablePageSize, type TableColumn, type CellChangeEvent } from '@/components/common/DataTable/types'
import type { FmeaItem, FmeaBoardSummary } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import SoftRefChip from './SoftRefChip.vue'

const props = defineProps<{
  boards: FmeaBoardSummary[]
  keyword: string
  highRiskOnly: boolean
  initialRefCode?: string
  refreshTick: number
}>()

const emit = defineEmits<{
  (e: 'locate', item: FmeaItem): void
  (e: 'edit-item', item: FmeaItem): void
  (e: 'create-global-item'): void
  (e: 'mutated'): void
}>()

const loading = ref(false)
const rows = ref<FmeaItem[]>([])
const localBoardFilter = ref<number | undefined>(undefined)
const localTypeFilter = ref<string>('')

const pagination = reactive({
  page: 1,
  pageSize: getStoredTablePageSize('fmea_global_ledger', 20),
  total: 0
})

const columns: TableColumn[] = [
  { prop: 'fmea_code', label: 'FMEA编号', width: 142, sortable: true, dataType: 'code', quickAddDisabled: true },
  {
    prop: 'fmea_type',
    label: '类型',
    width: 96,
    editable: true,
    editType: 'select',
    editOptions: [
      { label: 'DFMEA', value: 'DFMEA', color: 'primary' },
      { label: 'PFMEA', value: 'PFMEA', color: 'success' },
      { label: '历史教训', value: 'LESSON', color: 'warning' }
    ]
  },
  { prop: 'board_spot', label: '所属画板 / 挂载部位', minWidth: 185, slotName: 'board_spot', quickAddDisabled: true },
  { prop: 'failure_mode', label: '潜在失效模式', minWidth: 200, editable: true, editType: 'input' },
  { prop: 'failure_mech', label: '失效机理与根因', minWidth: 200, editable: true, editType: 'input' },
  { prop: 'prevention_measure', label: '现行预防控制 (设计防呆)', minWidth: 190, editable: true, editType: 'input' },
  { prop: 'detection_measure', label: '现行探测控制 (检验验证)', minWidth: 190, editable: true, editType: 'input' },
  { prop: 'risk_level', label: '风险等级', width: 112, slotName: 'risk_slot', quickAddDisabled: true },
  { prop: 'linked_refs', label: '软关联短码 / 标签', minWidth: 195, slotName: 'refs_slot', quickAddDisabled: true },
  { prop: 'photos', label: '实拍', width: 76, align: 'center', slotName: 'photos_slot', quickAddDisabled: true }
]

async function fetchLedger() {
  loading.value = true
  try {
    const res = await fmeaApi.listItems({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: props.keyword || undefined,
      board_id: localBoardFilter.value,
      fmea_type: localTypeFilter.value || undefined,
      risk_level: props.highRiskOnly ? 'HIGH' : undefined,
      ref_code: props.initialRefCode || undefined
    })
    rows.value = (res.items || []).map((it) => ({
      ...it,
      prevention_measure: it.prevention_measure || (!it.detection_measure ? it.control_measure : ''),
      detection_measure: it.detection_measure || ''
    }))
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  pagination.page = 1
  fetchLedger()
}

function onPageChange(p: number) {
  pagination.page = p
  fetchLedger()
}

function onSizeChange(sz: number) {
  pagination.pageSize = sz
  pagination.page = 1
  fetchLedger()
}

async function onCellChange(ev: CellChangeEvent) {
  try {
    await fmeaApi.updateItem(ev.row.id, { [ev.prop]: ev.value })
    ElMessage.success('已保存修改')
    fetchLedger()
    emit('mutated')
  } catch {
    ElMessage.error('单元格更新失败')
  }
}

async function onQuickAdd(draft: Record<string, any>, done?: () => void) {
  const mode = String(draft.failure_mode || draft.title || '').trim()
  if (!mode) {
    done?.()
    return
  }
  try {
    await fmeaApi.createItem({
      board_id: localBoardFilter.value || null,
      target_kind: 'unassigned',
      fmea_type: draft.fmea_type || 'DFMEA',
      risk_level: draft.risk_level || 'MED',
      failure_mode: mode
    })
    ElMessage.success('已极速记入 FMEA 全局台账')
    done?.()
    fetchLedger()
    emit('mutated')
  } catch {
    ElMessage.error('极速新增失败')
  }
}

async function onDeleteRow(row: FmeaItem) {
  try {
    await fmeaApi.deleteItem(row.id)
    ElMessage.success('已移除该条 FMEA 记录')
    fetchLedger()
    emit('mutated')
  } catch {
    ElMessage.error('删除失败')
  }
}

watch(() => [props.keyword, props.highRiskOnly, props.initialRefCode, props.refreshTick], () => {
  pagination.page = 1
  fetchLedger()
})

onMounted(fetchLedger)
</script>

<style scoped>
.fmea-ledger-view {
  flex: 1;
  height: 100%;
  padding: 12px 16px;
  background: #f8fafc;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ledger-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spot-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.spot-board {
  font-weight: 500;
  color: #1e293b;
}

.spot-shared-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: 5px;
  font-size: 11.5px;
  font-weight: 600;
  background: #f0fdfa;
  color: #0f766e;
  border: 1px solid #99f6e4;
}

.spot-sub {
  color: #64748b;
  font-size: 12px;
}

.ledger-risk-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11.5px;
  font-weight: 600;
}

.ledger-risk-pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.ledger-risk-pill.rk-high {
  background: #fef2f2;
  color: #b91c1c;
}

.ledger-risk-pill.rk-high .dot {
  background: #ef4444;
}

.ledger-risk-pill.rk-med {
  background: #fffbeb;
  color: #b45309;
}

.ledger-risk-pill.rk-med .dot {
  background: #f59e0b;
}

.ledger-risk-pill.rk-low {
  background: #ecfdf5;
  color: #047857;
}

.ledger-risk-pill.rk-low .dot {
  background: #10b981;
}

.rpn-num {
  font-weight: 400;
  opacity: 0.8;
}

.refs-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

.more-cnt {
  font-size: 11px;
  color: #64748b;
}

.photo-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #eff6ff;
  color: #1d4ed8;
}

.muted {
  color: #94a3b8;
}
</style>
