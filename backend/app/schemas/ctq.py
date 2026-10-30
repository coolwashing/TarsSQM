from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.main_data import PageResult


class CtqBase(BaseModel):
    part_id: int = Field(..., description="关联零件物料ID")
    feature_code: str = Field(..., max_length=64, description="关键特征代号 (如 KPC-01, CC-02)")
    feature_name: str = Field(..., max_length=128, description="特性中文名称")
    feature_type: str = Field("KPC", max_length=32, description="特性类别: KPC(产品关键特性) / KCC(过程关键特性)")
    standard_value: Optional[str] = Field(None, max_length=64, description="标称值 (如 45.00mm)")
    tolerance: str = Field(..., max_length=128, description="控制规格与公差要求 (如 +0.02/-0.01mm)")
    inspection_tool: Optional[str] = Field(None, max_length=64, description="测量检验量具")
    frequency: str = Field("首末件+每批5件", max_length=64, description="检验频次与抽检规则")
    control_method: Optional[str] = Field(None, max_length=128, description="控制方法 (如 SPC控制图)")
    remark: Optional[str] = Field(None, description="工程备忘说明")


class CtqCreate(CtqBase):
    pass


class CtqUpdate(BaseModel):
    feature_code: Optional[str] = Field(None, max_length=64)
    feature_name: Optional[str] = Field(None, max_length=128)
    feature_type: Optional[str] = Field(None, max_length=32)
    standard_value: Optional[str] = Field(None, max_length=64)
    tolerance: Optional[str] = Field(None, max_length=128)
    inspection_tool: Optional[str] = Field(None, max_length=64)
    frequency: Optional[str] = Field(None, max_length=64)
    control_method: Optional[str] = Field(None, max_length=128)
    remark: Optional[str] = None


class CtqBatchItem(BaseModel):
    feature_code: str = Field(..., max_length=64)
    feature_name: str = Field(..., max_length=128)
    feature_type: str = Field("KPC", max_length=32)
    standard_value: Optional[str] = None
    tolerance: str = Field(..., max_length=128)
    inspection_tool: Optional[str] = None
    frequency: str = Field("首末件+每批5件", max_length=64)
    control_method: Optional[str] = None
    remark: Optional[str] = None


class CtqBatchCreate(BaseModel):
    part_id: int
    items: List[CtqBatchItem]


class CtqOut(CtqBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
