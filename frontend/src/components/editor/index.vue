<template>
  <div class="editor-wrapper" :class="{ 'is-disabled': disabled }">
    <!-- 富文本工具栏 -->
    <Toolbar
      class="editor-toolbar"
      :editor="editorRef"
      :default-config="toolbarConfig"
      :mode="mode"
    />
    <!-- 富文本编辑区 -->
    <Editor
      v-model="valueHtml"
      class="editor-content"
      :style="{ minHeight: computedMinHeight }"
      :default-config="editorConfig"
      :mode="mode"
      @on-created="handleCreated"
      @on-change="handleChange"
      @on-blur="emit('blur', editorRef)"
      @on-focus="emit('focus', editorRef)"
    />
  </div>
</template>

<script setup lang="ts">
import '@wangeditor/editor/dist/css/style.css'
import { ref, shallowRef, computed, watch, onBeforeUnmount } from 'vue'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor } from '@wangeditor/editor'
import type { EditorProps, EditorEmits } from './types'
import { buildEditorConfig, buildToolbarConfig } from './config'

const props = withDefaults(defineProps<EditorProps>(), {
  modelValue: '',
  placeholder: '请输入质量分析与整改内容...',
  disabled: false,
  minHeight: 280,
  mode: 'default'
})

const emit = defineEmits<EditorEmits>()

// 必须使用 shallowRef，避免 Vue 深度响应式破坏编辑器内部状态
const editorRef = shallowRef<IDomEditor>()

// 双向绑定的 HTML 文本
const valueHtml = ref(props.modelValue)

// 构建工具栏与编辑器配置
const toolbarConfig = buildToolbarConfig()
const editorConfig = buildEditorConfig(props.placeholder)

const computedMinHeight = computed(() => {
  return typeof props.minHeight === 'number' ? `${props.minHeight}px` : props.minHeight
})

// 监听外部 modelValue 同步
watch(
  () => props.modelValue,
  (val) => {
    if (val !== valueHtml.value) {
      valueHtml.value = val || ''
    }
  }
)

// 监听禁用状态
watch(
  () => props.disabled,
  (val) => {
    const editor = editorRef.value
    if (!editor) return
    if (val) {
      editor.disable()
    } else {
      editor.enable()
    }
  }
)

const handleCreated = (editor: IDomEditor) => {
  editorRef.value = editor
  if (props.disabled) {
    editor.disable()
  }
  emit('created', editor)
}

const handleChange = (editor: IDomEditor) => {
  const html = editor.getHtml()
  emit('update:modelValue', html)
  emit('change', editor)
}

onBeforeUnmount(() => {
  const editor = editorRef.value
  if (editor) {
    editor.destroy()
  }
})

// 对外暴露获取纯文本与重置方法
defineExpose({
  getEditor: () => editorRef.value,
  getText: () => editorRef.value?.getText() || '',
  clear: () => editorRef.value?.clear()
})
</script>

<style scoped>
.editor-wrapper {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.editor-wrapper:hover {
  border-color: #9ca3af;
}

.editor-wrapper:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.editor-toolbar {
  border-bottom: 1px solid #e5e7eb;
  background-color: #fafbfc;
}

.editor-content {
  overflow-y: hidden;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
  padding: 4px 8px;
}

:deep(.w-e-text-container) {
  background-color: transparent;
}

:deep(.w-e-text-placeholder) {
  top: 12px;
  font-size: 13px;
  color: #9ca3af;
  font-style: normal;
}

.is-disabled {
  background-color: #f9fafb;
  opacity: 0.8;
  pointer-events: none;
}
</style>
