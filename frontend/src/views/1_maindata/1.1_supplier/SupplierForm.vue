<template>
  <DrawerContainer
    v-model="visible"
    :title="isEdit ? '编辑供应商' : '新建供应商'"
    :sub-title="isEdit ? `简称代号：${form.code}` : '主数据准入登记'"
    width="70%"
    body-class="has-fixed-tabs"
    :loading="loading"
    :is-dirty="isDirty"
    :before-close-handler="confirmBeforeClose"
    @submit="handleSave"
    @cancel="handleCancel"
  >
    <el-tabs v-model="activeTab" class="supplier-drawer-tabs">
      <!-- Tab 1: 核心主数据 -->
      <el-tab-pane name="basic">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><InfoFilled /></el-icon>
            <span>基本主数据</span>
          </span>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="110px"
          label-position="right"
          class="supplier-form"
        >
      <!-- 分组 1: 核心标识与主体 -->
      <div class="form-section-card">
        <div class="section-title">
          <span class="indicator"></span>
          <span>核心标识与主体信息</span>
        </div>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应商简称" prop="code">
              <el-input
                v-model="form.code"
                placeholder="唯一拼音代号，如 CK、SK、REM、ZS"
                clearable
                @input="handleCodeInput"
              >
                <template #append>
                  <el-button :icon="Search" :loading="checkingCode" @click="verifyCode">
                    校验唯一
                  </el-button>
                </template>
              </el-input>
              <div v-if="codeCheckTip" class="field-hint" :class="{ 'hint-error': !codeCheckAvailable }">
                {{ codeCheckTip }}
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="企业全称" prop="name">
              <el-input
                v-model="form.name"
                placeholder="工商注册全称，如 浙江三凯机电有限公司"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应层级" prop="supply_tier">
              <el-select
                v-model="form.supply_tier"
                placeholder="请选择供应层级"
                class="w-full"
                clearable
              >
                <el-option
                  v-for="opt in optionDict.supply_tiers"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="准入状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio-button value="合格">合格</el-radio-button>
                <el-radio-button value="考察">考察</el-radio-button>
                <el-radio-button value="潜在">潜在</el-radio-button>
                <el-radio-button value="冻结">冻结</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- 分组 2: 零件产品定位与企业资质 -->
      <div class="form-section-card">
        <div class="section-title">
          <span class="indicator"></span>
          <span>零件定位与企业资质</span>
        </div>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="零件/产品类型" prop="product_type">
              <el-select
                v-model="form.product_type"
                placeholder="选择或输入主营零件/产品类型"
                class="w-full"
                filterable
                allow-create
                clearable
              >
                <el-option
                  v-for="opt in optionDict.product_types"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所在城市" prop="city">
              <el-select
                v-model="form.city"
                placeholder="选择或输入城市"
                class="w-full"
                filterable
                allow-create
                clearable
              >
                <el-option
                  v-for="opt in optionDict.cities"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="质量体系认证" prop="quality_system">
              <el-select
                v-model="form.quality_system"
                placeholder="选择或输入质量体系"
                class="w-full"
                filterable
                allow-create
                clearable
              >
                <el-option
                  v-for="opt in optionDict.quality_systems"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="公司规模类型" prop="company_type">
              <el-select
                v-model="form.company_type"
                placeholder="选择公司类型"
                class="w-full"
                filterable
                allow-create
                clearable
              >
                <el-option
                  v-for="opt in optionDict.company_types"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应商配合度" prop="cooperation_rate">
              <el-radio-group v-model="form.cooperation_rate">
                <el-radio-button value="高">高</el-radio-button>
                <el-radio-button value="中">中</el-radio-button>
                <el-radio-button value="低">低</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="日常中文简称" prop="short_name">
              <el-input
                v-model="form.short_name"
                placeholder="日常口头简称（选填，如 浙江三凯）"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- 分组 3: 联络与制造基地 -->
      <div class="form-section-card">
        <div class="section-title">
          <span class="indicator"></span>
          <span>联络与制造基地地址</span>
        </div>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="主要联络人" prop="contact">
              <el-input v-model="form.contact" placeholder="联系人姓名" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联系电话" prop="phone">
              <el-input v-model="form.phone" placeholder="手机号或固话" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="电子邮箱" prop="email">
              <el-input v-model="form.email" placeholder="商务 / 质量邮箱" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="工厂/办公地址" prop="address">
              <el-input
                v-model="form.address"
                placeholder="制造生产基地或注册详细地址"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="台账备忘说明" prop="remark">
              <el-input
                v-model="form.remark"
                type="textarea"
                :rows="3"
                placeholder="客户定位、产值规模、合作工艺备忘等关键信息..."
              />
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </el-form>
      </el-tab-pane>

      <!-- Tab 2: 图文档案与附件 -->
      <el-tab-pane name="profile">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Document /></el-icon>
            <span>图文档案与附件</span>
            <el-badge
              v-if="attachmentList.length > 0"
              :value="attachmentList.length"
              class="tab-badge"
              type="primary"
            />
          </span>
        </template>

        <div class="profile-tab-content">
          <!-- 卡片 1: 供应商图文档案 -->
          <div class="form-section-card">
            <div class="section-title title-with-actions">
              <div class="title-left">
                <span class="indicator"></span>
                <span>图文详细档案</span>
              </div>
              <el-button
                type="primary"
                link
                size="small"
                :icon="Download"
                :loading="exportingWord"
                @click="downloadAsDocx"
              >
                导出为 Word (.docx)
              </el-button>
            </div>
            <div class="editor-wrapper-block">
              <Editor
                v-model="form.profile_html"
                placeholder="请输入供应商考察纪要、现场产线/设备照片、审核评分报告、质量攻关备忘..."
                :min-height="300"
              />
            </div>
          </div>

          <!-- 卡片 2: 资质与证明附件 -->
          <div class="form-section-card">
            <div class="section-title">
              <span class="indicator"></span>
              <span>资质与证明附件</span>
            </div>
            <div class="uploader-wrapper-block">
              <Uploader
                ref="uploaderRef"
                biz-type="supplier"
                :biz-id="form.id ?? null"
                v-model="attachmentList"
                accept=".pdf,.doc,.docx,.xlsx,.xls,.png,.jpg,.jpeg,.zip,.rar"
                :limit="10"
                :max-size-m-b="50"
              />
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </DrawerContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { Search, InfoFilled, Document, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import DrawerContainer from '@/components/common/DrawerContainer.vue'
import { useDirtyCheck } from '@/components/common/useDirtyCheck'
import Editor from '@/components/editor/index.vue'
import Uploader from '@/components/uploader/index.vue'
import type { AttachmentItem } from '@/components/uploader/types'

interface SupplierModel {
  id?: number
  code: string
  name: string
  short_name?: string
  pinyin?: string
  status: string
  supply_tier?: string
  product_type?: string
  cooperation_rate?: string
  quality_system?: string
  region?: string
  city?: string
  company_type?: string
  purchasing_status?: string
  contact?: string
  phone?: string
  email?: string
  address?: string
  remark?: string
  profile_html?: string
}

interface OptionDict {
  product_types: string[]
  cities: string[]
  quality_systems: string[]
  company_types: string[]
  supply_tiers: string[]
}

const emit = defineEmits<{
  (e: 'success'): void
}>()

const visible = ref(false)
const loading = ref(false)
const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()
const activeTab = ref<'basic' | 'profile'>('basic')
const attachmentList = ref<AttachmentItem[]>([])
const uploaderRef = ref<any>()

const checkingCode = ref(false)
const codeCheckTip = ref('')
const codeCheckAvailable = ref(true)

const exportingWord = ref(false)

const downloadAsDocx = async () => {
  if (!form.profile_html || !form.profile_html.trim()) {
    ElMessage.warning('当前富文本内容为空，请先录入图文内容后再导出')
    return
  }
  exportingWord.value = true
  try {
    const filename = `${form.name || form.code || '供应商'}_图文档案`
    const res = await axios.post(
      '/api/storage/export-docx',
      {
        title: filename,
        html: form.profile_html
      },
      { responseType: 'blob' }
    )
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.docx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('Word (.docx) 导出成功！')
  } catch (err: any) {
    ElMessage.error(`导出 Word 失败: ${err.message}`)
  } finally {
    exportingWord.value = false
  }
}

// 去重字典选项
const optionDict = reactive<OptionDict>({
  product_types: [
    '外购件-关节模组', '减速机', '结构件-手臂类', '结构件-胸腔类', '结构件-下肢类',
    '驱动板', '自研电机', '组装', '电池类', '线束类', '齿轮', '齿轮箱',
    '视触觉传感器', '摄像头', '代工', 'BMS', 'SMT', '充电宝', '适配器'
  ],
  cities: ['上海', '苏州', '东莞', '惠州', '台州', '无锡', '常州', '深圳', '江西共青城'],
  quality_systems: ['IATF16949', 'ISO9001', '14001 环境管理体系', '45001 职业健康安全管理体系', '50001 能源管理体系'],
  company_types: ['中型规模企业', '小型专精企业', '集团公司', '初创型企业', '国有企业'],
  supply_tiers: ['1供', '2供开发中', '在开发', '潜在供应商']
})

const form = reactive<SupplierModel>({
  id: undefined,
  code: '',
  name: '',
  short_name: '',
  pinyin: '',
  status: '合格',
  supply_tier: '1供',
  product_type: '',
  cooperation_rate: '高',
  quality_system: '',
  region: '',
  city: '',
  company_type: '',
  purchasing_status: '',
  contact: '',
  phone: '',
  email: '',
  address: '',
  remark: '',
  profile_html: ''
})

// 自动转大写
const handleCodeInput = (val: string) => {
  form.code = val.toUpperCase().replace(/\s+/g, '')
  form.pinyin = form.code
  codeCheckTip.value = ''
  codeCheckAvailable.value = true
}

// 异步校验供应商简称唯一性
const verifyCode = async () => {
  const code = form.code.trim().toUpperCase()
  if (!code) {
    codeCheckTip.value = '请先输入供应商简称'
    codeCheckAvailable.value = false
    return
  }
  checkingCode.value = true
  try {
    const res = await axios.get('/api/maindata/suppliers/check-code', {
      params: {
        code,
        exclude_id: form.id || undefined
      }
    })
    codeCheckAvailable.value = res.data.available
    codeCheckTip.value = res.data.message
    if (res.data.available) {
      ElMessage.success(`供应商简称 "${code}" 可用且唯一`)
    } else {
      ElMessage.warning(res.data.message)
    }
  } catch (err: any) {
    codeCheckTip.value = '校验接口异常'
  } finally {
    checkingCode.value = false
  }
}

// 表单校验规则（极简：仅供应商简称与企业全称必填，杜绝繁琐拦截）
const validateCodeAsync = async (_rule: any, value: string, callback: any) => {
  if (!value || !value.trim()) {
    return callback(new Error('供应商简称不可为空'))
  }
  const clean = value.trim().toUpperCase()
  try {
    const res = await axios.get('/api/maindata/suppliers/check-code', {
      params: {
        code: clean,
        exclude_id: form.id || undefined
      }
    })
    if (!res.data.available) {
      callback(new Error(res.data.message))
    } else {
      callback()
    }
  } catch {
    callback()
  }
}

const rules: FormRules = {
  code: [
    { required: true, message: '请输入供应商简称（如 CK、SK、REM）', trigger: 'blur' },
    { validator: validateCodeAsync, trigger: 'blur' }
  ],
  name: [
    { required: true, message: '企业全称不可为空', trigger: 'blur' }
  ]
}

// 加载后台去重字典集合
const loadOptions = async () => {
  try {
    const res = await axios.get('/api/maindata/suppliers/options')
    if (res.data) {
      if (res.data.product_types?.length) optionDict.product_types = res.data.product_types
      if (res.data.cities?.length) optionDict.cities = res.data.cities
      if (res.data.quality_systems?.length) optionDict.quality_systems = res.data.quality_systems
      if (res.data.company_types?.length) optionDict.company_types = res.data.company_types
      if (res.data.supply_tiers?.length) optionDict.supply_tiers = res.data.supply_tiers
    }
  } catch {
    // 使用预置字典静默容错
  }
}

// 绑定 70% 宽幅抽屉防呆 Dirty Check 机制
const { isDirty, captureInitialState, markClean, confirmBeforeClose } = useDirtyCheck(() => ({
  code: form.code,
  name: form.name,
  short_name: form.short_name,
  status: form.status,
  supply_tier: form.supply_tier,
  product_type: form.product_type,
  cooperation_rate: form.cooperation_rate,
  quality_system: form.quality_system,
  city: form.city,
  company_type: form.company_type,
  contact: form.contact,
  phone: form.phone,
  email: form.email,
  address: form.address,
  remark: form.remark,
  profile_html: form.profile_html
}))

const resetForm = () => {
  form.id = undefined
  form.code = ''
  form.name = ''
  form.short_name = ''
  form.pinyin = ''
  form.status = '合格'
  form.supply_tier = '1供'
  form.product_type = ''
  form.cooperation_rate = '高'
  form.quality_system = ''
  form.region = ''
  form.city = ''
  form.company_type = ''
  form.purchasing_status = ''
  form.contact = ''
  form.phone = ''
  form.email = ''
  form.address = ''
  form.remark = ''
  form.profile_html = ''
  attachmentList.value = []
  codeCheckTip.value = ''
  codeCheckAvailable.value = true
  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

// 打开新建抽屉
const openCreate = () => {
  resetForm()
  activeTab.value = 'basic'
  loadOptions()
  visible.value = true
  nextTick(() => {
    captureInitialState()
  })
}

// 打开编辑抽屉 (支持传入默认激活 tab)
const openEdit = async (supplierId: number, defaultTab: 'basic' | 'profile' = 'basic') => {
  resetForm()
  activeTab.value = defaultTab
  loadOptions()
  loading.value = true
  visible.value = true

  try {
    const res = await axios.get(`/api/maindata/suppliers/${supplierId}`)
    const data = res.data
    form.id = data.id
    form.code = data.code || ''
    form.name = data.name || ''
    form.short_name = data.short_name || ''
    form.pinyin = data.pinyin || data.code || ''
    form.status = data.status || '合格'
    form.supply_tier = data.supply_tier || '1供'
    form.product_type = data.product_type || ''
    form.cooperation_rate = data.cooperation_rate || '高'
    form.quality_system = data.quality_system || ''
    form.region = data.region || ''
    form.city = data.city || ''
    form.company_type = data.company_type || ''
    form.purchasing_status = data.purchasing_status || ''
    form.contact = data.contact || ''
    form.phone = data.phone || ''
    form.email = data.email || ''
    form.address = data.address || ''
    form.remark = data.remark || ''
    form.profile_html = data.profile_html || ''

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
      captureInitialState()
    })
  } catch (err: any) {
    ElMessage.error(`获取供应商详情失败: ${err.response?.data?.detail || err.message}`)
    visible.value = false
  } finally {
    loading.value = false
  }
}

