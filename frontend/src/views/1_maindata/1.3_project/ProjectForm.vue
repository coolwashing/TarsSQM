<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑项目信息' : '新建新产品项目'"
    :sub-title="isEdit ? form.project_code : '主数据车型/产品代号与量产里程碑'"
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
      class="project-form"
    >
      <el-divider content-position="left">基础代号与车型平台</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="项目唯一代号" prop="project_code">
            <el-input
              v-model="form.project_code"
              placeholder="如 PRJ-2026-X1 或 BPD-EVO"
              :disabled="isEdit"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="项目中文名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入产品/车型开发项目全称"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="所属平台/车型" prop="platform">
            <el-input
              v-model="form.platform"
              placeholder="如 具身机器人Bipedal-G2 或 全尺寸平台"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="项目开发状态" prop="status">
            <el-radio-group v-model="form.status">
              <el-radio-button value="立项">立项</el-radio-button>
              <el-radio-button value="开发中">开发中</el-radio-button>
              <el-radio-button value="量产">量产</el-radio-button>
              <el-radio-button value="结束">结束</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">量产节点计划</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="SOP 量产日期" prop="sop_date">
            <el-date-picker
              v-model="form.sop_date"
              type="date"
              placeholder="选择预估或锁定 SOP 日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">项目说明与备忘</el-divider>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="项目备忘备注" prop="remark">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="4"
              placeholder="填写项目客户背景、关键质量目标、首台样机试制计划等说明..."
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

interface ProjectModel {
  id?: number
  project_code: string
  name: string
  platform: string
  sop_date: string | null
  status: string
  remark: string
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()

const form = reactive<ProjectModel>({
  id: undefined,
  project_code: '',
  name: '',
  platform: '',
  sop_date: null,
  status: '开发中',
  remark: ''
})

const rules: FormRules = {
  project_code: [
    { required: true, message: '项目唯一代号不可为空', trigger: 'blur' },
    { min: 2, max: 64, message: '长度在 2 到 64 个字符', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '项目中文名称不可为空', trigger: 'blur' },
    { min: 2, max: 128, message: '长度在 2 到 128 个字符', trigger: 'blur' }
  ],
  status: [{ required: true, message: '请选择项目状态', trigger: 'change' }]
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  project_code: form.project_code,
  name: form.name,
  platform: form.platform,
  sop_date: form.sop_date,
  status: form.status,
  remark: form.remark
}))

const resetForm = () => {
  form.id = undefined
  form.project_code = ''
  form.name = ''
  form.platform = ''
  form.sop_date = null
  form.status = '开发中'
  form.remark = ''
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = (initialData?: Partial<ProjectModel>) => {
  resetForm()
  if (initialData) {
    Object.assign(form, initialData)
  }
  visible.value = true
  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉
const openEdit = async (projectId: number) => {
  resetForm()
  loading.value = true
  visible.value = true

  try {
    const res = await axios.get(`/api/maindata/projects/${projectId}`)
    const data = res.data
    form.id = data.id
    form.project_code = data.project_code
    form.name = data.name
    form.platform = data.platform || ''
    form.sop_date = data.sop_date || null
    form.status = data.status || '开发中'
    form.remark = data.remark || ''

    nextTick(() => {
      formRef.value?.clearValidate()
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`加载项目详情失败: ${err.response?.data?.detail || err.message}`)
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
        await axios.put(`/api/maindata/projects/${form.id}`, {
          name: form.name,
          platform: form.platform,
          sop_date: form.sop_date || null,
          status: form.status,
          remark: form.remark
        })
        ElMessage.success('项目信息更新成功')
      } else {
        await axios.post('/api/maindata/projects', {
          project_code: form.project_code,
          name: form.name,
          platform: form.platform,
          sop_date: form.sop_date || null,
          status: form.status,
          remark: form.remark
        })
        ElMessage.success('项目创建成功')
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
.project-form {
  padding: 8px 12px;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}
</style>
