from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class SqmTask(Base):
    """
    统一协同任务实体模型 (sqm_task)
    汇聚全厂多业务源头（供应商准入/零件试产/CTQ超差/规程编制/质量待办）的统一任务中枢模型
    """
    __tablename__ = "sqm_task"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    task_code = Column(String(32), unique=True, nullable=False, index=True, comment="任务流水编号, 如 TSK-202611-001")
    title = Column(String(255), nullable=False, comment="任务标题")
    description_html = Column(Text, nullable=True, comment="任务描述与验收Checklist (HTML/富文本)")

    # 状态与优先级
    status = Column(
        String(32),
        nullable=False,
        default="TODO",
        index=True,
        comment="任务流转状态: TODO / IN_PROGRESS / PENDING_REVIEW / DONE / BLOCKED"
    )
    priority = Column(
        String(16),
        nullable=False,
        default="MEDIUM",
        index=True,
        comment="优先级: LOW / MEDIUM / HIGH / URGENT"
    )

    # 多态业务源头挂钩
    source_type = Column(
        String(32),
        nullable=False,
        default="CUSTOM",
        index=True,
        comment="业务源头: SUPPLIER(供应商) / PART(零件) / CTQ(关键特性) / DOC_KB(规程知识库) / CUSTOM(自建待办)"
    )
    source_id = Column(Integer, nullable=True, index=True, comment="原业务主键ID")
    source_title = Column(String(255), nullable=True, comment="源头实体名称快照 (如 '苏州精工模具有限公司' 或 '法兰盘')")
    source_url = Column(String(255), nullable=True, comment="源头快捷回跳路由 (如 '/maindata/supplier')")

    # 人员与工期排程
    assignee_id = Column(Integer, nullable=True, index=True, comment="责任人ID")
    assignee_name = Column(String(64), nullable=True, index=True, comment="责任工程师姓名")
    creator_id = Column(Integer, nullable=True, comment="创建人ID")
    creator_name = Column(String(64), nullable=True, default="系统自动派发", comment="创建人姓名")
    start_date = Column(Date, nullable=True, comment="计划开始日期")
    due_date = Column(Date, nullable=True, index=True, comment="计划截止到期日")
    completed_at = Column(DateTime, nullable=True, comment="实际闭环交付时间")

    # 流程依赖 (DAG 拓扑与子任务)
    parent_id = Column(
        Integer,
        ForeignKey("sqm_task.id", ondelete="SET NULL"),
        nullable=True,
        comment="父任务ID"
    )
    predecessor_ids = Column(JSON, nullable=True, default=list, comment="前置依赖任务ID列表 [101, 102]")
    tags = Column(JSON, nullable=True, default=list, comment="标签池 ['PPAP试模', 'CTQ红线', '8D对策']")
    sort_order = Column(Integer, nullable=False, default=0, comment="看板/甘特排序权重")

    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # 自引用树形关系声明 (支持子任务拆解)
    parent = relationship("SqmTask", remote_side=[id], backref=backref("sub_tasks", cascade="all"))

    def __repr__(self) -> str:
        return f"<SqmTask id={self.id} code={self.task_code} status={self.status} title={self.title}>"
