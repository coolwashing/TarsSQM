from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class TeleprompterPresetItem(BaseModel):
    """
    开发套件 Alt+X 提词器快捷指令
    """
    id: str
    title: str
    prompt: str
    isCustom: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class TeleprompterPresetSave(BaseModel):
    """
    收藏/更新 Alt+X 提词器指令
    """
    id: Optional[str] = None
    title: str
    prompt: str
    isCustom: Optional[bool] = True


# ========================================================
# 数据库探针与异机连接配置模型
# ========================================================

class DbConfigReq(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    db_name: str = "sqm"


class DbConfigStatus(BaseModel):
    is_connected: bool
    message: str
    host: str
    port: int
    user: str
    db_name: str
    masked_password: str
    current_host: Optional[str] = None
    current_port: Optional[int] = None
    current_user: Optional[str] = None
    current_db: Optional[str] = None


class DbTableInfo(BaseModel):
    name: str
    table_name: Optional[str] = None
    comment: str
    row_count: int
    real_count: Optional[int] = None
    table_rows: Optional[int] = None
    data_size_kb: float
    data_length_kb: Optional[float] = None
    create_time: Optional[str] = None
    engine: Optional[str] = "InnoDB"


class DbColumnInfo(BaseModel):
    name: str
    column_name: Optional[str] = None
    data_type: str
    column_type: Optional[str] = None
    is_nullable: bool
    is_primary: bool
    default_val: Optional[str] = None
    column_default: Optional[str] = None
    comment: str
    column_comment: Optional[str] = None
    extra: Optional[str] = None


class DbColumnCommentUpdate(BaseModel):
    table_name: Optional[str] = None
    column_name: str
    comment: str


class DbRowUpdate(BaseModel):
    primary_key: Optional[str] = "id"
    primary_col: Optional[str] = "id"
    primary_value: Optional[Any] = None
    data: Optional[Dict[str, Any]] = None
    values: Optional[Dict[str, Any]] = None


class DbRowCreate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    values: Optional[Dict[str, Any]] = None


# ========================================================
# 数据表架构设计与文档配置 (data/table_docs/*.json)
# ========================================================

class DbTableDoc(BaseModel):
    table_name: str
    title: Optional[str] = None
    business_module: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = "系统架构师"
    version: Optional[str] = "1.0.0"
    updated_at: Optional[str] = None
    html_content: Optional[str] = ""
    markdown_content: Optional[str] = ""


class DbTableDocUpdate(BaseModel):
    title: Optional[str] = None
    business_module: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    html_content: Optional[str] = None
    markdown_content: Optional[str] = None


