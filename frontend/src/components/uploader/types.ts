/**
 * 附件独立组件 TypeScript 契约定义
 */

export interface AttachmentItem {
  id: number
  originalName: string
  fileSize: number
  filePath: string
  mimeType: string
  bizType: string
  bizId?: number | null
  createdAt?: string
  url: string
  status?: 'uploading' | 'success' | 'error'
  progress?: number
  errorMessage?: string
}

export interface UploaderProps {
  /**
   * 业务域标识 (如 supplier, part, quality_issue, ctq 等)
   */
  bizType?: string
  /**
   * 业务实体主键外键 ID (可选，未指定时可在父表单提交后统一批量绑定)
   */
  bizId?: number | null
  /**
   * 允许上传的文件格式 (如 .pdf,.doc,.docx,.png,.jpg,.xlsx)
   */
  accept?: string
  /**
   * 单文件大小限制 (单位: MB，默认 50MB)
   */
  maxSizeMB?: number
  /**
   * 最大允许上传文件数量 (默认 10)
   */
  limit?: number
  /**
   * 是否禁用
   */
  disabled?: boolean
  /**
   * 是否支持多选上传
   */
  multiple?: boolean
  /**
   * 外部受控或初始回显的附件列表
   */
  modelValue?: AttachmentItem[]
}

export type UploaderEmits = {
  (e: 'update:modelValue', value: AttachmentItem[]): void
  (e: 'success', item: AttachmentItem): void
  (e: 'remove', item: AttachmentItem): void
  (e: 'error', error: Error): void
  (e: 'change', list: AttachmentItem[]): void
}
