<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑关键质量特性' : '新增 CTQ 关键质量特性'"
    :sub-title="isEdit ? `${form.feature_code} (${form.feature_type})` : 'KPC产品/KCC过程特性与公差标准'"
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
      class="ctq-form"
    >
      <el-divider content-position="left">归属零部件与特征定级</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="关联零部件" prop="part_id">
            <el-select
              v-model="form.part_id"
              placeholder="搜索并选择归属零件物料"
              clearable
              filterable
              style="width: 100%"
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
          <el-form-item label="特性分类类别" prop="feature_type">
            <el-radio-group v-model="form.feature_type">
              <el-radio-button value="KPC">KPC (产品关键特性)</el-radio-button>
              <el-radio-button value="KCC">KCC (过程关键特性)</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="关键特征代号" prop="feature_code">
            <el-input
              v-model="form.feature_code"
              placeholder="如 KPC-01, CC-03, CTQ-DIM-01"
              clearable
            />
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="特性中文名称" prop="feature_name">
            <el-input
              v-model="form.feature_name"
              placeholder="如 轴承配合位外径尺寸, 齿面淬火硬度"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">规格公差与量具配置</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="标称标准值" prop="standard_value">
            <el-input
              v-model="form.standard_value"
              placeholder="如 35.000mm, 60 HRC, 0.020mm"
              clearable
            />
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="公差/控制规格" prop="tolerance">
            <el-input
              v-model="form.tolerance"
              placeholder="如 +0.012/-0.005mm, >=58HRC, <=0.03mm"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="检验测量量具" prop="inspection_tool">
            <el-select
              v-model="form.inspection_tool"
              placeholder="选择或输入检测设备"
              clearable
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option label="三坐标测量机 (CMM)" value="三坐标测量机 (CMM)" />
              <el-option label="数显外径千分尺 (0.001mm)" value="数显外径千分尺 (0.001mm)" />
              <el-option label="数显内径千分表" value="数显内径千分表" />
              <el-option label="高精度游标卡尺" value="高精度游标卡尺" />
              <el-option label="台式洛氏硬度计" value="台式洛氏硬度计" />
              <el-option label="显微硬度计" value="显微硬度计" />
              <el-option label="表面粗糙度仪" value="表面粗糙度仪" />
              <el-option label="光学二次元影像仪" value="光学二次元影像仪" />
              <el-option label="专用检具/止通规" value="专用检具/止通规" />
              <el-option label="气动量仪" value="气动量仪" />
            </el-select>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="检验抽样频次" prop="frequency">
            <el-select
              v-model="form.frequency"
              placeholder="选择或输入抽样频次"
              clearable
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option label="100% 全检" value="100% 全检" />
              <el-option label="首末件 + 每批抽检5件" value="首末件 + 每批抽检5件" />
              <el-option label="1次/2小时 (抽检3件)" value="1次/2小时 (抽检3件)" />
              <el-option label="首件 + 抽检3件/批" value="首件 + 抽检3件/批" />
              <el-option label="每炉抽样金相1件" value="每炉抽样金相1件" />
              <el-option label="每班次首检1件" value="每班次首检1件" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">质量控制方法与备忘</el-divider>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="质量控制方法" prop="control_method">
            <el-input
              v-model="form.control_method"
              placeholder="如 SPC Xbar-R控制图监控、加热功率与扫描速度程序互锁防错、CPK>=1.33能力要求等..."
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="技术备注说明" prop="remark">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="4"
              placeholder="关键特征设计背景、失效模式(FMEA)严重度、异常反应计划(OCAP)等说明..."
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

interface PartOption {
  id: number
  part_no: string
  name: string
}

