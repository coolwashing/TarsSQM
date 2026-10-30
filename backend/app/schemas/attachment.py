from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    """
    附件元数据响应契约
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    original_name: str
    file_size: int
    mime_type: str
    biz_type: str
    biz_id: Optional[int] = None
    created_at: datetime
    url: str


SysAttachmentOut = AttachmentOut


class AttachmentBindRequest(BaseModel):
    """
    附件批量绑定业务外键请求
    """
    attachment_ids: List[int]
    biz_id: int


class WangEditorUploadResponse(BaseModel):
    """
    适配 WangEditor 5 标准图文上传响应契约
    """
    errno: int = 0
    data: Dict[str, Any]
    message: Optional[str] = None
