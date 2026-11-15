<template>
  <el-dialog
    :model-value="modelValue"
    :title="editingItem ? `编辑机理卡 · ${editingItem.fmea_code}` : '补充 FMEA 失效机理与防错卡'"
    width="860px"
    class="fmea-item-dialog"
    destroy-on-close
    append-to-body
    top="4vh"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="fmea-dialog-body" @paste="onDialogPaste">
      <!-- 1. 顶部当前分析要素与类型定级状态栏 -->
      <div class="dialog-context-bar">
        <div class="dcb-left">
          <!-- 关联目标要素徽章 -->
          <div v-if="targetTitleSnapshot || defaultPartCode" class="target-badge-pill" :title="targetTitleSnapshot">
            <span class="tbp-dot" />
            <span class="tbp-kind">{{ formatTargetKind(targetKind) }}</span>
            <span class="tbp-sep">|</span>
            <strong class="tbp-title">{{ targetTitleSnapshot || defaultPartCode }}</strong>
          </div>

          <!-- DFMEA / PFMEA / 历史教训轻量切换徽章 (智能推导 + 点击快捷轮转) -->
          <button
            type="button"
            class="fmea-type-pill"
            :class="`type-${form.fmea_type.toLowerCase()}`"
            title="点击切换：DFMEA 设计 / PFMEA 工艺 / 历史教训"
            @click="cycleFmeaType"
          >
            <span class="ftp-tag">{{ form.fmea_type === 'PFMEA' ? 'PFMEA 工艺' : (form.fmea_type === 'LESSON' ? '历史教训' : 'DFMEA 设计') }}</span>
            <span class="ftp-arrow">▾</span>
          </button>

          <!-- 多父级共用件双轨归属开关：本体固有风险 vs 当前画板专属安装工况 -->
          <div v-if="effectiveSharedUnitCode" class="bom-scope-bar">
            <button
              type="button"
              class="bs-pill"
              :class="{ active: storeAsSharedUnit }"
              @click="storeAsSharedUnit = true"
            >
              共用本体 ({{ effectiveSharedUnitCode }})
            </button>
            <button
              v-if="boardId && targetId && targetKind !== 'shared_unit'"
              type="button"
              class="bs-pill"
              :class="{ active: !storeAsSharedUnit }"
              @click="storeAsSharedUnit = false"
            >
              仅当前画板专属
            </button>
          </div>
        </div>

        <div class="dcb-right">
          <!-- 风险定级 -->
          <div class="risk-group">
            <button
              v-for="rk in RISK_OPTS"
              :key="rk.value"
              type="button"
              class="rk-pill"
              :class="[`rk-${rk.value.toLowerCase()}`, { active: form.risk_level === rk.value }]"
              @click="form.risk_level = rk.value"
            >
              <i class="dot" />{{ rk.label }}
            </button>

            <!-- S·O·D 评分展开按钮 -->
            <button
              type="button"
              class="sod-toggle-btn"
              :class="{ active: useSod }"
              :title="useSod ? '点击折叠 S·O·D 评分条' : '展开严重度、频度、探测度评分滑块'"
              @click="toggleSod"
            >
              {{ useSod ? `RPN=${computedRpn} (折叠)` : '+ S·O·D' }}
            </button>
          </div>
        </div>
      </div>

      <!-- S·O·D 紧凑评分条 (按需展开) -->
      <div v-if="useSod" class="sod-strip">
        <div class="sod-col">
          <span class="sod-lbl">严重度 S: <strong>{{ form.severity }}</strong></span>
          <el-slider v-model="form.severity" :min="1" :max="10" :step="1" size="small" @change="syncRiskFromSod" />
        </div>
        <div class="sod-col">
          <span class="sod-lbl">频度 O: <strong>{{ form.occurrence }}</strong></span>
          <el-slider v-model="form.occurrence" :min="1" :max="10" :step="1" size="small" @change="syncRiskFromSod" />
        </div>
        <div class="sod-col">
          <span class="sod-lbl">探测度 D: <strong>{{ form.detection }}</strong></span>
          <el-slider v-model="form.detection" :min="1" :max="10" :step="1" size="small" @change="syncRiskFromSod" />
        </div>
        <div class="sod-badge">
          <span class="sod-rpn-lbl">RPN</span>
          <span class="sod-rpn-val">{{ computedRpn }}</span>
        </div>
      </div>

      <!-- 2. 【核心失效现象与现场实拍】(失效描述 + 现场图文同框，支持直接 Ctrl+V 粘贴) -->
      <div class="phenomenon-card">
        <div class="p-title-head">
          <span class="p-label">潜在失效模式 <span class="req">*</span></span>
          <div class="p-photo-actions">
            <span class="paste-hint">可按 <kbd>Ctrl+V</kbd> 任意粘贴实拍图</span>
            <button type="button" class="mini-upload-btn ng" @click="pickPhoto('NG')">+ 上传 NG 实拍</button>
            <button type="button" class="mini-upload-btn ok" @click="pickPhoto('OK')">+ 上传 OK 标准</button>
            <input
              ref="photoFileRef"
              type="file"
              accept="image/*"
              style="display: none"
              @change="onPhotoFileSelected"
            />
          </div>
        </div>

        <input
          v-model="form.failure_mode"
          type="text"
          class="phenomenon-input"
          placeholder="简明描述失效表现（如：定子引出线根部灌封胶边缘振动割裂绝缘皮）*"
          autofocus
        />

        <!-- 现场实拍照片直观预览栏 (图文同框) -->
        <div v-if="form.photos.length > 0" class="inline-photo-grid">
          <div v-for="(ph, idx) in form.photos" :key="ph.id || idx" class="inline-photo-item">
            <div class="ph-img-box">
              <img :src="ph.url" alt="失效实拍" />
              <button
                type="button"
                class="ph-tag-btn"
                :class="ph.tag === 'OK' ? 'ok' : 'ng'"
                title="点击切换 NG / OK 标签"
                @click="ph.tag = ph.tag === 'NG' ? 'OK' : 'NG'"
              >
                {{ ph.tag === 'OK' ? 'OK 标准' : 'NG 失效' }}
              </button>
              <button type="button" class="ph-del-btn" title="移除此图" @click="form.photos.splice(idx, 1)">×</button>
            </div>
            <input
              v-model="ph.caption"
              type="text"
              class="ph-mini-caption"
              placeholder="简短图注..."
            />
          </div>
        </div>
      </div>

      <!-- 3. 【深入因果分析】失效机理与根因 vs 潜在失效后果 (双栏并排) -->
      <div class="causal-split-row">
        <!-- 1) 失效机理与根因 -->
        <div class="causal-cell mech-cell">
          <div class="cell-head">
            <span class="cell-indicator warm" />
            <span class="cell-title">失效机理与根因</span>
          </div>
          <textarea
            v-model="form.failure_mech"
            rows="3"
            class="cell-textarea"
            placeholder="物理/微观机理或工艺失控原因（如：环氧灌封胶收口呈锐边，高频谐振下硅胶线护套疲劳破损）..."
          />
        </div>

        <!-- 2) 潜在失效后果 -->
        <div class="causal-cell effect-cell">
          <div class="cell-head">
            <span class="cell-indicator slate" />
            <span class="cell-title">潜在失效后果</span>
          </div>
          <textarea
            v-model="form.failure_effect"
            rows="3"
            class="cell-textarea"
            placeholder="对模组功能、寿命、整机安全或产线良率影响（如：定子相线对机壳耐压击穿短路）..."
          />
        </div>
      </div>

      <!-- 4. 【现行双轨控制对策】现行预防控制 vs 现行探测控制 (双栏并排分开) -->
      <div class="control-split-row">
        <!-- 1) 现行预防控制 -->
        <div class="causal-cell prevent-cell">
          <div class="cell-head">
            <span class="cell-indicator blue" />
            <span class="cell-title">现行预防控制</span>
          </div>
          <textarea
            v-model="form.prevention_measure"
            rows="2"
            class="cell-textarea"
            placeholder="前端如何防范？图纸红线、防呆工装夹具、公差裕量..."
          />
        </div>

        <!-- 2) 现行探测控制 -->
        <div class="causal-cell detect-cell">
          <div class="cell-head">
            <span class="cell-indicator emerald" />
            <span class="cell-title">现行探测控制</span>
          </div>
          <textarea
            v-model="form.detection_measure"
            rows="2"
            class="cell-textarea"
            placeholder="后端如何抓出？出厂检验、在线扫描、耐压试验判据..."
          />
        </div>
      </div>

      <!-- 5. 底部业务闭环协同栏 (标签 + 质量问题单绑定 + 改进任务派发) -->
      <div class="bottom-integration-section">
        <!-- 关联标签行 -->
        <div class="bi-row">
          <span class="bi-lbl">关联标签:</span>
          <div class="bi-content">
            <SoftRefTagInput v-model="form.linked_refs" />
          </div>
        </div>

        <!-- 质量问题单挂接与改进任务闭环行 -->
        <div class="bi-row bi-actions-row">
          <!-- 左侧：现场质量异常单挂接 -->
          <div class="bi-col">
            <span class="bi-lbl">🚨 现场问题单:</span>
            <div class="bi-chips">
              <div
                v-for="iss in linkedIssues"
                :key="iss.code"
                class="qi-mini-chip"
              >
                <span class="qic-tag">事故</span>
                <span class="qic-code">{{ iss.code }}</span>
                <span class="qic-title" :title="iss.label">{{ iss.label }}</span>
                <button type="button" class="qic-del" title="取消挂接" @click="removeLinkedIssue(iss.code)">×</button>
              </div>

              <button
                type="button"
                class="bi-add-btn"
                :class="{ active: showIssuePicker }"
                @click="toggleIssuePicker"
              >
                {{ showIssuePicker ? '收起候选' : '+ 挂接质量单' }}
              </button>
            </div>
          </div>

          <!-- 右侧：驱动改进任务闭环 -->
          <div class="bi-col">
            <span class="bi-lbl">📋 改进任务:</span>
            <div class="bi-chips">
              <div
                v-for="tsk in linkedTasks"
                :key="tsk.id"
                class="task-mini-chip"
                :class="`status-${tsk.status.toLowerCase()}`"
                :title="tsk.title"
              >
                <span class="tmc-code">{{ tsk.task_code }}</span>
                <span class="tmc-status">{{ tsk.status === 'DONE' ? '已完成' : '整改中' }}</span>
                <span class="tmc-name">{{ tsk.assignee_name || '待认领' }}</span>
              </div>

              <button
                type="button"
                class="bi-add-btn task-btn"
                @click="openTaskCreate"
              >
                + 派发整改任务
              </button>
            </div>
          </div>
        </div>

        <!-- 质量单展开检索列表 -->
        <div v-if="showIssuePicker" class="qi-picker-panel">
          <div class="qi-search-row">
            <input
              v-model="issueSearchText"
              type="text"
              class="qi-search-input"
              placeholder="输入问题单号 (如 QI-...)、标题、零件图号检索质量事故..."
              @input="onSearchIssues"
            />
            <span v-if="loadingIssues" class="qi-loading-txt">检索中...</span>
          </div>

          <div class="qi-candidate-list">
            <div
              v-for="iss in candidateIssues"
              :key="iss.id"
              class="qi-candidate-item"
              :class="{ linked: isIssueLinked(iss.issue_no) }"
              @click="pickQualityIssue(iss)"
            >
              <div class="qci-main">
                <span class="qci-badge" :class="`sev-${(iss.severity || '一般')}`">
                  {{ iss.severity || '一般' }}
                </span>
                <span class="qci-no">{{ iss.issue_no }}</span>
                <span class="qci-title" :title="iss.title">{{ iss.title }}</span>
              </div>
              <div class="qci-meta">
                <span v-if="iss.part_no" class="qci-part">{{ iss.part_no }}</span>
                <span class="qci-status">{{ iss.status }}</span>
                <button type="button" class="qci-action">
                  {{ isIssueLinked(iss.issue_no) ? '已挂接 √' : '+ 挂接对标' }}
                </button>
              </div>
            </div>

            <div v-if="!loadingIssues && candidateIssues.length === 0" class="qi-empty-tip">
              暂未找到匹配的现场质量问题，可尝试在上方输入其他关键词
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 派发改进任务轻量弹窗 -->
    <el-dialog
      v-model="showTaskCreateDialog"
      title="派发 FMEA 闭环改进任务"
      width="460px"
      append-to-body
      destroy-on-close
    >
      <div class="task-dialog-form">
        <div class="tdf-row">
          <label>任务标题 <span class="req">*</span></label>
          <el-input v-model="taskForm.title" placeholder="改进任务标题..." />
        </div>
        <div class="tdf-row">
          <label>责任人</label>
          <el-input v-model="taskForm.assignee_name" placeholder="如：李工 (研发/工艺)" />
        </div>
        <div class="tdf-split">
          <div class="tdf-row">
            <label>优先级</label>
            <el-select v-model="taskForm.priority" style="width: 100%;">
              <el-option label="高 (HIGH)" value="HIGH" />
              <el-option label="中 (MEDIUM)" value="MEDIUM" />
              <el-option label="紧要 (URGENT)" value="URGENT" />
              <el-option label="低 (LOW)" value="LOW" />
            </el-select>
          </div>
          <div class="tdf-row">
            <label>截止日期</label>
            <el-date-picker v-model="taskForm.due_date" type="date" value-format="YYYY-MM-DD" placeholder="整改截止" style="width: 100%;" />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showTaskCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingTask" @click="submitCreateTask">确认派发</el-button>
      </template>
    </el-dialog>

    <template #footer>
      <div class="dlg-foot">
        <el-button size="default" @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" size="default" :loading="saving || uploading" @click="handleSave">
          保存机理卡
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FmeaItem, FmeaType, RiskLevel, FmeaPhoto, FmeaLinkedRef, TargetKind } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import { taskApi } from '@/api/task'
import type { TaskItem, TaskPriority } from '@/types/task'
import { useFmeaUpload } from '@/views/6_fmea/composables/useFmeaUpload'
import SoftRefTagInput from './SoftRefTagInput.vue'

