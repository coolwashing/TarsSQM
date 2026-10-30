<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑质量问题台账' : '登记新质量异常'"
    :sub-title="isEdit ? form.issue_no : '质量异常台账与轻量化整改跟踪'"
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
      class="issue-form"
    >
      <el-divider content-position="left">基础信息与定级</el-divider>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="质量问题单号" prop="issue_no">
            <el-input
              v-model="form.issue_no"
              placeholder="系统将自动编号 (如 QI-20261018-001)"
              :disabled="isEdit"
              clearable
            />
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="严重等级" prop="severity">
            <el-radio-group v-model="form.severity">
              <el-radio-button value="致命">致命</el-radio-button>
              <el-radio-button value="严重">严重</el-radio-button>
              <el-radio-button value="一般">一般</el-radio-button>
              <el-radio-button value="微小">微小</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="24">
          <el-form-item label="问题主题简述" prop="title">
            <el-input
              v-model="form.title"
              placeholder="简要概括缺陷现象 (如: 机械臂传动法兰外圆跳动超差 0.04mm)"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="关联零部件" prop="part_id">
            <el-select
              v-model="form.part_id"
              placeholder="可选择关联零件物料"
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
          <el-form-item label="责任供应商" prop="supplier_id">
            <el-select
              v-model="form.supplier_id"
              placeholder="可选择承制供应商"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="s in supplierOptions"
                :key="s.id"
                :label="`[${s.code}] ${s.name}`"
                :value="s.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="闭环状态" prop="status">
            <el-radio-group v-model="form.status" @change="onStatusChange">
              <el-radio-button value="登记">登记</el-radio-button>
              <el-radio-button value="已提改善">已提改善</el-radio-button>
              <el-radio-button value="已验证">已验证</el-radio-button>
              <el-radio-button value="闭环">闭环</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="跟进责任人" prop="responsible">
            <el-input
              v-model="form.responsible"
              placeholder="责任SQE / 质量工程师"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="发现日期" prop="occurred_date">
            <el-date-picker
              v-model="form.occurred_date"
              type="date"
              placeholder="异常发生/首检日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>

        <el-col :span="12">
          <el-form-item label="闭环日期" prop="closed_date">
            <el-date-picker
              v-model="form.closed_date"
              type="date"
              placeholder="问题整改完成并验证闭环日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">缺陷现象描述 (嵌入 WangEditor 富文本)</el-divider>

      <div class="editor-block">
        <Editor
          v-model="form.issue_desc"
          placeholder="详细录入缺陷现场照片、缺陷特征、缺陷尺寸测量值、受影响批次等..."
          :min-height="220"
        />
      </div>

      <el-divider content-position="left">轻量化整改与改善方案 (嵌入 WangEditor 富文本)</el-divider>

      <div class="editor-block">
        <Editor
          v-model="form.solution"
          placeholder="录入根本原因分析 (5Why/人机料法环)、临时围堵措施、永久纠正预防措施 (CAPA)..."
          :min-height="220"
        />
      </div>

      <el-divider content-position="left">改善报告与检验整改附件 (嵌入流式 Uploader)</el-divider>

      <div class="uploader-block">
        <Uploader
          ref="uploaderRef"
          biz-type="quality_issue"
          :biz-id="form.id ?? null"
          v-model="attachmentList"
          accept=".pdf,.docx,.xlsx,.jpg,.png,.zip"
          :limit="8"
          :max-size-m-b="50"
        />
      </div>
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
import Editor from '@/components/editor/index.vue'
import Uploader from '@/components/uploader/index.vue'
import type { AttachmentItem } from '@/components/uploader/types'

interface OptionItem {
  id: number
  part_no?: string
  code?: string
  name: string
}

interface IssueModel {
  id?: number
  issue_no: string
  title: string
  part_id?: number | null
  supplier_id?: number | null
  severity: string
  status: string
  issue_desc: string
  solution: string
  responsible: string
  occurred_date: string | null
  closed_date: string | null
  remark: string
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()
const uploaderRef = ref<InstanceType<typeof Uploader>>()

const partOptions = ref<OptionItem[]>([])
const supplierOptions = ref<OptionItem[]>([])
const attachmentList = ref<AttachmentItem[]>([])

const form = reactive<IssueModel>({
  id: undefined,
  issue_no: '',
  title: '',
  part_id: null,
  supplier_id: null,
  severity: '一般',
  status: '登记',
  issue_desc: '',
  solution: '',
  responsible: '',
  occurred_date: new Date().toISOString().slice(0, 10),
  closed_date: null,
  remark: ''
})

const rules: FormRules = {
  title: [
    { required: true, message: '问题主题简述不可为空', trigger: 'blur' },
    { min: 4, max: 255, message: '长度在 4 到 255 个字符', trigger: 'blur' }
  ],
  severity: [{ required: true, message: '请选择严重等级', trigger: 'change' }],
  status: [{ required: true, message: '请选择闭环状态', trigger: 'change' }]
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  title: form.title,
  part_id: form.part_id,
  supplier_id: form.supplier_id,
  severity: form.severity,
  status: form.status,
  issue_desc: form.issue_desc,
  solution: form.solution,
  responsible: form.responsible,
  occurred_date: form.occurred_date,
  closed_date: form.closed_date
}))

