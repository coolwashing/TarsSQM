export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'PENDING_REVIEW' | 'DONE' | 'BLOCKED'
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
export type TaskSourceType = 'SUPPLIER' | 'PART' | 'CTQ' | 'DOC_KB' | 'CUSTOM'

export interface TaskAttachmentItem {
  id: number
  file_path: string
  original_name: string
  file_size: number
  mime_type: string
  biz_type: string
  biz_id?: number
  created_at: string
}

export interface TaskItem {
  id: number
  task_code: string
  title: string
  description_html?: string
  status: TaskStatus
  priority: TaskPriority
  source_type: TaskSourceType
  source_id?: number | string | null
  source_title?: string | null
  source_url?: string | null
  assignee_id?: number | null
  assignee_name?: string | null
  creator_id?: number | null
  creator_name?: string | null
  start_date?: string | null
  due_date?: string | null
  completed_at?: string | null
  parent_id?: number | null
  predecessor_ids?: number[]
  tags?: string[]
  sort_order: number
  created_at: string
  updated_at: string
  is_overdue?: boolean
  attachment_count?: number
  attachments?: TaskAttachmentItem[]
}

export interface TaskSummaryStats {
  total: number
  todo: number
  in_progress: number
  pending_review: number
  done: number
  blocked: number
  overdue: number
}

export interface TaskFilterParams {
  keyword?: string
  source_type?: string
  source_id?: string | number
  status?: string
  priority?: string
  assignee_id?: number
  due_filter?: 'all' | 'today' | 'this_week' | 'overdue'
  page?: number
  page_size?: number
}
