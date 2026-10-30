import { ref, computed } from 'vue'
import { ElMessageBox } from 'element-plus'

/**
 * 深度比对两个对象是否内容一致 (忽略属性键顺序)
 */
export function deepEqual(a: any, b: any): boolean {
  if (a === b) return true
  if (a == null || b == null) return a === b
  if (typeof a !== 'object' || typeof b !== 'object') return a === b

  if (Array.isArray(a) !== Array.isArray(b)) return false

  if (Array.isArray(a)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false
    }
    return true
  }

  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  if (keysA.length !== keysB.length) return false

  for (const key of keysA) {
    if (!Object.prototype.hasOwnProperty.call(b, key)) return false
    if (!deepEqual(a[key], b[key])) return false
  }
  return true
}

/**
 * 表单退出防呆脏检查钩子
 * @param getFormData 获取当前表单数据的 Getter
 * @param options 可选提示配置
 */
export function useDirtyCheck<T extends Record<string, any>>(
  getFormData: () => T,
  options?: {
    confirmTitle?: string
    confirmMessage?: string
  }
) {
  // 记录表单初始快照状态
  const initialSnapshot = ref<string>('')

  /**
   * 记录当前数据为初始基线快照 (通常在打开抽屉加载完详情后调用)
   */
  const captureInitialState = (data?: T) => {
    const target = data !== undefined ? data : getFormData()
    try {
      initialSnapshot.value = JSON.stringify(target)
    } catch {
      initialSnapshot.value = ''
    }
  }

  /**
   * 计算当前是否被篡改或存在未保存修改
   */
  const isDirty = computed(() => {
    if (!initialSnapshot.value) return false
    try {
      const currentStr = JSON.stringify(getFormData())
      return currentStr !== initialSnapshot.value
    } catch {
      return false
    }
  })

  /**
   * 重置快照 (通常在保存成功后调用)
   */
  const markClean = () => {
    captureInitialState()
  }

  /**
   * 关闭拦截防呆逻辑
   */
  const confirmBeforeClose = async (done: (cancel?: boolean) => void) => {
    if (!isDirty.value) {
      done()
      return
    }

    try {
      await ElMessageBox.confirm(
        options?.confirmMessage || '当前表单已有修改尚未保存，确认退出将丢失所有未保存数据？',
        options?.confirmTitle || '表单未保存防呆提示',
        {
          confirmButtonText: '放弃修改并退出',
          cancelButtonText: '留在本页继续编辑',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
          distinguishCancelAndClose: true
        }
      )
      // 用户确认退出
      done()
    } catch {
      // 用户取消退出，保持留在抽屉中
      done(true)
    }
  }

  return {
    initialSnapshot,
    isDirty,
    captureInitialState,
    markClean,
    confirmBeforeClose
  }
}
