from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class SqmKbDoc(Base):
    """
    质量知识库与技术文档表 (单表自关联无限树形结构)
    包含富文本存储与 RAG 全文检索预留字段
    """
    __tablename__ = "sqm_kb_doc"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="物理主键")
    parent_id = Column(
        Integer,
        ForeignKey("sqm_kb_doc.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="父节点ID(NULL为根节点，自关联)"
    )
    title = Column(String(255), nullable=False, default="无标题文档", index=True, comment="文档标题")
    icon = Column(String(32), nullable=False, default="📄", comment="文档图标")
    is_folder = Column(Boolean, nullable=False, default=False, comment="是否为目录分类节点")
    sort_order = Column(Integer, nullable=False, default=0, comment="同级排序权重")
    content_html = Column(Text, nullable=True, comment="富文本HTML格式正文")
    content_text = Column(Text, nullable=True, comment="纯文本清洗正文(供RAG与全文检索)")
    biz_type = Column(String(32), nullable=True, index=True, comment="业务归属类型(如SUPPLIER/IQC/CTQ)")
    biz_id = Column(Integer, nullable=True, index=True, comment="业务关联对象ID")
    author = Column(String(64), nullable=False, default="系统管理员", comment="维护人姓名")
    is_favorite = Column(Boolean, nullable=False, default=False, comment="是否标星/收藏")
    status = Column(String(32), nullable=False, default="ACTIVE", comment="文档状态: DRAFT/REVIEW/ACTIVE/OBSOLETE")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="最后更新时间")

    # 自关联关系声明：父子树形联动与级联删除
    parent = relationship("SqmKbDoc", remote_side=[id], backref="children")

    def __repr__(self) -> str:
        return f"<SqmKbDoc id={self.id} parent_id={self.parent_id} title={self.title}>"
