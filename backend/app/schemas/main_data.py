from datetime import date, datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """
    通用分页响应契约
    """
    total: int = Field(..., description="总记录数")
    items: List[T] = Field(..., description="当前页数据列表")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(10, description="每页条数")


# ========================================================
# 1.1 供应商数据契约 (Supplier)
# ========================================================

class SupplierBase(BaseModel):
    code: str = Field(..., max_length=64, description="供应商唯一编码")
    name: str = Field(..., max_length=128, description="供应商中文名称")
    status: str = Field("潜在", max_length=32, description="准入状态: 潜在/考察/合格/冻结")
    short_name: Optional[str] = Field(None, max_length=64, description="企业简称")
    pinyin: Optional[str] = Field(None, max_length=32, description="拼音/缩写")
    supply_tier: Optional[str] = Field(None, max_length=32, description="供应层级: 1供/2供开发中/在开发/潜在供应商")
    product_type: Optional[str] = Field(None, max_length=255, description="主营产品类型")
    cooperation_rate: Optional[str] = Field(None, max_length=16, description="配合度: 高/中/低")
    quality_system: Optional[str] = Field(None, max_length=255, description="质量体系认证")
    region: Optional[str] = Field(None, max_length=32, description="所属区域")
    city: Optional[str] = Field(None, max_length=64, description="所在城市")
    company_type: Optional[str] = Field(None, max_length=64, description="公司类型")
    importance: Optional[str] = Field(None, max_length=16, description="重要程度")
    urgency: Optional[str] = Field(None, max_length=16, description="紧急程度")
    purchasing_status: Optional[str] = Field(None, max_length=32, description="采购状态")
    contact: Optional[str] = Field(None, max_length=64, description="联络人")
    phone: Optional[str] = Field(None, max_length=32, description="联系电话")
    email: Optional[str] = Field(None, max_length=128, description="电子邮箱")
    address: Optional[str] = Field(None, max_length=255, description="办公/工厂地址")
    remark: Optional[str] = Field(None, description="资质与备注说明")
    profile_html: Optional[str] = Field(None, description="供应商图文详细档案富文本")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    status: Optional[str] = Field(None, max_length=32)
    short_name: Optional[str] = Field(None, max_length=64)
    pinyin: Optional[str] = Field(None, max_length=32)
    supply_tier: Optional[str] = Field(None, max_length=32)
    product_type: Optional[str] = Field(None, max_length=255)
    cooperation_rate: Optional[str] = Field(None, max_length=16)
    quality_system: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=32)
    city: Optional[str] = Field(None, max_length=64)
    company_type: Optional[str] = Field(None, max_length=64)
    importance: Optional[str] = Field(None, max_length=16)
    urgency: Optional[str] = Field(None, max_length=16)
    purchasing_status: Optional[str] = Field(None, max_length=32)
    contact: Optional[str] = Field(None, max_length=64)
    phone: Optional[str] = Field(None, max_length=32)
    email: Optional[str] = Field(None, max_length=128)
    address: Optional[str] = Field(None, max_length=255)
    remark: Optional[str] = None
    profile_html: Optional[str] = None


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SupplierDetailOut(SupplierOut):
    attachments: List[dict] = Field(default_factory=list, description="关联附件列表")


# ========================================================
# 1.3 项目数据契约 (Project)
# ========================================================

class ProjectBase(BaseModel):
    project_code: str = Field(..., max_length=64, description="项目唯一代号")
    name: str = Field(..., max_length=128, description="项目名称")
    platform: Optional[str] = Field(None, max_length=64, description="所属车型/平台")
    sop_date: Optional[date] = Field(None, description="量产节点 (SOP)")
    status: str = Field("开发中", max_length=32, description="项目状态: 立项/开发中/量产/结束")
    remark: Optional[str] = Field(None, description="项目备注说明")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    platform: Optional[str] = Field(None, max_length=64)
    sop_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=32)
    remark: Optional[str] = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ========================================================
# 1.2 零件数据契约 (Part)
# ========================================================

class PartBase(BaseModel):
    part_no: str = Field(..., max_length=64, description="零件图号/物料编码")
    name: str = Field(..., max_length=128, description="零件中文名称")
    project_id: Optional[int] = Field(None, description="关联新产品项目外键ID")
    category: Optional[str] = Field(None, max_length=64, description="零件分类")
    drawing_version: str = Field("A.0", max_length=32, description="当前图纸版本")
    engineer: Optional[str] = Field(None, max_length=64, description="责任工程师")
    remark: Optional[str] = Field(None, description="零件工艺备注")


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    project_id: Optional[int] = None
    category: Optional[str] = Field(None, max_length=64)
    drawing_version: Optional[str] = Field(None, max_length=32)
    engineer: Optional[str] = Field(None, max_length=64)
    remark: Optional[str] = None


class PartOut(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
