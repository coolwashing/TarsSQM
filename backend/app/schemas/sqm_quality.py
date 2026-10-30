from datetime import date, datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.main_data import PageResult
from app.schemas.attachment import SysAttachmentOut

T = TypeVar("T")


# ========================================================
# 2.1 零件开发管理数据契约 (PartDev)
# ========================================================

class PartDevBase(BaseModel):
    part_id: int = Field(..., description="关联零件主数据ID")
    supplier_id: int = Field(..., description="关联供应商主数据ID")
    dev_phase: str = Field("OTS", max_length=32, description="开发所处阶段: OTS/工装样件/PPAP/SOP")
    status: str = Field("进行中", max_length=32, description="审批状态: 进行中/待评审/已批准/已冻结")
    target_date: Optional[date] = Field(None, description="计划目标达成日期")
    sample_qty: Optional[int] = Field(0, description="送样数量")
    responsible: Optional[str] = Field(None, max_length=64, description="责任工程师/跟进人")
    remark: Optional[str] = Field(None, description="开发说明与备忘")


class PartDevCreate(PartDevBase):
    pass


class PartDevUpdate(BaseModel):
    dev_phase: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, max_length=32)
    target_date: Optional[date] = None
    sample_qty: Optional[int] = None
    responsible: Optional[str] = Field(None, max_length=64)
    remark: Optional[str] = None


class PartDevOut(PartDevBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ========================================================
# 2.2 质量问题台账数据契约 (QualityIssue)
# ========================================================

class QualityIssueBase(BaseModel):
    issue_no: Optional[str] = Field(None, max_length=64, description="质量问题单号 (为空自动生成)")
    title: str = Field(..., max_length=255, description="问题主题简述")
    part_id: Optional[int] = Field(None, description="关联零件ID")
    supplier_id: Optional[int] = Field(None, description="关联供应商ID")
    severity: str = Field("一般", max_length=32, description="严重等级: 致命/严重/一般/微小")
    status: str = Field("登记", max_length=32, description="闭环状态: 登记/已提改善/已验证/闭环")
    issue_desc: Optional[str] = Field(None, description="质量缺陷现象描述 (HTML/文本)")
    solution: Optional[str] = Field(None, description="整改改善措施 (HTML/文本)")
    responsible: Optional[str] = Field(None, max_length=64, description="责任人")
    occurred_date: Optional[date] = Field(None, description="发生日期")
    closed_date: Optional[date] = Field(None, description="闭环日期")
    remark: Optional[str] = Field(None, description="备注")


class QualityIssueCreate(QualityIssueBase):
    pass


class QualityIssueUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    part_id: Optional[int] = None
    supplier_id: Optional[int] = None
    severity: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, max_length=32)
    issue_desc: Optional[str] = None
    solution: Optional[str] = None
    responsible: Optional[str] = Field(None, max_length=64)
    occurred_date: Optional[date] = None
    closed_date: Optional[date] = None
    remark: Optional[str] = None


class QualityIssueOut(QualityIssueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None
    attachments: List[SysAttachmentOut] = Field(default_factory=list, description="关联整改附件清单")
    created_at: datetime
    updated_at: datetime
