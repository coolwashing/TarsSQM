<template>
  <node-view-wrapper
    class="resizable-image-node-view"
    :class="[
      `align-${node.attrs.align || 'center'}`,
      { 'is-selected': selected, 'is-resizing': isResizing }
    ]"
    :data-align="node.attrs.align || 'center'"
  >
    <div
      class="image-resizable-container"
      ref="containerRef"
      :style="{ width: displayWidth }"
      @click.stop="handleContainerClick"
    >
      <img
        :src="node.attrs.src"
        :alt="node.attrs.alt"
        :title="node.attrs.title"
        class="rendered-image"
        ref="imgRef"
        draggable="false"
      />

      <!-- 选中时展示的四角等比缩放拖拽锚点 (Resize Handles) -->
      <div v-if="selected && editor?.isEditable" class="resize-handle-layer">
        <span
          class="handle-anchor top-left"
          @mousedown.prevent.stop="startResize('top-left', $event)"
          title="按住等比缩放"
        ></span>
        <span
          class="handle-anchor top-right"
          @mousedown.prevent.stop="startResize('top-right', $event)"
          title="按住等比缩放"
        ></span>
        <span
          class="handle-anchor bottom-left"
          @mousedown.prevent.stop="startResize('bottom-left', $event)"
          title="按住等比缩放"
        ></span>
        <span
          class="handle-anchor bottom-right"
          @mousedown.prevent.stop="startResize('bottom-right', $event)"
          title="按住等比缩放"
        ></span>
      </div>

      <!-- 选中时浮现的飞书/Notion 风格快捷尺寸与对齐浮动胶囊 -->
      <transition name="toolbar-fade">
        <div
          v-if="selected && editor?.isEditable"
          class="image-action-bubble"
          @mousedown.stop
          @click.stop
        >
          <div class="bubble-btn-group size-group">
            <button
              type="button"
              class="bubble-pill-btn"
              :class="{ active: isRatioActive('25%') }"
              @click="setPresetWidth('25%')"
              title="缩放到 25% 宽度"
            >
              25%
            </button>
            <button
              type="button"
              class="bubble-pill-btn"
              :class="{ active: isRatioActive('50%') }"
              @click="setPresetWidth('50%')"
              title="缩放到 50% 宽度"
            >
              50%
            </button>
            <button
              type="button"
              class="bubble-pill-btn"
              :class="{ active: isRatioActive('75%') }"
              @click="setPresetWidth('75%')"
              title="缩放到 75% 宽度"
            >
              75%
            </button>
            <button
              type="button"
              class="bubble-pill-btn"
              :class="{ active: isRatioActive('100%') }"
              @click="setPresetWidth('100%')"
              title="撑满 100% 宽度"
            >
              100%
            </button>
          </div>

          <span class="bubble-sep"></span>

          <div class="bubble-btn-group align-group">
            <button
              type="button"
              class="bubble-icon-btn"
              :class="{ active: (node.attrs.align || 'center') === 'left' }"
              @click="setAlignment('left')"
              title="居左排版"
            >
              <span class="align-icon">⇤</span>
            </button>
            <button
              type="button"
              class="bubble-icon-btn"
              :class="{ active: (node.attrs.align || 'center') === 'center' }"
              @click="setAlignment('center')"
              title="居中排版"
            >
              <span class="align-icon">⇥⇤</span>
            </button>
            <button
              type="button"
              class="bubble-icon-btn"
              :class="{ active: (node.attrs.align || 'center') === 'right' }"
              @click="setAlignment('right')"
              title="居右排版"
            >
              <span class="align-icon">⇥</span>
            </button>
          </div>

          <span class="bubble-sep"></span>

          <div class="bubble-btn-group action-group">
            <button
              type="button"
              class="bubble-icon-btn preview-btn"
              @click="triggerLightbox"
              title="免下载全屏大图预览"
            >
              <span>🔍</span>
              <span class="btn-text">全屏</span>
            </button>
            <button
              type="button"
              class="bubble-icon-btn delete-btn"
              @click="deleteImageNode"
              title="删除此图片 (Delete)"
            >
              <span>🗑️</span>
            </button>
          </div>
        </div>
      </transition>
    </div>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

const containerRef = ref<HTMLElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)
const isResizing = ref(false)

// 当前显示宽度 (支持 25%, 50%, 100% 或像素)
const displayWidth = computed(() => {
  const w = props.node.attrs.width
  if (!w || w === 'auto') return 'auto'
  return typeof w === 'number' ? `${w}px` : w
})

const isRatioActive = (ratioStr: string) => {
  return props.node.attrs.width === ratioStr
}

// 快速预设比例
const setPresetWidth = (widthStr: string) => {
  props.updateAttributes({
    width: widthStr
  })
}

// 设置对齐方式 (left / center / right)
const setAlignment = (alignStr: string) => {
  props.updateAttributes({
    align: alignStr
  })
}

// 删除图片
const deleteImageNode = () => {
  props.deleteNode()
}

// 呼出灯箱预览
const triggerLightbox = () => {
  const src = props.node.attrs.src
  if (!src) return
  window.dispatchEvent(
    new CustomEvent('sqm-image-lightbox', {
      detail: { src }
    })
  )
}

