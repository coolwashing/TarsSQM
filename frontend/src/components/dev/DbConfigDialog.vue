<template>
  <el-dialog
    v-model="visible"
    title="数据库连接向导与异机密码配置"
    width="560px"
    destroy-on-close
    class="db-config-dialog"
    :close-on-click-modal="false"
  >
    <div class="dialog-body">
      <!-- 异机密码与架构说明提示卡 -->
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mb-4 tip-alert"
      >
        <template #title>
          <span class="alert-title">异机密码隔离与持久化机制</span>
        </template>
        <div class="alert-desc">
          配置成功后将自动写入本地 <code>.env</code> 文件。由于 <code>.env</code> 已加入 <code>.gitignore</code>，不同电脑拉取代码不会相互覆盖数据库密码。
        </div>
      </el-alert>

      <!-- 当前存活状态指示条 -->
      <div class="status-banner" :class="{ 'is-online': statusInfo.is_connected, 'is-offline': !statusInfo.is_connected }">
        <div class="status-left">
          <span class="status-dot"></span>
          <span class="status-label">
            当前连接状态：<strong>{{ statusInfo.is_connected ? '正常连接中' : '连接不可用' }}</strong>
          </span>
        </div>
        <div class="status-meta" v-if="statusInfo.current_host">
          {{ statusInfo.current_host }}:{{ statusInfo.current_port }} / {{ statusInfo.current_db }}
        </div>
      </div>

      <!-- 表单配置区域 -->
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-position="top"
        class="config-form"
      >
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="主机地址 (Host)" prop="host">
              <el-input v-model="formData.host" placeholder="例如：127.0.0.1" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="端口 (Port)" prop="port">
              <el-input-number
                v-model="formData.port"
                :min="1"
                :max="65535"
                class="w-full"
                controls-position="right"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名 (User)" prop="user">
              <el-input v-model="formData.user" placeholder="例如：root" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库名 (Database)" prop="db_name">
              <el-input v-model="formData.db_name" placeholder="例如：sqm" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="连接密码 (Password)" prop="password">
          <el-input
            v-model="formData.password"
            type="password"
            show-password
            placeholder="请输入本机 MySQL 密码"
            autocomplete="new-password"
          />
          <div class="form-tip">
            留空或显示星号表示保留现有密码；输入新密码保存后将热重载连接池。
          </div>
        </el-form-item>
      </el-form>

      <!-- 测试结果反馈 -->
      <div v-if="testResult" class="test-feedback" :class="{ success: testResult.success, error: !testResult.success }">
        <el-icon class="feedback-icon">
          <CircleCheckFilled v-if="testResult.success" />
          <CircleCloseFilled v-else />
        </el-icon>
        <span class="feedback-text">{{ testResult.message }}</span>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          type="warning"
          plain
          :loading="testing"
          @click="handleTestConnection"
        >
          <el-icon class="mr-1"><Connection /></el-icon>
          测试连接
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveConfig"
        >
          保存并热重载
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { CircleCheckFilled, CircleCloseFilled, Connection } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import axios from 'axios'

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const visible = ref(false)
const testing = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()

const statusInfo = reactive({
  is_connected: false,
  current_host: '',
  current_port: 3306,
  current_user: '',
  current_db: '',
  masked_password: ''
})

const formData = reactive({
  host: '127.0.0.1',
  port: 3306,
  user: 'root',
  password: '',
  db_name: 'sqm'
})

const testResult = ref<{ success: boolean; message: string } | null>(null)

const formRules: FormRules = {
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }],
  user: [{ required: true, message: '请输入数据库用户名', trigger: 'blur' }],
  db_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }]
}

// 打开弹窗并同步后端当前真实配置
const open = async () => {
  visible.value = true
  testResult.value = null
  await fetchStatus()
}

const fetchStatus = async () => {
  try {
    const res = await axios.get('/api/dev/db/status')
    const data = res.data
    statusInfo.is_connected = data.is_connected
    statusInfo.current_host = data.current_host
    statusInfo.current_port = data.current_port
    statusInfo.current_user = data.current_user
    statusInfo.current_db = data.current_db
    statusInfo.masked_password = data.masked_password

    // 同步到表单
    formData.host = data.current_host || '127.0.0.1'
    formData.port = data.current_port || 3306
    formData.user = data.current_user || 'root'
    formData.db_name = data.current_db || 'sqm'
    formData.password = ''
  } catch (err: any) {
    ElMessage.error(`获取当前数据库连接信息失败: ${err.response?.data?.detail || err.message}`)
  }
}

// 测试连接
const handleTestConnection = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    testing.value = true
    testResult.value = null
    try {
      const res = await axios.post('/api/dev/db/test', {
        host: formData.host,
        port: formData.port,
        user: formData.user,
        password: formData.password || undefined,
        db_name: formData.db_name
      })
      testResult.value = {
        success: res.data.success,
        message: res.data.message
      }
      if (res.data.success) {
        ElMessage.success('连接测试成功！')
      } else {
        ElMessage.warning(`连接测试未通过: ${res.data.message}`)
      }
    } catch (err: any) {
      testResult.value = {
        success: false,
        message: err.response?.data?.detail || err.message || '测试失败'
      }
    } finally {
      testing.value = false
    }
  })
}

// 保存配置并热重载
const handleSaveConfig = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const res = await axios.post('/api/dev/db/save', {
        host: formData.host,
        port: formData.port,
        user: formData.user,
        password: formData.password || undefined,
        db_name: formData.db_name
      })
      ElMessage.success(res.data.message || '数据库配置已保存并生效')
      visible.value = false
      emit('saved')
    } catch (err: any) {
      ElMessage.error(`保存失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      saving.value = false
    }
  })
}

defineExpose({
  open
})
</script>

<style scoped>
.dialog-body {
  padding: 0 4px;
}

.tip-alert {
  margin-bottom: 16px;
  border-radius: 8px;
}

.alert-title {
  font-weight: 600;
  font-size: 13.5px;
}

.alert-desc {
  margin-top: 4px;
  font-size: 12.5px;
  line-height: 1.5;
  color: #475569;
}

.status-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 18px;
  font-size: 13px;
  transition: all 0.2s ease;
}

.status-banner.is-online {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.status-banner.is-offline {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.is-online .status-dot {
  background: #16a34a;
  box-shadow: 0 0 6px rgba(22, 163, 74, 0.4);
}

.is-offline .status-dot {
  background: #dc2626;
  box-shadow: 0 0 6px rgba(220, 38, 38, 0.4);
}

.status-meta {
  font-family: monospace;
  font-size: 12px;
  opacity: 0.85;
}

.config-form {
  margin-top: 6px;
}

.w-full {
  width: 100%;
}

.form-tip {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.test-feedback {
  margin-top: 14px;
  padding: 8px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.test-feedback.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.test-feedback.error {
  background: #fff1f2;
  color: #9f1239;
  border: 1px solid #fecdd3;
}

.feedback-icon {
  font-size: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
