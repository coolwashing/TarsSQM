<template>
  <el-popover
    placement="top"
    :width="276"
    trigger="click"
    @show="loadLiveSnapshot"
  >
    <template #reference>
      <span
        class="soft-ref-chip"
        :class="[`type-${item.type || 'free'}`, { 'is-free': item.type === 'free' || !item.code }]"
        :title="item.code ? `${item.code} · ${item.label}` : item.label"
        @click.stop
      >
        <span class="chip-code">{{ displayShortText }}</span>
        <button
          v-if="removable"
          type="button"
          class="chip-rm"
          title="移除关联"
          @click.stop="$emit('remove')"
        >
          ×
        </button>
      </span>
    </template>

    <div class="ref-snap-pop">
      <div class="snap-head">
        <span class="snap-badge" :class="`type-${item.type || 'free'}`">{{ typeLabel }}</span>
        <span v-if="snapshot?.status" class="snap-status" :class="{ muted: !snapshot.exists }">
          {{ snapshot.status }}
        </span>
      </div>

      <div v-if="loading" class="snap-loading">正在穿透读取实时档案...</div>
      <template v-else-if="snapshot">
        <div class="snap-title">{{ snapshot.label }}</div>
        <div class="snap-lines">
          <div v-for="(ln, idx) in snapshot.detail_lines" :key="idx" class="snap-line">
            {{ ln }}
          </div>
        </div>
        <div v-if="snapshot.jump_route" class="snap-foot">
          <button type="button" class="jump-link-btn" @click="goToTargetRoute">
            前往对应台账查看 ↗
          </button>
        </div>
      </template>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { FmeaLinkedRef, SoftRefSnapshot } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'

const props = defineProps<{
  item: FmeaLinkedRef
  removable?: boolean
  showLabelWithCode?: boolean
}>()

defineEmits<{
  (e: 'remove'): void
}>()

const router = useRouter()
const loading = ref(false)
const snapshot = ref<SoftRefSnapshot | null>(null)

const TYPE_MAP: Record<string, string> = {
  part: '零部件',
  supplier: '供应商',
  issue: '质量问题',
  project: '工程项目',
  ctq: 'CTQ特性',
  free: '自由标签'
}

const typeLabel = computed(() => TYPE_MAP[props.item.type] || '软关联')

const displayShortText = computed(() => {
  if (props.item.code) {
    return props.item.code
  }
  return props.item.label.length > 12 ? `${props.item.label.slice(0, 11)}…` : props.item.label
})

async function loadLiveSnapshot() {
  loading.value = true
  try {
    const res = await fmeaApi.resolveSoftRefs([props.item])
    snapshot.value = res[0] || null
  } catch {
    snapshot.value = {
      key: '',
      type: props.item.type,
      exists: false,
      code: props.item.code,
      label: props.item.label,
      status: '本地快照',
      detail_lines: [props.item.code ? `${props.item.code} · ${props.item.label}` : props.item.label]
    }
  } finally {
    loading.value = false
  }
}

function goToTargetRoute() {
  if (!snapshot.value?.jump_route) return
  router.push({
    path: snapshot.value.jump_route,
    query: snapshot.value.jump_keyword ? { keyword: snapshot.value.jump_keyword } : undefined
  })
}
</script>

<style scoped>
.soft-ref-chip {
  height: 21px;
  padding: 0 7px;
  height: 22px;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: 1px solid transparent;
  background: #f1f5f9;
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  transition: all 0.12s ease;
  user-select: none;
}

.soft-ref-chip:hover {
  border-color: #cbd5e1;
  background: #e2e8f0;
}

.soft-ref-chip.type-part {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #334155;
}

.soft-ref-chip.type-supplier {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.soft-ref-chip.type-issue {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.soft-ref-chip.type-project,
.soft-ref-chip.type-ctq {
  background: #f5f3ff;
  border-color: #ddd6fe;
  color: #5b21b6;
}

.soft-ref-chip.is-free {
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  color: #475569;
  font-family: inherit;
  font-weight: 500;
}

.chip-code {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-rm {
  border: none;
  background: transparent;
  color: currentColor;
  opacity: 0.65;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  padding: 0 1px;
}

.chip-rm:hover {
  opacity: 1;
}

.ref-snap-pop {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.snap-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.snap-badge {
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #334155;
}

.snap-status {
  font-size: 11px;
  color: #059669;
  font-weight: 500;
}

.snap-status.muted {
  color: #64748b;
}

.snap-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.snap-lines {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11.5px;
  color: #475569;
  line-height: 1.45;
}

.snap-loading {
  font-size: 12px;
  color: #64748b;
  padding: 6px 0;
}

.snap-foot {
  padding-top: 6px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
}

.jump-link-btn {
  border: none;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11.5px;
  font-weight: 500;
  padding: 4px 9px;
  border-radius: 5px;
  cursor: pointer;
}

.jump-link-btn:hover {
  background: #dbeafe;
}
</style>

