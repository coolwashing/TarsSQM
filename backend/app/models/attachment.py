from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class SysAttachment(Base):
    """
    通用附件元数据表
    按照 files/{biz_type}/{YYYYMM}/{uuid}.ext 动态分片统一纳管全站文件资产
    """
    __tablename__ = "sys_attachment"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="物理主键")
    file_path = Column(String(500), nullable=False, comment="动态分片相对物理路径")
    original_name = Column(String(255), nullable=False, comment="原始上传文件名")
    file_size = Column(Integer, nullable=False, default=0, comment="文件字节大小")
    mime_type = Column(String(128), nullable=False, default="application/octet-stream", comment="MIME内容类型")
    biz_type = Column(String(64), nullable=False, index=True, comment="业务域(如supplier/part/quality_issue/editor)")
    biz_id = Column(Integer, nullable=True, index=True, comment="业务外键ID(可选，支持后关联)")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="上传归档时间")

    def __repr__(self) -> str:
        return f"<SysAttachment id={self.id} biz_type={self.biz_type} name={self.original_name}>"