interface CtqModel {
  id?: number
  part_id: number | null
  feature_code: string
  feature_name: string
  feature_type: string
  standard_value: string
  tolerance: string
  inspection_tool: string
  frequency: string
  control_method: string
  remark: string
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()
const partOptions = ref<PartOption[]>([])

const form = reactive<CtqModel>({
  id: undefined,
  part_id: null,
  feature_code: '',
  feature_name: '',
  feature_type: 'KPC',
  standard_value: '',
  tolerance: '',
  inspection_tool: '三坐标测量机 (CMM)',
  frequency: '首末件 + 每批抽检5件',
  control_method: '',
  remark: ''
})

const rules: FormRules = {
  part_id: [{ required: true, message: '请选择归属零部件', trigger: 'change' }],
  feature_code: [
    { required: true, message: '关键特征代号不可为空', trigger: 'blur' },
    { min: 2, max: 64, message: '长度在 2 到 64 个字符', trigger: 'blur' }
  ],
  feature_name: [
    { required: true, message: '特性中文名称不可为空', trigger: 'blur' },
    { min: 2, max: 128, message: '长度在 2 到 128 个字符', trigger: 'blur' }
  ],
  feature_type: [{ required: true, message: '请选择特性类别', trigger: 'change' }],
  tolerance: [{ required: true, message: '请输入公差/控制规格要求', trigger: 'blur' }]
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  part_id: form.part_id,
  feature_code: form.feature_code,
  feature_name: form.feature_name,
  feature_type: form.feature_type,
  standard_value: form.standard_value,
  tolerance: form.tolerance,
  inspection_tool: form.inspection_tool,
  frequency: form.frequency,
  control_method: form.control_method,
  remark: form.remark
}))

const loadPartOptions = async () => {
  try {
    const res = await axios.get('/api/maindata/parts', { params: { page_size: 200 } })
    partOptions.value = res.data.items || []
  } catch (err: any) {
    console.error('加载零件候选项失败:', err)
  }
}

const resetForm = () => {
  form.id = undefined
  form.part_id = null
  form.feature_code = ''
  form.feature_name = ''
  form.feature_type = 'KPC'
  form.standard_value = ''
  form.tolerance = ''
  form.inspection_tool = '三坐标测量机 (CMM)'
  form.frequency = '首末件 + 每批抽检5件'
  form.control_method = ''
  form.remark = ''
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = async (defaultPartOrData?: number | Partial<CtqModel>) => {
  resetForm()
  visible.value = true
  await loadPartOptions()
  if (typeof defaultPartOrData === 'number') {
    form.part_id = defaultPartOrData
  } else if (defaultPartOrData && typeof defaultPartOrData === 'object') {
    Object.assign(form, defaultPartOrData)
  }
  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉
const openEdit = async (ctqId: number) => {
  resetForm()
  loading.value = true
  visible.value = true

  try {
    await loadPartOptions()
    const res = await axios.get(`/api/ctq/${ctqId}`)
    const data = res.data
    form.id = data.id
    form.part_id = data.part_id
    form.feature_code = data.feature_code
    form.feature_name = data.feature_name
    form.feature_type = data.feature_type || 'KPC'
    form.standard_value = data.standard_value || ''
    form.tolerance = data.tolerance || ''
    form.inspection_tool = data.inspection_tool || ''
    form.frequency = data.frequency || '首末件 + 每批抽检5件'
    form.control_method = data.control_method || ''
    form.remark = data.remark || ''

    nextTick(() => {
      formRef.value?.clearValidate()
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`加载 CTQ 详情失败: ${err.response?.data?.detail || err.message}`)
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
        await axios.put(`/api/ctq/${form.id}`, {
          feature_code: form.feature_code,
          feature_name: form.feature_name,
          feature_type: form.feature_type,
          standard_value: form.standard_value || null,
          tolerance: form.tolerance,
          inspection_tool: form.inspection_tool || null,
          frequency: form.frequency,
          control_method: form.control_method || null,
          remark: form.remark || null
        })
        ElMessage.success('CTQ 关键特性更新成功')
      } else {
        await axios.post('/api/ctq', {
          part_id: form.part_id,
          feature_code: form.feature_code,
          feature_name: form.feature_name,
          feature_type: form.feature_type,
          standard_value: form.standard_value || null,
          tolerance: form.tolerance,
          inspection_tool: form.inspection_tool || null,
          frequency: form.frequency,
          control_method: form.control_method || null,
          remark: form.remark || null
        })
        ElMessage.success('CTQ 关键特性创建成功')
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
.ctq-form {
  padding: 8px 12px;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}
</style>
