<template>
  <el-config-provider :locale="zhCn">
    <div class="app-layout">
      <LeftSidebar />
      <MainWorkspace />
      <!-- 全局挂载 AI 开发态提词器 (Alt+X 唤出，开发环境启用) -->
      <Teleprompter v-if="isDev" />
      <!-- 全局挂载 数据字典与 UI 页面脚手架 (Alt+S 唤出，开发环境启用) -->
      <SchemaScaffolderDialog v-if="isDev" />
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import LeftSidebar from '@/layout/LeftSidebar.vue'
import MainWorkspace from '@/layout/MainWorkspace.vue'
import Teleprompter from '@/components/dev/teleprompter/index.vue'
import SchemaScaffolderDialog from '@/components/dev/schema/SchemaScaffolderDialog.vue'

const isDev = import.meta.env.DEV
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #app {
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
</style>
