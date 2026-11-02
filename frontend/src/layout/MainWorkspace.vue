<template>
  <div class="workspace-wrapper">
    <!-- Top Workspace Header (在全屏沉浸式页面如知识库下自动隐藏，消除双层顶栏) -->
    <header class="workspace-header" v-if="!isFullBleedRoute">
      <div class="header-left">
        <span class="current-title">{{ currentTitle }}</span>
        <!-- 业务页面专属操作区插槽 (如 TaskCenter 视图切换与详细立项 Teleport 目标) -->
        <div id="workspace-header-actions" class="workspace-header-actions"></div>
      </div>

      <div class="header-right">
        <el-tag
          type="info"
          effect="light"
          class="teleprompter-badge clickable-badge"
          @click="openTeleprompter"
          title="点击或按 Alt+X 唤出 AI 提词器与 DOM 拾取器"
        >
          开发套件：<kbd>Alt</kbd> + <kbd>X</kbd> 提词器
        </el-tag>

        <el-tag
          type="primary"
          effect="light"
          class="teleprompter-badge clickable-badge schema-badge"
          @click="openSchemaScaffolder"
          title="点击或按 Alt+S 唤出数据字典与 UI 页面脚手架"
        >
          🛠️ 字段脚手架：<kbd>Alt</kbd> + <kbd>S</kbd>
        </el-tag>

        <div class="backend-status">
          <span class="status-indicator" :class="{ online: isBackendOnline }"></span>
          <span class="status-text">{{ isBackendOnline ? '后端服务正常' : '后端检测中' }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="workspace-main" :class="{ 'is-full-bleed': isFullBleedRoute }">
      <router-view v-slot="{ Component, route: currentRoute }">
        <transition name="fade" mode="out-in">
          <keep-alive>
            <component :is="Component" :key="currentRoute.path" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const isBackendOnline = ref(false)

const openTeleprompter = () => {
  window.dispatchEvent(new CustomEvent('sqm:toggle-teleprompter'))
}

const openSchemaScaffolder = () => {
  window.dispatchEvent(new CustomEvent('sqm:toggle-schema-scaffolder'))
}

const isFullBleedRoute = computed(() => route.path.startsWith('/kb'))

const currentTitle = computed(() => {
  const raw = (route.meta?.title as string) || '工作台'
  return raw.replace(/^\d+(\.\d+)?\s*/, '')
})

const checkHealth = async () => {
  try {
    const res = await axios.get('/api/health')
    if (res.data?.status === 'healthy') {
      isBackendOnline.value = true
    }
  } catch (_e) {
    isBackendOnline.value = false
  }
}

onMounted(() => {
  checkHealth()
  // 30秒定时体检
  setInterval(checkHealth, 30000)
})
</script>

<style scoped>
.workspace-wrapper {
  flex: 1;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
  overflow: hidden;
}

.workspace-header {
  height: 48px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.workspace-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.module-tag {
  font-weight: 700;
  font-family: monospace;
}

.current-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.teleprompter-badge {
  font-size: 12px;
}

.clickable-badge {
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
}

.clickable-badge:hover {
  background-color: #e0e7ff !important;
  color: #4338ca !important;
  border-color: #c7d2fe !important;
}

.teleprompter-badge kbd {
  background: #e5e7eb;
  color: #374151;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 11px;
}

.backend-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4b5563;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 6px #ef4444;
}

.status-indicator.online {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.workspace-main {
  flex: 1;
  padding: 10px 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.workspace-main.is-full-bleed {
  padding: 0;
}

.workspace-main > * {
  height: 100%;
  width: 100%;
  min-height: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
