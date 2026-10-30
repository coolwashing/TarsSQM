from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.models.sqm_quality import SqmPartDev, SqmQualityIssue
from app.models.main_data import SqmPart, SqmSupplier, SqmProject
from app.models.attachment import SysAttachment
from app.schemas.main_data import PageResult
from app.schemas.attachment import SysAttachmentOut
from app.schemas.sqm_quality import (
    PartDevCreate,
    PartDevUpdate,
    PartDevOut,
    QualityIssueCreate,
    QualityIssueUpdate,
    QualityIssueOut
)

router = APIRouter(prefix="/api/sqm", tags=["2. SQM 供应商质量管理"])


def generate_issue_no(db: Session) -> str:
    """
    自动生成规范质量问题单号: QI-YYYYMMDD-001
    """
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"QI-{today_str}-"
    last_issue = (
        db.query(SqmQualityIssue.issue_no)
        .filter(SqmQualityIssue.issue_no.like(f"{prefix}%"))
        .order_by(desc(SqmQualityIssue.id))
        .first()
    )

    if last_issue and last_issue[0]:
        try:
            seq_str = last_issue[0].replace(prefix, "")
            seq = int(seq_str) + 1
        except Exception:
            seq = 1
    else:
        seq = 1

    return f"{prefix}{seq:03d}"


# ========================================================
# 2.1 零件开发管理 (PartDev CRUD)
# ========================================================

