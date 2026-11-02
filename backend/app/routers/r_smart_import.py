"""
AI 智能批量导入与冲突排重协同中心路由 API
支持：
- GET  /api/smart-import/schema/{biz_key}    : 获取业务实体的字段定义与唯一键
- POST /api/smart-import/pre-check/{biz_key} : 针对解析出的数据进行数据库唯一键排重预检
- POST /api/smart-import/commit/{biz_key}    : 依据冲突策略(跳过/覆盖)进行事务性批量持久化
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.common.excel_configs import get_excel_config
from app.models.main_data import SqmSupplier, SqmPart, SqmProject

router = APIRouter(
    prefix="/api/smart-import",
    tags=["AI 智能批量导入与冲突排重协同中心"]
)


@router.get("/schema/{biz_key}", summary="获取业务实体的 AI 结构定义与唯一主键")
def get_biz_schema(biz_key: str):
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的配置")

    return {
        "biz_key": biz_key,
        "title": config["title"],
        "unique_key": config.get("unique_key"),
        "fields": [
            {
                "prop": f["prop"],
                "label": f["label"],
                "required": f.get("required", False),
                "enums": f.get("enums"),
                "comment": f.get("comment"),
                "sample": f.get("sample"),
            }
            for f in config["fields"]
        ]
    }


@router.post("/pre-check/{biz_key}", summary="按唯一键预检数据库已有冲突记录")
def pre_check_duplicates(
    biz_key: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    检查一组候选题头或主键（如 code, part_no）是否已经在数据库中存在
    返回存在的 keys 列表，供前端高亮显示黄色冲突并让用户确认策略
    """
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的导入配置")

    unique_key = config.get("unique_key")
    candidate_keys: List[str] = payload.get("keys", [])
    if not unique_key or not candidate_keys:
        return {"existing_keys": [], "unique_key": unique_key}

    model_cls = config["model"]
    if not hasattr(model_cls, unique_key):
        return {"existing_keys": [], "unique_key": unique_key}

    col_attr = getattr(model_cls, unique_key)
    # 去重并清洗空值
    valid_keys = [str(k).strip() for k in candidate_keys if str(k).strip()]
    if not valid_keys:
        return {"existing_keys": [], "unique_key": unique_key}

    existing_rows = db.query(model_cls).filter(col_attr.in_(valid_keys)).all()
    # 提取实际存在的 key 集合与字段快照
    existing_keys = []
    existing_records = {}
    prop_names = [f["prop"] for f in config["fields"]]

    for r in existing_rows:
        val = getattr(r, unique_key, None)
        if val is not None:
            k_str = str(val).strip()
            existing_keys.append(k_str)
            rec_dict = {}
            for p in prop_names:
                if hasattr(r, p):
                    v = getattr(r, p)
                    rec_dict[p] = str(v) if v is not None else ""
            existing_records[k_str] = rec_dict

    return {
        "unique_key": unique_key,
        "existing_keys": existing_keys,
        "existing_records": existing_records,
        "total_checked": len(valid_keys)
    }