// 保存提交
const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) {
      activeTab.value = 'basic'
      ElMessage.warning('请先完善基本主数据中的必填项')
      return
    }

    loading.value = true
    try {
      form.code = form.code.trim().toUpperCase()
      form.pinyin = form.code
      if (!form.short_name) {
        form.short_name = form.name.length <= 6 ? form.name : form.code
      }

      let savedId = form.id
      if (isEdit.value && form.id) {
        await axios.put(`/api/maindata/suppliers/${form.id}`, form)
        ElMessage.success(`供应商 ${form.name}（${form.code}）更新成功`)
      } else {
        const createRes = await axios.post('/api/maindata/suppliers', form)
        savedId = createRes.data.id
        ElMessage.success(`供应商 ${form.name}（${form.code}）新建成功`)
      }

      // 无论新建还是编辑，如上传了新附件统一批量绑定实体 ID
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

onMounted(() => {
  loadOptions()
})

defineExpose({
  openCreate,
  openEdit
})
</script>

<style scoped>
.supplier-form {
  padding: 0;
}

.form-section-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px 4px 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}

.title-with-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.indicator {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: #6366f1;
}

.field-hint {
  font-size: 12px;
  color: #10b981;
  margin-top: 4px;
}

.hint-error {
  color: #ef4444;
}

