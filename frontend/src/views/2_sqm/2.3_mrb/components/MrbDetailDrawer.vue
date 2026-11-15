<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? (isJudgeMode ? 'MRB 会签审理与处置判定' : '编辑 MRB 单据') : '登记新 MRB 审理单'"
    :sub-title="isEdit ? `${form.mrb_no || ''} | ${form.mrb_source || ''}` : '进料/制程物料评审与处置闭环'"
    width="75%"
    :loading="loading"
    :is-dirty="isDirty"
    :before-close-handler="confirmBeforeClose"
    @submit="handleSave"
    @cancel="handleCancel"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="130px"
      label-position="right"
      class="mrb-drawer-form"
    >
      <!-- 一、基础溯源与物料信息 -->
      <el-divider content-position="left">一、基础溯源与物料信息</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="MRB 单号" prop="mrb_no">
            <el-input
              v-model="form.mrb_no"
              placeholder="系统自动生成 (如 MRB-20261116-001)"
              :disabled="isEdit"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="业务来源环节" prop="mrb_source">
            <el-select v-model="form.mrb_source" style="width: 100%">
              <el-option label="IQC来料" value="IQC来料" />
              <el-option label="制程装配" value="制程装配" />
              <el-option label="研发试制" value="研发试制" />
              <el-option label="售后客诉" value="售后客诉" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="发生/送检日期" prop="occurred_date">
            <el-date-picker
              v-model="form.occurred_date"
              type="date"
              placeholder="选择发生日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="供应商名称" prop="supplier_name">
            <el-input v-model="form.supplier_name" placeholder="供应商全称或简称" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="物料编码/图号" prop="part_no">
            <el-input v-model="form.part_no" placeholder="如 Z04110008" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="物料名称(型号)" prop="part_name">
            <el-input v-model="form.part_name" placeholder="如 MCP减速器" clearable />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="版本号" prop="version">
            <el-input v-model="form.version" placeholder="如 A / V1.0" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="物料类型" prop="material_type">
            <el-input v-model="form.material_type" placeholder="如 机械 / 电子 / 外购" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="批次号/来料批次" prop="batch_no">
            <el-input v-model="form.batch_no" placeholder="批次号" clearable />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 二、不良事实与数量 -->
      <el-divider content-position="left">二、不良事实与缺陷现象</el-divider>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-form-item label="批次/送检数量" prop="batch_qty">
            <el-input-number v-model="form.batch_qty" :min="0" :precision="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="抽样/检验数量" prop="sample_qty">
            <el-input-number v-model="form.sample_qty" :min="0" :precision="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="不合格数量" prop="defect_qty">
            <el-input-number v-model="form.defect_qty" :min="1" :precision="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="不良率" prop="defect_rate">
            <el-input v-model="form.defect_rate" placeholder="如 100.00%" clearable />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="不合格类型" prop="defect_type">
            <el-input v-model="form.defect_type" placeholder="如 严重不合格（性能）" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="发现人/检验员" prop="reporter">
            <el-input v-model="form.reporter" placeholder="检验员姓名" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="物料归属人/SQE" prop="owner">
            <el-input v-model="form.owner" placeholder="责任工程师" clearable />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="不合格现象描述" prop="defect_desc">
        <el-input
          v-model="form.defect_desc"
          type="textarea"
          :rows="3"
          placeholder="详细说明测量超差、外观缺陷、性能异常现象..."
        />
      </el-form-item>

      <el-form-item label="现场照片/附件" prop="attachments">
        <div class="attachment-input-box">
          <el-input
            v-model="attachmentsText"
            placeholder="图片文件名（多个以逗号隔开，如 20261026-110952.jpg）"
            clearable
          />
          <div v-if="parsedAttachments.length > 0" class="attachment-tags-row">
            <el-tag
              v-for="(att, idx) in parsedAttachments"
              :key="idx"
              size="small"
              type="info"
              effect="plain"
              class="attachment-tag"
            >
              📷 {{ att }}
            </el-tag>
          </div>
        </div>
      </el-form-item>

      <!-- 三、MRB 审理与处置决策 -->
      <el-divider content-position="left">三、MRB 审理与处置决策</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="审理处置意见" prop="mrb_decision">
            <el-select v-model="form.mrb_decision" placeholder="选择审理意见" style="width: 100%">
              <el-option label="退货" value="退货" />
              <el-option label="让步接收" value="让步接收" />
              <el-option label="让步" value="让步" />
              <el-option label="内部返修" value="内部返修" />
              <el-option label="挑选" value="挑选" />
              <el-option label="报废" value="报废" />
              <el-option label="待审理" value="待审理" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="责任归属" prop="duty_attribution">
            <el-select v-model="form.duty_attribution" placeholder="选择责任归属" style="width: 100%">
              <el-option label="供应商责任" value="供应商责任" />
              <el-option label="生产责任" value="生产责任" />
              <el-option label="研发设计责任" value="研发设计责任" />
              <el-option label="待定" value="待定" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="闭环状态" prop="status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="待审理" value="待审理" />
              <el-option label="改善中" value="改善中" />
              <el-option label="已验证" value="已验证" />
              <el-option label="已结案" value="已结案" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="有无供应商报告" prop="has_supplier_report">
            <el-radio-group v-model="form.has_supplier_report">
              <el-radio value="有">有</el-radio>
              <el-radio value="无">无</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="是否结案" prop="is_closed">
            <el-radio-group v-model="form.is_closed">
              <el-radio value="是">是</el-radio>
              <el-radio value="否">否</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 四、8D 根本原因与纠正预防措施 -->
      <el-divider content-position="left">四、8D 根本原因与纠正预防措施</el-divider>
      <el-form-item label="根本原因分析" prop="root_cause">
        <el-input
          v-model="form.root_cause"
          type="textarea"
          :rows="2"
          placeholder="人、机、料、法、环根因深入分析..."
        />
      </el-form-item>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="遏制/临时措施" prop="immediate_action">
            <el-input
              v-model="form.immediate_action"
              type="textarea"
              :rows="2"
              placeholder="库存隔离、产线拦截、加急调件等..."
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="长期纠正对策" prop="long_term_action">
            <el-input
              v-model="form.long_term_action"
              type="textarea"
              :rows="2"
              placeholder="工艺防错升级、工装改进、标准修编等..."
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="措施验证" prop="action_verification">
        <el-input
          v-model="form.action_verification"
          type="textarea"
          :rows="2"
          placeholder="小批量试装、连续批次良率验证记录..."
        />
      </el-form-item>

      <el-form-item label="备注说明" prop="remark">
        <el-input v-model="form.remark" placeholder="追溯、交接与备忘说明" clearable />
      </el-form-item>
    </el-form>
  </DrawerContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import axios from 'axios'
