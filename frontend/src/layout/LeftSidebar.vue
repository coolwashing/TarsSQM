<template>
  <div class="sidebar-wrapper" :class="{ collapsed: isCollapsed }">
    <div class="brand-header">
      <div class="logo-box">
        <el-icon :size="20" color="#ffffff"><DataAnalysis /></el-icon>
      </div>
      <div class="brand-text" v-if="!isCollapsed">
        <h1 class="brand-title">SQM 质量系统</h1>
      </div>
    </div>

    <el-scrollbar class="menu-scrollbar">
      <el-menu
        :default-active="activeRoute"
        :collapse="isCollapsed"
        router
        class="custom-menu"
        :collapse-transition="false"
      >
        <!-- MainData 主数据 -->
        <el-sub-menu index="1">
          <template #title>
            <el-icon><Folder /></el-icon>
            <span class="menu-title">主数据</span>
          </template>
          <el-menu-item index="/maindata/supplier">
            <el-icon><OfficeBuilding /></el-icon>
            <span>供应商清单</span>
          </el-menu-item>
          <el-menu-item index="/maindata/part">
            <el-icon><Cpu /></el-icon>
            <span>零件清单</span>
          </el-menu-item>
          <el-menu-item index="/maindata/project">
            <el-icon><Management /></el-icon>
            <span>项目清单</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- SQM 供应商质量管理 -->
        <el-sub-menu index="2">
          <template #title>
            <el-icon><Checked /></el-icon>
            <span class="menu-title">供应商质量管理</span>
          </template>
          <el-menu-item index="/sqm/part-dev">
            <el-icon><TrendCharts /></el-icon>
            <span>零件开发管理</span>
          </el-menu-item>
          <el-menu-item index="/sqm/quality-issue">
            <el-icon><WarningFilled /></el-icon>
            <span>质量问题清单</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- CTQ 关键质量特性 -->
        <el-sub-menu index="3">
          <template #title>
            <el-icon><Aim /></el-icon>
            <span class="menu-title">CTQ（关键质量特性）</span>
          </template>
          <el-menu-item index="/ctq/list">
            <el-icon><List /></el-icon>
            <span>关键特征清单</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-scrollbar>

    <div class="sidebar-footer">
      <div class="mode-badge" v-if="!isCollapsed">
        <span class="dot"></span> 免密直进工作台
      </div>
      <el-button
        link
        class="collapse-btn"
        @click="isCollapsed = !isCollapsed"
        :title="isCollapsed ? '展开菜单' : '收起菜单'"
      >
        <el-icon :size="18">
          <component :is="isCollapsed ? 'Expand' : 'Fold'" />
        </el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  DataAnalysis,
  Folder,
  OfficeBuilding,
  Cpu,
  Management,
  Checked,
  TrendCharts,
  WarningFilled,
  Aim,
  List,
  Expand,
  Fold
} from '@element-plus/icons-vue'

const route = useRoute()
const isCollapsed = ref(false)

const activeRoute = computed(() => route.path)
</script>

<style scoped>
.sidebar-wrapper {
  width: 250px;
  height: 100vh;
  background: linear-gradient(180deg, #0b1120 0%, #0f172a 45%, #0b0f19 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
  user-select: none;
  position: relative;
  z-index: 20;
}

.sidebar-wrapper.collapsed {
  width: 64px;
}

/* 顶部品牌区 (信标 6) */
.brand-header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.015);
}

.sidebar-wrapper.collapsed .brand-header {
  justify-content: center;
  padding: 0;
}

.logo-box {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: linear-gradient(135deg, #6366f1 0%, #4338ca 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.brand-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #f8fafc;
  margin: 0;
  line-height: 1.25;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.brand-sub {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  letter-spacing: 0.01em;
}

/* 菜单滚动区 (信标 4) */
.menu-scrollbar {
  flex: 1;
}

.custom-menu {
  background: transparent !important;
  border-right: none !important;
  padding: 8px 0;
}

/* 分组标题与子菜单标题 */
:deep(.el-sub-menu__title) {
  font-weight: 600;
  color: #94a3b8 !important;
  font-size: 12.5px;
  height: 42px;
  line-height: 42px;
  margin: 2px 10px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

:deep(.el-sub-menu__title:hover) {
  color: #f1f5f9 !important;
  background-color: rgba(255, 255, 255, 0.05) !important;
}

:deep(.el-sub-menu__title .el-icon) {
  color: #818cf8;
  font-size: 16px;
  margin-right: 8px;
}

:deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
  color: #64748b;
  font-size: 12px;
}

/* 菜单内嵌展开容器背景透明 */
:deep(.el-menu--inline) {
  background: transparent !important;
  padding: 2px 0;
}

/* 具体菜单链接项 */
:deep(.el-menu-item) {
  font-size: 13px;
  color: #94a3b8 !important;
  height: 40px;
  line-height: 40px;
  margin: 2px 10px 2px 18px;
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

:deep(.el-menu-item .el-icon) {
  color: #64748b;
  font-size: 15px;
  margin-right: 8px;
  transition: color 0.2s ease;
}

:deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.06) !important;
  color: #f8fafc !important;
}

:deep(.el-menu-item:hover .el-icon) {
  color: #a5b4fc;
}

/* 激活选中的菜单项 */
:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.22) 0%, rgba(99, 102, 241, 0.05) 100%) !important;
  color: #ffffff !important;
  font-weight: 600;
  border: 1px solid rgba(99, 102, 241, 0.35);
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.18);
}

:deep(.el-menu-item.is-active .el-icon) {
  color: #818cf8 !important;
}

:deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 0 4px 4px 0;
  background: #818cf8;
  box-shadow: 0 0 10px #818cf8;
}

/* 底部状态与收起按钮 (信标 5) */
.sidebar-footer {
  height: 52px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.015);
}

.sidebar-wrapper.collapsed .sidebar-footer {
  justify-content: center;
  padding: 0;
}

.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #34d399;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.28);
  padding: 3px 10px;
  border-radius: 99px;
  font-weight: 500;
  letter-spacing: 0.02em;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.08);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.collapse-btn {
  color: #94a3b8;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
}

.collapse-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
}
</style>
