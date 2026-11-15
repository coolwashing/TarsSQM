import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fmeaApi } from '@/api/fmea'

export function useFmeaUpload() {
  const uploading = ref(false)

  async function uploadImageFile(
    file: File,
    bizType: 'fmea_blueprint' | 'fmea_photo' = 'fmea_photo',
    bizId?: number | null
  ): Promise<{ attachment_id: number; url: string; name: string } | null> {
    if (!file.type.startsWith('image/')) {
      ElMessage.warning('请上传 PNG / JPG / WEBP / SVG 格式的图片文件')
      return null
    }
    uploading.value = true
    try {
      const normalizedFile = file.name
        ? file
        : new File([file], `paste_${Date.now()}.png`, { type: file.type || 'image/png' })
      const res = await fmeaApi.uploadFile(normalizedFile, bizType, bizId)
      return {
        attachment_id: res.id,
        url: res.url,
        name: res.original_name.replace(/\.[^.]+$/, '')
      }
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.detail || '图片流式上传失败')
      return null
    } finally {
      uploading.value = false
    }
  }

  function extractImagesFromClipboard(e: ClipboardEvent): File[] {
    const items = e.clipboardData?.items
    if (!items) return []
    const files: File[] = []
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.kind === 'file' && item.type.startsWith('image/')) {
        const f = item.getAsFile()
        if (f) {
          const ext = item.type.split('/')[1] || 'png'
          files.push(new File([f], `clipboard_${Date.now()}_${i}.${ext}`, { type: item.type }))
        }
      }
    }
    return files
  }

  function extractImagesFromDrop(e: DragEvent): File[] {
    const dtFiles = e.dataTransfer?.files
    if (!dtFiles) return []
    return Array.from(dtFiles).filter((f) => f.type.startsWith('image/'))
  }

  return {
    uploading,
    uploadImageFile,
    extractImagesFromClipboard,
    extractImagesFromDrop
  }
}