const onStatusChange = (val: string) => {
  if (val === '闭环' && !form.closed_date) {
    form.closed_date = new Date().toISOString().slice(0, 10)
  }
}

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

const resetForm = () => {
  form.id = undefined
  form.issue_no = ''
  form.title = ''
  form.part_id = null
  form.supplier_id = null
  form.severity = '一般'
  form.status = '登记'
  form.issue_desc = ''
  form.solution = ''
  form.responsible = ''
  form.occurred_date = new Date().toISOString().slice(0, 10)
  form.closed_date = null
  form.remark = ''
  attachmentList.value = []
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = async () => {
  resetForm()
  visible.value = true
  await loadBaseOptions()

  // 预取系统下一个问题单号
  try {
    const nextRes = await axios.get('/api/sqm/issues/next-no')
    form.issue_no = nextRes.data.next_issue_no || ''
  } catch (e) {
    // 忽略异常，由后端自动生成
  }

  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉
const openEdit = async (issueId: number) => {
  resetForm()
  loading.value = true
  visible.value = true

  try {
    await loadBaseOptions()
    const res = await axios.get(`/api/sqm/issues/${issueId}`)
    const data = res.data
    form.id = data.id
    form.issue_no = data.issue_no
    form.title = data.title
    form.part_id = data.part_id ?? null
    form.supplier_id = data.supplier_id ?? null
    form.severity = data.severity || '一般'
    form.status = data.status || '登记'
    form.issue_desc = data.issue_desc || ''
    form.solution = data.solution || ''
    form.responsible = data.responsible || ''
    form.occurred_date = data.occurred_date || null
    form.closed_date = data.closed_date || null
    form.remark = data.remark || ''

    if (data.attachments && Array.isArray(data.attachments)) {
      attachmentList.value = data.attachments.map((att: any) => ({
        id: att.id,
        filePath: att.file_path,
        originalName: att.original_name,
        fileSize: att.file_size,
        mimeType: att.mime_type,
        bizType: att.biz_type,
        bizId: att.biz_id,
        url: att.url,
        status: 'success'
      }))
    }

    nextTick(() => {
      formRef.value?.clearValidate()
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`加载问题详情失败: ${err.response?.data?.detail || err.message}`)
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
      let savedId = form.id

      if (isEdit.value && form.id) {
        await axios.put(`/api/sqm/issues/${form.id}`, {
          title: form.title,
          part_id: form.part_id,
          supplier_id: form.supplier_id,
          severity: form.severity,
          status: form.status,
          issue_desc: form.issue_desc,
          solution: form.solution,
          responsible: form.responsible,
          occurred_date: form.occurred_date || null,
          closed_date: form.closed_date || null,
          remark: form.remark
        })
        ElMessage.success('质量问题记录更新成功')
      } else {
        const createRes = await axios.post('/api/sqm/issues', {
          issue_no: form.issue_no || undefined,
          title: form.title,
          part_id: form.part_id,
          supplier_id: form.supplier_id,
          severity: form.severity,
          status: form.status,
          issue_desc: form.issue_desc,
          solution: form.solution,
          responsible: form.responsible,
          occurred_date: form.occurred_date || null,
          closed_date: form.closed_date || null,
          remark: form.remark
        })
        savedId = createRes.data.id
        ElMessage.success(`质量问题 ${createRes.data.issue_no} 创建成功`)
      }

      // 如果有上传的文件且处于新建状态，执行二次绑定
      if (savedId && uploaderRef.value) {
        await uploaderRef.value.bindToBizId(savedId)
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
.issue-form {
  padding: 8px 12px;
}
:deep(.el-divider__text) {
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}
.editor-block {
  margin-bottom: 16px;
}
.uploader-block {
  margin-top: 8px;
  margin-bottom: 16px;
}
</style>
