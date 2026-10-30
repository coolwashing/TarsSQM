from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.main_data import SqmSupplier, SqmProject, SqmPart
from app.schemas.main_data import (
    PageResult,
    SupplierCreate,
    SupplierUpdate,
    SupplierOut,
    SupplierDetailOut,
    ProjectCreate,
    ProjectUpdate,
    ProjectOut,
    PartCreate,
    PartUpdate,
    PartOut
)

router = APIRouter(prefix="/api/maindata", tags=["1. MainData 主数据管理"])


# ========================================================
# 1.1 供应商接口 (Supplier CRUD)
# ========================================================

@router.get("/suppliers", response_model=PageResult[SupplierOut], summary="1.1 分页获取供应商清单")
def get_suppliers(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    supply_tier: Optional[str] = None,
    cooperation_rate: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SqmSupplier)

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SqmSupplier.code.like(kw),
                SqmSupplier.name.like(kw),
                SqmSupplier.short_name.like(kw),
                SqmSupplier.pinyin.like(kw),
                SqmSupplier.product_type.like(kw),
                SqmSupplier.city.like(kw)
            )
        )

    if status and isinstance(status, str) and status != "ALL":
        query = query.filter(SqmSupplier.status == status)

    if supply_tier and isinstance(supply_tier, str) and supply_tier != "ALL":
        query = query.filter(SqmSupplier.supply_tier == supply_tier)

    if cooperation_rate and isinstance(cooperation_rate, str) and cooperation_rate != "ALL":
        query = query.filter(SqmSupplier.cooperation_rate == cooperation_rate)

    if region and isinstance(region, str) and region != "ALL":
        query = query.filter(SqmSupplier.region == region)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    items = query.order_by(SqmSupplier.id.desc()).offset((actual_page - 1) * actual_size).limit(actual_size).all()

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/suppliers/options", summary="获取供应商去重字典选项集合")
def get_supplier_options(db: Session = Depends(get_db)):
    base_product_types = [
        "外购件-关节模组", "减速机", "结构件-手臂类", "结构件-胸腔类", "结构件-下肢类",
        "驱动板", "自研电机", "组装", "电池类", "线束类", "齿轮", "齿轮箱",
        "视触觉传感器", "摄像头", "代工", "BMS", "SMT", "充电宝", "适配器", "充电器、充电柜类产品"
    ]
    base_cities = ["上海", "苏州", "东莞", "惠州", "台州", "无锡", "常州", "深圳", "江西共青城"]
    base_quality_systems = ["IATF16949", "ISO9001", "14001 环境管理体系", "45001 职业健康安全管理体系", "50001 能源管理体系"]
    base_company_types = ["中型规模企业", "小型专精企业", "集团公司", "初创型企业", "国有企业"]
    base_supply_tiers = ["1供", "2供开发中", "在开发", "潜在供应商"]

    suppliers = db.query(SqmSupplier).all()
    product_set = set(base_product_types)
    city_set = set(base_cities)
    qs_set = set(base_quality_systems)
    ct_set = set(base_company_types)
    st_set = set(base_supply_tiers)

    for s in suppliers:
        if s.product_type:
            for item in s.product_type.replace("；", " / ").replace(",", " / ").replace("，", " / ").split(" / "):
                clean = item.strip()
                if clean: product_set.add(clean)
        if s.city:
            clean = s.city.strip()
            if clean: city_set.add(clean)
        if s.quality_system:
            for item in s.quality_system.replace("；", " / ").replace(",", " / ").split(" / "):
                clean = item.strip()
                if clean: qs_set.add(clean)
        if s.company_type:
            clean = s.company_type.strip()
            if clean: ct_set.add(clean)
        if s.supply_tier:
            clean = s.supply_tier.strip()
            if clean: st_set.add(clean)

    def sort_by_list(items, priority_list):
        p_dict = {val: i for i, val in enumerate(priority_list)}
        return sorted(list(items), key=lambda x: (p_dict.get(x, 999), x))

    return {
        "product_types": sort_by_list(product_set, base_product_types),
        "cities": sort_by_list(city_set, base_cities),
        "quality_systems": sort_by_list(qs_set, base_quality_systems),
        "company_types": sort_by_list(ct_set, base_company_types),
        "supply_tiers": sort_by_list(st_set, base_supply_tiers)
    }


