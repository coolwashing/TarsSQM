<template>
  <div class="fmea-gallery-view">
    <div v-if="loading" class="gallery-empty">正在加载全库失效实拍与标准图鉴...</div>

    <div v-else-if="photoEntries.length === 0" class="gallery-empty">
      <p>暂无匹配的失效实拍或防错对比图</p>
      <span class="sub">可在画板中点选任意模块或热点，按 Ctrl+V 直接粘贴现场照片沉淀图鉴</span>
    </div>

    <div v-else class="gallery-grid">
      <div
        v-for="entry in photoEntries"
        :key="`${entry.item.id}_${entry.photoIdx}`"
        class="gallery-card"
      >
        <div class="gc-img-box" @click="previewEntry = entry">
          <img :src="entry.photo.url" :alt="entry.item.failure_mode" />
          <span class="gc-tag" :class="entry.photo.tag === 'OK' ? 'ok' : 'ng'">
            {{ entry.photo.tag === 'OK' ? 'OK 防错标准' : 'NG 失效实拍' }}
          </span>
          <span class="gc-risk" :class="`rk-${entry.item.risk_level.toLowerCase()}`">
            {{ entry.item.risk_level === 'HIGH' ? '高危' : entry.item.risk_level === 'LOW' ? '低危' : '中危' }}
          </span>
        </div>

        <div class="gc-body">
          <div class="gc-breadcrumb">
            <span v-if="entry.item.target_kind === 'shared_unit'" class="gc-shared-tag">
              共用本体 · {{ entry.item.target_id }}
            </span>
            <span v-else>{{ entry.item.board_name || '全局未分配' }}</span>
            <span v-if="entry.item.target_title_snapshot"> · {{ entry.item.target_title_snapshot }}</span>
          </div>
          <h4 class="gc-mode">{{ entry.item.failure_mode }}</h4>
          <p v-if="entry.item.failure_mech" class="gc-mech">{{ entry.item.failure_mech }}</p>

          <div class="gc-foot">
            <div class="gc-refs">
              <SoftRefChip
                v-for="(rf, idx) in (entry.item.linked_refs || []).slice(0, 2)"
                :key="idx"
                :item="rf"
              />
            </div>
            <button
              v-if="entry.item.board_id || (entry.item.target_kind === 'shared_unit' && entry.item.target_id)"
              type="button"
              class="locate-btn"
              @click="$emit('locate', entry.item)"
            >
              定位画板 ↗
            </button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog
      :model-value="!!previewEntry"
      :title="previewEntry?.item.failure_mode || '失效图鉴预览'"
      width="740px"
      append-to-body
      @update:model-value="(val: boolean) => { if (!val) previewEntry = null }"
    >
      <div v-if="previewEntry" class="preview-modal">
        <div class="pm-img-wrap">
          <img :src="previewEntry.photo.url" alt="高清图鉴" />
        </div>
        <div class="pm-info">
          <p><strong>失效机理：</strong>{{ previewEntry.item.failure_mech || '-' }}</p>
          <p v-if="previewEntry.item.prevention_measure"><strong>现行预防：</strong>{{ previewEntry.item.prevention_measure }}</p>
          <p v-if="previewEntry.item.detection_measure"><strong>现行探测：</strong>{{ previewEntry.item.detection_measure }}</p>
          <p v-else-if="previewEntry.item.control_measure"><strong>防错与探测：</strong>{{ previewEntry.item.control_measure }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { FmeaItem, FmeaPhoto } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import SoftRefChip from './SoftRefChip.vue'

const props = defineProps<{
  keyword: string
  highRiskOnly: boolean
  refreshTick: number
}>()

defineEmits<{
  (e: 'locate', item: FmeaItem): void
}>()

const loading = ref(false)
const items = ref<FmeaItem[]>([])
const previewEntry = ref<{ item: FmeaItem; photo: FmeaPhoto; photoIdx: number } | null>(null)

async function fetchPhotoItems() {
  loading.value = true
  try {
    const res = await fmeaApi.listItems({
      page: 1,
      page_size: 200,
      keyword: props.keyword || undefined,
      risk_level: props.highRiskOnly ? 'HIGH' : undefined,
      has_photo: true
    })
    items.value = res.items
  } finally {
    loading.value = false
  }
}

const photoEntries = computed(() => {
  const arr: { item: FmeaItem; photo: FmeaPhoto; photoIdx: number }[] = []
  for (const it of items.value) {
    ;(it.photos || []).forEach((ph, idx) => {
      arr.push({ item: it, photo: ph, photoIdx: idx })
    })
  }
  return arr
})

watch(() => [props.keyword, props.highRiskOnly, props.refreshTick], fetchPhotoItems)
onMounted(fetchPhotoItems)
</script>

<style scoped>
.fmea-gallery-view {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  padding: 18px 22px;
  background: #f8fafc;
}

.gallery-empty {
  padding: 80px 20px;
  text-align: center;
  color: #64748b;
  font-size: 13.5px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gallery-empty .sub {
  font-size: 12px;
  color: #94a3b8;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.gallery-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s, box-shadow 0.15s;
}

.gallery-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
}

.gc-img-box {
  position: relative;
  height: 164px;
  background: #0f172a;
  cursor: zoom-in;
  overflow: hidden;
}

.gc-img-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.gc-tag {
  position: absolute;
  left: 8px;
  top: 8px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 600;
  color: #fff;
}

.gc-tag.ng {
  background: rgba(220, 38, 38, 0.9);
}

.gc-tag.ok {
  background: rgba(5, 150, 105, 0.9);
}

.gc-risk {
  position: absolute;
  right: 8px;
  top: 8px;
  padding: 2px 7px;
  border-radius: 10px;
  font-size: 10.5px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.92);
}

.gc-risk.rk-high {
  color: #dc2626;
}

.gc-risk.rk-med {
  color: #d97706;
}

.gc-risk.rk-low {
  color: #059669;
}

.gc-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.gc-breadcrumb {
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gc-shared-tag {
  color: #0f766e;
  font-weight: 600;
}

.gc-mode {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
}

.gc-mech {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.gc-foot {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.gc-refs {
  display: flex;
  gap: 4px;
  overflow: hidden;
}

.locate-btn {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 5px;
  cursor: pointer;
  flex-shrink: 0;
}

.locate-btn:hover {
  background: #dbeafe;
}

.preview-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pm-img-wrap {
  background: #0f172a;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  justify-content: center;
}

.pm-img-wrap img {
  max-width: 100%;
  max-height: 58vh;
  object-fit: contain;
}

.pm-info {
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
}
</style>
