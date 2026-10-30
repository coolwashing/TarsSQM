from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class SqmPartDev(Base):
    """
    2.1 零件开发管理实体模型 (sqm_part_dev)
    用于管理零部件与供应商的双向绑定、试制进度（OTS/工装样件/PPAP/SOP）、送样与评审状态
    """
    __tablename__ = "sqm_part_dev"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    part_id = Column(
        Integer,
        ForeignKey("sqm_part.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联零件主数据ID"
    )
    supplier_id = Column(
        Integer,
        ForeignKey("sqm_supplier.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联供应商主数据ID"
    )
    dev_phase = Column(
        String(32),
        nullable=False,
        default="OTS",
        comment="开发所处阶段: OTS/工装样件/PPAP/SOP"
    )
    status = Column(
        String(32),
        nullable=False,
        default="进行中",
        comment="当前阶段审批状态: 进行中/待评审/已批准/已冻结"
    )
    target_date = Column(Date, nullable=True, comment="当前试制阶段计划目标达成日期")
    sample_qty = Column(Integer, nullable=True, default=0, comment="送样/试制送检数量")
    responsible = Column(String(64), nullable=True, comment="SQE / 质量跟进人")
    remark = Column(Text, nullable=True, comment="阶段开发备忘与评审意见说明")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # ORM 双向关系声明
    part = relationship(
        "SqmPart",
        backref=backref("part_devs", passive_deletes=True, cascade="all, delete-orphan")
    )
    supplier = relationship(
        "SqmSupplier",
        backref=backref("part_devs", passive_deletes=True, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<SqmPartDev(id={self.id}, part_id={self.part_id}, supplier_id={self.supplier_id}, dev_phase='{self.dev_phase}', status='{self.status}')>"


class SqmQualityIssue(Base):
    """
    2.2 质量问题台账与改善管理实体模型 (sqm_quality_issue)
    用于记录零部件在试制、量产或进料阶段的质量异常，内嵌富文本缺陷现象与轻量化改善方案
    """
    __tablename__ = "sqm_quality_issue"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    issue_no = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="质量问题唯一单号 (如 QI-20261018-001)"
    )
    title = Column(String(255), nullable=False, comment="问题主题简述")
    part_id = Column(
        Integer,
        ForeignKey("sqm_part.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联零件ID (可选)"
    )
    supplier_id = Column(
        Integer,
        ForeignKey("sqm_supplier.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联供应商ID (可选)"
    )
    severity = Column(
        String(32),
        nullable=False,
        default="一般",
        comment="严重等级: 致命/严重/一般/微小"
    )
    status = Column(
        String(32),
        nullable=False,
        default="登记",
        comment="闭环处理状态: 登记/已提改善/已验证/闭环"
    )
    issue_desc = Column(Text, nullable=True, comment="质量缺陷现象描述 (支持富文本与贴图)")
    solution = Column(Text, nullable=True, comment="轻量化整改与改善措施方案 (支持富文本)")
    responsible = Column(String(64), nullable=True, comment="问题责任人 / 处理跟进人")
    occurred_date = Column(Date, nullable=True, comment="异常发生/发现日期")
    closed_date = Column(Date, nullable=True, comment="闭环解决归档日期")
    remark = Column(Text, nullable=True, comment="备忘与追溯说明")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # ORM 双向关系声明
    part = relationship("SqmPart", backref="quality_issues")
    supplier = relationship("SqmSupplier", backref="quality_issues")

    def __repr__(self):
        return f"<SqmQualityIssue(id={self.id}, issue_no='{self.issue_no}', title='{self.title}', status='{self.status}')>"
