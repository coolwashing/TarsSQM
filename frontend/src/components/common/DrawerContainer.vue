<template>
  <el-drawer
    v-model="internalVisible"
    :size="width"
    :title="title"
    :before-close="handleBeforeClose"
    :destroy-on-close="destroyOnClose"
    class="custom-70-drawer"
    append-to-body
  >
    <template #header>
      <div class="drawer-header-content">
        <div class="header-main">
          <span class="drawer-title">{{ title }}</span>
          <el-tag v-if="subTitle" type="info" size="small" effect="plain" class="sub-title-tag">
            {{ subTitle }}
          </el-tag>
          <el-tag v-if="isDirty" type="warning" size="small" effect="light" class="dirty-tag">
            * 存在未保存修改
          </el-tag>
        </div>
      </div>
    </template>

    <div class="drawer-body" :class="bodyClass" v-loading="loading">
      <slot />
    </div>

    <template #footer v-if="showFooter">
      <div class="drawer-footer-content">
        <div class="footer-left">
          <slot name="footer-left" />
        </div>
        <div class="footer-right">
          <el-button @click="handleCancel" :disabled="loading">
            {{ cancelText }}
          </el-button>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            {{ submitText }}
          </el-button>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface DrawerProps {
  modelValue: boolean
  title: string
  subTitle?: string
  width?: string
  loading?: boolean
  isDirty?: boolean
  showFooter?: boolean
  submitText?: string
  cancelText?: string
  destroyOnClose?: boolean
  beforeCloseHandler?: (done: (cancel?: boolean) => void) => void
  bodyClass?: string
}

const props = withDefaults(defineProps<DrawerProps>(), {
  width: '70%',
  loading: false,
  isDirty: false,
  showFooter: true,
  submitText: '保存并提交',
  cancelText: '取消退出',
  destroyOnClose: true,
  bodyClass: ''
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'submit'): void
  (e: 'cancel'): void
}>()

const internalVisible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const handleBeforeClose = (done: () => void) => {
  if (props.beforeCloseHandler) {
    props.beforeCloseHandler((cancel) => {
      if (!cancel) {
        done()
        emit('update:modelValue', false)
      }
    })
  } else {
    done()
    emit('update:modelValue', false)
  }
}

const handleCancel = () => {
  handleBeforeClose(() => {
    emit('cancel')
    emit('update:modelValue', false)
  })
}

const handleSubmit = () => {
  emit('submit')
}
</script>

<style>
/* 全局精确作用于 70% 宽幅抽屉，击穿 append-to-body 样式隔离，消除多余 60px 间隙 */
.custom-70-drawer.el-drawer {
  --el-drawer-padding-primary: 0px !important;
}

.custom-70-drawer .el-drawer__header {
  margin-bottom: 0 !important;
  padding: 10px 18px !important;
  border-bottom: 1px solid #e2e8f0 !important;
}

.custom-70-drawer .el-drawer__body {
  padding: 0 !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
  height: 100% !important;
}

.custom-70-drawer .el-drawer__footer {
  padding: 8px 18px !important;
  border-top: 1px solid #e2e8f0 !important;
  background-color: #fafbfc !important;
}
</style>

<style scoped>
.drawer-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.sub-title-tag {
  font-weight: 500;
}

.dirty-tag {
  font-size: 11px;
}

.drawer-body {
  flex: 1;
  padding: 10px 16px;
  overflow-y: auto;
}

.drawer-body.has-fixed-tabs {
  padding: 4px 16px 0 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.drawer-footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
