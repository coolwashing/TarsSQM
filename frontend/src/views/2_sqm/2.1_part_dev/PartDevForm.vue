<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑零件开发进度' : '绑定零部件与供应商开发关系'"
    :sub-title="isEdit ? `${form.part_no || ''} ↔ ${form.supplier_name || ''}` : '零部件试制阶段与样件交付矩阵'"
    width="70%"
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
      class="part-dev-form"
    >
      <el-divider content-position="left">双向绑定关系设定</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="关联零部件" prop="part_id">
            <el-select
              v-model="form.part_id"
              placeholder="搜索或选择零件物料"
              clearable
              filterable
              :disabled="isEdit"
              style="width: 100%"
              @change="onPartChange"
            >
              <el-option
                v-for="p in partOptions"
                :key="p.id"
                :label="`[${p.part_no}] ${p.name}`"
                :value="p.id"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="选定承制供应商" prop="supplier_id">
            <el-select
              v-model="form.supplier_id"
              placeholder="搜索或选择承制供应商"
              clearable
              filterable
              :disabled="isEdit"
              style="width: 100%"
              @change="onSupplierChange"
            >
              <el-option
                v-for="s in supplierOptions"
                :key="s.id"
                :label="`[${s.code}] ${s.name} (${s.status})`"
                :value="s.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">开发阶段与评审推进</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="当前试制阶段" prop="dev_phase">
            <el-radio-group v-model="form.dev_phase">
              <el-radio-button value="OTS">OTS</el-radio-button>
              <el-radio-button value="工装样件">工装样件</el-radio-button>
              <el-radio-button value="PPAP">PPAP</el-radio-button>
              <el-radio-button value="SOP">SOP</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="阶段审批状态" prop="status">
            <el-radio-group v-model="form.status">
              <el-radio-button value="进行中">进行中</el-radio-button>
              <el-radio-button value="待评审">待评审</el-radio-button>
              <el-radio-button value="已批准">已批准</el-radio-button>
              <el-radio-button value="已冻结">已冻结</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">进度排期与试制指标</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="计划达成节点" prop="target_date">
            <el-date-picker
              v-model="form.target_date"
              type="date"
              placeholder="选择当前阶段达成日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="送样数量(件)" prop="sample_qty">
            <el-input-number
              v-model="form.sample_qty"
              :min="0"
              :step="1"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="SQE 责任工程师" prop="responsible">
            <el-input
              v-model="form.responsible"
              placeholder="主要质量跟进人"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">阶段技术备忘与评审意见</el-divider>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="备忘与评审意见" prop="remark">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="4"
              placeholder="试制样件外观检验结果、关键尺寸实测偏差、PPAP 提交资料包归档记录等..."
            />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
  </DrawerContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DrawerContainer from '@/components/common/DrawerContainer.vue'
import { useDirtyCheck } from '@/components/common/useDirtyCheck'

interface OptionItem {
  id: number
  part_no?: string
  code?: string
  name: string
  status?: string
}

interface PartDevModel {
  id?: number
  part_id?: number | null
  supplier_id?: number | null
  part_no?: string
  supplier_name?: string
  dev_phase: string
  status: string
  target_date: string | null
  sample_qty: number
  responsible: string
  remark: string
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()

const partOptions = ref<OptionItem[]>([])
const supplierOptions = ref<OptionItem[]>([])

const form = reactive<PartDevModel>({
  id: undefined,
  part_id: null,
  supplier_id: null,
  part_no: '',
  supplier_name: '',
  dev_phase: 'OTS',
  status: '进行中',
  target_date: null,
  sample_qty: 5,
  responsible: '',
  remark: ''
})

const rules: FormRules = {
  part_id: [{ required: true, message: '请选择关联零部件', trigger: 'change' }],
  supplier_id: [{ required: true, message: '请选择承制供应商', trigger: 'change' }],
  dev_phase: [{ required: true, message: '请设定开发阶段', trigger: 'change' }],
  status: [{ required: true, message: '请设定审批状态', trigger: 'change' }]
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  part_id: form.part_id,
  supplier_id: form.supplier_id,
  dev_phase: form.dev_phase,
  status: form.status,
  target_date: form.target_date,
  sample_qty: form.sample_qty,
  responsible: form.responsible,
  remark: form.remark
}))

const loadBaseOptions = async () => {
  try {
    const [partRes, supRes] = await Promise.all([
      axios.get('/api/maindata/parts', { params: { page_size: 200 } }),
      axios.get('/api/maindata/suppliers', { params: { page_size: 200 } })
    ])
    partOptions.value = partRes.data.items || []
    supplierOptions.value = supRes.data.items || []
  } catch (err: any) {
    console.error('加载零件与供应商下拉失败:', err)
  }
}

const onPartChange = (val?: number) => {
  const p = partOptions.value.find((item) => item.id === val)
  form.part_no = p?.part_no || ''
}

const onSupplierChange = (val?: number) => {
  const s = supplierOptions.value.find((item) => item.id === val)
  form.supplier_name = s?.name || ''
}

const resetForm = () => {
  form.id = undefined
  form.part_id = null
  form.supplier_id = null
  form.part_no = ''
  form.supplier_name = ''
  form.dev_phase = 'OTS'
  form.status = '进行中'
  form.target_date = null
  form.sample_qty = 5
  form.responsible = ''
  form.remark = ''
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = async () => {
  resetForm()
  visible.value = true
  await loadBaseOptions()
  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉
const openEdit = async (devId: number) => {
  resetForm()
  loading.value = true
  visible.value = true

  try {
    await loadBaseOptions()
    const res = await axios.get(`/api/sqm/part-devs/${devId}`)
    const data = res.data
    form.id = data.id
    form.part_id = data.part_id
    form.supplier_id = data.supplier_id
    form.part_no = data.part_no || ''
    form.supplier_name = data.supplier_name || ''
    form.dev_phase = data.dev_phase || 'OTS'
    form.status = data.status || '进行中'
    form.target_date = data.target_date || null
    form.sample_qty = data.sample_qty || 0
    form.responsible = data.responsible || ''
    form.remark = data.remark || ''

    nextTick(() => {
      formRef.value?.clearValidate()
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`加载零件开发详情失败: ${err.response?.data?.detail || err.message}`)
    visible.value = false
  } finally {
    loading.value = false
  }
}

// 保存表单
const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      if (isEdit.value && form.id) {
        await axios.put(`/api/sqm/part-devs/${form.id}`, {
          dev_phase: form.dev_phase,
          status: form.status,
          target_date: form.target_date || null,
          sample_qty: form.sample_qty,
          responsible: form.responsible,
          remark: form.remark
        })
        ElMessage.success('零件开发进度更新成功')
      } else {
        await axios.post('/api/sqm/part-devs', {
          part_id: form.part_id,
          supplier_id: form.supplier_id,
          dev_phase: form.dev_phase,
          status: form.status,
          target_date: form.target_date || null,
          sample_qty: form.sample_qty,
          responsible: form.responsible,
          remark: form.remark
        })
        ElMessage.success('零件开发双向绑定创建成功')
      }

      markClean()
      visible.value = false
      emit('success')
    } catch (err: any) {
      ElMessage.error(`保存失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      loading.value = false
    }
  })
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
.part-dev-form {
  padding: 8px 12px;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}
</style>
