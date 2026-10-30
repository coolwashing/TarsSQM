import { ElMessage } from 'element-plus'
import type { IEditorConfig, IToolbarConfig } from '@wangeditor/editor'

/**
 * 获取富文本核心编辑器配置
 */
export function buildEditorConfig(placeholder: string = '请输入质量分析与整改内容...'): Partial<IEditorConfig> {
  return {
    placeholder,
    autoFocus: false,
    MENU_CONF: {
      // 图片流式上传配置：直接对接后端 r_storage.py 动态附件接口
      uploadImage: {
        server: '/api/storage/editor-upload',
        fieldName: 'file',
        maxFileSize: 10 * 1024 * 1024, // 10MB
        maxNumberOfFiles: 5,
        allowedFileTypes: ['image/*'],
        timeout: 20 * 1000,
        // 自定义插入图片到富文本光标处
        customInsert(res: any, insertFn: (url: string, alt: string, href: string) => void) {
          if (res.errno === 0 && res.data && res.data.url) {
            insertFn(res.data.url, res.data.alt || '质量配图', res.data.href || res.data.url)
            ElMessage.success('配图已上传并插入')
          } else {
            ElMessage.error(res.message || '图片上传失败')
          }
        },
        onError(file: File, err: any, res: any) {
          ElMessage.error(`图片 ${file.name} 上传异常: ${err.message || res?.message || '网络错误'}`)
        }
      }
    }
  }
}

/**
 * 获取工具栏配置
 */
export function buildToolbarConfig(): Partial<IToolbarConfig> {
  return {
    // 剔除视频上传等复杂非质量管理必需菜单，保留文本、表格、图片、列表等工业排版必需项
    excludeKeys: ['group-video', 'insertVideo', 'uploadVideo']
  }
}
