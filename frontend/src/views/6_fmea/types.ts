export type FmeaViewMode = 'canvas' | 'gallery' | 'ledger'
export type CanvasToolMode = 'select' | 'pin' | 'node'
export type PortSide = 'top' | 'right' | 'bottom' | 'left'
export type RiskLevel = 'HIGH' | 'MED' | 'LOW'
export type FmeaType = 'DFMEA' | 'PFMEA' | 'LESSON'
export type TargetKind = 'pin' | 'node' | 'edge' | 'shared_unit' | 'unassigned'
export type SoftRefType = 'part' | 'supplier' | 'issue' | 'project' | 'ctq' | 'free'

export interface CanvasViewport {
  panX: number
  panY: number
  zoom: number
}

export interface BlueprintPin {
  id: string
  num: number
  rx: number // 0 ~ 1 相对底图宽度比例
  ry: number // 0 ~ 1 相对底图高度比例
  title: string
  sub?: string
  is_limit?: boolean // 是否为图纸设计极限特征/公差
  limit_spec?: string // 极限公差/尺寸说明 (如 R0.15极小圆角 / 0.8mm薄壁)
}

export interface CanvasImageBoard {
  id: string
  title: string
  img_url: string
  attachment_id?: number | null
  x: number
  y: number
  w: number
  h: number
  pins: BlueprintPin[]
}

export interface CanvasModuleNode {
  id: string
  title: string
  sub?: string
  unit_code?: string | null // 跨画板共用零件/标准单元编码 (如 PRT-109)
  sub_board_id?: number | null // 嵌套引用的子模块画板 ID (支持多父级借用与双击下钻)
  x: number
  y: number
}

export interface CanvasInterfaceEdge {
  id: string
  from: string
  fromPort: PortSide
  to: string
  toPort: PortSide
  label: string
  sub?: string
  kind?: 'normal' | 'process_challenge' // 连线属性：normal=常规配合接口，process_challenge=设计极限引发制程挑战
}

export interface BoardCanvasData {
  viewport: CanvasViewport
  image_boards: CanvasImageBoard[]
  nodes: CanvasModuleNode[]
  edges: CanvasInterfaceEdge[]
}

export interface FmeaPhoto {
  id?: string
  attachment_id?: number | null
  url: string
  tag: 'NG' | 'OK'
  caption?: string
}

export interface FmeaLinkedRef {
  type: SoftRefType
  ref_id?: number | null
  code?: string | null
  label: string
}

export interface FmeaItem {
  id: number
  fmea_code: string
  board_id: number | null
  board_name?: string | null
  board_group?: string | null
  target_kind: TargetKind
  target_id: string | null
  target_title_snapshot?: string | null
  fmea_type: FmeaType
  failure_mode: string
  failure_mech?: string | null
  failure_effect?: string | null
  control_measure?: string | null
  prevention_measure?: string | null
  detection_measure?: string | null
  risk_level: RiskLevel
  severity?: number | null
  occurrence?: number | null
  detection?: number | null
  rpn?: number | null
  photos: FmeaPhoto[]
  linked_refs: FmeaLinkedRef[]
  ref_codes_text?: string | null
  source_issue_no?: string | null
  created_at: string
  updated_at: string
}

export interface SubBoardRollupStat {
  board_id: number
  board_code: string
  group_name: string
  name: string
  total_items: number
  high_risk_count: number
  photo_count: number
}

export interface WhereUsedRef {
  board_id: number
  board_name: string
  group_name: string
  node_id?: string | null
  node_title?: string | null
}

export interface SharedUnitOption {
  unit_code: string
  title: string
  used_board_count: number
  shared_item_count: number
}

export interface FmeaBomChildSummary {
  node_id: string
  title: string
  ref_type: 'sub_board' | 'shared_unit'
  sub_board_id?: number | null
  sub_board_code?: string | null
  sub_board_name?: string | null
  unit_code?: string | null
  instance_index: number
  high_risk_count: number
  total_items: number
}

export interface FmeaBoardSummary {
  id: number
  board_code: string
  group_name: string
  name: string
  board_type: string
  description?: string | null
  sort_order: number
  is_archived: boolean
  total_items: number
  high_risk_count: number
  photo_count: number
  node_count: number
  bom_children?: FmeaBomChildSummary[]
  created_at: string
  updated_at: string
}

export interface FmeaBoardGroup {
  group_name: string
  boards: FmeaBoardSummary[]
}

export interface FmeaBoardDetail {
  id: number
  board_code: string
  group_name: string
  name: string
  board_type: string
  description?: string | null
  canvas_data: BoardCanvasData
  sort_order: number
  is_archived: boolean
  items: FmeaItem[]
  sub_board_stats: Record<string, SubBoardRollupStat>
  parent_boards: WhereUsedRef[]
  unit_where_used: Record<string, WhereUsedRef[]>
  created_at: string
  updated_at: string
}

export interface CanvasSelection {
  kind: 'pin' | 'node' | 'edge'
  id: string
  boardImgId?: string // 若 kind === 'pin'，记录所属底图 id
}

export interface SoftRefSuggestion {
  type: SoftRefType
  ref_id: number
  code: string
  label: string
  sub_info?: string | null
  status?: string | null
}

export interface SoftRefSnapshot {
  key: string
  type: SoftRefType
  exists: boolean
  ref_id?: number | null
  code?: string | null
  label: string
  status?: string | null
  detail_lines: string[]
  jump_route?: string | null
  jump_keyword?: string | null
}

export interface FmeaAiDraft {
  fmea_type: FmeaType
  failure_mode: string
  failure_mech: string
  failure_effect: string
  control_measure: string
  risk_level: RiskLevel
  severity?: number | null
  occurrence?: number | null
  detection?: number | null
  suggested_target_kind: 'node' | 'edge'
  suggested_target_id?: string | null
  suggested_node_title?: string | null
  suggested_edge_from_title?: string | null
  suggested_edge_to_title?: string | null
  suggested_edge_label?: string | null
  linked_refs: FmeaLinkedRef[]
}
