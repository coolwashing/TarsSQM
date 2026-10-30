/**
 * WangEditor 5 富文本组件类型定义
 */

export interface EditorProps {
  /**
   * HTML 富文本内容 (支持 v-model)
   */
  modelValue?: string
  /**
   * 输入框占位提示文案
   */
  placeholder?: string
  /**
   * 是否只读/禁用
   */
  disabled?: boolean
  /**
   * 最小高度 (如 320 或 '320px')
   */
  minHeight?: number | string
  /**
   * 工具栏模式 ('default' 完整模式 | 'simple' 精简模式)
   */
  mode?: 'default' | 'simple'
}

export type EditorEmits = {
  (e: 'update:modelValue', html: string): void
  (e: 'change', editor: any): void
  (e: 'created', editor: any): void
  (e: 'blur', editor: any): void
  (e: 'focus', editor: any): void
}
