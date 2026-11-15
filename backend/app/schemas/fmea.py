from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FmeaPhotoSchema(BaseModel):
    id: Optional[str] = None
    attachment_id: Optional[int] = None
    url: str
    tag: str = Field("NG", description="照片标识: NG(失效实拍) / OK(防错标准)")
    caption: Optional[str] = Field("", description="简短图注说明")


class FmeaLinkedRefSchema(BaseModel):
    type: str = Field(
        "free",
        description="关联类型: part / supplier / issue / project / ctq / free"
    )
    ref_id: Optional[int] = None
    code: Optional[str] = None
    label: str = Field(..., description="名称快照或自由标签文本")


# ==================== 画板、多级 BOM 与目录树模型 ====================

class FmeaBoardCreate(BaseModel):
    board_code: Optional[str] = Field(None, max_length=64)
    group_name: str = Field("关节执行器系统", max_length=100)
    name: str = Field(..., max_length=150)
    board_type: str = Field("MIXED", description="DFMEA / PFMEA / MIXED")
    description: Optional[str] = Field(None, max_length=500)
    canvas_data: Optional[Dict[str, Any]] = None
    sort_order: int = 0


class FmeaBoardUpdate(BaseModel):
    group_name: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=150)
    board_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    canvas_data: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_archived: Optional[bool] = None


class FmeaGroupRenameReq(BaseModel):
    old_name: str = Field(..., max_length=100)
    new_name: str = Field(..., max_length=100)


class FmeaBoardDuplicateReq(BaseModel):
    new_name: Optional[str] = Field(None, max_length=150)
    group_name: Optional[str] = Field(None, max_length=100)


class SubBoardRollupStat(BaseModel):
    board_id: int
    board_code: str
    group_name: str
    name: str
    total_items: int = 0
    high_risk_count: int = 0
    photo_count: int = 0


class WhereUsedRefOut(BaseModel):
    board_id: int
    board_name: str
    group_name: str
    node_id: Optional[str] = None
    node_title: Optional[str] = None


class SharedUnitOptionOut(BaseModel):
    unit_code: str
    title: str
    used_board_count: int = 0
    shared_item_count: int = 0


class FmeaBomChildSummary(BaseModel):
    node_id: str
    title: str
    ref_type: str = "sub_board"  # sub_board | shared_unit
    sub_board_id: Optional[int] = None
    sub_board_code: Optional[str] = None
    sub_board_name: Optional[str] = None
    unit_code: Optional[str] = None
    instance_index: int = 1
    high_risk_count: int = 0
    total_items: int = 0


class FmeaBoardSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_code: str
    group_name: str
    name: str
    board_type: str
    description: Optional[str] = None
    sort_order: int = 0
    is_archived: bool = False
    total_items: int = 0
    high_risk_count: int = 0
    photo_count: int = 0
    node_count: int = 0
    bom_children: List[FmeaBomChildSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FmeaBoardGroupNode(BaseModel):
    group_name: str
    boards: List[FmeaBoardSummaryOut] = Field(default_factory=list)


class FmeaBoardTreeResp(BaseModel):
    groups: List[FmeaBoardGroupNode] = Field(default_factory=list)
    boards: List[FmeaBoardSummaryOut] = Field(default_factory=list)


# ==================== FMEA 失效机理卡模型 ====================

class FmeaItemCreate(BaseModel):
    fmea_code: Optional[str] = Field(None, max_length=64)
    board_id: Optional[int] = None
    target_kind: str = Field(
        "unassigned",
        description="pin / node / edge / shared_unit / unassigned"
    )
    target_id: Optional[str] = Field(None, max_length=64)
    target_title_snapshot: Optional[str] = Field(None, max_length=150)
    fmea_type: str = Field("DFMEA", description="DFMEA / PFMEA / LESSON")
    failure_mode: str = Field(..., max_length=255)
    failure_mech: Optional[str] = None
    failure_effect: Optional[str] = None
    control_measure: Optional[str] = None
    prevention_measure: Optional[str] = None
    detection_measure: Optional[str] = None
    risk_level: Optional[str] = Field(None, description="HIGH / MED / LOW")
    severity: Optional[int] = Field(None, ge=1, le=10)
    occurrence: Optional[int] = Field(None, ge=1, le=10)
    detection: Optional[int] = Field(None, ge=1, le=10)
    photos: List[FmeaPhotoSchema] = Field(default_factory=list)
    linked_refs: List[FmeaLinkedRefSchema] = Field(default_factory=list)
    source_issue_no: Optional[str] = None


class FmeaItemUpdate(BaseModel):
    board_id: Optional[int] = None
    target_kind: Optional[str] = None
    target_id: Optional[str] = None
    target_title_snapshot: Optional[str] = None
    fmea_type: Optional[str] = None
    failure_mode: Optional[str] = Field(None, max_length=255)
    failure_mech: Optional[str] = None
    failure_effect: Optional[str] = None
    control_measure: Optional[str] = None
    prevention_measure: Optional[str] = None
    detection_measure: Optional[str] = None
    risk_level: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=10)
    occurrence: Optional[int] = Field(None, ge=1, le=10)
    detection: Optional[int] = Field(None, ge=1, le=10)
    clear_sod: Optional[bool] = False
    photos: Optional[List[FmeaPhotoSchema]] = None
    linked_refs: Optional[List[FmeaLinkedRefSchema]] = None


class FmeaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fmea_code: str
    board_id: Optional[int] = None
    board_name: Optional[str] = None
    board_group: Optional[str] = None
    target_kind: str
    target_id: Optional[str] = None
    target_title_snapshot: Optional[str] = None
    fmea_type: str
    failure_mode: str
    failure_mech: Optional[str] = None
    failure_effect: Optional[str] = None
    control_measure: Optional[str] = None
    prevention_measure: Optional[str] = None
    detection_measure: Optional[str] = None
    risk_level: str
    severity: Optional[int] = None
    occurrence: Optional[int] = None
    detection: Optional[int] = None
    rpn: Optional[int] = None
    photos: List[Dict[str, Any]] = Field(default_factory=list)
    linked_refs: List[Dict[str, Any]] = Field(default_factory=list)
    ref_codes_text: Optional[str] = None
    source_issue_no: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FmeaBoardDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_code: str
    group_name: str
    name: str
    board_type: str
    description: Optional[str] = None
    canvas_data: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_archived: bool = False
    items: List[FmeaItemOut] = Field(default_factory=list)
    sub_board_stats: Dict[str, SubBoardRollupStat] = Field(default_factory=dict)
    parent_boards: List[WhereUsedRefOut] = Field(default_factory=list)
    unit_where_used: Dict[str, List[WhereUsedRefOut]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class FmeaItemPageResult(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[FmeaItemOut] = Field(default_factory=list)


# ==================== 软关联联想与穿透快照模型 ====================

class SoftRefSuggestItem(BaseModel):
    type: str
    ref_id: int
    code: str
    label: str
    sub_info: Optional[str] = None
    status: Optional[str] = None


class SoftRefResolveReq(BaseModel):
    refs: List[FmeaLinkedRefSchema] = Field(default_factory=list)


class SoftRefSnapshotOut(BaseModel):
    key: str
    type: str
    exists: bool = False
    ref_id: Optional[int] = None
    code: Optional[str] = None
    label: str
    status: Optional[str] = None
    detail_lines: List[str] = Field(default_factory=list)
    jump_route: Optional[str] = None
    jump_keyword: Optional[str] = None


# ==================== AI 智能拆解与质量单沉淀模型 ====================

class FmeaAiParseReq(BaseModel):
    raw_text: str = Field("", description="现场异常记录、8D片段或外部大模型输出")
    board_id: Optional[int] = None
    photos: List[FmeaPhotoSchema] = Field(default_factory=list)


class FmeaAiParseDraft(BaseModel):
    fmea_type: str = "DFMEA"
    failure_mode: str
    failure_mech: str = ""
    failure_effect: str = ""
    control_measure: str = ""
    risk_level: str = "HIGH"
    severity: Optional[int] = None
    occurrence: Optional[int] = None
    detection: Optional[int] = None
    suggested_target_kind: str = "node"
    suggested_target_id: Optional[str] = None
    suggested_node_title: Optional[str] = None
    suggested_edge_from_title: Optional[str] = None
    suggested_edge_to_title: Optional[str] = None
    suggested_edge_label: Optional[str] = None
    linked_refs: List[FmeaLinkedRefSchema] = Field(default_factory=list)


class FmeaAiParseResp(BaseModel):
    engine_mode: str = Field("llm", description="llm(在线大模型) / rule_fallback(工程规则拆解)")
    drafts: List[FmeaAiParseDraft] = Field(default_factory=list)


class DepositFromQualityIssueReq(BaseModel):
    board_id: int
    target_kind: str = Field("node", description="node / pin / edge / new_node")
    target_id: Optional[str] = None
    new_node_title: Optional[str] = None
    fmea_type: str = "DFMEA"
    risk_level: Optional[str] = None
    failure_mode: Optional[str] = None
    failure_mech: Optional[str] = None
    failure_effect: Optional[str] = None
    control_measure: Optional[str] = None
