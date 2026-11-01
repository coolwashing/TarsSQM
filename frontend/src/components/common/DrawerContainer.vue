<template>
  <el-drawer
    v-model="internalVisible"
    :size="drawerSize"
    :title="title"
    direction="rtl"
    :before-close="handleBeforeClose"
    :destroy-on-close="destroyOnClose"
    class="custom-70-drawer"
    append-to-body
  >
    <!-- 左侧可拖拽手柄 (支持水平拖拽改变抽屉宽度) -->
    <div
      v-if="resizable"
      class="drawer-resize-handle"
      :class="{ 'is-resizing': isResizing }"
      title="按住向左/向右拖拽调整抽屉宽度"
      @mousedown.prevent.stop="handleMouseDownResize"
    >
      <div class="resize-handle-pill" />
    </div>

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
import { ref, computed, watch } from 'vue'

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
  resizable?: boolean
  minWidth?: number
}

const props = withDefaults(defineProps<DrawerProps>(), {
  width: '70%',
  loading: false,
  isDirty: false,
  showFooter: true,
  submitText: '保存并提交',
  cancelText: '取消退出',
  destroyOnClose: true,
  bodyClass: '',
  resizable: true,
  minWidth: 460
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

const drawerSize = ref<string>(props.width || '70%')
const isResizing = ref(false)

// 响应外部 width 属性变化
watch(() => props.width, (val) => {
  if (!isResizing.value && val) {
    drawerSize.value = val
  }
})

// 监听抽屉开启，保证初始大小有效
watch(() => props.modelValue, (isOpen) => {
  if (isOpen && !drawerSize.value) {
    drawerSize.value = props.width || '70%'
  }
})

let startX = 0
let startWidth = 0

const handleMouseDownResize = (e: MouseEvent) => {
  if (!props.resizable) return
  isResizing.value = true
  startX = e.clientX

  // 获取抽屉 DOM 当前实际像素宽度
  const drawerEl = document.querySelector('.custom-70-drawer.el-drawer') as HTMLElement
  if (drawerEl) {
    startWidth = drawerEl.offsetWidth
  } else {
    startWidth = window.innerWidth * 0.7
  }

  document.body.style.cursor = 'ew-resize'
  document.body.style.userSelect = 'none'

  const onMouseMove = (moveEvent: MouseEvent) => {
    // 抽屉位于屏幕右侧向左展开，向左移(moveEvent.clientX < startX)宽度变大
    const dx = startX - moveEvent.clientX
    const minW = props.minWidth || 460
    const maxW = Math.round(window.innerWidth * 0.96)
    const newWidth = Math.min(Math.max(startWidth + dx, minW), maxW)
    drawerSize.value = `${newWidth}px`
  }

  const onMouseUp = () => {
    isResizing.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

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
/* 全局精确作用于 70% 宽幅抽屉，击穿 append-to-body 样式隔离 */
.custom-70-drawer.el-drawer {
  --el-drawer-padding-primary: 0px !important;
  position: absolute !important;
  right: 0 !important;
  top: 0 !important;
  bottom: 0 !important;
  height: 100% !important;
  margin: 0 !important;
  overflow: visible !important;
}

.custom-70-drawer .el-drawer__header {
  margin-bottom: 0 !important;
  padding: 10px 18px !important;
  border-bottom: 1px solid #e2e8f0 !important;
  background-color: #ffffff !important;
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

/* 左侧拖拽调整把手 */
.drawer-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 10px;
  cursor: ew-resize;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s ease;
  user-select: none;
}

.drawer-resize-handle:hover,
.drawer-resize-handle.is-resizing {
  background-color: rgba(37, 99, 235, 0.12);
}

.resize-handle-pill {
  width: 3px;
  height: 48px;
  background-color: #cbd5e1;
  border-radius: 2px;
  transition: all 0.15s ease;
}

.drawer-resize-handle:hover .resize-handle-pill,
.drawer-resize-handle.is-resizing .resize-handle-pill {
  background-color: #2563eb;
  height: 64px;
  width: 4px;
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
