from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.models.ctq import SqmCtq
from app.models.main_data import SqmPart, SqmProject
from app.schemas.main_data import PageResult
from app.schemas.ctq import (
    CtqCreate,
    CtqUpdate,
    CtqBatchCreate,
    CtqOut
)

router = APIRouter(prefix="/api/ctq", tags=["3. CTQ 关键质量特性"])


@router.get("", response_model=PageResult[CtqOut], summary="3.1 分页获取 CTQ 关键质量特性清单")
def get_ctq_list(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    feature_type: Optional[str] = None,
    part_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            SqmCtq,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmProject.project_code,
            SqmProject.name.label("project_name")
        )
        .join(SqmPart, SqmCtq.part_id == SqmPart.id)
        .outerjoin(SqmProject, SqmPart.project_id == SqmProject.id)
    )

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmCtq.feature_code.like(kw),
                SqmCtq.feature_name.like(kw),
                SqmPart.part_no.like(kw),
                SqmPart.name.like(kw),
                SqmCtq.inspection_tool.like(kw)
            )
        )

    if feature_type and isinstance(feature_type, str) and feature_type != "ALL":
        query = query.filter(SqmCtq.feature_type == feature_type)

    if part_id and isinstance(part_id, int):
        query = query.filter(SqmCtq.part_id == part_id)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    rows = (
        query.order_by(SqmCtq.part_id.asc(), SqmCtq.feature_type.asc(), SqmCtq.id.asc())
        .offset((actual_page - 1) * actual_size)
        .limit(actual_size)
        .all()
    )

    items = []
    for ctq, p_no, p_name, prj_code, prj_name in rows:
        out = CtqOut(
            id=ctq.id,
            part_id=ctq.part_id,
            feature_code=ctq.feature_code,
            feature_name=ctq.feature_name,
            feature_type=ctq.feature_type,
            standard_value=ctq.standard_value,
            tolerance=ctq.tolerance,
            inspection_tool=ctq.inspection_tool,
            frequency=ctq.frequency,
            control_method=ctq.control_method,
            remark=ctq.remark,
            part_no=p_no,
            part_name=p_name,
            project_code=prj_code,
            project_name=prj_name,
            created_at=ctq.created_at,
            updated_at=ctq.updated_at
        )
        items.append(out)

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/by-part/{part_id}", response_model=List[CtqOut], summary="获取指定零件的全部 CTQ 特征清单")
def get_ctq_by_part(part_id: int, db: Session = Depends(get_db)):
    part = db.query(SqmPart).filter(SqmPart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail=f"零件ID {part_id} 不存在")

    p_proj = db.query(SqmProject).filter(SqmProject.id == part.project_id).first() if part.project_id else None

    rows = (
        db.query(SqmCtq)
        .filter(SqmCtq.part_id == part_id)
        .order_by(SqmCtq.feature_type.asc(), SqmCtq.feature_code.asc())
        .all()
    )

    return [
        CtqOut(
            id=ctq.id,
            part_id=ctq.part_id,
            feature_code=ctq.feature_code,
            feature_name=ctq.feature_name,
            feature_type=ctq.feature_type,
            standard_value=ctq.standard_value,
            tolerance=ctq.tolerance,
            inspection_tool=ctq.inspection_tool,
            frequency=ctq.frequency,
            control_method=ctq.control_method,
            remark=ctq.remark,
            part_no=part.part_no,
            part_name=part.name,
            project_code=p_proj.project_code if p_proj else None,
            project_name=p_proj.name if p_proj else None,
            created_at=ctq.created_at,
            updated_at=ctq.updated_at
        )
        for ctq in rows
    ]