@router.get("/part-devs", response_model=PageResult[PartDevOut], summary="2.1 分页获取零件开发看板清单")
def get_part_devs(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    dev_phase: Optional[str] = None,
    status: Optional[str] = None,
    part_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            SqmPartDev,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmSupplier.code.label("supplier_code"),
            SqmSupplier.name.label("supplier_name"),
            SqmProject.project_code,
            SqmProject.name.label("project_name")
        )
        .join(SqmPart, SqmPartDev.part_id == SqmPart.id)
        .join(SqmSupplier, SqmPartDev.supplier_id == SqmSupplier.id)
        .outerjoin(SqmProject, SqmPart.project_id == SqmProject.id)
    )

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmPart.part_no.like(kw),
                SqmPart.name.like(kw),
                SqmSupplier.code.like(kw),
                SqmSupplier.name.like(kw),
                SqmPartDev.responsible.like(kw)
            )
        )

    if dev_phase and isinstance(dev_phase, str) and dev_phase != "ALL":
        query = query.filter(SqmPartDev.dev_phase == dev_phase)

    if status and isinstance(status, str) and status != "ALL":
        query = query.filter(SqmPartDev.status == status)

    if part_id and isinstance(part_id, int):
        query = query.filter(SqmPartDev.part_id == part_id)

    if supplier_id and isinstance(supplier_id, int):
        query = query.filter(SqmPartDev.supplier_id == supplier_id)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    rows = query.order_by(SqmPartDev.id.desc()).offset((actual_page - 1) * actual_size).limit(actual_size).all()

    items = []
    for pd, p_no, p_name, s_code, s_name, prj_code, prj_name in rows:
        out = PartDevOut(
            id=pd.id,
            part_id=pd.part_id,
            supplier_id=pd.supplier_id,
            dev_phase=pd.dev_phase,
            status=pd.status,
            target_date=pd.target_date,
            sample_qty=pd.sample_qty or 0,
            responsible=pd.responsible,
            remark=pd.remark,
            part_no=p_no,
            part_name=p_name,
            supplier_code=s_code,
            supplier_name=s_name,
            project_code=prj_code,
            project_name=prj_name,
            created_at=pd.created_at,
            updated_at=pd.updated_at
        )
        items.append(out)

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/part-devs/{dev_id}", response_model=PartDevOut, summary="获取零件开发详情")
def get_part_dev_detail(dev_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(
            SqmPartDev,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmSupplier.code.label("supplier_code"),
            SqmSupplier.name.label("supplier_name"),
            SqmProject.project_code,
            SqmProject.name.label("project_name")
        )
        .join(SqmPart, SqmPartDev.part_id == SqmPart.id)
        .join(SqmSupplier, SqmPartDev.supplier_id == SqmSupplier.id)
        .outerjoin(SqmProject, SqmPart.project_id == SqmProject.id)
        .filter(SqmPartDev.id == dev_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="零件开发记录不存在")

    pd, p_no, p_name, s_code, s_name, prj_code, prj_name = row
    return PartDevOut(
        id=pd.id,
        part_id=pd.part_id,
        supplier_id=pd.supplier_id,
        dev_phase=pd.dev_phase,
        status=pd.status,
        target_date=pd.target_date,
        sample_qty=pd.sample_qty or 0,
        responsible=pd.responsible,
        remark=pd.remark,
        part_no=p_no,
        part_name=p_name,
        supplier_code=s_code,
        supplier_name=s_name,
        project_code=prj_code,
        project_name=prj_name,
        created_at=pd.created_at,
        updated_at=pd.updated_at
    )


@router.post("/part-devs", response_model=PartDevOut, status_code=status.HTTP_201_CREATED, summary="新建零件与供应商开发绑定")
def create_part_dev(payload: PartDevCreate, db: Session = Depends(get_db)):
    # 验证零件与供应商是否存在
    part = db.query(SqmPart).filter(SqmPart.id == payload.part_id).first()
    if not part:
        raise HTTPException(status_code=400, detail=f"零件ID {payload.part_id} 不存在")

    supplier = db.query(SqmSupplier).filter(SqmSupplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail=f"供应商ID {payload.supplier_id} 不存在")

    pd = SqmPartDev(
        part_id=payload.part_id,
        supplier_id=payload.supplier_id,
        dev_phase=payload.dev_phase,
        status=payload.status,
        target_date=payload.target_date,
        sample_qty=payload.sample_qty or 0,
        responsible=payload.responsible,
        remark=payload.remark
    )
    db.add(pd)
    db.commit()
    db.refresh(pd)
    return get_part_dev_detail(pd.id, db)


@router.put("/part-devs/{dev_id}", response_model=PartDevOut, summary="更新零件开发阶段与状态")
def update_part_dev(dev_id: int, payload: PartDevUpdate, db: Session = Depends(get_db)):
    pd = db.query(SqmPartDev).filter(SqmPartDev.id == dev_id).first()
    if not pd:
        raise HTTPException(status_code=404, detail="零件开发记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(pd, key, val)

    db.commit()
    db.refresh(pd)
    return get_part_dev_detail(pd.id, db)


@router.delete("/part-devs/{dev_id}", summary="删除零件开发记录")
def delete_part_dev(dev_id: int, db: Session = Depends(get_db)):
    pd = db.query(SqmPartDev).filter(SqmPartDev.id == dev_id).first()
    if not pd:
        raise HTTPException(status_code=404, detail="零件开发记录不存在")

    db.delete(pd)
    db.commit()
    return {"status": "success", "deleted_id": dev_id}


# ========================================================
# 2.2 质量问题台账 (QualityIssue CRUD)
# ========================================================

@router.get("/issues/next-no", summary="获取系统预生成的下一个问题单号")
def get_next_issue_no(db: Session = Depends(get_db)):
    return {"next_issue_no": generate_issue_no(db)}


@router.get("/issues", response_model=PageResult[QualityIssueOut], summary="2.2 分页获取质量问题台账清单")
@router.get("/quality-issues", response_model=PageResult[QualityIssueOut], include_in_schema=False)
def get_quality_issues(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    part_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            SqmQualityIssue,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmSupplier.code.label("supplier_code"),
            SqmSupplier.name.label("supplier_name")
        )
        .outerjoin(SqmPart, SqmQualityIssue.part_id == SqmPart.id)
        .outerjoin(SqmSupplier, SqmQualityIssue.supplier_id == SqmSupplier.id)
    )

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmQualityIssue.issue_no.like(kw),
                SqmQualityIssue.title.like(kw),
                SqmQualityIssue.responsible.like(kw),
                SqmPart.part_no.like(kw),
                SqmPart.name.like(kw),
                SqmSupplier.name.like(kw)
            )
        )

    if severity and isinstance(severity, str) and severity != "ALL":
        query = query.filter(SqmQualityIssue.severity == severity)

    if status and isinstance(status, str) and status != "ALL":
        query = query.filter(SqmQualityIssue.status == status)

    if part_id and isinstance(part_id, int):
        query = query.filter(SqmQualityIssue.part_id == part_id)

    if supplier_id and isinstance(supplier_id, int):
        query = query.filter(SqmQualityIssue.supplier_id == supplier_id)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    rows = query.order_by(SqmQualityIssue.id.desc()).offset((actual_page - 1) * actual_size).limit(actual_size).all()

    items = []
    for issue, p_no, p_name, s_code, s_name in rows:
        out = QualityIssueOut(
            id=issue.id,
            issue_no=issue.issue_no,
            title=issue.title,
            part_id=issue.part_id,
            supplier_id=issue.supplier_id,
            severity=issue.severity,
            status=issue.status,
            issue_desc=issue.issue_desc,
            solution=issue.solution,
            responsible=issue.responsible,
            occurred_date=issue.occurred_date,
            closed_date=issue.closed_date,
            remark=issue.remark,
            part_no=p_no,
            part_name=p_name,
            supplier_code=s_code,
            supplier_name=s_name,
            attachments=[],
            created_at=issue.created_at,
            updated_at=issue.updated_at
        )
        items.append(out)

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/issues/{issue_id}", response_model=QualityIssueOut, summary="获取质量问题详情与关联附件")
def get_quality_issue_detail(issue_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(
            SqmQualityIssue,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmSupplier.code.label("supplier_code"),
            SqmSupplier.name.label("supplier_name")
        )
        .outerjoin(SqmPart, SqmQualityIssue.part_id == SqmPart.id)
        .outerjoin(SqmSupplier, SqmQualityIssue.supplier_id == SqmSupplier.id)
        .filter(SqmQualityIssue.id == issue_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="质量问题记录不存在")

    issue, p_no, p_name, s_code, s_name = row

    # 加载已绑定的整改附件清单
    attachments = (
        db.query(SysAttachment)
        .filter(SysAttachment.biz_type == "quality_issue", SysAttachment.biz_id == issue.id)
        .order_by(SysAttachment.id.asc())
        .all()
    )

    return QualityIssueOut(
        id=issue.id,
        issue_no=issue.issue_no,
        title=issue.title,
        part_id=issue.part_id,
        supplier_id=issue.supplier_id,
        severity=issue.severity,
        status=issue.status,
        issue_desc=issue.issue_desc,
        solution=issue.solution,
        responsible=issue.responsible,
        occurred_date=issue.occurred_date,
        closed_date=issue.closed_date,
        remark=issue.remark,
        part_no=p_no,
        part_name=p_name,
        supplier_code=s_code,
        supplier_name=s_name,
        attachments=[
            SysAttachmentOut(
                id=att.id,
                file_path=att.file_path,
                original_name=att.original_name,
                file_size=att.file_size,
                mime_type=att.mime_type,
                biz_type=att.biz_type,
                biz_id=att.biz_id,
                created_at=att.created_at,
                url=f"/api/storage/file/{att.id}"
            )
            for att in attachments
        ],
        created_at=issue.created_at,
        updated_at=issue.updated_at
    )


@router.post("/issues", response_model=QualityIssueOut, status_code=status.HTTP_201_CREATED, summary="新建质量问题异常记录")
def create_quality_issue(payload: QualityIssueCreate, db: Session = Depends(get_db)):
    issue_no = payload.issue_no.strip() if payload.issue_no and payload.issue_no.strip() else generate_issue_no(db)

    # 校验单号防重复
    exist = db.query(SqmQualityIssue).filter(SqmQualityIssue.issue_no == issue_no).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"问题单号 '{issue_no}' 已存在")

    issue = SqmQualityIssue(
        issue_no=issue_no,
        title=payload.title.strip(),
        part_id=payload.part_id,
        supplier_id=payload.supplier_id,
        severity=payload.severity,
        status=payload.status,
        issue_desc=payload.issue_desc,
        solution=payload.solution,
        responsible=payload.responsible,
        occurred_date=payload.occurred_date or date.today(),
        closed_date=payload.closed_date,
        remark=payload.remark
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return get_quality_issue_detail(issue.id, db)


@router.put("/issues/{issue_id}", response_model=QualityIssueOut, summary="更新质量问题记录与改善方案")
def update_quality_issue(issue_id: int, payload: QualityIssueUpdate, db: Session = Depends(get_db)):
    issue = db.query(SqmQualityIssue).filter(SqmQualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="质量问题记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)

    # 若状态流转至闭环且未指定闭环日期，自动补全当日日期
    if update_dict.get("status") == "闭环" and not update_dict.get("closed_date") and not issue.closed_date:
        update_dict["closed_date"] = date.today()

    for key, val in update_dict.items():
        setattr(issue, key, val)

    db.commit()
    db.refresh(issue)
    return get_quality_issue_detail(issue.id, db)


@router.delete("/issues/{issue_id}", summary="删除质量问题记录")
def delete_quality_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = db.query(SqmQualityIssue).filter(SqmQualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="质量问题记录不存在")

    db.delete(issue)
    db.commit()
    return {"status": "success", "deleted_id": issue_id}