const props = defineProps<{
  modelValue: boolean
  boardId: number | null
  targetKind: TargetKind
  targetId: string | null
  targetTitleSnapshot?: string
  sharedUnitCode?: string | null
  defaultPartCode?: string
  editingItem?: FmeaItem | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved', item: FmeaItem): void
}>()

const RISK_OPTS: { label: string; value: RiskLevel }[] = [
  { label: '高危', value: 'HIGH' },
  { label: '中危', value: 'MED' },
  { label: '低危', value: 'LOW' }
]

function formatTargetKind(kind?: TargetKind): string {
  switch (kind) {
    case 'node': return '工序/模块'
    case 'pin': return '图纸热点'
    case 'edge': return '配合接口'
    case 'shared_unit': return '共用件'
    default: return '要素'
  }
}

function inferFmeaType(kind?: TargetKind, title?: string): FmeaType {
  if (kind === 'shared_unit') return 'DFMEA'
  const t = (title || '').toLowerCase()
  if (
    t.includes('工序') ||
    t.includes('产线') ||
    t.includes('eol') ||
    t.includes('装配') ||
    t.includes('铣齿') ||
    t.includes('加工') ||
    t.includes('op-')
  ) {
    return 'PFMEA'
  }
  return 'DFMEA'
}

const { uploading, uploadImageFile, extractImagesFromClipboard } = useFmeaUpload()
const saving = ref(false)
const useSod = ref(false)
const storeAsSharedUnit = ref(false)
const photoFileRef = ref<HTMLInputElement | null>(null)
const pendingPhotoTag = ref<'NG' | 'OK'>('NG')

