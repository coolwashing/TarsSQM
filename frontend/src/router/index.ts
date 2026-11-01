import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/maindata/supplier'
  },
  // MainData 主数据模块
  {
    path: '/maindata/supplier',
    name: 'SupplierList',
    component: () => import('@/views/1_maindata/1.1_supplier/SupplierList.vue'),
    meta: { title: '供应商清单' }
  },
  {
    path: '/maindata/part',
    name: 'PartList',
    component: () => import('@/views/1_maindata/1.2_part/PartList.vue'),
    meta: { title: '零件清单' }
  },
  {
    path: '/maindata/project',
    name: 'ProjectList',
    component: () => import('@/views/1_maindata/1.3_project/ProjectList.vue'),
    meta: { title: '项目清单' }
  },
  // SQM 供应商质量管理模块
  {
    path: '/sqm/part-dev',
    name: 'PartDevList',
    component: () => import('@/views/2_sqm/2.1_part_dev/PartDevList.vue'),
    meta: { title: '零件开发管理' }
  },
  {
    path: '/sqm/quality-issue',
    name: 'QualityIssueList',
    component: () => import('@/views/2_sqm/2.2_quality_issue/QualityIssueList.vue'),
    meta: { title: '质量问题清单' }
  },
  // CTQ 关键质量特性模块
  {
    path: '/ctq/list',
    name: 'CTQList',
    component: () => import('@/views/3_ctq/3.1_ctq/CTQList.vue'),
    meta: { title: '关键特征清单' }
  },
  // 质量知识库模块
  {
    path: '/kb/docs',
    name: 'KnowledgeBase',
    component: () => import('@/views/4_kb/KnowledgeBase.vue'),
    meta: { title: '质量知识库' }
  },
  {
    path: '/kb/editor/:id',
    name: 'KbDocEditor',
    component: () => import('@/views/4_kb/DocEditorPage.vue'),
    meta: { title: '质量规程文档编辑' }
  },
  // 研发与数据工作台
  {
    path: '/dev/database',
    name: 'DatabaseStudio',
    component: () => import('@/views/5_dev/DatabaseStudio.vue'),
    meta: { title: '数据库工作台' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 免密直进：设置页面标题
router.beforeEach((to, _from, next) => {
  if (to.meta && to.meta.title) {
    document.title = `${to.meta.title} - SQM 供应商与质量管理系统`
  }
  next()
})

export default router
