<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑协同任务' : '新建质量协同任务'"
    width="840px"
    top="6vh"
    destroy-on-close
    append-to-body
    :before-close="handleClose"
    class="task-edit-dialog"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="110px"
      size="default"
      class="task-form"
    >
      <el-form-item label="任务标题" prop="title">
        <el-input
          v-model="formData.title"
          placeholder="请输入清晰的质量待办/整改任务标题..."
          clearable
        />
      </el-form-item>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="业务源头" prop="source_type">
            <el-select v-model="formData.source_type" style="width: 100%">
              <el-option label="🏢 供应商清单" value="SUPPLIER" />
              <el-option label="⚙️ 零件开发试产" value="PART" />
              <el-option label="🎯 CTQ 关键特性" value="CTQ" />
              <el-option label="📑 质量知识规程" value="DOC_KB" />
              <el-option label="📋 协同待办" value="CUSTOM" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="源头实体名" prop="source_title">
            <el-input
              v-model="formData.source_title"
              placeholder="如: 苏州精工模具 / 法兰盘"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="责任人" prop="assignee_name">
            <el-input
              v-model="formData.assignee_name"
              placeholder="指定责任工程师姓名"
              clearable
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="任务优先级" prop="priority">
            <el-select v-model="formData.priority" style="width: 100%">
              <el-option label="🟢 普通" value="MEDIUM" />
              <el-option label="🟡 重点关注" value="HIGH" />
              <el-option label="🔴 紧急红线" value="URGENT" />
              <el-option label="⚪ 低优先级" value="LOW" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="计划开始日">
            <el-date-picker
              v-model="formData.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择起始日期"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计划截止日" prop="due_date">
            <el-date-picker
              v-model="formData.due_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择截止日期"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="流转状态" prop="status">
        <el-radio-group v-model="formData.status" size="small">
          <el-radio-button value="TODO">待办</el-radio-button>
          <el-radio-button value="IN_PROGRESS">进行中</el-radio-button>
          <el-radio-button value="PENDING_REVIEW">待复核</el-radio-button>
          <el-radio-button value="DONE">已闭环</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="验收与说明">
        <div class="tiptap-modal-editor-box">
          <TiptapEditor
            v-model="formData.description_html"
            placeholder="输入任务具体技术要求、验收清单 Checklist 或改善对策，支持表格与截图直接粘贴..."
            :show-ai="false"
          />
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存更改' : '立即创建' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { taskApi } from '@/api/task'
import TiptapEditor from '@/components/editor/TiptapEditor.vue'
import type { TaskItem, TaskStatus, TaskPriority, TaskSourceType } from '@/types/task'

const props = defineProps<{
  modelValue: boolean
  task?: Partial<TaskItem> | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.task?.id)
const formRef = ref<FormInstance>()
const saving = ref(false)

const formData = reactive({
  title: '',
  source_type: 'CUSTOM' as TaskSourceType,
  source_id: null as string | number | null,
  source_title: '',
  source_url: '',
  assignee_name: '',
  priority: 'MEDIUM' as TaskPriority,
  status: 'TODO' as TaskStatus,
  start_date: null as string | null,
  due_date: null as string | null,
  description_html: ''
})

const formRules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择业务源头', trigger: 'change' }]
}

watch(
  () => props.task,
  (t) => {
    if (t) {
      formData.title = t.title || ''
      formData.source_type = t.source_type || 'CUSTOM'
      formData.source_id = t.source_id !== undefined ? t.source_id : null
      formData.source_title = t.source_title || ''
      formData.source_url = t.source_url || ''
      formData.assignee_name = t.assignee_name || ''
      formData.priority = t.priority || 'MEDIUM'
      formData.status = t.status || 'TODO'
      formData.start_date = t.start_date || null
      formData.due_date = t.due_date || null
      formData.description_html = t.description_html || ''
    } else {
      formData.title = ''
      formData.source_type = 'CUSTOM'
      formData.source_id = null
      formData.source_title = ''
      formData.source_url = ''
      formData.assignee_name = ''
      formData.priority = 'MEDIUM'
      formData.status = 'TODO'
      formData.start_date = null
      formData.due_date = null
      formData.description_html = ''
    }
  },
  { immediate: true }
)

const handleClose = () => {
  visible.value = false
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      saving.value = true
      if (isEdit.value && props.task && props.task.id) {
        await taskApi.updateTask(props.task.id, formData)
        ElMessage.success('任务信息已更新')
      } else {
        await taskApi.createTask(formData)
        ElMessage.success('协同任务创建成功')
      }
      emit('saved')
      handleClose()
    } catch (err: any) {
      ElMessage.error(`保存失败: ${err.message || '网络异常'}`)
    } finally {
      saving.value = false
    }
  })
}
</script>

<style scoped>
.task-form {
  padding-right: 8px;
}

.tiptap-modal-editor-box {
  width: 100%;
  height: 280px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