.w-full {
  width: 100%;
}

/* 抽屉顶部选项卡：100% 物理置顶固定 + 无垂直滚动条 + 零冗余间距 */
.supplier-drawer-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.supplier-drawer-tabs :deep(.el-tabs__header) {
  flex-shrink: 0;
  margin: 0 !important;
  padding: 0 0 4px 0;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  overflow: hidden !important;
}

.supplier-drawer-tabs :deep(.el-tabs__nav-wrap),
.supplier-drawer-tabs :deep(.el-tabs__nav-scroll) {
  overflow: hidden !important;
  margin: 0 !important;
}

.supplier-drawer-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding-top: 8px;
  padding-right: 4px;
  padding-bottom: 16px;
}

.supplier-drawer-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  padding: 0 14px;
  height: 34px;
  line-height: 34px;
}

.supplier-drawer-tabs :deep(.el-tabs__item.is-active) {
  color: #4f46e5;
  font-weight: 700;
}

.tab-label-custom {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.tab-badge {
  margin-left: 4px;
}

.tab-badge :deep(.el-badge__content) {
  background-color: #6366f1;
}

.profile-tab-content {
  padding: 0 0 12px 0;
}

.editor-wrapper-block {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 4px;
}

.uploader-wrapper-block {
  margin-top: 4px;
}
</style>