@router.post("/commit/{biz_key}", summary="执行智能导入与幂等批量写入")
def commit_smart_import(
    biz_key: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    接收用户确认的数据行，支持三种冲突策略：
    - 'skip'       : 库中已存在则跳过，仅插入新增记录
    - 'supplement' : 库中已存在则仅补充空缺未填字段，保护原有历史数据
    - 'overwrite'  : 库中已存在则全量按唯一键覆盖更新已有属性
    """
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的导入配置")

    rows: List[Dict[str, Any]] = payload.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="没有待入库的数据记录")

    conflict_strategy: str = payload.get("conflict_strategy", "supplement")
    unique_key = config.get("unique_key")
    model_cls = config["model"]
    valid_cols = {c.name for c in model_cls.__table__.columns}

    # 预载外键映射缓存（若 fields 中有 fk_target）
    fk_fields = [f for f in config["fields"] if f.get("fk_target")]
    fk_cache: Dict[str, Dict[str, int]] = {}
    for f in fk_fields:
        fk_target = f["fk_target"]
        if fk_target not in fk_cache:
            fk_cache[fk_target] = {}
            if fk_target == "project":
                for prj in db.query(SqmProject.id, SqmProject.project_code, SqmProject.name).all():
                    fk_cache[fk_target][prj.project_code] = prj.id
                    fk_cache[fk_target][prj.name] = prj.id
            elif fk_target == "supplier":
                for sup in db.query(SqmSupplier.id, SqmSupplier.code, SqmSupplier.name).all():
                    fk_cache[fk_target][sup.code] = sup.id
                    fk_cache[fk_target][sup.name] = sup.id
            elif fk_target == "part":
                for pt in db.query(SqmPart.id, SqmPart.part_no, SqmPart.name).all():
                    fk_cache[fk_target][pt.part_no] = pt.id
                    fk_cache[fk_target][pt.name] = pt.id

    created_count = 0
    updated_count = 0
    supplemented_count = 0
    skipped_count = 0

    try:
        # 如果存在 unique_key，先将已有记录索引出来
        existing_map = {}
        if unique_key and hasattr(model_cls, unique_key):
            col_attr = getattr(model_cls, unique_key)
            all_keys = [str(r.get(unique_key, "")).strip() for r in rows if r.get(unique_key)]
            if all_keys:
                found_records = db.query(model_cls).filter(col_attr.in_(all_keys)).all()
                for rec in found_records:
                    rec_k = str(getattr(rec, unique_key, "")).strip()
                    if rec_k:
                        existing_map[rec_k] = rec

        instances_to_add = []

        for row_data in rows:
            # 清洗字段
            clean_dict: Dict[str, Any] = {}
            for k, v in row_data.items():
                if v is not None and str(v).strip() != "":
                    clean_dict[k] = v

            # 解析外键
            for f in fk_fields:
                fk_target = f["fk_target"]
                fk_field = f["fk_field"]
                val = str(clean_dict.get(f["prop"], "")).strip()
                if val and val in fk_cache.get(fk_target, {}):
                    clean_dict[fk_field] = fk_cache[fk_target][val]

            # 仅保留数据库有效字段
            filtered_payload = {k: v for k, v in clean_dict.items() if k in valid_cols and k != "id"}

            # 业务实体特定字段智能自愈与兜底补全 (防止必填字段如 name 为空导致 IntegrityError)
            if biz_key == "supplier":
                name_val = filtered_payload.get("name")
                code_val = filtered_payload.get("code")
                short_val = filtered_payload.get("short_name")

                eff_name = name_val or short_val or code_val
                if eff_name and str(eff_name).strip() not in ("", "-"):
                    filtered_payload["name"] = str(eff_name).strip()
                    if not filtered_payload.get("short_name") or str(filtered_payload["short_name"]).strip() in ("", "-"):
                        filtered_payload["short_name"] = str(short_val or code_val or eff_name).strip()
                    if not filtered_payload.get("code") or str(filtered_payload["code"]).strip() in ("", "-"):
                        filtered_payload["code"] = str(code_val or short_val or eff_name).strip()

                if not filtered_payload.get("status") or str(filtered_payload["status"]).strip() in ("", "-"):
                    filtered_payload["status"] = "潜在"

                # 自动根据名称生成首字母拼音 (如 金晟芯 -> JSX)
                if not filtered_payload.get("pinyin") or str(filtered_payload["pinyin"]).strip() in ("", "-"):
                    base_str = filtered_payload.get("short_name") or filtered_payload.get("name") or filtered_payload.get("code") or ""
                    if base_str:
                        try:
                            import pypinyin
                            letters = pypinyin.lazy_pinyin(base_str, style=pypinyin.Style.FIRST_LETTER)
                            filtered_payload["pinyin"] = "".join(letters).upper()[:32]
                        except Exception:
                            filtered_payload["pinyin"] = base_str[:16].upper()

            elif biz_key == "project":
                if not filtered_payload.get("name") or str(filtered_payload["name"]).strip() in ("", "-"):
                    filtered_payload["name"] = filtered_payload.get("project_code") or "新建项目"
                if not filtered_payload.get("status") or str(filtered_payload["status"]).strip() in ("", "-"):
                    filtered_payload["status"] = "立项"

            elif biz_key == "task":
                if not filtered_payload.get("title") or str(filtered_payload["title"]).strip() in ("", "-"):
                    filtered_payload["title"] = filtered_payload.get("task_code") or "新建待办协同任务"
                if not filtered_payload.get("status") or str(filtered_payload["status"]).strip() in ("", "-"):
                    filtered_payload["status"] = "TODO"
                if not filtered_payload.get("priority") or str(filtered_payload["priority"]).strip() in ("", "-"):
                    filtered_payload["priority"] = "MEDIUM"
                if not filtered_payload.get("task_code") or str(filtered_payload["task_code"]).strip() in ("", "-"):
                    import datetime, random
                    filtered_payload["task_code"] = f"TSK-{datetime.datetime.now().strftime('%Y%m')}-{random.randint(100, 999)}"

            key_val = str(clean_dict.get(unique_key, "")).strip() if unique_key else None
            # 支持每行单独指定的 _conflict_action 策略覆盖全局
            row_strategy = row_data.get("_conflict_action") or conflict_strategy

            # 冲突判断
            if unique_key and key_val and key_val in existing_map:
                existing_instance = existing_map[key_val]
                if row_strategy == "overwrite":
                    for prop_k, prop_v in filtered_payload.items():
                        setattr(existing_instance, prop_k, prop_v)
                    updated_count += 1
                elif row_strategy == "supplement":
                    has_supp = False
                    for prop_k, prop_v in filtered_payload.items():
                        cur_val = getattr(existing_instance, prop_k, None)
                        # 仅当库中原有值为空或占位符时才补充
                        if cur_val is None or str(cur_val).strip() in ("", "-", "None", "null"):
                            if prop_v is not None and str(prop_v).strip() not in ("", "-"):
                                setattr(existing_instance, prop_k, prop_v)
                                has_supp = True
                    if has_supp:
                        supplemented_count += 1
                    else:
                        skipped_count += 1
                else:  # skip
                    skipped_count += 1
            else:
                # 新记录
                instances_to_add.append(model_cls(**filtered_payload))
                created_count += 1

        if instances_to_add:
            db.add_all(instances_to_add)

        db.commit()

        msg_parts = []
        if created_count > 0:
            msg_parts.append(f"新增 {created_count} 条")
        if supplemented_count > 0:
            msg_parts.append(f"补充填补 {supplemented_count} 条")
        if updated_count > 0:
            msg_parts.append(f"覆盖更新 {updated_count} 条")
        if skipped_count > 0:
            msg_parts.append(f"跳过重复 {skipped_count} 条")

        return {
            "success": True,
            "created_count": created_count,
            "supplemented_count": supplemented_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "message": f"【{config['title']}】数据处理完成: {', '.join(msg_parts) if msg_parts else '未做修改'}"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量入库失败: {str(e)}")
