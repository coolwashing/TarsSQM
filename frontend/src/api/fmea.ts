import axios from 'axios'
import type {
  FmeaBoardGroup,
  FmeaBoardSummary,
  FmeaBoardDetail,
  BoardCanvasData,
  FmeaItem,
  FmeaPhoto,
  FmeaLinkedRef,
  SoftRefSuggestion,
  SoftRefSnapshot,
  FmeaAiDraft,
  SharedUnitOption
} from '@/views/6_fmea/types'

export interface FmeaBoardTreeResponse {
  groups: FmeaBoardGroup[]
  boards: FmeaBoardSummary[]
}

export interface FmeaItemPageResponse {
  total: number
  page: number
  page_size: number
  items: FmeaItem[]
}

export const fmeaApi = {
  // 1. 画板、系统分组与多级 BOM 目录树
  async getBoardTree(includeArchived = false): Promise<FmeaBoardTreeResponse> {
    const { data } = await axios.get<FmeaBoardTreeResponse>('/api/fmea/boards/tree', {
      params: { include_archived: includeArchived }
    })
    return data
  },

  async getBoardDetail(boardId: number): Promise<FmeaBoardDetail> {
    const { data } = await axios.get<FmeaBoardDetail>(`/api/fmea/boards/${boardId}`)
    return data
  },

  async createBoard(payload: {
    group_name: string
    name: string
    board_type?: string
    description?: string
    canvas_data?: BoardCanvasData
  }): Promise<FmeaBoardDetail> {
    const { data } = await axios.post<FmeaBoardDetail>('/api/fmea/boards', payload)
    return data
  },

  async duplicateBoard(
    boardId: number,
    payload: { new_name?: string; group_name?: string } = {}
  ): Promise<FmeaBoardDetail> {
    const { data } = await axios.post<FmeaBoardDetail>(`/api/fmea/boards/${boardId}/duplicate`, payload)
    return data
  },

  async renameGroup(oldName: string, newName: string): Promise<void> {
    await axios.put('/api/fmea/groups/rename', { old_name: oldName, new_name: newName })
  },

  async dissolveGroup(groupName: string): Promise<void> {
    await axios.delete('/api/fmea/groups', { params: { group_name: groupName } })
  },

  async listSharedUnits(q = ''): Promise<SharedUnitOption[]> {
    const { data } = await axios.get<SharedUnitOption[]>('/api/fmea/shared-units', { params: { q } })
    return data
  },

  async listQualityIssues(params: {
    page?: number
    page_size?: number
    keyword?: string
    severity?: string
    status?: string
  } = {}): Promise<{ total: number; items: any[] }> {
    const { data } = await axios.get('/api/sqm/issues', { params })
    return data
  },

  async updateBoard(
    boardId: number,
    payload: {
      group_name?: string
      name?: string
      board_type?: string
      description?: string
      canvas_data?: BoardCanvasData
      sort_order?: number
      is_archived?: boolean
    }
  ): Promise<FmeaBoardDetail> {
    const { data } = await axios.put<FmeaBoardDetail>(`/api/fmea/boards/${boardId}`, payload)
    return data
  },

  async deleteBoard(boardId: number, deleteItems = false): Promise<void> {
    await axios.delete(`/api/fmea/boards/${boardId}`, {
      params: { delete_items: deleteItems }
    })
  },

  async seedDemoBoards(): Promise<void> {
    await axios.post('/api/fmea/boards/seed-demo')
  },

  // 2. FMEA 机理卡 CRUD 与分页检索
  async listItems(params: {
    page?: number
    page_size?: number
    keyword?: string
    board_id?: number
    fmea_type?: string
    risk_level?: string
    has_photo?: boolean
    ref_code?: string
  }): Promise<FmeaItemPageResponse> {
    const { data } = await axios.get<FmeaItemPageResponse>('/api/fmea/items', { params })
    return data
  },

  async createItem(payload: Partial<FmeaItem> & { failure_mode: string }): Promise<FmeaItem> {
    const { data } = await axios.post<FmeaItem>('/api/fmea/items', payload)
    return data
  },

  async updateItem(
    itemId: number,
    payload: Partial<FmeaItem> & { clear_sod?: boolean }
  ): Promise<FmeaItem> {
    const { data } = await axios.put<FmeaItem>(`/api/fmea/items/${itemId}`, payload)
    return data
  },

  async deleteItem(itemId: number): Promise<void> {
    await axios.delete(`/api/fmea/items/${itemId}`)
  },

  // 3. 软关联联想、实时快照穿透与跨模块计数
  async suggestSoftRefs(q: string, types = 'part,supplier,issue,project,ctq'): Promise<SoftRefSuggestion[]> {
    const { data } = await axios.get<SoftRefSuggestion[]>('/api/fmea/refs/suggest', {
      params: { q, types, limit: 18 }
    })
    return data
  },

  async resolveSoftRefs(refs: FmeaLinkedRef[]): Promise<SoftRefSnapshot[]> {
    const { data } = await axios.post<SoftRefSnapshot[]>('/api/fmea/refs/resolve', { refs })
    return data
  },

  async getRefCounts(codes: string[]): Promise<Record<string, { total: number; high: number }>> {
    if (!codes.length) return {}
    const { data } = await axios.get<Record<string, { total: number; high: number }>>(
      '/api/fmea/refs/counts',
      { params: { codes: codes.join(',') } }
    )
    return data
  },

  // 4. 质量问题反哺与 AI 智能拆解
  async depositFromQualityIssue(
    issueId: number,
    payload: {
      board_id: number
      target_kind: string
      target_id?: string | null
      new_node_title?: string
      fmea_type?: string
      risk_level?: string
      failure_mode?: string
      failure_mech?: string
      failure_effect?: string
      control_measure?: string
    }
  ): Promise<FmeaItem> {
    const { data } = await axios.post<FmeaItem>(`/api/fmea/from-quality-issue/${issueId}`, payload)
    return data
  },

  async aiParseDrafts(payload: {
    raw_text: string
    board_id?: number | null
    photos?: FmeaPhoto[]
  }): Promise<{ engine_mode: string; drafts: FmeaAiDraft[] }> {
    const { data } = await axios.post<{ engine_mode: string; drafts: FmeaAiDraft[] }>(
      '/api/fmea/ai-parse',
      payload
    )
    return data
  },

  // 5. 流式物理文件上传 (复用 r_storage)
  async uploadFile(
    file: File,
    bizType: 'fmea_blueprint' | 'fmea_photo' = 'fmea_photo',
    bizId?: number | null
  ): Promise<{ id: number; url: string; original_name: string }> {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('biz_type', bizType)
    if (bizId) {
      fd.append('biz_id', String(bizId))
    }
    const { data } = await axios.post<{ id: number; url: string; original_name: string }>(
      '/api/storage/upload',
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  }
}
