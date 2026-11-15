from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class SqmFmeaBoard(Base):
    """
    FMEA 系统与模块视觉画板表 (sqm_fmea_board)
    承载左侧「系统分组 -> 模块画板」目录树及画布轻量空间骨架 (底图/打点Pins/极简节点/贝塞尔接口连线)
    """
    __tablename__ = "sqm_fmea_board"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    board_code = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="画板唯一编码 (如 BRD-ACT-G2)"
    )
    group_name = Column(
        String(100),
        nullable=False,
        default="未分组系统",
        index=True,
        comment="所属系统或产线分组名称 (如 关节执行器系统)"
    )
    name = Column(String(150), nullable=False, comment="模块/工序画板名称 (如 二代旋转关节模组)")
    board_type = Column(
        String(20),
        nullable=False,
        default="MIXED",
        comment="画板主导类型: DFMEA / PFMEA / MIXED"
    )
    description = Column(String(500), nullable=True, comment="模块范围或工艺边界简述")
    canvas_data = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="画布空间骨架JSON (viewport, image_boards+pins, nodes, edges)"
    )
    sort_order = Column(Integer, nullable=False, default=0, comment="同组内排序权重")
    is_archived = Column(Boolean, nullable=False, default=False, index=True, comment="是否已归档")

    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<SqmFmeaBoard id={self.id} code={self.board_code} group={self.group_name} name={self.name}>"


class SqmFmeaItem(Base):
    """
    FMEA 失效机理与防错经验卡主表 (sqm_fmea_item)
    同源驱动：画板右侧悬浮卡、失效照片图鉴墙、全局结构化台账；采用双态非硬外键软关联 (linked_refs)
    """
    __tablename__ = "sqm_fmea_item"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="自增物理主键")
    fmea_code = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="FMEA 条目唯一编码 (如 FMEA-202611-001)"
    )
    board_id = Column(
        Integer,
        ForeignKey("sqm_fmea_board.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属画板ID (允许为空以支持先记入台账后挂画板)"
    )
    target_kind = Column(
        String(20),
        nullable=False,
        default="unassigned",
        index=True,
        comment="画布挂载容器类型: pin(图纸热点) / node(模块节点) / edge(接口连线) / unassigned(未分配)"
    )
    target_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="画布内元素稳定短ID (如 pin_1 / nd_flex / ed_oil)"
    )
    target_title_snapshot = Column(
        String(150),
        nullable=True,
        comment="挂载部位名称快照 (冗余加速全局台账展示)"
    )

    fmea_type = Column(
        String(20),
        nullable=False,
        default="DFMEA",
        index=True,
        comment="经验类型: DFMEA(设计) / PFMEA(制程) / LESSON(历史教训)"
    )
    failure_mode = Column(String(255), nullable=False, comment="潜在失效模式 (核心必填)")
    failure_mech = Column(Text, nullable=True, comment="失效机理与根本原因")
    failure_effect = Column(Text, nullable=True, comment="潜在失效后果")
    control_measure = Column(Text, nullable=True, comment="综合控制措施 (历史兼容字段)")
    prevention_measure = Column(Text, nullable=True, comment="现行预防控制 (设计防错/工艺参数)")
    detection_measure = Column(Text, nullable=True, comment="现行探测控制 (检验标准/测试验证)")

    # 混合风险定级：支持一键直选 HIGH/MED/LOW，选填 S·O·D 自动精算 RPN
    risk_level = Column(
        String(16),
        nullable=False,
        default="MED",
        index=True,
        comment="风险等级: HIGH(高危) / MED(中危) / LOW(低危)"
    )
    severity = Column(Integer, nullable=True, comment="严重度 S (1-10 选填)")
    occurrence = Column(Integer, nullable=True, comment="频度 O (1-10 选填)")
    detection = Column(Integer, nullable=True, comment="探测度 D (1-10 选填)")
    rpn = Column(Integer, nullable=True, index=True, comment="风险优先数 RPN = S*O*D (选填自动计算)")

    # 实拍/标准对比照片流 (物理文件统一走 r_storage 流式存储，此处仅存 URL 与元数据)
    photos = Column(
        JSON,
        nullable=True,
        default=list,
        comment="NG失效实拍与OK防错标准图列表 [{id, attachment_id, url, tag, caption}]"
    )

    # 双态非硬外键软关联协议 (零物理外键锁死，兼容已建档短码与未建档自由标签)
    linked_refs = Column(
        JSON,
        nullable=True,
        default=list,
        comment="软关联引用数组 [{type: part/supplier/issue/project/ctq/free, ref_id, code, label}]"
    )
    ref_codes_text = Column(
        String(500),
        nullable=True,
        index=True,
        comment="关联编码与名称拼接检索索引串 (加速按零件图号/供应商码反向穿透检索)"
    )
    source_issue_no = Column(
        String(64),
        nullable=True,
        index=True,
        comment="反哺来源质量问题单号 (如 QI-20261018-001)"
    )

    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    board = relationship(
        "SqmFmeaBoard",
        backref=backref("items", passive_deletes=True)
    )

    def __repr__(self) -> str:
        return f"<SqmFmeaItem id={self.id} code={self.fmea_code} risk={self.risk_level} mode={self.failure_mode}>"