import DrawerContainer from '@/components/common/DrawerContainer.vue'
import { useDirtyCheck } from '@/components/common/useDirtyCheck'

const emit = defineEmits(['success'])

const visible = ref(false)
const isEdit = ref(false)
const isJudgeMode = ref(false)
const loading = ref(false)
const recordId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const initialFormData = () => ({
  mrb_no: '',
  mrb_source: 'IQC来料',
  occurred_date: new Date().toISOString().slice(0, 10),
  inspection_month: '',
  supplier_name: '',
  material_type: '',
  part_no: '',
  part_name: '',
  version: 'A',
  batch_no: '',
  batch_qty: 0,
  sample_qty: 0,
  defect_qty: 1,
  pass_qty: 0,
  defect_rate: '',
  defect_type: '',
  defect_desc: '',
  attachments: null as any,
  mrb_decision: '待审理',
  duty_attribution: '',
  reporter: '',
  owner: '',
  has_supplier_report: '无',
  root_cause: '',
  immediate_action: '',
  long_term_action: '',
  action_verification: '',
  status: '待审理',
  is_closed: '否',
  remark: ''
})

const form = reactive(initialFormData())
const attachmentsText = ref('')

const parsedAttachments = computed(() => {
  if (!attachmentsText.value) return []
  return attachmentsText.value
    .split(/[,，;\n]/)
    .map(s => s.trim())
    .filter(Boolean)
})

const rules: FormRules = {
  mrb_source: [{ required: true, message: '请选择业务来源环节', trigger: 'change' }],
  defect_qty: [{ required: true, message: '请输入不合格品数量', trigger: 'blur' }]
}

const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  ...form
}))

const openCreate = (defaultSource: string = 'IQC来料') => {
  isEdit.value = false
  isJudgeMode.value = false
  recordId.value = null
  Object.assign(form, initialFormData())
  form.mrb_source = defaultSource
  attachmentsText.value = ''

  // 预取下一个单号
  axios.get('/api/sqm/mrb/next-no').then(res => {
    if (res.data?.next_mrb_no) {
      form.mrb_no = res.data.next_mrb_no
      captureInitialState()
    }
  }).catch(() => {})

  visible.value = true
  captureInitialState()
}

const openEdit = async (id: number, judge: boolean = false) => {
  isEdit.value = true
  isJudgeMode.value = judge
  recordId.value = id
  loading.value = true
  visible.value = true

  try {
    const res = await axios.get(`/api/sqm/mrb/${id}`)
    const data = res.data
    Object.assign(form, data)

    // 处理附件
    if (Array.isArray(data.attachments)) {
      attachmentsText.value = data.attachments.join(', ')
    } else if (typeof data.attachments === 'string') {
      attachmentsText.value = data.attachments
    } else {
      attachmentsText.value = ''
    }

    captureInitialState()
  } catch (err: any) {
    ElMessage.error(`加载 MRB 详情失败: ${err.response?.data?.detail || err.message}`)
    visible.value = false
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const payload: any = { ...form }
    payload.attachments = parsedAttachments.value.length > 0 ? parsedAttachments.value : null

    if (isEdit.value && recordId.value) {
      await axios.put(`/api/sqm/mrb/${recordId.value}`, payload)
      ElMessage.success(`MRB 单据 "${form.mrb_no}" 已更新`)
    } else {
      await axios.post('/api/sqm/mrb', payload)
      ElMessage.success(`MRB 单据 "${form.mrb_no}" 登记成功`)
    }

    markClean()
    visible.value = false
    emit('success')
  } catch (err: any) {
    ElMessage.error(`保存失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}

defineExpose({
  openCreate,
  openEdit
})
</script>

<style scoped>
.mrb-drawer-form {
  padding: 10px 16px 24px;
}
.attachment-input-box {
  width: 100%;
}
.attachment-tags-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.attachment-tag {
  font-family: monospace;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
