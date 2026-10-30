import { ref } from 'vue'

export interface BeaconItem {
  id: number
  tag: string // e.g. "【信标 1】"
  compName: string
  filePath: string
  line: string
  viewport: string
  domPath: string
  className: string
  innerText: string
}

export function usePicker(onPickCallback?: (beacon: BeaconItem) => void) {
  const isPicking = ref(false)
  const beacons = ref<BeaconItem[]>([])
  let beaconCounter = 0

  let highlightBox: HTMLDivElement | null = null
  let highlightTag: HTMLDivElement | null = null

  const getOrCreateHighlightBox = () => {
    if (highlightBox && document.body.contains(highlightBox)) return highlightBox
    const div = document.createElement('div')
    div.id = '__sqm_picker_highlight__'
    div.style.position = 'fixed'
    div.style.pointerEvents = 'none'
    div.style.zIndex = '999998'
    div.style.border = '2px solid #6366f1'
    div.style.backgroundColor = 'rgba(99, 102, 241, 0.14)'
    div.style.boxShadow = '0 0 12px rgba(99, 102, 241, 0.45)'
    div.style.borderRadius = '4px'
    div.style.transition = 'all 0.05s ease'
    div.style.display = 'none'
    document.body.appendChild(div)
    highlightBox = div
    return div
  }

  const getOrCreateHighlightTag = () => {
    if (highlightTag && document.body.contains(highlightTag)) return highlightTag
    const tag = document.createElement('div')
    tag.id = '__sqm_picker_tag__'
    tag.style.position = 'fixed'
    tag.style.pointerEvents = 'none'
    tag.style.zIndex = '999999'
    tag.style.background = '#4f46e5'
    tag.style.color = '#ffffff'
    tag.style.padding = '3px 8px'
    tag.style.borderRadius = '4px'
    tag.style.fontSize = '11px'
    tag.style.fontFamily = 'monospace'
    tag.style.fontWeight = '600'
    tag.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.25)'
    tag.style.display = 'none'
    tag.style.whiteSpace = 'nowrap'
    document.body.appendChild(tag)
    highlightTag = tag
    return tag
  }

  const removeHighlightElements = () => {
    if (highlightBox && highlightBox.parentNode) {
      highlightBox.parentNode.removeChild(highlightBox)
      highlightBox = null
    }
    if (highlightTag && highlightTag.parentNode) {
      highlightTag.parentNode.removeChild(highlightTag)
      highlightTag = null
    }
  }

  const getVueInstance = (el: HTMLElement): any => {
    let curr: any = el
    while (curr) {
      if (curr.__vueParentComponent) return curr.__vueParentComponent
      if (curr.__vnode?.component) return curr.__vnode.component
      curr = curr.parentElement
    }
    return null
  }

  const extractComponentInfo = (el: HTMLElement) => {
    let inst = getVueInstance(el)
    let filePath = ''
    let compName = ''
    let line = ''

    // 1. 尝试从 Vite vue-inspector 的 data-v-inspector 属性提取精确路径与行号
    const inspectorNode = el.closest('[data-v-inspector]') as HTMLElement
    if (inspectorNode) {
      const raw = inspectorNode.getAttribute('data-v-inspector') || ''
      const parts = raw.split(':')
      if (parts.length >= 2) {
        filePath = parts[0].replace(/\\/g, '/')
        line = parts[1]
        compName = filePath.split('/').pop()?.replace(/\.vue$/, '') || ''
      }
    }

    // 2. 向上递归 Vue 组件实例树反射真实组件文件名
    while (inst) {
      const compType = inst.type || {}
      const file = compType.__file || ''
      const name = compType.name || compType.__name || ''

      // 过滤第三方库（如 Element Plus 内置组件），定位开发者业务组件
      if (file && !file.includes('node_modules')) {
        const normalized = file.replace(/\\/g, '/')
        const srcIndex = normalized.indexOf('src/')
        filePath = srcIndex !== -1 ? normalized.substring(srcIndex) : normalized
        compName = name || filePath.split('/').pop()?.replace(/\.vue$/, '') || 'Component'
        break
      }
      inst = inst.parent
    }

    // 3. 上下文与路由智能推断兜底
    if (!compName || compName === 'Component') {
      const route = window.location.pathname
      if (route.includes('supplier')) compName = 'SupplierList.vue'
      else if (route.includes('part-dev')) compName = 'PartDevList.vue'
      else if (route.includes('quality-issue')) compName = 'QualityIssueList.vue'
      else if (route.includes('part')) compName = 'PartList.vue'
      else if (route.includes('project')) compName = 'ProjectList.vue'
      else if (route.includes('ctq')) compName = 'CTQList.vue'
      else compName = 'MainWorkspace.vue'
    }

    if (!filePath) {
      if (compName.includes('Supplier')) filePath = `src/views/1_maindata/1.1_supplier/${compName}`
      else if (compName.includes('PartDev')) filePath = `src/views/2_sqm/2.1_part_dev/${compName}`
      else if (compName.includes('QualityIssue')) filePath = `src/views/2_sqm/2.2_quality_issue/${compName}`
      else if (compName.includes('Part')) filePath = `src/views/1_maindata/1.2_part/${compName}`
      else if (compName.includes('Project')) filePath = `src/views/1_maindata/1.3_project/${compName}`
      else if (compName.includes('CTQ')) filePath = `src/views/3_ctq/3.1_ctq/${compName}`
      else if (compName.includes('LeftSidebar')) filePath = 'src/layout/LeftSidebar.vue'
      else filePath = 'src/layout/MainWorkspace.vue'
    }

    // 若元素位于抽屉内，修正指向对应的表单组件
    if (el.closest('.el-drawer') || el.closest('.drawer-container')) {
      if (compName.endsWith('List.vue') || compName.endsWith('List')) {
        const base = compName.replace(/List(\.vue)?$/, '')
        compName = `${base}Form.vue`
        filePath = filePath.replace(/List(\.vue)?$/, 'Form.vue')
      }
    }

    return { compName, filePath, line }
  }

  const getViewport = (el: HTMLElement): string => {
    if (el.closest('.el-drawer') || el.closest('.drawer-container')) {
      return 'DrawerContainer (70% 宽幅抽屉)'
    }
    if (el.closest('.el-dialog')) {
      return 'Dialog (弹窗视口)'
    }
    if (el.closest('.left-sidebar')) {
      return 'LeftSidebar (左侧导航栏)'
    }
    if (el.closest('.workspace-header')) {
      return 'WorkspaceHeader (顶部状态栏)'
    }
    return 'MainWorkspace (主数据展示区)'
  }

  const getDOMPath = (el: HTMLElement): string => {
    const stack: string[] = []
    let curr: HTMLElement | null = el
    while (curr && curr.tagName !== 'BODY' && stack.length < 5) {
      let desc = curr.tagName.toLowerCase()
      if (curr.id) {
        desc += `#${curr.id}`
      } else if (curr.classList && curr.classList.length > 0) {
        const validClasses = Array.from(curr.classList).filter(
          c => !c.startsWith('__sqm_') && !c.includes('teleprompter') && !c.startsWith('is-')
        )
        if (validClasses.length > 0) {
          desc += `.${validClasses.slice(0, 2).join('.')}`
        }
      }
      stack.unshift(desc)
      curr = curr.parentElement
    }
    return stack.join(' > ')
  }

  const isIgnoredElement = (target: HTMLElement | null): boolean => {
    if (!target) return true

    // 提词器浮窗与高亮标记自身必须忽略
    if (
      target.closest('.teleprompter-floating-panel') ||
      target.closest('.beacon-popover') ||
      target.id === '__sqm_picker_highlight__' ||
      target.id === '__sqm_picker_tag__'
    ) {
      return true
    }

    // 全局消息浮层忽略
    if (
      target.closest('.el-message') ||
      target.closest('.el-message-box') ||
      target.closest('.el-notification')
    ) {
      return true
    }

    // 遮罩层处理：忽略点击抽屉/弹窗外的纯灰色背景遮罩，但抽屉与弹窗内的表单元素绝不忽略
    const overlay = target.closest('.el-overlay')
    if (overlay) {
      const isInDrawerOrDialog = target.closest('.el-drawer') || target.closest('.drawer-container') || target.closest('.el-dialog')
      if (!isInDrawerOrDialog) {
        return true
      }
    }

    return false
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (!isPicking.value) return
    const target = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null
    if (!target || isIgnoredElement(target)) {
      if (highlightBox) highlightBox.style.display = 'none'
      if (highlightTag) highlightTag.style.display = 'none'
      return
    }

    const rect = target.getBoundingClientRect()
    const box = getOrCreateHighlightBox()
    const tag = getOrCreateHighlightTag()

    box.style.display = 'block'
    box.style.top = `${rect.top}px`
    box.style.left = `${rect.left}px`
    box.style.width = `${rect.width}px`
    box.style.height = `${rect.height}px`

    const { compName } = extractComponentInfo(target)
    const tagDesc = target.tagName.toLowerCase()
    tag.innerText = `🎯 ${compName} <${tagDesc}>`
    tag.style.display = 'block'

    let tagTop = rect.top - 26
    if (tagTop < 6) tagTop = rect.bottom + 6
    tag.style.top = `${tagTop}px`
    tag.style.left = `${Math.max(rect.left, 6)}px`
  }

  const handleClickCapture = (e: MouseEvent) => {
    if (!isPicking.value) return
    const target = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null
    if (!target || isIgnoredElement(target)) {
      return
    }

    e.preventDefault()
    e.stopPropagation()

    beaconCounter++
    const beaconTag = `【信标 ${beaconCounter}】`
    const { compName, filePath, line } = extractComponentInfo(target)
    const viewport = getViewport(target)
    const domPath = getDOMPath(target)
    const className = typeof target.className === 'string' ? target.className.trim() : ''
    const innerText = target.innerText ? target.innerText.slice(0, 80).replace(/\s+/g, ' ').trim() : ''

    const beaconItem: BeaconItem = {
      id: beaconCounter,
      tag: beaconTag,
      compName,
      filePath,
      line,
      viewport,
      domPath,
      className,
      innerText
    }

    beacons.value.push(beaconItem)

    if (onPickCallback) {
      onPickCallback(beaconItem)
    }
  }

  const startPicking = () => {
    isPicking.value = true
    getOrCreateHighlightBox()
    getOrCreateHighlightTag()
    document.addEventListener('mousemove', handleMouseMove, { passive: true })
    document.addEventListener('click', handleClickCapture, { capture: true })
  }

  const stopPicking = () => {
    isPicking.value = false
    if (highlightBox) highlightBox.style.display = 'none'
    if (highlightTag) highlightTag.style.display = 'none'
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('click', handleClickCapture, { capture: true })
  }

  const removeBeacon = (id: number) => {
    const idx = beacons.value.findIndex(b => b.id === id)
    if (idx !== -1) {
      beacons.value.splice(idx, 1)
    }
  }

  const clearBeacons = () => {
    beacons.value = []
    beaconCounter = 0
  }

  return {
    isPicking,
    beacons,
    startPicking,
    stopPicking,
    removeHighlightElements,
    removeBeacon,
    clearBeacons,
    extractComponentInfo,
    getViewport,
    getDOMPath
  }
}
