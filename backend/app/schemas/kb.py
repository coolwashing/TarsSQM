from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class KbDocTreeNode(BaseModel):
    """
    文档树形嵌套节点 (不含长正文，秒级轻量加载)
    """
    id: int
    parent_id: Optional[int] = None
    title: str
    icon: str = "📄"
    is_folder: bool = False
    is_favorite: bool = False
    sort_order: int = 0
    type: str = "doc"
    target_id: Optional[int] = None
    file_url: Optional[str] = None
    children: List["KbDocTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


class KbDocDetail(BaseModel):
    """
    单篇文档详情
    """
    id: int
    parent_id: Optional[int] = None
    title: str
    icon: str = "📄"
    is_folder: bool = False
    sort_order: int = 0
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    biz_type: Optional[str] = None
    biz_id: Optional[int] = None
    author: str = "系统管理员"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KbDocCreate(BaseModel):
    """
    新建文档/分类入参
    """
    parent_id: Optional[int] = None
    title: str = "新建质量规范文档"
    icon: str = "📄"
    is_folder: bool = False
    sort_order: Optional[int] = 0
    biz_type: Optional[str] = None
    biz_id: Optional[int] = None


class KbDocUpdate(BaseModel):
    """
    更新文档入参 (0.5s 静默保存)
    """
    title: Optional[str] = None
    icon: Optional[str] = None
    content_html: Optional[str] = None
    author: Optional[str] = None


class KbDocMove(BaseModel):
    """
    拖拽调整节点位置与顺序
    """
    target_parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class KbDocSearchResult(BaseModel):
    """
    知识库搜索结果条目
    """
    id: int
    title: str
    icon: str
    snippet: str
    updated_at: datetime
    location: str = "文档正文"
    kind: str = "doc"

    model_config = ConfigDict(from_attributes=True)


class KbAiCopilotRequest(BaseModel):
    """
    网页端 AI 智写请求
    """
    prompt: str
    doc_id: Optional[int] = None
    selected_text: Optional[str] = None
    scope: Optional[str] = "ALL"
    scope_name: Optional[str] = None


class KbPromptPresetItem(BaseModel):
    """
    AI 智写快捷指令预设条目 (同步自 data/kb_prompt_presets.json)
    """
    id: str
    name: str
    prompt: str
    is_system: bool = False


class KbPromptPresetSave(BaseModel):
    """
    新增或保存快捷指令
    """
    id: Optional[str] = None
    name: str
    prompt: str


# ========================================================
# Windows 资源管理器交互数据结构
# ========================================================
class KbExplorerItem(BaseModel):
    id: int
    name: str
    type: str  # "folder" | "doc" | "shortcut"
    icon: str
    date: str
    proj: Optional[str] = None
    size: Optional[str] = None
    is_favorite: bool = False
    status: str = "ACTIVE"
    is_shortcut: bool = False
    target_id: Optional[int] = None
    author: Optional[str] = None
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    attachment_id: Optional[int] = None
    index_status: Optional[str] = None
    index_message: Optional[str] = None
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KbItemStatusUpdate(BaseModel):
    status: str = Field(..., description="文档状态: DRAFT/REVIEW/ACTIVE/OBSOLETE")


class KbBreadcrumbNode(BaseModel):
    id: Optional[int] = None
    name: str


class KbFolderCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = "新建文件夹"
    icon: Optional[str] = "📁"
    biz_type: Optional[str] = None


class KbDocFastCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = "新建质量规程文档"
    icon: Optional[str] = "📄"
    biz_type: Optional[str] = None


class KbShortcutCreate(BaseModel):
    target_doc_id: int
    parent_id: Optional[int] = None
    name: Optional[str] = None


class KbItemRename(BaseModel):
    id: int
    name: str


class KbItemMove(BaseModel):
    id: int
    target_folder_id: Optional[int] = None
    reference_id: Optional[int] = None
    placement: Literal["inside", "before", "after"] = "inside"


class KbItemIconUpdate(BaseModel):
    id: int
    icon: str
