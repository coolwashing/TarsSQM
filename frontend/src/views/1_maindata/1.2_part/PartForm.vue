<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑零件' : '新建零件'"
    :sub-title="isEdit ? form.part_no : '主数据零件图号与设计规格'"
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
      label-width="120px"
      label-position="right"
      class="part-form"
    >
      <el-divider content-position="left">基础标识与所属项目</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="零件图号/编码" prop="part_no">
            <el-input
              v-model="form.part_no"
              placeholder="如 P100234 或 MAT-ARM-01"
              :disabled="isEdit"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="零件中文名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入零件规格中文名称"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="所属车型/项目" prop="project_id">
            <el-select
              v-model="form.project_id"
              placeholder="请选择关联项目"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="item in projectOptions"
                :key="item.id"
                :label="`[${item.project_code}] ${item.name}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="零件分类" prop="category">
            <el-select
              v-model="form.category"
              placeholder="请选择物料类别"
              clearable
              filterable
              allow-create
              default-first-option
              style="width: 100%"
            >
              <el-option label="机械结构件" value="机械结构件" />
              <el-option label="驱动执行器" value="驱动执行器" />
              <el-option label="传感器件" value="传感器件" />
              <el-option label="电子电气" value="电子电气" />
              <el-option label="动力电池/电源" value="动力电池/电源" />
              <el-option label="线束接插件" value="线束接插件" />
              <el-option label="紧固标准件" value="紧固标准件" />
              <el-option label="流体气动件" value="流体气动件" />
              <el-option label="外观注塑件" value="外观注塑件" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">设计规格与责任体系</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="当前图纸版本" prop="drawing_version">
            <el-input
              v-model="form.drawing_version"
              placeholder="如 A.0, A.1, B.0"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="责任工程师" prop="engineer">
            <el-input
              v-model="form.engineer"
              placeholder="零件设计/质量责任人姓名"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">工艺说明与技术备忘</el-divider>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="工艺技术备注" prop="remark">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="4"
              placeholder="材质牌号 (如 AL6061-T6)、表面阳极氧化/电泳处理、关键装配配合公差等说明..."
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

interface ProjectOption {
  id: number
  project_code: string
  name: string
}

interface PartModel {
  id?: number
  part_no: string
  name: string
  project_id?: number | null
  category: string
  drawing_version: string
  engineer: string
  remark: string
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()
const projectOptions = ref<ProjectOption[]>([])

const form = reactive<PartModel>({
  id: undefined,
  part_no: '',
  name: '',
  project_id: null,
  category: '机械结构件',
  drawing_version: 'A.0',
  engineer: '',
  remark: ''
})

const rules: FormRules = {
  part_no: [
    { required: true, message: '零件物料编码不可为空', trigger: 'blur' },
    { min: 2, max: 64, message: '长度在 2 到 64 个字符', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '零件中文名称不可为空', trigger: 'blur' },
    { min: 2, max: 128, message: '长度在 2 到 128 个字符', trigger: 'blur' }
  ],
  drawing_version: [
    { required: true, message: '请输入当前图纸版本', trigger: 'blur' }
  ]
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  part_no: form.part_no,
  name: form.name,
  project_id: form.project_id,
  category: form.category,
  drawing_version: form.drawing_version,
  engineer: form.engineer,
  remark: form.remark
}))

// 加载项目候选下拉
const fetchProjectOptions = async () => {
  try {
    const res = await axios.get('/api/maindata/projects/options')
    projectOptions.value = res.data || []
  } catch (err: any) {
    console.error('加载项目候选项失败:', err)
  }
}

const resetForm = () => {
  form.id = undefined
  form.part_no = ''
  form.name = ''
  form.project_id = null
  form.category = '机械结构件'
  form.drawing_version = 'A.0'
  form.engineer = ''
  form.remark = ''
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = async (initialData?: Partial<PartModel>) => {
  resetForm()
  if (initialData) {
    Object.assign(form, initialData)
  }
  visible.value = true
  await fetchProjectOptions()
  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉
const openEdit = async (partId: number) => {
  resetForm()
  loading.value = true
  visible.value = true

  try {
    await fetchProjectOptions()
    const res = await axios.get(`/api/maindata/parts/${partId}`)
    const data = res.data
    form.id = data.id
    form.part_no = data.part_no
    form.name = data.name
    form.project_id = data.project_id ?? null
    form.category = data.category || '机械结构件'
    form.drawing_version = data.drawing_version || 'A.0'
    form.engineer = data.engineer || ''
    form.remark = data.remark || ''

    nextTick(() => {
      formRef.value?.clearValidate()
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`加载零件详情失败: ${err.response?.data?.detail || err.message}`)
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
        await axios.put(`/api/maindata/parts/${form.id}`, {
          name: form.name,
          project_id: form.project_id,
          category: form.category,
          drawing_version: form.drawing_version,
          engineer: form.engineer,
          remark: form.remark
        })
        ElMessage.success('零件信息已成功更新')
      } else {
        await axios.post('/api/maindata/parts', {
          part_no: form.part_no,
          name: form.name,
          project_id: form.project_id,
          category: form.category,
          drawing_version: form.drawing_version,
          engineer: form.engineer,
          remark: form.remark
        })
        ElMessage.success('零件已成功创建')
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
.part-form {
  padding: 8px 12px;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}
</style>
