from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.database import get_db
from app.models.sqm_mrb import SqmMrb
from app.models.main_data import SqmPart, SqmSupplier
from app.schemas.main_data import PageResult
from app.schemas.sqm_mrb import MrbCreate, MrbUpdate, MrbOut

router = APIRouter(prefix="/api/sqm/mrb", tags=["2.3 SQM MRB 审理台账"])


def generate_mrb_no(db: Session, prefix: str = "MRB") -> str:
    """
    自动生成规范 MRB 单号: MRB-YYYYMMDD-001
    """
    today_str = datetime.now().strftime("%Y%m%d")
    full_prefix = f"{prefix}-{today_str}-"
    last_record = (
        db.query(SqmMrb.mrb_no)
        .filter(SqmMrb.mrb_no.like(f"{full_prefix}%"))
        .order_by(desc(SqmMrb.id))
        .first()
    )

    if last_record and last_record[0]:
        try:
            seq_str = last_record[0].replace(full_prefix, "")
            seq = int(seq_str) + 1
        except Exception:
            seq = 1
    else:
        seq = 1

    return f"{full_prefix}{seq:03d}"


@router.get("/next-no", summary="获取系统预生成的下一个 MRB 单号")
def get_next_mrb_no(db: Session = Depends(get_db)):
    return {"next_mrb_no": generate_mrb_no(db)}


@router.get("/stats", summary="获取 MRB 台账宏观统计指标")
def get_mrb_statistics(db: Session = Depends(get_db)):
    total = db.query(func.count(SqmMrb.id)).scalar() or 0
    pending = db.query(func.count(SqmMrb.id)).filter(
        or_(SqmMrb.status == "待审理", SqmMrb.mrb_decision.in_(["待审理", None, ""]))
    ).scalar() or 0
    returned = db.query(func.count(SqmMrb.id)).filter(
        SqmMrb.mrb_decision.like("%退货%")
    ).scalar() or 0
    concession = db.query(func.count(SqmMrb.id)).filter(
        SqmMrb.mrb_decision.like("%让步%")
    ).scalar() or 0
    rework = db.query(func.count(SqmMrb.id)).filter(
        or_(SqmMrb.mrb_decision.like("%返修%"), SqmMrb.mrb_decision.like("%挑选%"))
    ).scalar() or 0
    scrap = db.query(func.count(SqmMrb.id)).filter(
        SqmMrb.mrb_decision.like("%报废%")
    ).scalar() or 0

    # 按来源分布
    source_stats = (
        db.query(SqmMrb.mrb_source, func.count(SqmMrb.id))
        .group_by(SqmMrb.mrb_source)
        .all()
    )
    source_map = {src: count for src, count in source_stats}

    return {
        "total": total,
        "pending": pending,
        "returned": returned,
        "concession": concession,
        "rework": rework,
        "scrap": scrap,
        "by_source": source_map
    }


@router.get("/list", response_model=PageResult[MrbOut], summary="分页获取 MRB 审理台账列表")
def get_mrb_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    mrb_source: Optional[str] = None,
    mrb_decision: Optional[str] = None,
    status: Optional[str] = None,
    supplier_name: Optional[str] = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SqmMrb)

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmMrb.mrb_no.like(kw),
                SqmMrb.supplier_name.like(kw),
                SqmMrb.part_no.like(kw),
                SqmMrb.part_name.like(kw),
                SqmMrb.batch_no.like(kw),
                SqmMrb.defect_desc.like(kw),
                SqmMrb.reporter.like(kw),
                SqmMrb.owner.like(kw)
            )
        )

    if mrb_source and mrb_source != "ALL":
        query = query.filter(SqmMrb.mrb_source == mrb_source)

    if mrb_decision and mrb_decision != "ALL":
        query = query.filter(SqmMrb.mrb_decision == mrb_decision)

    if status and status != "ALL":
        query = query.filter(SqmMrb.status == status)

    if supplier_name and supplier_name.strip():
        query = query.filter(SqmMrb.supplier_name.like(f"%{supplier_name.strip()}%"))

    if date_start:
        query = query.filter(SqmMrb.occurred_date >= date_start)

    if date_end:
        query = query.filter(SqmMrb.occurred_date <= date_end)

    total = query.count()
    items = (
        query.order_by(desc(SqmMrb.occurred_date), desc(SqmMrb.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PageResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{mrb_id}", response_model=MrbOut, summary="获取单个 MRB 单详情")
def get_mrb_detail(mrb_id: int, db: Session = Depends(get_db)):
    record = db.query(SqmMrb).filter(SqmMrb.id == mrb_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="MRB 记录不存在")
    return record


@router.post("", response_model=MrbOut, status_code=status.HTTP_201_CREATED, summary="登记新 MRB 审理单")
def create_mrb(payload: MrbCreate, db: Session = Depends(get_db)):
    if not payload.mrb_no or not payload.mrb_no.strip():
        payload.mrb_no = generate_mrb_no(db)

    # 查重
    existing = db.query(SqmMrb).filter(SqmMrb.mrb_no == payload.mrb_no.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"MRB 单号 [{payload.mrb_no}] 已存在，请更换或使用系统自增")

    # 自动关联供应商ID
    supp_id = payload.supplier_id
    if not supp_id and payload.supplier_name:
        supp = db.query(SqmSupplier).filter(
            or_(SqmSupplier.name == payload.supplier_name.strip(), SqmSupplier.code == payload.supplier_name.strip())
        ).first()
        if supp:
            supp_id = supp.id

    # 自动关联零件ID
    p_id = payload.part_id
    if not p_id and payload.part_no:
        part = db.query(SqmPart).filter(SqmPart.part_no == payload.part_no.strip()).first()
        if part:
            p_id = part.id

    data = payload.model_dump()
    data["supplier_id"] = supp_id
    data["part_id"] = p_id

    record = SqmMrb(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/{mrb_id}", response_model=MrbOut, summary="更新 MRB 审理单")
def update_mrb(mrb_id: int, payload: MrbUpdate, db: Session = Depends(get_db)):
    record = db.query(SqmMrb).filter(SqmMrb.id == mrb_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="MRB 记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)

    # 如果有修改供应商/零件
    if "supplier_name" in update_dict and not update_dict.get("supplier_id") and update_dict["supplier_name"]:
        supp = db.query(SqmSupplier).filter(
            or_(SqmSupplier.name == update_dict["supplier_name"].strip(), SqmSupplier.code == update_dict["supplier_name"].strip())
        ).first()
        if supp:
            update_dict["supplier_id"] = supp.id

    if "part_no" in update_dict and not update_dict.get("part_id") and update_dict["part_no"]:
        part = db.query(SqmPart).filter(SqmPart.part_no == update_dict["part_no"].strip()).first()
        if part:
            update_dict["part_id"] = part.id

    for key, val in update_dict.items():
        setattr(record, key, val)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{mrb_id}", summary="删除 MRB 审理单")
def delete_mrb(mrb_id: int, db: Session = Depends(get_db)):
    record = db.query(SqmMrb).filter(SqmMrb.id == mrb_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="MRB 记录不存在")

    db.delete(record)
    db.commit()
    return {"status": "success", "deleted_id": mrb_id, "deleted_mrb_no": record.mrb_no}