@router.get("/suppliers/check-code", summary="检查供应商简称/编码唯一性")
def check_supplier_code(code: str, exclude_id: Optional[int] = None, db: Session = Depends(get_db)):
    clean_code = code.strip().upper()
    query = db.query(SqmSupplier).filter(SqmSupplier.code == clean_code)
    if exclude_id:
        query = query.filter(SqmSupplier.id != exclude_id)
    exist = query.first()
    if exist:
        return {"available": False, "message": f"供应商简称/代号 '{clean_code}' 已存在（{exist.name}），请保持唯一"}
    return {"available": True, "message": "简称代号可用"}


@router.get("/suppliers/{supplier_id}", response_model=SupplierDetailOut, summary="获取指定供应商详情")
def get_supplier_detail(supplier_id: int, db: Session = Depends(get_db)):
    sup = db.query(SqmSupplier).filter(SqmSupplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="供应商记录不存在")

    from app.models.attachment import SysAttachment
    attachments = db.query(SysAttachment).filter(
        SysAttachment.biz_type == "supplier",
        SysAttachment.biz_id == supplier_id
    ).order_by(SysAttachment.id.asc()).all()

    att_list = [
        {
            "id": a.id,
            "file_path": a.file_path,
            "original_name": a.original_name,
            "file_size": a.file_size,
            "mime_type": a.mime_type,
            "biz_type": a.biz_type,
            "biz_id": a.biz_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "url": f"/api/storage/file/{a.id}"
        }
        for a in attachments
    ]

    sup_out = SupplierOut.model_validate(sup)
    return SupplierDetailOut(
        **sup_out.model_dump(),
        attachments=att_list
    )


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED, summary="新建供应商")
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    exist = db.query(SqmSupplier).filter(SqmSupplier.code == payload.code.strip()).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"供应商编码 '{payload.code}' 已存在，不可重复新建")

    supplier_data = payload.model_dump()
    supplier_data["code"] = supplier_data["code"].strip()
    supplier_data["name"] = supplier_data["name"].strip()
    supplier = SqmSupplier(**supplier_data)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut, summary="更新供应商信息")
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    sup = db.query(SqmSupplier).filter(SqmSupplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="供应商记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(sup, key, val)

    db.commit()
    db.refresh(sup)
    return sup


@router.delete("/suppliers/{supplier_id}", summary="删除供应商")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    sup = db.query(SqmSupplier).filter(SqmSupplier.id == supplier_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="供应商记录不存在")

    db.delete(sup)
    db.commit()
    return {"status": "success", "deleted_id": supplier_id}


# ========================================================
# 1.3 项目接口 (Project CRUD)
# ========================================================

@router.get("/projects", response_model=PageResult[ProjectOut], summary="1.3 分页获取新产品项目清单")
def get_projects(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SqmProject)

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(or_(SqmProject.project_code.like(kw), SqmProject.name.like(kw), SqmProject.platform.like(kw)))

    if status and isinstance(status, str) and status != "ALL":
        query = query.filter(SqmProject.status == status)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    items = query.order_by(SqmProject.id.desc()).offset((actual_page - 1) * actual_size).limit(actual_size).all()

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/projects/options", response_model=List[ProjectOut], summary="获取全部项目下拉候选项")
def get_project_options(db: Session = Depends(get_db)):
    return db.query(SqmProject).order_by(SqmProject.project_code.asc()).all()


@router.get("/projects/{project_id}", response_model=ProjectOut, summary="获取项目详情")
def get_project_detail(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(SqmProject).filter(SqmProject.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="项目记录不存在")
    return proj


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, summary="新建新产品项目")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    exist = db.query(SqmProject).filter(SqmProject.project_code == payload.project_code.strip()).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"项目代号 '{payload.project_code}' 已存在")

    proj = SqmProject(
        project_code=payload.project_code.strip(),
        name=payload.name.strip(),
        platform=payload.platform,
        sop_date=payload.sop_date,
        status=payload.status,
        remark=payload.remark
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.put("/projects/{project_id}", response_model=ProjectOut, summary="更新项目信息")
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    proj = db.query(SqmProject).filter(SqmProject.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="项目记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(proj, key, val)

    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/projects/{project_id}", summary="删除项目")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(SqmProject).filter(SqmProject.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="项目记录不存在")

    db.delete(proj)
    db.commit()
    return {"status": "success", "deleted_id": project_id}


# ========================================================
# 1.2 零件接口 (Part CRUD with Joined Project Info)
# ========================================================

@router.get("/parts", response_model=PageResult[PartOut], summary="1.2 分页获取零件清单")
def get_parts(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SqmPart, SqmProject.project_code, SqmProject.name.label("project_name")).outerjoin(
        SqmProject, SqmPart.project_id == SqmProject.id
    )

    if keyword and isinstance(keyword, str) and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(or_(SqmPart.part_no.like(kw), SqmPart.name.like(kw)))

    if project_id and isinstance(project_id, int):
        query = query.filter(SqmPart.project_id == project_id)

    if category and isinstance(category, str) and category != "ALL":
        query = query.filter(SqmPart.category == category)

    actual_page = page if isinstance(page, int) and page >= 1 else 1
    actual_size = page_size if isinstance(page_size, int) and page_size >= 1 else 10

    total = query.count()
    rows = query.order_by(SqmPart.id.desc()).offset((actual_page - 1) * actual_size).limit(actual_size).all()

    items = []
    for part, p_code, p_name in rows:
        part_out = PartOut(
            id=part.id,
            part_no=part.part_no,
            name=part.name,
            project_id=part.project_id,
            project_code=p_code,
            project_name=p_name,
            category=part.category,
            drawing_version=part.drawing_version,
            engineer=part.engineer,
            remark=part.remark,
            created_at=part.created_at,
            updated_at=part.updated_at
        )
        items.append(part_out)

    return PageResult(
        total=total,
        items=items,
        page=actual_page,
        page_size=actual_size
    )


@router.get("/parts/{part_id}", response_model=PartOut, summary="获取零件详情")
def get_part_detail(part_id: int, db: Session = Depends(get_db)):
    row = db.query(SqmPart, SqmProject.project_code, SqmProject.name.label("project_name")).outerjoin(
        SqmProject, SqmPart.project_id == SqmProject.id
    ).filter(SqmPart.id == part_id).first()

    if not row:
        raise HTTPException(status_code=404, detail="零件记录不存在")

    part, p_code, p_name = row
    return PartOut(
        id=part.id,
        part_no=part.part_no,
        name=part.name,
        project_id=part.project_id,
        project_code=p_code,
        project_name=p_name,
        category=part.category,
        drawing_version=part.drawing_version,
        engineer=part.engineer,
        remark=part.remark,
        created_at=part.created_at,
        updated_at=part.updated_at
    )


@router.post("/parts", response_model=PartOut, status_code=status.HTTP_201_CREATED, summary="新建零件")
def create_part(payload: PartCreate, db: Session = Depends(get_db)):
    exist = db.query(SqmPart).filter(SqmPart.part_no == payload.part_no.strip()).first()
    if exist:
        raise HTTPException(status_code=400, detail=f"零件图号 '{payload.part_no}' 已存在")

    part = SqmPart(
        part_no=payload.part_no.strip(),
        name=payload.name.strip(),
        project_id=payload.project_id,
        category=payload.category,
        drawing_version=payload.drawing_version,
        engineer=payload.engineer,
        remark=payload.remark
    )
    db.add(part)
    db.commit()
    db.refresh(part)

    p_code, p_name = None, None
    if part.project_id:
        proj = db.query(SqmProject).filter(SqmProject.id == part.project_id).first()
        if proj:
            p_code, p_name = proj.project_code, proj.name

    return PartOut(
        id=part.id,
        part_no=part.part_no,
        name=part.name,
        project_id=part.project_id,
        project_code=p_code,
        project_name=p_name,
        category=part.category,
        drawing_version=part.drawing_version,
        engineer=part.engineer,
        remark=part.remark,
        created_at=part.created_at,
        updated_at=part.updated_at
    )


@router.put("/parts/{part_id}", response_model=PartOut, summary="更新零件信息")
def update_part(part_id: int, payload: PartUpdate, db: Session = Depends(get_db)):
    part = db.query(SqmPart).filter(SqmPart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="零件记录不存在")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(part, key, val)

    db.commit()
    db.refresh(part)

    p_code, p_name = None, None
    if part.project_id:
        proj = db.query(SqmProject).filter(SqmProject.id == part.project_id).first()
        if proj:
            p_code, p_name = proj.project_code, proj.name

    return PartOut(
        id=part.id,
        part_no=part.part_no,
        name=part.name,
        project_id=part.project_id,
        project_code=p_code,
        project_name=p_name,
        category=part.category,
        drawing_version=part.drawing_version,
        engineer=part.engineer,
        remark=part.remark,
        created_at=part.created_at,
        updated_at=part.updated_at
    )


@router.delete("/parts/{part_id}", summary="删除零件")
def delete_part(part_id: int, db: Session = Depends(get_db)):
    part = db.query(SqmPart).filter(SqmPart.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="零件记录不存在")

    db.delete(part)
    db.commit()
    return {"status": "success", "deleted_id": part_id}
