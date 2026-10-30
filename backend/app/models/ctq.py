from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class SqmCtq(Base):
    """
    3.1 CTQ 关键质量特性实体模型 (sqm_ctq)
    用于管理零部件的关键产品特性(KPC)与关键过程特性(KCC)、公差要求、量具与检验频次
    """
    __tablename__ = "sqm_ctq"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    part_id = Column(
        Integer,
        ForeignKey("sqm_part.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联零件主数据ID"
    )
    feature_code = Column(
        String(64),
        nullable=False,
        index=True,
        comment="关键特征代号 (如 KPC-01, CC-03, CTQ-DIM-01)"
    )
    feature_name = Column(
        String(128),
        nullable=False,
        comment="特性名称 (如 安装法兰止口外圆直径, 齿圈齿面淬火硬度)"
    )
    feature_type = Column(
        String(32),
        nullable=False,
        default="KPC",
        comment="特性类别: KPC(产品关键特性) / KCC(过程关键特性)"
    )
    standard_value = Column(
        String(64),
        nullable=True,
        comment="标称标准值/名义规格 (如 45.00mm, 58-62 HRC)"
    )
    tolerance = Column(
        String(128),
        nullable=False,
        comment="规格要求与公差区间 (如 +0.02/-0.01mm, >=58HRC)"
    )
    inspection_tool = Column(
        String(64),
        nullable=True,
        comment="测量仪器与量具 (如 三坐标CMM, 外径千分尺, 洛氏硬度计)"
    )
    frequency = Column(
        String(64),
        nullable=False,
        default="首末件+每批5件",
        comment="检测频次与抽样规则 (如 100%全检, 1次/2小时, 首末件+抽检5件)"
    )
    control_method = Column(
        String(128),
        nullable=True,
        comment="质量控制方法与反应计划 (如 SPC控制图, 停机报警防错)"
    )
    remark = Column(Text, nullable=True, comment="质量控制备忘说明")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # ORM 关联关系
    part = relationship(
        "SqmPart",
        backref=backref("ctqs", passive_deletes=True, cascade="all, delete-orphan")
    )

    def __repr__(self):
        return f"<SqmCtq(id={self.id}, part_id={self.part_id}, code='{self.feature_code}', type='{self.feature_type}')>"
