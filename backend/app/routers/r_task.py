import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.core.database import get_db, Base, engine
from app.models.task import SqmTask
from app.models.attachment import SysAttachment
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskDateUpdate,
    TaskOut,
    TaskDetailOut,
    TaskSummaryStats,
    TaskPageResult
)

router = APIRouter(prefix="/api/tasks", tags=["协同任务中心引擎"])

# 确保数据表自动迁移就绪
Base.metadata.create_all(bind=engine)


def generate_task_code(db: Session) -> str:
    """生成形如 TSK-202611-001 的全局唯一顺序任务流水号"""
    prefix = datetime.now().strftime("TSK-%Y%m-")
    last_task = (
        db.query(SqmTask)
        .filter(SqmTask.task_code.like(f"{prefix}%"))
        .order_by(SqmTask.id.desc())
        .first()
    )
    if not last_task or not last_task.task_code:
        return f"{prefix}001"
    try:
        last_num = int(last_task.task_code.split("-")[-1])
        return f"{prefix}{str(last_num + 1).padStart(3, '0') if hasattr(str(last_num + 1), 'padStart') else str(last_num + 1).zfill(3)}"
    except Exception:
        return f"{prefix}{uuid.uuid4().hex[:4].upper()}"


@router.get("/stats/summary", response_model=TaskSummaryStats, summary="获取任务全局统计指标")
def get_task_summary_stats(db: Session = Depends(get_db)):
    """返回任务中心顶部数据徽标统计"""
    tasks = db.query(SqmTask).all()
    today = date.today()

    stats = TaskSummaryStats()
    stats.total = len(tasks)
    for t in tasks:
        if t.status == "TODO":
            stats.todo += 1
        elif t.status == "IN_PROGRESS":
            stats.in_progress += 1
        elif t.status == "PENDING_REVIEW":
            stats.pending_review += 1
        elif t.status == "DONE":
            stats.done += 1
        elif t.status == "BLOCKED":
            stats.blocked += 1

        if t.due_date and t.due_date < today and t.status != "DONE":
            stats.overdue += 1

    return stats


