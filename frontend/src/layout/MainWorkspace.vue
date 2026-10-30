<template>
  <div class="workspace-wrapper">
    <!-- Top Workspace Header -->
    <header class="workspace-header">
      <div class="header-left">
        <span class="current-title">{{ currentTitle }}</span>
      </div>

      <div class="header-right">
        <el-tag
          type="info"
          effect="light"
          class="teleprompter-badge clickable-badge"
          @click="openTeleprompter"
          title="点击或按 Alt+X 唤出 AI 提词器与 DOM 拾取器"
        >
          开发套件：按 <kbd>Alt</kbd> + <kbd>X</kbd> 唤出 AI 提词器
        </el-tag>

        <div class="backend-status">
          <span class="status-indicator" :class="{ online: isBackendOnline }"></span>
          <span class="status-text">{{ isBackendOnline ? '后端服务正常' : '后端检测中' }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="workspace-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
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
  height: 64px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.module-tag {
  font-weight: 700;
  font-family: monospace;
}

.current-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
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
  padding: 16px 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.workspace-main > * {
  height: 100%;
  display: flex;
  flex-direction: column;
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
