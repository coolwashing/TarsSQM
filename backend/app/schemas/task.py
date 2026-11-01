from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.attachment import SysAttachmentOut


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255, description="任务主题/待办名称")
    description_html: Optional[str] = Field(None, description="任务描述与Checklist (HTML/富文本)")
    status: str = Field("TODO", description="状态: TODO / IN_PROGRESS / PENDING_REVIEW / DONE / BLOCKED")
    priority: str = Field("MEDIUM", description="优先级: LOW / MEDIUM / HIGH / URGENT")
    
    # 多态源头
    source_type: str = Field("CUSTOM", description="业务源头类型: SUPPLIER / PART / CTQ / DOC_KB / CUSTOM")
    source_id: Optional[int] = Field(None, description="业务源头主键ID")
    source_title: Optional[str] = Field(None, max_length=255, description="源头实体名称快照")
    source_url: Optional[str] = Field(None, max_length=255, description="回跳路由路径")
    
    # 人员与排期
    assignee_id: Optional[int] = Field(None, description="责任人ID")
    assignee_name: Optional[str] = Field(None, max_length=64, description="责任人姓名")
    creator_id: Optional[int] = Field(None, description="创建人ID")
    creator_name: Optional[str] = Field("系统自动派发", max_length=64, description="创建人姓名")
    start_date: Optional[date] = Field(None, description="计划开始日期")
    due_date: Optional[date] = Field(None, description="计划截止日期")
    
    # 拓扑与标签
    parent_id: Optional[int] = Field(None, description="父任务ID")
    predecessor_ids: Optional[List[int]] = Field(default_factory=list, description="前置任务ID列表")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签池")
    sort_order: Optional[int] = Field(0, description="排序权重")


class TaskCreate(TaskBase):
    task_code: Optional[str] = Field(None, max_length=32, description="任务编号，留空自动生成流水号")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description_html: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    parent_id: Optional[int] = None
    predecessor_ids: Optional[List[int]] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="目标状态: TODO / IN_PROGRESS / PENDING_REVIEW / DONE / BLOCKED")


class TaskDateUpdate(BaseModel):
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_code: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    attachment_count: int = 0


class TaskDetailOut(TaskOut):
    attachments: List[SysAttachmentOut] = Field(default_factory=list)


class TaskSummaryStats(BaseModel):
    total: int = 0
    todo: int = 0
    in_progress: int = 0
    pending_review: int = 0
    done: int = 0
    blocked: int = 0
    overdue: int = 0


class TaskPageResult(BaseModel):
    total: int
    items: List[TaskOut]