@router.get("", response_model=TaskPageResult, summary="多维过滤分页查询总任务池")
def list_tasks(
    keyword: Optional[str] = Query(None, description="任务标题、编码或源头名称模糊检索"),
    source_type: Optional[str] = Query(None, description="业务源头切片 (SUPPLIER/PART/CTQ/DOC_KB/CUSTOM)"),
    source_id: Optional[str] = Query(None, description="业务源头主键ID"),
    status: Optional[str] = Query(None, description="任务状态 (TODO/IN_PROGRESS/PENDING_REVIEW/DONE/BLOCKED)"),
    priority: Optional[str] = Query(None, description="优先级 (LOW/MEDIUM/HIGH/URGENT)"),
    assignee_id: Optional[int] = Query(None, description="责任人ID"),
    due_filter: Optional[str] = Query(None, description="到期日快捷过滤: all/today/this_week/overdue"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(SqmTask)

    if keyword:
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmTask.title.ilike(kw),
                SqmTask.task_code.ilike(kw),
                SqmTask.source_title.ilike(kw),
                SqmTask.assignee_name.ilike(kw)
            )
        )

    if source_type and source_type != "ALL":
        query = query.filter(SqmTask.source_type == source_type)

    if source_id:
        query = query.filter(SqmTask.source_id == str(source_id))

    if status and status != "ALL":
        query = query.filter(SqmTask.status == status)

    if priority and priority != "ALL":
        query = query.filter(SqmTask.priority == priority)

    if assignee_id:
        query = query.filter(SqmTask.assignee_id == assignee_id)

    today = date.today()
    if due_filter == "today":
        query = query.filter(SqmTask.due_date == today)
    elif due_filter == "this_week":
        end_of_week = today + timedelta(days=(6 - today.weekday()))
        query = query.filter(and_(SqmTask.due_date >= today, SqmTask.due_date <= end_of_week))
    elif due_filter == "overdue":
        query = query.filter(and_(SqmTask.due_date < today, SqmTask.status != "DONE"))

    total = query.count()
    items = (
        query.order_by(
            SqmTask.sort_order.asc(),
            SqmTask.due_date.asc(),
            SqmTask.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 聚合每个任务的附件数量与超期标识
    result_items = []
    task_ids = [t.id for t in items]
    attachment_counts = {}
    if task_ids:
        counts = (
            db.query(SysAttachment.biz_id, func.count(SysAttachment.id))
            .filter(SysAttachment.biz_type == "task", SysAttachment.biz_id.in_(task_ids))
            .group_by(SysAttachment.biz_id)
            .all()
        )
        attachment_counts = {cid: cnt for cid, cnt in counts}

    for t in items:
        out = TaskOut.model_validate(t)
        out.is_overdue = bool(t.due_date and t.due_date < today and t.status != "DONE")
        out.attachment_count = attachment_counts.get(t.id, 0)
        result_items.append(out)

    return TaskPageResult(total=total, items=result_items)


@router.get("/by-source/{source_type}/{source_id}", response_model=List[TaskOut], summary="获取指定业务对象的关联任务")
def get_tasks_by_source(
    source_type: str,
    source_id: str,
    db: Session = Depends(get_db)
):
    """供供应商详情/零件详情等子组件快捷调用"""
    tasks = (
        db.query(SqmTask)
        .filter(SqmTask.source_type == source_type, SqmTask.source_id == str(source_id))
        .order_by(SqmTask.id.desc())
        .all()
    )
    today = date.today()
    result = []
    for t in tasks:
        out = TaskOut.model_validate(t)
        out.is_overdue = bool(t.due_date and t.due_date < today and t.status != "DONE")
        result.append(out)
    return result


@router.get("/{task_id}", response_model=TaskDetailOut, summary="获取任务详情与附件")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.query(SqmTask).filter(SqmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    attachments = (
        db.query(SysAttachment)
        .filter(SysAttachment.biz_type == "task", SysAttachment.biz_id == task_id)
        .order_by(SysAttachment.id.desc())
        .all()
    )

    today = date.today()
    out = TaskDetailOut.model_validate(task)
    out.is_overdue = bool(task.due_date and task.due_date < today and task.status != "DONE")
    out.attachment_count = len(attachments)
    out.attachments = attachments
    return out


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="创建新协同任务")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("task_code"):
        data["task_code"] = generate_task_code(db)

    task = SqmTask(**data)
    db.add(task)
    db.commit()
    db.refresh(task)

    out = TaskOut.model_validate(task)
    return out


@router.put("/{task_id}", response_model=TaskOut, summary="更新任务属性")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(SqmTask).filter(SqmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    if "status" in update_dict and update_dict["status"] == "DONE" and not task.completed_at:
        update_dict["completed_at"] = datetime.now()
    elif "status" in update_dict and update_dict["status"] != "DONE":
        update_dict["completed_at"] = None

    for k, v in update_dict.items():
        setattr(task, k, v)

    db.commit()
    db.refresh(task)
    out = TaskOut.model_validate(task)
    return out


@router.patch("/{task_id}/status", response_model=TaskOut, summary="跨泳道/快捷流转任务状态")
def update_task_status(task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db)):
    task = db.query(SqmTask).filter(SqmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.status = payload.status
    if payload.status == "DONE":
        task.completed_at = datetime.now()
    else:
        task.completed_at = None

    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.patch("/{task_id}/dates", response_model=TaskOut, summary="日历/甘特视图拖拽调整排期")
def update_task_dates(task_id: int, payload: TaskDateUpdate, db: Session = Depends(get_db)):
    task = db.query(SqmTask).filter(SqmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if payload.start_date is not None:
        task.start_date = payload.start_date
    if payload.due_date is not None:
        task.due_date = payload.due_date

    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除任务")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(SqmTask).filter(SqmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    db.delete(task)
    db.commit()
    return None


@router.post("/seed-demo", summary="初始化预置制造协同演示任务")
def seed_demo_tasks(db: Session = Depends(get_db)):
    """若任务库为空，则预置涵盖供应商/零件/CTQ/规程的实战仿真任务"""
    if db.query(SqmTask).count() > 0:
        return {"message": "任务库已有数据，跳过预置", "seeded": False}

    today = date.today()
    demo_tasks = [
        {
            "task_code": "TSK-202611-001",
            "title": "年度供应商现场质量体系审计整改 (IATF 16949)",
            "description_html": "<p>针对上周在<strong>苏州精工模具有限公司</strong>现场审核中发现的 3 项一般不合格项，跟进纠正预防对策表 (CAPA)。</p><ul data-type=\"taskList\"><li data-checked=\"true\">整改报告初审</li><li data-checked=\"true\">现场飞检二次验证</li><li data-checked=\"false\">关闭审核整改单</li></ul>",
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "source_type": "SUPPLIER",
            "source_id": 1,
            "source_title": "苏州精工模具有限公司",
            "source_url": "/maindata/supplier",
            "assignee_name": "张工 (SQE)",
            "start_date": today - timedelta(days=3),
            "due_date": today + timedelta(days=2),
            "tags": ["供应商审核", "CAPA整改", "IATF16949"]
        },
        {
            "task_code": "TSK-202611-002",
            "title": "法兰盘主驱动轴 PPAP 送样试产首件检测 (FAI)",
            "description_html": "<p>零件号 <code>P-2026-009</code> 工装样件三坐标全尺寸检测与材料力学性能测试。</p><ul data-type=\"taskList\"><li data-checked=\"true\">三坐标全尺寸实测表提交</li><li data-checked=\"false\">Cpk 过程能力评价报告 ≥ 1.33</li><li data-checked=\"false\">PPAP PSW 质量签样</li></ul>",
            "status": "TODO",
            "priority": "URGENT",
            "source_type": "PART",
            "source_id": 1,
            "source_title": "法兰盘主驱动轴",
            "source_url": "/maindata/part",
            "assignee_name": "李工 (零件工程师)",
            "start_date": today,
            "due_date": today + timedelta(days=5),
            "tags": ["PPAP试产", "三坐标FAI", "高风险"]
        },
        {
            "task_code": "TSK-202611-003",
            "title": "CTQ-01 外径公差连续 3 点超差红线遏制与 SPC 溯源",
            "description_html": "<p>冲压工序关键质量特性 CTQ-01 外径出现 +0.025mm 上限漂移，启动临时质量遏制与模具磨损排查。</p>",
            "status": "IN_PROGRESS",
            "priority": "URGENT",
            "source_type": "CTQ",
            "source_id": 1,
            "source_title": "CTQ-01 法兰盘外径尺寸",
            "source_url": "/ctq/list",
            "assignee_name": "王工 (工艺质量)",
            "start_date": today - timedelta(days=1),
            "due_date": today + timedelta(days=1),
            "tags": ["CTQ红线", "SPC失控", "8D对策"]
        },
        {
            "task_code": "TSK-202611-004",
            "title": "2026 第四季度精密零件出厂检验规程发布复审",
            "description_html": "<p>对知识库中的《SQM 协同任务中心：架构目标与开发计划》第 5 章技术规程进行工程评审会签。</p>",
            "status": "PENDING_REVIEW",
            "priority": "MEDIUM",
            "source_type": "DOC_KB",
            "source_id": 9,
            "source_title": "SQM 协同任务中心架构设计",
            "source_url": "/kb/editor/9",
            "assignee_name": "赵工 (质量部经理)",
            "start_date": today - timedelta(days=5),
            "due_date": today + timedelta(days=3),
            "tags": ["规程评审", "体系发布"]
        },
        {
            "task_code": "TSK-202611-005",
            "title": "注塑模具 T1 试模飞边缺陷 8D 根本原因对策编写",
            "description_html": "<p>已查明模具分型面合模力不足，已完成排气槽加宽修正，待封样。</p>",
            "status": "DONE",
            "priority": "MEDIUM",
            "source_type": "PART",
            "source_id": 2,
            "source_title": "电控外壳前盖",
            "source_url": "/maindata/part",
            "assignee_name": "刘工 (SQE)",
            "start_date": today - timedelta(days=8),
            "due_date": today - timedelta(days=2),
            "completed_at": datetime.now() - timedelta(days=1),
            "tags": ["8D闭环", "模具修模"]
        }
    ]

    for item in demo_tasks:
        db.add(SqmTask(**item))
    db.commit()

    return {"message": "已成功预置 5 条协同任务仿真数据", "seeded": True, "count": len(demo_tasks)}