const effectiveSharedUnitCode = computed(() => {
  if (props.editingItem?.target_kind === 'shared_unit' && props.editingItem.target_id) {
    return props.editingItem.target_id
  }
  return props.sharedUnitCode || null
})

const form = reactive<{
  fmea_type: FmeaType
  risk_level: RiskLevel
  severity: number
  occurrence: number
  detection: number
  failure_mode: string
  failure_mech: string
  failure_effect: string
  control_measure: string
  prevention_measure: string
  detection_measure: string
  photos: FmeaPhoto[]
  linked_refs: FmeaLinkedRef[]
  source_issue_no: string | null
}>({
  fmea_type: 'DFMEA',
  risk_level: 'HIGH',
  severity: 7,
  occurrence: 4,
  detection: 4,
  failure_mode: '',
  failure_mech: '',
  failure_effect: '',
  control_measure: '',
  prevention_measure: '',
  detection_measure: '',
  photos: [],
  linked_refs: [],
  source_issue_no: null
})

function cycleFmeaType() {
  if (form.fmea_type === 'DFMEA') {
    form.fmea_type = 'PFMEA'
  } else if (form.fmea_type === 'PFMEA') {
    form.fmea_type = 'LESSON'
  } else {
    form.fmea_type = 'DFMEA'
  }
}

