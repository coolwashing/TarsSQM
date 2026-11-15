"""
2.3 MRB 审理台账实体模型 (sqm_mrb)
用于统一纳管 IQC 来料、制程装配、研发试制、客诉等全业务场景的物料评审与处置闭环
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SqmMrb(Base):
    __tablename__ = "sqm_mrb"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    mrb_no = Column(String(64), unique=True, nullable=False, index=True, comment="MRB唯一单号 (如 MRB20261026628)")
    mrb_source = Column(String(32), nullable=False, default="IQC来料", index=True, comment="来源环节: IQC来料/制程装配/研发试制/售后客诉")

    # 溯源信息
    occurred_date = Column(Date, nullable=True, index=True, comment="发生/送检/发现日期")
    inspection_month = Column(String(16), nullable=True, comment="检验月份 (如 2026-09)")
    supplier_name = Column(String(128), nullable=True, index=True, comment="供应商名称")
    supplier_id = Column(Integer, ForeignKey("sqm_supplier.id", ondelete="SET NULL"), nullable=True, index=True, comment="关联供应商ID")
    material_type = Column(String(64), nullable=True, comment="物料类型 (机械/电子等)")
    part_no = Column(String(64), nullable=True, index=True, comment="物料编码/零件图号")
    part_id = Column(Integer, ForeignKey("sqm_part.id", ondelete="SET NULL"), nullable=True, index=True, comment="关联零件ID")
    part_name = Column(String(255), nullable=True, comment="物料名称(型号)")
    version = Column(String(32), nullable=True, comment="版本号")
    batch_no = Column(String(64), nullable=True, comment="批次号/来料批次")

    # 不良事实与数量
    batch_qty = Column(Integer, nullable=True, default=0, comment="批次/送检数量")
    sample_qty = Column(Integer, nullable=True, default=0, comment="抽样/检验数量")
    defect_qty = Column(Integer, nullable=False, default=1, comment="不合格品数量")
    pass_qty = Column(Integer, nullable=True, default=0, comment="合格数量")
    defect_rate = Column(String(32), nullable=True, comment="不良率 (如 100.00%)")
    defect_type = Column(String(64), nullable=True, comment="不合格类型 (严重不合格/轻微不合格等)")
    defect_desc = Column(Text, nullable=True, comment="不合格描述/缺陷现象")
    attachments = Column(JSON, nullable=True, comment="缺陷照片/视频/附件文件名列表")

    # 审理处置与责任判定
    mrb_decision = Column(String(64), nullable=True, index=True, comment="MRB审理意见/最终判定 (退货/让步/内部返修/报废/挑选)")
    duty_attribution = Column(String(64), nullable=True, comment="责任归属 (供应商责任/生产责任/研发责任/待定)")
    reporter = Column(String(64), nullable=True, comment="反馈人/检验员")
    owner = Column(String(64), nullable=True, comment="物料归属人/责任工程师")

    # 改善与8D跟踪
    has_supplier_report = Column(String(16), nullable=True, default="无", comment="有无供应商报告 (有/无)")
    root_cause = Column(Text, nullable=True, comment="根本原因分析")
    immediate_action = Column(Text, nullable=True, comment="临时措施")
    long_term_action = Column(Text, nullable=True, comment="长期对策/改善方案")
    action_verification = Column(Text, nullable=True, comment="措施验证")
    status = Column(String(32), nullable=False, default="待审理", index=True, comment="闭环状态: 待审理/改善中/已验证/已结案")
    is_closed = Column(String(16), nullable=True, default="否", comment="是否结案 (是/否)")

    # 扩展属性与追溯
    remark = Column(Text, nullable=True, comment="备注说明")
    extra_attrs = Column(JSON, nullable=True, comment="业务来源专有扩展属性 (如 机台号、AQL标准、检验依据、检验记录ID等)")

    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    supplier = relationship("SqmSupplier", backref="mrb_records")
    part = relationship("SqmPart", backref="mrb_records")

    def __repr__(self):
        return f"<SqmMrb(id={self.id}, mrb_no='{self.mrb_no}', source='{self.mrb_source}', decision='{self.mrb_decision}')>"