// 单机容器：唤起 NodeSelection
const handleContainerClick = () => {
  // ProseMirror 自身会同步 selected prop
}

// 四角拖拽等比缩放
let startX = 0
let startWidthPx = 0
let parentWidthPx = 0
let activeHandle = ''

const onMouseMoveResize = (e: MouseEvent) => {
  if (!isResizing.value) return
  const deltaX = e.clientX - startX

  let newWidthPx = startWidthPx
  if (activeHandle === 'bottom-right' || activeHandle === 'top-right') {
    newWidthPx = startWidthPx + deltaX
  } else if (activeHandle === 'bottom-left' || activeHandle === 'top-left') {
    newWidthPx = startWidthPx - deltaX
  }

  // 约束在 80px 到 parentWidth 之间
  const minWidth = 80
  const maxWidth = Math.max(parentWidthPx, 300)
  const clampedWidthPx = Math.max(minWidth, Math.min(maxWidth, newWidthPx))

  // 计算百分比
  const percent = Math.round((clampedWidthPx / parentWidthPx) * 100)
  const clampedPercent = Math.max(15, Math.min(100, percent))

  props.updateAttributes({
    width: `${clampedPercent}%`
  })
}

const onMouseUpResize = () => {
  isResizing.value = false
  window.removeEventListener('mousemove', onMouseMoveResize)
  window.removeEventListener('mouseup', onMouseUpResize)
}

const startResize = (handle: string, e: MouseEvent) => {
  activeHandle = handle
  isResizing.value = true
  startX = e.clientX

  if (containerRef.value) {
    startWidthPx = containerRef.value.offsetWidth
    const editorDom = containerRef.value.closest('.ProseMirror') as HTMLElement
    parentWidthPx = editorDom ? editorDom.clientWidth - 36 : containerRef.value.parentElement?.clientWidth || 800
  }

  window.addEventListener('mousemove', onMouseMoveResize)
  window.addEventListener('mouseup', onMouseUpResize)
}
</script>

<style scoped>
.resizable-image-node-view {
  display: block;
  margin: 14px 0;
  position: relative;
  user-select: none;
}

/* 对齐排版布局 */
.resizable-image-node-view.align-left {
  display: flex;
  justify-content: flex-start;
}
.resizable-image-node-view.align-center {
  display: flex;
  justify-content: center;
}
.resizable-image-node-view.align-right {
  display: flex;
  justify-content: flex-end;
}

.image-resizable-container {
  position: relative;
  display: inline-block;
  max-width: 100%;
  line-height: 0;
  border-radius: 8px;
  transition: box-shadow 0.15s ease, outline 0.15s ease;
}

.rendered-image {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
  pointer-events: auto;
  cursor: default;
}

/* 选中高亮状态 */
.resizable-image-node-view.is-selected .image-resizable-container {
  outline: 2px solid #2563eb;
  outline-offset: 3px;
  box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.15), 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* 四角拉伸手柄 */
.resize-handle-layer {
  position: absolute;
  inset: -6px;
  pointer-events: none;
  z-index: 20;
}

.handle-anchor {
  position: absolute;
  width: 11px;
  height: 11px;
  background: #ffffff;
  border: 2px solid #2563eb;
  border-radius: 50%;
  pointer-events: auto;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  transition: transform 0.1s ease, background 0.1s ease;
}

.handle-anchor:hover {
  transform: scale(1.35);
  background: #2563eb;
  border-color: #ffffff;
}

.handle-anchor.top-left {
  top: 0;
  left: 0;
  cursor: nwse-resize;
}
.handle-anchor.top-right {
  top: 0;
  right: 0;
  cursor: nesw-resize;
}
.handle-anchor.bottom-left {
  bottom: 0;
  left: 0;
  cursor: nesw-resize;
}
.handle-anchor.bottom-right {
  bottom: 0;
  right: 0;
  cursor: nwse-resize;
}

/* 飞书/Notion 风格快捷尺寸与对齐操作胶囊 */
.image-action-bubble {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  background: #0f172a;
  color: #ffffff;
  padding: 4px 8px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.15);
  z-index: 30;
  white-space: nowrap;
  line-height: normal;
}

.bubble-btn-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.bubble-pill-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.bubble-pill-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.bubble-pill-btn.active {
  background: #2563eb;
  color: #ffffff;
}

.bubble-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 11px;
  padding: 3px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.bubble-icon-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.bubble-icon-btn.active {
  background: #2563eb;
  color: #ffffff;
}

.bubble-icon-btn.preview-btn {
  color: #38bdf8;
}
.bubble-icon-btn.preview-btn:hover {
  background: rgba(56, 189, 248, 0.2);
  color: #ffffff;
}

.bubble-icon-btn.delete-btn {
  color: #f87171;
}
.bubble-icon-btn.delete-btn:hover {
  background: rgba(239, 68, 68, 0.25);
  color: #ffffff;
}

.align-icon {
  font-size: 12px;
  font-weight: bold;
}

.btn-text {
  font-size: 11px;
}

.bubble-sep {
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.18);
  margin: 0 4px;
}

.toolbar-fade-enter-active,
.toolbar-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.toolbar-fade-enter-from,
.toolbar-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 6px);
}
</style>