const computedRpn = computed(() => form.severity * form.occurrence * form.detection)

// 质量问题单挑选与智能对标相关性状态
const showIssuePicker = ref(false)
const issueSearchText = ref('')
const loadingIssues = ref(false)
const candidateIssues = ref<any[]>([])
let searchTimer: any = null

async function loadCandidateIssues() {
  loadingIssues.value = true
  try {
    const res = await fmeaApi.listQualityIssues({
      keyword: issueSearchText.value.trim() || undefined,
      page: 1,
      page_size: 15
    })
    candidateIssues.value = res.items || []
  } catch {
    candidateIssues.value = []
  } finally {
    loadingIssues.value = false
  }
}

function toggleIssuePicker() {
  showIssuePicker.value = !showIssuePicker.value
  if (showIssuePicker.value && candidateIssues.value.length === 0) {
    loadCandidateIssues()
  }
}

function onSearchIssues() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadCandidateIssues()
  }, 250)
}

function isIssueLinked(issueNo: string) {
  return form.linked_refs.some((r) => r.type === 'issue' && r.code === issueNo)
}

function pickQualityIssue(iss: any) {
  if (isIssueLinked(iss.issue_no)) {
    removeLinkedIssue(iss.issue_no)
    return
  }
  form.linked_refs.push({
    type: 'issue',
    ref_id: iss.id,
    code: iss.issue_no,
    label: iss.title
  })
  if (!form.source_issue_no) {
    form.source_issue_no = iss.issue_no
  }
  if (!form.failure_mode?.trim()) {
    form.failure_mode = iss.title
  }
  const cleanDesc = (iss.issue_desc || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  if (!form.failure_mech?.trim() && cleanDesc) {
    form.failure_mech = cleanDesc
  }
  const cleanSol = (iss.solution || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  if (!form.prevention_measure?.trim() && cleanSol) {
    form.prevention_measure = cleanSol
  }
  if (Array.isArray(iss.attachments) && form.photos.length === 0) {
    for (const att of iss.attachments) {
      if (att.url && /\.(png|jpe?g|webp|svg|gif)$/i.test(att.url)) {
        form.photos.push({
          id: `ph_iss_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          url: att.url,
          tag: 'NG',
          caption: `${iss.issue_no} 现场实拍`
        })
      }
    }
  }
  ElMessage.success(`已挂接现场问题单「${iss.issue_no}」，智能对齐真实失效与对策`)
}

function removeLinkedIssue(issueNo: string) {
  form.linked_refs = form.linked_refs.filter((r) => !(r.type === 'issue' && r.code === issueNo))
  if (form.source_issue_no === issueNo) {
    form.source_issue_no = null
  }
}

const linkedIssues = computed<Array<FmeaLinkedRef & { code: string }>>(() => {
  return form.linked_refs.filter(
    (r): r is FmeaLinkedRef & { code: string } => r.type === 'issue' && typeof r.code === 'string' && r.code.length > 0
  )
})

// 改进任务协同闭环
const linkedTasks = ref<TaskItem[]>([])
const showTaskCreateDialog = ref(false)
const savingTask = ref(false)
const taskForm = reactive<{
  title: string
  assignee_name: string
  priority: TaskPriority
  due_date: string
}>({
  title: '',
  assignee_name: '',
  priority: 'HIGH',
  due_date: ''
})

async function fetchLinkedTasks(fmeaId: number) {
  try {
    linkedTasks.value = await taskApi.getTasksBySource('CUSTOM', fmeaId)
  } catch {
    linkedTasks.value = []
  }
}

function openTaskCreate() {
  if (!props.editingItem?.id) {
    ElMessage.info('请先保存机理卡，即可一键派发闭环整改任务')
    return
  }
  taskForm.title = `针对【${form.failure_mode || props.editingItem.fmea_code}】实施防错整改`
  taskForm.priority = form.risk_level === 'HIGH' ? 'HIGH' : 'MEDIUM'
  taskForm.assignee_name = ''
  taskForm.due_date = ''
  showTaskCreateDialog.value = true
}

async function submitCreateTask() {
  if (!props.editingItem?.id) return
  if (!taskForm.title.trim()) {
    ElMessage.warning('请输入改进任务标题')
    return
  }
  savingTask.value = true
  try {
    await taskApi.createTask({
      title: taskForm.title.trim(),
      priority: taskForm.priority,
      assignee_name: taskForm.assignee_name.trim() || undefined,
      due_date: taskForm.due_date || undefined,
      source_type: 'CUSTOM',
      source_id: props.editingItem.id,
      source_title: form.failure_mode,
      source_url: `/fmea?board_id=${props.boardId || ''}&item_id=${props.editingItem.id}`,
      status: 'TODO'
    })
    ElMessage.success('已成功派发改进任务至任务中心')
    showTaskCreateDialog.value = false
    await fetchLinkedTasks(props.editingItem.id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '派发任务失败')
  } finally {
    savingTask.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    showIssuePicker.value = false
    issueSearchText.value = ''
    candidateIssues.value = []
    const it = props.editingItem
    if (it) {
      form.fmea_type = it.fmea_type || 'DFMEA'
      form.risk_level = it.risk_level || 'MED'
      useSod.value = Boolean(it.severity && it.occurrence && it.detection)
      storeAsSharedUnit.value = it.target_kind === 'shared_unit'
      form.severity = it.severity || 7
      form.occurrence = it.occurrence || 4
      form.detection = it.detection || 4
      form.failure_mode = it.failure_mode || ''
      form.failure_mech = it.failure_mech || ''
      form.failure_effect = it.failure_effect || ''
      form.control_measure = it.control_measure || ''
      form.prevention_measure = it.prevention_measure || ''
      form.detection_measure = it.detection_measure || ''
      // 若历史数据只有 control_measure，智能回填
      if (!form.prevention_measure && !form.detection_measure && it.control_measure) {
        form.prevention_measure = it.control_measure
      }
      form.source_issue_no = it.source_issue_no || null
      form.photos = JSON.parse(jsonCloneStr(it.photos || []))
      form.linked_refs = JSON.parse(jsonCloneStr(it.linked_refs || []))
      fetchLinkedTasks(it.id)
    } else {
      form.fmea_type = inferFmeaType(props.targetKind, props.targetTitleSnapshot)
      form.risk_level = 'HIGH'
      useSod.value = false
      storeAsSharedUnit.value = Boolean(props.sharedUnitCode)
      form.severity = 7
      form.occurrence = 4
      form.detection = 4
      form.failure_mode = ''
      form.failure_mech = ''
      form.failure_effect = ''
      form.control_measure = ''
      form.prevention_measure = ''
      form.detection_measure = ''
      form.source_issue_no = null
      form.photos = []
      linkedTasks.value = []
      const codeHint = props.sharedUnitCode || props.defaultPartCode
      form.linked_refs = codeHint
        ? [{ type: 'part', ref_id: null, code: codeHint, label: props.targetTitleSnapshot || codeHint }]
        : []
    }
  }
)

function jsonCloneStr(val: unknown): string {
  return JSON.stringify(val)
}

function toggleSod() {
  useSod.value = !useSod.value
  if (useSod.value) syncRiskFromSod()
}

function syncRiskFromSod() {
  const rpn = computedRpn.value
  if (rpn >= 100 || form.severity >= 9) form.risk_level = 'HIGH'
  else if (rpn >= 40 || form.severity >= 6) form.risk_level = 'MED'
  else form.risk_level = 'LOW'
}

function pickPhoto(tag: 'NG' | 'OK') {
  pendingPhotoTag.value = tag
  photoFileRef.value?.click()
}

async function appendUploadedPhoto(file: File, tag: 'NG' | 'OK') {
  const res = await uploadImageFile(file, 'fmea_photo', props.editingItem?.id || props.boardId)
  if (!res) return
  form.photos.push({
    id: `ph_${Date.now().toString(36)}`,
    attachment_id: res.attachment_id,
    url: res.url,
    tag,
    caption: ''
  })
}

async function onPhotoFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (f) {
    await appendUploadedPhoto(f, pendingPhotoTag.value)
  }
}

async function onDialogPaste(e: ClipboardEvent) {
  const files = extractImagesFromClipboard(e)
  if (!files.length) return
  e.preventDefault()
  for (const f of files) {
    const autoTag: 'NG' | 'OK' = form.photos.some((p) => p.tag === 'NG') ? 'OK' : 'NG'
    await appendUploadedPhoto(f, autoTag)
  }
  ElMessage.success('已从剪贴板上传实拍图')
}

async function handleSave() {
  if (!form.failure_mode.trim()) {
    ElMessage.warning('请填写潜在失效模式')
    return
  }
  saving.value = true
  try {
    const useShared = Boolean(effectiveSharedUnitCode.value && storeAsSharedUnit.value)
    const finalTargetKind: TargetKind = useShared ? 'shared_unit' : props.targetKind
    const finalTargetId = useShared ? effectiveSharedUnitCode.value : props.targetId
    const finalBoardId = useShared ? null : props.boardId
    const finalSnap = useShared
      ? `${props.targetTitleSnapshot || effectiveSharedUnitCode.value} (共用本体)`
      : props.targetTitleSnapshot

    const ctrlParts: string[] = []
    if (form.prevention_measure.trim()) ctrlParts.push(`【预防】${form.prevention_measure.trim()}`)
    if (form.detection_measure.trim()) ctrlParts.push(`【探测】${form.detection_measure.trim()}`)
    const synthControl = ctrlParts.join('\n') || form.control_measure.trim()

    let saved: FmeaItem
    if (props.editingItem) {
      saved = await fmeaApi.updateItem(props.editingItem.id, {
        board_id: finalBoardId,
        target_kind: finalTargetKind,
        target_id: finalTargetId,
        target_title_snapshot: finalSnap,
        fmea_type: form.fmea_type,
        risk_level: form.risk_level,
        severity: useSod.value ? form.severity : undefined,
        occurrence: useSod.value ? form.occurrence : undefined,
        detection: useSod.value ? form.detection : undefined,
        clear_sod: !useSod.value,
        failure_mode: form.failure_mode.trim(),
        failure_mech: form.failure_mech.trim(),
        failure_effect: form.failure_effect.trim(),
        control_measure: synthControl,
        prevention_measure: form.prevention_measure.trim(),
        detection_measure: form.detection_measure.trim(),
        source_issue_no: form.source_issue_no,
        photos: form.photos,
        linked_refs: form.linked_refs
      })
    } else {
      saved = await fmeaApi.createItem({
        board_id: finalBoardId,
        target_kind: finalTargetKind,
        target_id: finalTargetId,
        target_title_snapshot: finalSnap,
        fmea_type: form.fmea_type,
        risk_level: form.risk_level,
        severity: useSod.value ? form.severity : null,
        occurrence: useSod.value ? form.occurrence : null,
        detection: useSod.value ? form.detection : null,
        failure_mode: form.failure_mode.trim(),
        failure_mech: form.failure_mech.trim(),
        failure_effect: form.failure_effect.trim(),
        control_measure: synthControl,
        prevention_measure: form.prevention_measure.trim(),
        detection_measure: form.detection_measure.trim(),
        source_issue_no: form.source_issue_no,
        photos: form.photos,
        linked_refs: form.linked_refs
      })
    }
    emit('saved', saved)
    emit('update:modelValue', false)
    ElMessage.success(useShared ? '已保存至跨画板共用本体经验库' : 'FMEA 机理卡已保存')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* 弹窗视口约束：彻底杜绝容器溢出浏览器 */
:deep(.el-overlay-dialog) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
}

:deep(.el-dialog) {
  max-height: 88vh !important;
  display: flex !important;
  flex-direction: column !important;
  margin: 0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 20px 25px -5px rgba(15, 23, 42, 0.2), 0 8px 10px -6px rgba(15, 23, 42, 0.12);
}

:deep(.el-dialog__header) {
  flex-shrink: 0;
  padding: 12px 18px 10px;
  margin-right: 0;
  border-bottom: 1px solid #f1f5f9;
}

:deep(.el-dialog__title) {
  font-size: 14.5px;
  font-weight: 700;
  color: #0f172a;
}

:deep(.el-dialog__body) {
  flex: 1;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  padding: 12px 18px;
}

:deep(.el-dialog__footer) {
  flex-shrink: 0;
  padding: 10px 18px 12px;
  border-top: 1px solid #f1f5f9;
  background: #f8fafc;
}

.fmea-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 1. 顶部当前分析要素与类型定级状态栏 */
.dialog-context-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.dcb-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dcb-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.target-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  font-size: 12px;
}

.tbp-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
}

.tbp-kind {
  font-size: 11px;
  color: #1d4ed8;
  font-weight: 600;
}

.tbp-sep {
  color: #bfdbfe;
  font-size: 10px;
}

.tbp-title {
  color: #1e3a8a;
  font-weight: 600;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fmea-type-pill {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  padding: 3px 7px;
  border-radius: 6px;
  font-size: 11.5px;
  color: #475569;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}

.fmea-type-pill:hover {
  border-color: #3b82f6;
  color: #2563eb;
}

.fmea-type-pill.type-dfmea {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
  font-weight: 600;
}

.fmea-type-pill.type-pfmea {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #15803d;
  font-weight: 600;
}

.fmea-type-pill.type-lesson {
  background: #fefce8;
  border-color: #fef08a;
  color: #a16207;
  font-weight: 600;
}

.ftp-arrow {
  font-size: 10px;
  opacity: 0.7;
}

/* 共用件层级开关 */
.bom-scope-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 2px 4px;
}

.bs-pill {
  border: none;
  background: transparent;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  color: #64748b;
  cursor: pointer;
}

.bs-pill.active {
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 600;
}

.risk-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rk-pill {
  border: 1px solid transparent;
  background: transparent;
  padding: 3px 8px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #64748b;
  transition: all 0.15s;
}

.rk-pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.rk-pill.rk-high .dot { background: #ef4444; }
.rk-pill.rk-med .dot { background: #f59e0b; }
.rk-pill.rk-low .dot { background: #10b981; }

.rk-pill:hover {
  background: #f8fafc;
}

.rk-pill.active.rk-high {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
  font-weight: 600;
}

.rk-pill.active.rk-med {
  background: #fffbeb;
  border-color: #fde68a;
  color: #d97706;
  font-weight: 600;
}

.rk-pill.active.rk-low {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #059669;
  font-weight: 600;
}

.sod-toggle-btn {
  border: 1px dashed #cbd5e1;
  background: #ffffff;
  font-size: 11.5px;
  color: #64748b;
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.sod-toggle-btn:hover {
  border-color: #3b82f6;
  color: #2563eb;
}

.sod-toggle-btn.active {
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

/* SOD 紧凑滑块条 */
.sod-strip {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 14px;
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 12px;
}

.sod-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sod-lbl {
  font-size: 11px;
  color: #64748b;
}

.sod-lbl strong {
  color: #0f172a;
}

.sod-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 4px 10px;
}

.sod-rpn-lbl {
  font-size: 9.5px;
  font-weight: 700;
  color: #3b82f6;
  text-transform: uppercase;
}

.sod-rpn-val {
  font-size: 15px;
  font-weight: 800;
  color: #1e40af;
  line-height: 1.1;
}

/* 2. 失效现象与实拍图卡片 */
.phenomenon-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 12px;
  transition: border-color 0.15s;
}

.phenomenon-card:focus-within {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.p-title-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.p-label {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
}

.req {
  color: #ef4444;
}

.p-photo-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.paste-hint {
  font-size: 11px;
  color: #94a3b8;
}

.mini-upload-btn {
  padding: 2px 7px;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
  font-weight: 500;
}

.mini-upload-btn.ng {
  background: #fee2e2;
  border-color: #fecaca;
  color: #b91c1c;
}

.mini-upload-btn.ok {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #047857;
}

.phenomenon-input {
  width: 100%;
  height: 32px;
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  padding: 0;
  background: transparent;
}

.phenomenon-input::placeholder {
  font-weight: 400;
  font-size: 12.5px;
  color: #94a3b8;
}

/* 现象实拍预览区 */
.inline-photo-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 6px;
  border-top: 1px dashed #f1f5f9;
}

.inline-photo-item {
  width: 90px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.ph-img-box {
  position: relative;
  width: 100%;
  height: 64px;
  background: #0f172a;
}

.ph-img-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ph-tag-btn {
  position: absolute;
  top: 3px;
  left: 3px;
  font-size: 9.5px;
  padding: 1px 4px;
  border-radius: 3px;
  border: none;
  font-weight: 700;
  cursor: pointer;
}

.ph-tag-btn.ng {
  background: #ef4444;
  color: #ffffff;
}

.ph-tag-btn.ok {
  background: #10b981;
  color: #ffffff;
}

.ph-del-btn {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: none;
  background: rgba(15, 23, 42, 0.65);
  color: #ffffff;
  font-size: 11px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.ph-mini-caption {
  border: none;
  border-top: 1px solid #f1f5f9;
  font-size: 10.5px;
  padding: 2px 4px;
  outline: none;
  color: #475569;
}

/* 3 & 4. 因果深入分析与现行双轨控制对策 */
.causal-split-row,
.control-split-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.causal-cell {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  transition: border-color 0.15s;
}

.causal-cell:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.08);
}

.cell-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
}

.cell-indicator {
  width: 3px;
  height: 12px;
  border-radius: 2px;
  flex-shrink: 0;
}

.cell-indicator.warm { background: #f59e0b; }
.cell-indicator.slate { background: #64748b; }
.cell-indicator.blue { background: #2563eb; }
.cell-indicator.emerald { background: #059669; }

.cell-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.cell-textarea {
  width: 100%;
  border: none;
  outline: none;
  font-size: 12px;
  line-height: 1.5;
  color: #1e293b;
  resize: vertical;
  background: transparent;
  padding: 0;
}

.cell-textarea::placeholder {
  color: #94a3b8;
  font-size: 11px;
}

/* 5. 底部业务闭环协同栏 */
.bottom-integration-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}

.bi-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bi-actions-row {
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.bi-col {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.bi-lbl {
  font-size: 11.5px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
}

.bi-content {
  flex: 1;
  min-width: 0;
}

.bi-chips {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.bi-add-btn {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  font-size: 11px;
  border: 1px dashed #cbd5e1;
  background: #ffffff;
  color: #475569;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.bi-add-btn:hover {
  border-color: #3b82f6;
  color: #2563eb;
}

.bi-add-btn.active {
  border-color: #ef4444;
  color: #dc2626;
  background: #fef2f2;
}

.bi-add-btn.task-btn {
  border-color: #3b82f6;
  color: #1d4ed8;
  background: #eff6ff;
  font-weight: 600;
}

.bi-add-btn.task-btn:hover {
  background: #dbeafe;
}

/* 质量单胶囊 */
.qi-mini-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #fff1f2;
  border: 1px solid #fecdd3;
  border-radius: 4px;
  font-size: 11px;
}

.qic-tag {
  color: #e11d48;
  font-weight: 700;
  font-size: 9.5px;
}

.qic-code {
  font-family: monospace;
  font-weight: 700;
  color: #9f1239;
}

.qic-title {
  color: #475569;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qic-del {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 12px;
  padding: 0 1px;
}

.qic-del:hover {
  color: #e11d48;
}

/* 改进任务胶囊 */
.task-mini-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  font-size: 11px;
}

.task-mini-chip.status-done {
  background: #f1f5f9;
  border-color: #e2e8f0;
  opacity: 0.8;
}

.tmc-code {
  font-family: monospace;
  font-weight: 700;
  color: #15803d;
}

.tmc-status {
  font-size: 9.5px;
  padding: 0 3px;
  border-radius: 2px;
  background: #dcfce7;
  color: #166534;
}

.tmc-name {
  color: #475569;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 质量单检索面板 */
.qi-picker-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qi-search-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.qi-search-input {
  flex: 1;
  height: 28px;
  padding: 0 8px;
  font-size: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  outline: none;
}

.qi-search-input:focus {
  border-color: #2563eb;
}

.qi-loading-txt {
  font-size: 11px;
  color: #94a3b8;
}

.qi-candidate-list {
  max-height: 160px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qi-candidate-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 4px;
  background: #f8fafc;
  cursor: pointer;
  transition: background 0.12s;
}

.qi-candidate-item:hover {
  background: #f1f5f9;
}

.qi-candidate-item.linked {
  background: #fff1f2;
}

.qci-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.qci-badge {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}

.qci-badge.sev-致命, .qci-badge.sev-严重 {
  background: #fee2e2;
  color: #dc2626;
}

.qci-badge.sev-一般 {
  background: #fef3c7;
  color: #d97706;
}

.qci-no {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
  flex-shrink: 0;
}

.qci-title {
  font-size: 12px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qci-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.qci-part {
  font-family: monospace;
  font-size: 10.5px;
  color: #64748b;
}

.qci-status {
  font-size: 10.5px;
  color: #64748b;
}

.qci-action {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
  color: #475569;
}

.qi-candidate-item:hover .qci-action {
  border-color: #2563eb;
  color: #2563eb;
}

.qi-candidate-item.linked .qci-action {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #b91c1c;
}

.qi-empty-tip {
  padding: 10px;
  text-align: center;
  font-size: 11.5px;
  color: #94a3b8;
}

/* 派发任务表单 */
.task-dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 6px 0;
}

.tdf-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tdf-row label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.tdf-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
