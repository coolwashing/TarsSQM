<template>
  <div class="soft-ref-input-wrap">
    <div class="tag-input-shell" :class="{ 'is-focused': isInputFocused }">
      <!-- 已选软关联胶囊列表（行内自适应紧凑排布） -->
      <SoftRefChip
        v-for="(r, idx) in modelValue"
        :key="`${r.type}_${r.code || ''}_${r.label}_${idx}`"
        :item="r"
        removable
        @remove="removeAt(idx)"
      />

      <!-- 搜索与自由回车输入区 -->
      <input
        v-model="queryText"
        type="text"
        class="ref-search-input"
        :placeholder="modelValue.length === 0 ? '搜索零件图号 / 供应商 / 问题单，或回车存自由标签...' : '+ 添加标签...'"
        @focus="onFocusInput"
        @blur="onBlurInput"
        @input="onQueryInput"
        @keydown.enter.prevent="onPressEnter"
        @keydown.backspace="onBackspace"
      />
    </div>

    <!-- 实时主数据联想下拉层 -->
    <div v-if="dropdownOpen" class="suggest-panel">
      <div v-if="loading" class="sug-hint">检索主数据中...</div>

      <template v-else>
        <div
          v-for="sug in suggestions"
          :key="`${sug.type}_${sug.ref_id}`"
          class="sug-row"
          @mousedown.prevent="pickSuggestion(sug)"
        >
          <span class="sug-type" :class="`t-${sug.type}`">{{ TYPE_NAMES[sug.type] || sug.type }}</span>
          <span class="sug-code">{{ sug.code }}</span>
          <span class="sug-label">{{ sug.label }}</span>
          <span v-if="sug.sub_info" class="sug-sub">{{ sug.sub_info }}</span>
        </div>

        <div
          v-if="queryText.trim()"
          class="sug-free-row"
          @mousedown.prevent="addFreeTag(queryText.trim())"
        >
          <span>+ 创建非硬关联自由标签：</span>
          <strong>「{{ queryText.trim() }}」</strong>
          <span class="enter-kbd">Enter</span>
        </div>

        <div v-else-if="suggestions.length === 0" class="sug-hint">
          输入编码搜索已建档主数据，或直接输入新名词回车存为自由标签
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FmeaLinkedRef, SoftRefSuggestion } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import SoftRefChip from './SoftRefChip.vue'

const props = defineProps<{
  modelValue: FmeaLinkedRef[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: FmeaLinkedRef[]): void
}>()

const TYPE_NAMES: Record<string, string> = {
  part: '零件',
  supplier: '供应商',
  issue: '问题单',
  project: '项目',
  ctq: 'CTQ'
}

const queryText = ref('')
const dropdownOpen = ref(false)
const loading = ref(false)
const isInputFocused = ref(false)
const suggestions = ref<SoftRefSuggestion[]>([])
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function fetchSuggestions(q: string) {
  loading.value = true
  try {
    suggestions.value = await fmeaApi.suggestSoftRefs(q)
  } catch {
    suggestions.value = []
  } finally {
    loading.value = false
  }
}

function onFocusInput() {
  isInputFocused.value = true
  dropdownOpen.value = true
  fetchSuggestions(queryText.value.trim())
}

function onBlurInput() {
  isInputFocused.value = false
  setTimeout(() => {
    dropdownOpen.value = false
  }, 160)
}

function onBackspace() {
  if (!queryText.value && props.modelValue.length > 0) {
    removeAt(props.modelValue.length - 1)
  }
}

function onQueryInput() {
  dropdownOpen.value = true
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchSuggestions(queryText.value.trim())
  }, 200)
}

function appendRef(newRef: FmeaLinkedRef) {
  const exists = props.modelValue.some(
    (r) => r.type === newRef.type && (r.code || '') === (newRef.code || '') && r.label === newRef.label
  )
  if (!exists) {
    emit('update:modelValue', [...props.modelValue, newRef])
  }
  queryText.value = ''
}

function pickSuggestion(sug: SoftRefSuggestion) {
  appendRef({
    type: sug.type,
    ref_id: sug.ref_id,
    code: sug.code,
    label: sug.label
  })
}

function addFreeTag(text: string) {
  if (!text) return
  appendRef({
    type: 'free',
    ref_id: null,
    code: null,
    label: text
  })
}

function onPressEnter() {
  const txt = queryText.value.trim()
  if (!txt) return
  const exactMatch = suggestions.value.find(
    (s) => s.code.toLowerCase() === txt.toLowerCase() || s.label.toLowerCase() === txt.toLowerCase()
  )
  if (exactMatch) {
    pickSuggestion(exactMatch)
  } else {
    addFreeTag(txt)
  }
}

function removeAt(idx: number) {
  const copy = [...props.modelValue]
  copy.splice(idx, 1)
  emit('update:modelValue', copy)
}
</script>

<style scoped>
.soft-ref-input-wrap {
  position: relative;
  width: 100%;
}

.tag-input-shell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  min-height: 32px;
  padding: 4px 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  transition: all 0.15s ease;
  cursor: text;
}

.tag-input-shell:hover {
  border-color: #cbd5e1;
}

.tag-input-shell.is-focused {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.ref-search-input {
  flex: 1;
  min-width: 110px;
  height: 22px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12px;
  color: #1e293b;
  padding: 0;
}

.ref-search-input::placeholder {
  color: #94a3b8;
}

.suggest-panel {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  max-height: 220px;
  overflow-y: auto;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
  padding: 4px;
  z-index: 99;
}

.sug-row {
  padding: 6px 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.12s;
}

.sug-row:hover {
  background: #f1f5f9;
}

.sug-type {
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 600;
  flex-shrink: 0;
}

.sug-type.t-part {
  background: #eff6ff;
  color: #1d4ed8;
}

.sug-type.t-supplier {
  background: #ecfdf5;
  color: #047857;
}

.sug-type.t-issue {
  background: #fff1f2;
  color: #be123c;
}

.sug-type.t-project,
.sug-type.t-ctq {
  background: #f5f3ff;
  color: #6d28d9;
}

.sug-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 600;
  color: #0f172a;
  flex-shrink: 0;
}

.sug-label {
  flex: 1;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sug-sub {
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}

.sug-free-row {
  margin-top: 2px;
  padding: 7px 8px;
  border-top: 1px dashed #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  color: #2563eb;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.sug-free-row:hover {
  background: #eff6ff;
}

.enter-kbd {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
}

.sug-hint {
  padding: 10px;
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
}
</style>
