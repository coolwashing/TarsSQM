from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SqmSupplier(Base):
    """
    1.1 供应商主数据表
    准入状态：潜在 / 考察 / 合格 / 冻结
    """
    __tablename__ = "sqm_supplier"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="物理主键")
    code = Column(String(64), unique=True, nullable=False, index=True, comment="供应商唯一编码")
    name = Column(String(128), nullable=False, index=True, comment="供应商中文全称")
    status = Column(String(32), nullable=False, default="潜在", index=True, comment="准入状态: 潜在/考察/合格/冻结")
    short_name = Column(String(64), nullable=True, comment="企业简称")
    pinyin = Column(String(32), nullable=True, index=True, comment="拼音缩写/标识代号")
    supply_tier = Column(String(32), nullable=True, index=True, comment="供应层级: 1供/2供开发中/在开发/潜在供应商")
    product_type = Column(String(255), nullable=True, comment="主营产品类型 (如减速机/驱动板/结构件等)")
    cooperation_rate = Column(String(16), nullable=True, comment="配合度: 高/中/低")
    quality_system = Column(String(255), nullable=True, comment="质量体系认证 (如ISO9001/IATF16949等)")
    region = Column(String(32), nullable=True, index=True, comment="所属区域: 华东/华南等")
    city = Column(String(64), nullable=True, index=True, comment="所在城市: 台州/东莞/惠州等")
    company_type = Column(String(64), nullable=True, comment="公司类型: 集团公司/中型规模/小型专精等")
    importance = Column(String(16), nullable=True, comment="重要程度: 高/中/低")
    urgency = Column(String(16), nullable=True, comment="紧急程度: 高/中/低")
    purchasing_status = Column(String(32), nullable=True, comment="采购状态: 审核通过/量产中/C样中/审核中等")
    contact = Column(String(64), nullable=True, comment="联络人姓名")
    phone = Column(String(32), nullable=True, comment="联系电话")
    email = Column(String(128), nullable=True, comment="电子邮箱")
    address = Column(String(255), nullable=True, comment="厂商办公/工厂地址")
    remark = Column(Text, nullable=True, comment="供应商资质与备忘台账")
    profile_html = Column(Text, nullable=True, comment="供应商图文详细档案/富文本")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    def __repr__(self) -> str:
        return f"<SqmSupplier id={self.id} code={self.code} name={self.name} status={self.status}>"


class SqmProject(Base):
    """
    1.3 新产品项目表
    车型/产品项目代码、开发周期阶段、量产节点（SOP）统筹
    """
    __tablename__ = "sqm_project"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="物理主键")
    project_code = Column(String(64), unique=True, nullable=False, index=True, comment="项目唯一代号")
    name = Column(String(128), nullable=False, index=True, comment="项目名称")
    platform = Column(String(64), nullable=True, comment="所属平台/车型")
    sop_date = Column(Date, nullable=True, comment="量产节点 (SOP)")
    status = Column(String(32), nullable=False, default="开发中", index=True, comment="项目状态: 立项/开发中/量产/结束")
    remark = Column(Text, nullable=True, comment="项目备注与周期概述")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关联零件反向关系
    parts = relationship("SqmPart", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SqmProject id={self.id} code={self.project_code} name={self.name}>"


class SqmPart(Base):
    """
    1.2 零件主数据表
    按项目/车型归属维护物料编码、中文名称、图纸版本及工程师责任
    """
    __tablename__ = "sqm_part"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="物理主键")
    project_id = Column(Integer, ForeignKey("sqm_project.id", ondelete="SET NULL"), nullable=True, index=True, comment="所属项目外键")
    part_no = Column(String(64), unique=True, nullable=False, index=True, comment="零件图号/物料编码")
    name = Column(String(128), nullable=False, index=True, comment="零件中文名称")
    category = Column(String(64), nullable=True, comment="零件分类(如冲压件/注塑件/紧固件/电子等)")
    drawing_version = Column(String(32), nullable=False, default="A.0", comment="图纸当前版本")
    engineer = Column(String(64), nullable=True, comment="责任工程师")
    remark = Column(Text, nullable=True, comment="零件技术要求备注")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    # 关联项目对象
    project = relationship("SqmProject", back_populates="parts")

    def __repr__(self) -> str:
        return f"<SqmPart id={self.id} part_no={self.part_no} name={self.name} version={self.drawing_version}>"
