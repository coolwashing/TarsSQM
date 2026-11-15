<template>
  <el-dialog
    :model-value="modelValue"
    title="沉淀至 FMEA 视觉风险画板与经验库"
    width="540px"
    destroy-on-close
    append-to-body
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="issue" class="deposit-body">
      <div class="issue-banner">
        <span class="iss-code">{{ issue.issue_no }}</span>
        <span class="iss-title">{{ issue.title }}</span>
      </div>

      <el-form label-position="top" size="default">
        <el-form-item label="1. 选择归属模块画板" required>
          <el-select
            v-model="form.board_id"
            placeholder="请选择目标系统/模块画板"
            style="width: 100%"
            @change="onBoardPicked"
          >
            <el-option
              v-for="b in boards"
              :key="b.id"
              :label="`${b.group_name} / ${b.name}`"
              :value="b.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="2. 选择画布挂载节点">
          <el-select v-model="form.nodeChoice" style="width: 100%">
            <el-option
              value="__NEW__"
              :label="`+ 在画板上自动新建节点：「${form.new_node_title}」`"
            />
            <el-option
              v-for="nd in boardNodes"
              :key="nd.id"
              :value="nd.id"
              :label="`挂载至已有节点：${nd.title} ${nd.sub ? `(${nd.sub})` : ''}`"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="3. 确认沉淀的潜在失效模式">
          <el-input v-model="form.failure_mode" placeholder="潜在失效模式简述" />
        </el-form-item>

        <div class="row-2col">
          <el-form-item label="经验类型">
            <el-radio-group v-model="form.fmea_type" size="small">
              <el-radio-button label="DFMEA">DFMEA 设计</el-radio-button>
              <el-radio-button label="PFMEA">PFMEA 工艺</el-radio-button>
              <el-radio-button label="LESSON">历史教训</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="风险等级">
            <el-radio-group v-model="form.risk_level" size="small">
              <el-radio-button label="HIGH">高危</el-radio-button>
              <el-radio-button label="MED">中危</el-radio-button>
              <el-radio-button label="LOW">低危</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>
      </el-form>

      <div class="auto-bind-tip">
        系统将自动提取该问题单的现象、整改对策与现场缺陷图片，并软关联单号
        <strong>{{ issue.issue_no }}</strong>
        <template v-if="issue.part_no">、零件 <strong>{{ issue.part_no }}</strong></template>
        <template v-if="issue.supplier_name">、供应商 <strong>{{ issue.supplier_name }}</strong></template>。
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitDeposit">
        一键沉淀并打开画板
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FmeaBoardSummary, CanvasModuleNode } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'

export interface QualityIssueMinimal {
  id: number
  issue_no: string
  title: string
  severity?: string
  part_no?: string
  part_name?: string
  supplier_name?: string
}

const props = defineProps<{
  modelValue: boolean
  issue: QualityIssueMinimal | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'deposited'): void
}>()

const router = useRouter()
const boards = ref<FmeaBoardSummary[]>([])
const boardNodes = ref<CanvasModuleNode[]>([])
const submitting = ref(false)

const form = reactive({
  board_id: undefined as number | undefined,
  nodeChoice: '__NEW__',
  new_node_title: '',
  failure_mode: '',
  fmea_type: 'DFMEA',
  risk_level: 'HIGH'
})

watch(
  () => props.modelValue,
  async (open) => {
    if (!open || !props.issue) return
    form.failure_mode = props.issue.title
    form.new_node_title = props.issue.part_name || props.issue.title.slice(0, 12)
    form.risk_level =
      props.issue.severity === '致命' || props.issue.severity === '严重'
        ? 'HIGH'
        : props.issue.severity === '微小'
          ? 'LOW'
          : 'MED'

    const tree = await fmeaApi.getBoardTree()
    boards.value = tree.boards
    if (tree.boards.length > 0) {
      form.board_id = tree.boards[0].id
      await onBoardPicked(tree.boards[0].id)
    }
  }
)

async function onBoardPicked(boardId: number) {
  const detail = await fmeaApi.getBoardDetail(boardId)
  boardNodes.value = detail.canvas_data?.nodes || []
  // 若已有节点匹配零件名，优先自动选中
  const matched = props.issue?.part_name
    ? boardNodes.value.find((n) => n.title.includes(props.issue!.part_name!) || n.sub === props.issue?.part_no)
    : undefined
  form.nodeChoice = matched ? matched.id : '__NEW__'
}

async function submitDeposit() {
  if (!props.issue || !form.board_id) {
    ElMessage.warning('请选择目标 FMEA 画板')
    return
  }
  submitting.value = true
  try {
    const created = await fmeaApi.depositFromQualityIssue(props.issue.id, {
      board_id: form.board_id,
      target_kind: form.nodeChoice === '__NEW__' ? 'new_node' : 'node',
      target_id: form.nodeChoice === '__NEW__' ? null : form.nodeChoice,
      new_node_title: form.new_node_title,
      fmea_type: form.fmea_type,
      risk_level: form.risk_level,
      failure_mode: form.failure_mode
    })
    ElMessage.success(`已沉淀为 ${created.fmea_code}`)
    emit('deposited')
    emit('update:modelValue', false)
    router.push({
      path: '/fmea/workspace',
      query: {
        boardId: String(form.board_id),
        targetKind: created.target_kind,
        targetId: created.target_id || ''
      }
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '沉淀失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.deposit-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-banner {
  padding: 9px 12px;
  border-radius: 8px;
  background: #fff1f2;
  border: 1px solid #fecdd3;
  display: flex;
  align-items: center;
  gap: 8px;
}

.iss-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  font-weight: 700;
  color: #be123c;
}

.iss-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.auto-bind-tip {
  padding: 8px 10px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}
</style>

