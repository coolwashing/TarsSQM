<template>
  <node-view-wrapper class="code-block-wrapper" :class="{ 'is-mermaid-diagram': isMermaid }">
    <!-- 1. Mermaid 矢量图表展示卡片 -->
    <div v-if="isMermaid" class="mermaid-diagram-card">
      <div class="diagram-toolbar">
        <div class="toolbar-left">
          <span class="mac-dot red"></span>
          <span class="mac-dot yellow"></span>
          <span class="mac-dot green"></span>
          <span class="diagram-badge">
            <span class="badge-icon">📊</span>
            <span>Mermaid 架构流程图</span>
          </span>
        </div>
        <div class="toolbar-right">
          <button
            type="button"
            class="mini-action-btn"
            :class="{ active: showMermaidSource }"
            @click="toggleMermaidSource"
            title="查看/编辑图表源码"
          >
            {{ showMermaidSource ? '收起源码' : '编辑源码' }}
          </button>
          <button
            type="button"
            class="mini-action-btn"
            @click="copyCode"
            title="复制图表源码"
          >
            {{ copied ? '已复制 ✓' : '复制代码' }}
          </button>
        </div>
      </div>

      <!-- 动态渲染出的 SVG 矢量图舞台 -->
      <div
        class="diagram-svg-container"
        v-show="!mermaidError && svgContent"
        v-html="svgContent"
      ></div>

      <!-- 语法错误提示条 -->
      <div v-if="mermaidError" class="diagram-error-hint">
        <span class="error-icon">⚠️</span>
        <span class="error-msg">Mermaid 语法解析提示：{{ mermaidError }}</span>
      </div>

      <!-- Mermaid 源码可折叠编辑区 (在需要修改或语法错误时展开) -->
      <div v-show="showMermaidSource || mermaidError || !svgContent" class="mermaid-source-box">
        <pre class="hljs-pre"><code class="hljs-code"><node-view-content /></code></pre>
      </div>
    </div>

    <!-- 2. 常规深色终端代码块卡片 (SQL, TypeScript, Python, JSON...) -->
    <div v-else class="dark-terminal-card">
      <div class="terminal-header">
        <div class="header-left">
          <span class="mac-dot red"></span>
          <span class="mac-dot yellow"></span>
          <span class="mac-dot green"></span>
          <span class="lang-tag">{{ displayLanguage }}</span>
        </div>
        <div class="header-right">
          <button
            type="button"
            class="copy-btn"
            @click="copyCode"
            title="复制代码到剪贴板"
          >
            <span class="copy-icon">{{ copied ? '✓' : '📋' }}</span>
            <span>{{ copied ? '已复制' : '复制代码' }}</span>
          </button>
        </div>
      </div>

      <!-- 代码内容区 (由 Lowlight 执行关键字着色) -->
      <pre class="terminal-body"><code class="terminal-code"><node-view-content /></code></pre>
    </div>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { NodeViewWrapper, NodeViewContent, nodeViewProps } from '@tiptap/vue-3'
import mermaid from 'mermaid'

const props = defineProps(nodeViewProps)

const copied = ref(false)
const showMermaidSource = ref(false)
const svgContent = ref('')
const mermaidError = ref('')

const isMermaid = computed(() => {
  const lang = (props.node.attrs.language || '').toLowerCase().trim()
  return lang === 'mermaid'
})

const displayLanguage = computed(() => {
  const lang = (props.node.attrs.language || '').trim()
  if (!lang) return 'CODE'
  return lang.toUpperCase()
})

// 初始化 Mermaid 配置 (仅需配置一次)
let mermaidInitialized = false
const initMermaid = () => {
  if (mermaidInitialized) return
  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'neutral',
      securityLevel: 'loose',
      fontFamily: 'inherit',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    })
    mermaidInitialized = true
  } catch (e) {
    console.warn('Mermaid initialize warning:', e)
  }
}

// 动态渲染 Mermaid SVG
let renderSeq = 0
const renderMermaidDiagram = async () => {
  if (!isMermaid.value) return
  const rawCode = props.node.textContent?.trim()
  if (!rawCode) {
    svgContent.value = ''
    mermaidError.value = ''
    return
  }

  initMermaid()
  const currentSeq = ++renderSeq
  const elementId = `sqm-mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`

  try {
    const { svg } = await mermaid.render(elementId, rawCode)
    if (currentSeq === renderSeq) {
      svgContent.value = svg
      mermaidError.value = ''
    }
  } catch (err: any) {
    if (currentSeq === renderSeq) {
      mermaidError.value = err?.message || '图表语法格式有误，请核对'
      console.warn('Mermaid render error:', err)
    }
  }
}

// 切换 Mermaid 源码展示
const toggleMermaidSource = () => {
  showMermaidSource.value = !showMermaidSource.value
}

// 一键复制代码
const copyCode = async () => {
  const text = props.node.textContent || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

// 监听内容变化实时渲染
watch(
  () => [props.node.textContent, props.node.attrs.language],
  () => {
    if (isMermaid.value) {
      nextTick(() => {
        renderMermaidDiagram()
      })
    }
  },
  { deep: true }
)

onMounted(() => {
  if (isMermaid.value) {
    nextTick(() => {
      renderMermaidDiagram()
    })
  }
})
</script>

<style scoped>
.code-block-wrapper {
  margin: 16px 0;
  user-select: text;
}

/* Mac 风格三色圆点 */
.mac-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.mac-dot.red { background-color: #ef4444; }
.mac-dot.yellow { background-color: #f59e0b; }
.mac-dot.green { background-color: #10b981; }

/* 1. 常规深色终端卡片样式 */
.dark-terminal-card {
  background: #0f172a;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.25);
  overflow: hidden;
  transition: all 0.2s ease;
}

.terminal-header {
  height: 36px;
  background: #1e293b;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 7px;
}

.lang-tag {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.5px;
  margin-left: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.copy-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 11.5px;
  padding: 3px 9px;
  border-radius: 5px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.copy-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.terminal-body {
  margin: 0;
  padding: 16px 18px;
  overflow-x: auto;
  color: #f8fafc;
  background: transparent;
  font-size: 13px;
  line-height: 1.6;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.terminal-code {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
}

/* 2. Mermaid 图表卡片样式 */
.mermaid-diagram-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 18px -4px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  transition: all 0.2s ease;
}

.diagram-toolbar {
  height: 38px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
}

.diagram-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  margin-left: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-action-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 11.5px;
  padding: 3px 9px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.mini-action-btn:hover {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}

.mini-action-btn.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}

.diagram-svg-container {
  padding: 24px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow-x: auto;
  background: radial-gradient(#e2e8f0 1px, transparent 1px);
  background-size: 16px 16px;
  background-color: #fafbfd;
  min-height: 120px;
}

.diagram-svg-container :deep(svg) {
  max-width: 100% !important;
  height: auto !important;
  display: block;
  margin: 0 auto;
}

.diagram-error-hint {
  padding: 10px 16px;
  background: #fef2f2;
  border-bottom: 1px solid #fee2e2;
  color: #dc2626;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mermaid-source-box {
  background: #0f172a;
  border-top: 1px solid #1e293b;
  padding: 12px 16px;
  max-height: 280px;
  overflow-y: auto;
}

.hljs-pre {
  margin: 0;
  padding: 0;
  background: transparent;
  color: #f8fafc;
  font-size: 12.5px;
  line-height: 1.5;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.hljs-code {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
}
</style>
