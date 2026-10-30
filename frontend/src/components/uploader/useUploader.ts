import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { AttachmentItem } from './types'

export function useUploader() {
  const fileList = ref<AttachmentItem[]>([])
  const isUploading = ref(false)

  /**
   * 格式化文件字节大小为可读字符串 (B / KB / MB)
   */
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * 单文件流式上传处理
   */
  const uploadSingleFile = async (
    rawFile: File,
    bizType: string = 'general',
    bizId?: number | null,
    maxSizeMB: number = 50
  ): Promise<AttachmentItem | null> => {
    // 文件大小校验
    const isExceedSize = rawFile.size / 1024 / 1024 > maxSizeMB
    if (isExceedSize) {
      ElMessage.error(`文件 "${rawFile.name}" 超过大小限制 (${maxSizeMB}MB)`)
      return null
    }

    // 创建本地临时项以展示上传中进度
    const tempId = -Date.now()
    const tempItem: AttachmentItem = {
      id: tempId,
      originalName: rawFile.name,
      fileSize: rawFile.size,
      filePath: '',
      mimeType: rawFile.type || 'application/octet-stream',
      bizType: bizType,
      bizId: bizId ?? null,
      url: '',
      status: 'uploading',
      progress: 0
    }

    fileList.value.push(tempItem)
    isUploading.value = true

    const formData = new FormData()
    formData.append('file', rawFile)
    formData.append('biz_type', bizType)
    if (bizId != null) {
      formData.append('biz_id', String(bizId))
    }

    try {
      const response = await axios.post('/api/storage/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            const target = fileList.value.find((f) => f.id === tempId)
            if (target) {
              target.progress = percentCompleted
            }
          }
        }
      })

      const data = response.data
      const targetIndex = fileList.value.findIndex((f) => f.id === tempId)

      const successItem: AttachmentItem = {
        id: data.id,
        originalName: data.original_name,
        fileSize: data.file_size,
        filePath: data.file_path,
        mimeType: data.mime_type,
        bizType: data.biz_type,
        bizId: data.biz_id,
        createdAt: data.created_at,
        url: data.url || `/api/storage/file/${data.id}`,
        status: 'success',
        progress: 100
      }

      if (targetIndex !== -1) {
        fileList.value[targetIndex] = successItem
      }

      ElMessage.success(`文件 "${data.original_name}" 上传成功`)
      return successItem
    } catch (err: any) {
      const target = fileList.value.find((f) => f.id === tempId)
      if (target) {
        target.status = 'error'
        target.errorMessage = err.response?.data?.detail || err.message || '上传异常'
      }
      ElMessage.error(`文件 "${rawFile.name}" 上传失败: ${err.response?.data?.detail || err.message}`)
      return null
    } finally {
      isUploading.value = fileList.value.some((f) => f.status === 'uploading')
    }
  }

  /**
   * 按照业务域与外键查询已存附件
   */
  const fetchAttachments = async (bizType: string, bizId: number): Promise<AttachmentItem[]> => {
    try {
      const res = await axios.get(`/api/storage/attachments/${bizType}/${bizId}`)
      const remoteItems: AttachmentItem[] = (res.data || []).map((d: any) => ({
        id: d.id,
        originalName: d.original_name,
        fileSize: d.file_size,
        filePath: d.file_path,
        mimeType: d.mime_type,
        bizType: d.biz_type,
        bizId: d.biz_id,
        createdAt: d.created_at,
        url: d.url || `/api/storage/file/${d.id}`,
        status: 'success',
        progress: 100
      }))
      fileList.value = remoteItems
      return remoteItems
    } catch (err: any) {
      ElMessage.error(`拉取附件失败: ${err.message}`)
      return []
    }
  }

  /**
   * 删除指定附件
   */
  const removeAttachment = async (item: AttachmentItem): Promise<boolean> => {
    if (item.id < 0) {
      // 临时未上传成功的直接本地移除
      fileList.value = fileList.value.filter((f) => f.id !== item.id)
      return true
    }

    try {
      await axios.delete(`/api/storage/file/${item.id}`)
      fileList.value = fileList.value.filter((f) => f.id !== item.id)
      ElMessage.success(`附件 "${item.originalName}" 已删除`)
      return true
    } catch (err: any) {
      ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
      return false
    }
  }

  /**
   * 批量将已有附件绑定到新生成的业务外键
   */
  const bindAttachmentsToBiz = async (attachmentIds: number[], bizId: number): Promise<boolean> => {
    if (!attachmentIds.length) return true
    try {
      await axios.post('/api/storage/bind', {
        attachment_ids: attachmentIds,
        biz_id: bizId
      })
      return true
    } catch (err: any) {
      ElMessage.error(`绑定附件失败: ${err.message}`)
      return false
    }
  }

  return {
    fileList,
    isUploading,
    formatFileSize,
    uploadSingleFile,
    fetchAttachments,
    removeAttachment,
    bindAttachmentsToBiz
  }
}
