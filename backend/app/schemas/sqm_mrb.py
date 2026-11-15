from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.main_data import PageResult


class MrbBase(BaseModel):
    mrb_no: Optional[str] = Field(None, max_length=64, description="MRB单号 (为空自动生成)")
    mrb_source: str = Field("IQC来料", max_length=32, description="来源环节: IQC来料/制程装配/研发试制/售后客诉")
    occurred_date: Optional[date] = Field(None, description="发生/送检/发现日期")
    inspection_month: Optional[str] = Field(None, max_length=16, description="检验月份")
    supplier_name: Optional[str] = Field(None, max_length=128, description="供应商名称")
    supplier_id: Optional[int] = Field(None, description="关联供应商ID")
    material_type: Optional[str] = Field(None, max_length=64, description="物料类型")
    part_no: Optional[str] = Field(None, max_length=64, description="物料编码/零件图号")
    part_id: Optional[int] = Field(None, description="关联零件ID")
    part_name: Optional[str] = Field(None, max_length=255, description="物料名称(型号)")
    version: Optional[str] = Field(None, max_length=32, description="版本号")
    batch_no: Optional[str] = Field(None, max_length=64, description="批次号/来料批次")
    batch_qty: Optional[int] = Field(0, description="批次/送检数量")
    sample_qty: Optional[int] = Field(0, description="抽样/检验数量")
    defect_qty: int = Field(1, description="不合格品数量")
    pass_qty: Optional[int] = Field(0, description="合格数量")
    defect_rate: Optional[str] = Field(None, max_length=32, description="不良率")
    defect_type: Optional[str] = Field(None, max_length=64, description="不合格类型")
    defect_desc: Optional[str] = Field(None, description="不合格描述/缺陷现象")
    attachments: Optional[Any] = Field(None, description="缺陷照片/视频/附件文件名列表")
    mrb_decision: Optional[str] = Field("待审理", max_length=64, description="MRB审理意见/最终判定")
    duty_attribution: Optional[str] = Field(None, max_length=64, description="责任归属")
    reporter: Optional[str] = Field(None, max_length=64, description="反馈人/检验员")
    owner: Optional[str] = Field(None, max_length=64, description="物料归属人/责任工程师")
    has_supplier_report: Optional[str] = Field("无", max_length=16, description="有无供应商报告")
    root_cause: Optional[str] = Field(None, description="根本原因分析")
    immediate_action: Optional[str] = Field(None, description="临时措施")
    long_term_action: Optional[str] = Field(None, description="长期对策")
    action_verification: Optional[str] = Field(None, description="措施验证")
    status: str = Field("待审理", max_length=32, description="闭环状态: 待审理/改善中/已验证/已结案")
    is_closed: Optional[str] = Field("否", max_length=16, description="是否结案")
    remark: Optional[str] = Field(None, description="备注说明")
    extra_attrs: Optional[Any] = Field(None, description="来源专有扩展属性")


class MrbCreate(MrbBase):
    pass


class MrbUpdate(BaseModel):
    mrb_source: Optional[str] = Field(None, max_length=32)
    occurred_date: Optional[date] = None
    inspection_month: Optional[str] = Field(None, max_length=16)
    supplier_name: Optional[str] = Field(None, max_length=128)
    supplier_id: Optional[int] = None
    material_type: Optional[str] = Field(None, max_length=64)
    part_no: Optional[str] = Field(None, max_length=64)
    part_id: Optional[int] = None
    part_name: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=32)
    batch_no: Optional[str] = Field(None, max_length=64)
    batch_qty: Optional[int] = None
    sample_qty: Optional[int] = None
    defect_qty: Optional[int] = None
    pass_qty: Optional[int] = None
    defect_rate: Optional[str] = Field(None, max_length=32)
    defect_type: Optional[str] = Field(None, max_length=64)
    defect_desc: Optional[str] = None
    attachments: Optional[Any] = None
    mrb_decision: Optional[str] = Field(None, max_length=64)
    duty_attribution: Optional[str] = Field(None, max_length=64)
    reporter: Optional[str] = Field(None, max_length=64)
    owner: Optional[str] = Field(None, max_length=64)
    has_supplier_report: Optional[str] = Field(None, max_length=16)
    root_cause: Optional[str] = None
    immediate_action: Optional[str] = None
    long_term_action: Optional[str] = None
    action_verification: Optional[str] = None
    status: Optional[str] = Field(None, max_length=32)
    is_closed: Optional[str] = Field(None, max_length=16)
    remark: Optional[str] = None
    extra_attrs: Optional[Any] = None


class MrbOut(MrbBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
