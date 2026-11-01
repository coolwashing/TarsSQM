import axios from 'axios'
import type {
  TaskItem,
  TaskSummaryStats,
  TaskFilterParams,
  TaskStatus
} from '@/types/task'

export const taskApi = {
  // 获取统计概览指标
  getStats: () => {
    return axios.get<TaskSummaryStats>('/api/tasks/stats/summary').then(res => res.data)
  },

  // 分页多维查询任务列表
  listTasks: (params: TaskFilterParams) => {
    return axios.get<{ total: number; items: TaskItem[] }>('/api/tasks', { params }).then(res => res.data)
  },

  // 获取特定任务详情（含附件列表）
  getTaskDetail: (id: number) => {
    return axios.get<TaskItem>(`/api/tasks/${id}`).then(res => res.data)
  },

  // 创建任务
  createTask: (data: Partial<TaskItem>) => {
    return axios.post<TaskItem>('/api/tasks', data).then(res => res.data)
  },

  // 更新任务
  updateTask: (id: number, data: Partial<TaskItem>) => {
    return axios.put<TaskItem>(`/api/tasks/${id}`, data).then(res => res.data)
  },

  // 快捷变更状态 (看板/勾选)
  updateStatus: (id: number, status: TaskStatus) => {
    return axios.patch<TaskItem>(`/api/tasks/${id}/status`, { status }).then(res => res.data)
  },

  // 快捷变更起止日期 (日历/甘特拖拽)
  updateDates: (id: number, dates: { start_date?: string | null; due_date?: string | null }) => {
    return axios.patch<TaskItem>(`/api/tasks/${id}/dates`, dates).then(res => res.data)
  },

  // 删除任务
  deleteTask: (id: number) => {
    return axios.delete(`/api/tasks/${id}`)
  },

  // 按源头获取关联任务 (供业务内嵌组件)
  getTasksBySource: (sourceType: string, sourceId: number | string) => {
    return axios.get<TaskItem[]>(`/api/tasks/by-source/${sourceType}/${sourceId}`).then(res => res.data)
  },

  // 播种演示数据
  seedDemoTasks: () => {
    return axios.post('/api/tasks/seed-demo').then(res => res.data)
  }
}