@router.get("/{ctq_id}", response_model=CtqOut, summary="获取单个 CTQ 特征详情")
def get_ctq_detail(ctq_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(
            SqmCtq,
            SqmPart.part_no,
            SqmPart.name.label("part_name"),
            SqmProject.project_code,
            SqmProject.name.label("project_name")
        )
        .join(SqmPart, SqmCtq.part_id == SqmPart.id)
        .outerjoin(SqmProject, SqmPart.project_id == SqmProject.id)
        .filter(SqmCtq.id == ctq_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="CTQ 关键特性记录不存在")

    ctq, p_no, p_name, prj_code, prj_name = row
    return CtqOut(
        id=ctq.id,
        part_id=ctq.part_id,
        feature_code=ctq.feature_code,
        feature_name=ctq.feature_name,
        feature_type=ctq.feature_type,
        standard_value=ctq.standard_value,
        tolerance=ctq.tolerance,
        inspection_tool=ctq.inspection_tool,
        frequency=ctq.frequency,
        control_method=ctq.control_method,
        remark=ctq.remark,
        part_no=p_no,
        part_name=p_name,
        project_code=prj_code,
        project_name=prj_name,
        created_at=ctq.created_at,
        updated_at=ctq.updated_at
    )


@router.post("", response_model=CtqOut, status_code=status.HTTP_201_CREATED, summary="新建 CTQ 关键质量特性")
def create_ctq(payload: CtqCreate, db: Session = Depends(get_db)):
    part = db.query(SqmPart).filter(SqmPart.id == payload.part_id).first()
    if not part:
        raise HTTPException(status_code=400, detail=f"关联零件ID {payload.part_id} 不存在")

    ctq = SqmCtq(
        part_id=payload.part_id,
        feature_code=payload.feature_code.strip(),
        feature_name=payload.feature_name.strip(),
        feature_type=payload.feature_type,
        standard_value=payload.standard_value,
        tolerance=payload.tolerance.strip(),
        inspection_tool=payload.inspection_tool,
        frequency=payload.frequency,
        control_method=payload.control_method,
        remark=payload.remark
    )
    db.add(ctq)
    db.commit()
    db.refresh(ctq)
    return get_ctq_detail(ctq.id, db)


@router.post("/batch", summary="批量录入/更新零件 CTQ 特性")
def batch_create_ctq(payload: CtqBatchCreate, db: Session = Depends(get_db)):
    part = db.query(SqmPart).filter(SqmPart.id == payload.part_id).first()
    if not part:
        raise HTTPException(status_code=400, detail=f"关联零件ID {payload.part_id} 不存在")

    created_ids = []
    for item in payload.items:
        ctq = SqmCtq(
            part_id=payload.part_id,
            feature_code=item.feature_code.strip(),
            feature_name=item.feature_name.strip(),
            feature_type=item.feature_type,
            standard_value=item.standard_value,
            tolerance=item.tolerance.strip(),
            inspection_tool=item.inspection_tool,
            frequency=item.frequency,
            control_method=item.control_method,
            remark=item.remark
        )
        db.add(ctq)
        db.flush()
        created_ids.append(ctq.id)

    db.commit()
    return {"status": "success", "count": len(created_ids), "ids": created_ids}


@router.put("/{ctq_id}", response_model=CtqOut, summary="更新 CTQ 关键特性")
def update_ctq(ctq_id: int, payload: CtqUpdate, db: Session = Depends(get_db)):
    ctq = db.query(SqmCtq).filter(SqmCtq.id == ctq_id).first()
    if not ctq:
        raise HTTPException(status_code=404, detail="CTQ 关键特性记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(ctq, key, val)

    db.commit()
    db.refresh(ctq)
    return get_ctq_detail(ctq.id, db)


@router.delete("/{ctq_id}", summary="删除 CTQ 关键特性")
def delete_ctq(ctq_id: int, db: Session = Depends(get_db)):
    ctq = db.query(SqmCtq).filter(SqmCtq.id == ctq_id).first()
    if not ctq:
        raise HTTPException(status_code=404, detail="CTQ 关键特性记录不存在")

    db.delete(ctq)
    db.commit()
    return {"status": "success", "deleted_id": ctq_id}
