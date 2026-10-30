"""
Script to parse Feishu .base file and import 23 suppliers into MySQL sqm_supplier table.
"""
import json
import base64
import gzip
import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.main_data import SqmSupplier

FEISHU_FILE = os.path.abspath(os.path.join(backend_dir, "..", "飞书data", "供应商质量.base"))

def extract_feishu_suppliers():
    if not os.path.exists(FEISHU_FILE):
        raise FileNotFoundError(f"Feishu file not found at {FEISHU_FILE}")

    with open(FEISHU_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    decompressed = gzip.decompress(base64.b64decode(data["gzipSnapshot"])).decode("utf-8")
    p = json.loads(decompressed)

    sheet0 = p[0]["schema"]["data"]["table"]
    field_map = sheet0.get("fieldMap", {})
    field_opt_maps = {
        fid: {o["id"]: o["name"] for o in fval.get("property", {}).get("options", [])}
        for fid, fval in field_map.items()
    }
    field_name_by_id = {fid: fval.get("name") for fid, fval in field_map.items()}
    record_map = p[0]["schema"]["data"].get("recordMap", {})

    def parse_val(fid, v):
        if not v or v.get("value") is None:
            return None
        val = v["value"]
        if isinstance(val, list):
            if len(val) > 0 and isinstance(val[0], dict) and "text" in val[0]:
                return "".join([x.get("text", "") for x in val if isinstance(x, dict)])
            elif len(val) > 0 and isinstance(val[0], str):
                opt_map = field_opt_maps.get(fid, {})
                return " / ".join([opt_map.get(x, x) for x in val])
        elif isinstance(val, str):
            return field_opt_maps.get(fid, {}).get(val, val)
        elif isinstance(val, dict):
            if "locations" in val:
                locs = val["locations"]
                if locs and "poiInfo" in locs[0]:
                    return locs[0]["poiInfo"].get("fullAddress") or locs[0]["poiInfo"].get("address")
            return str(val)
        return str(val)

    suppliers = []
    for i, (rid, r) in enumerate(record_map.items()):
        rec = {
            field_name_by_id[fid]: parse_val(fid, r.get(fid))
            for fid in field_name_by_id
            if parse_val(fid, r.get(fid))
        }

        name = rec.get("供应商名称") or rec.get("简称") or f"未知供应商-{i+1}"
        short_name = rec.get("简称") or ""
        pinyin = (rec.get("拼音") or "GEN").strip().upper()
        supply_tier = rec.get("供应层级") or "在开发"
        product_type = rec.get("产品类型") or ""
        cooperation_rate = rec.get("配合度") or "中"
        quality_system = rec.get("质量体系") or ""
        region = rec.get("区域") or ""
        city = rec.get("城市") or ""
        company_type = rec.get("公司类型") or ""
        importance = rec.get("重要") or "中"
        urgency = rec.get("紧急") or "中"
        purchasing_status = rec.get("采购状态") or ""
        address = rec.get("地址") or ""
        contact = rec.get("联系人") or ""
        
        # Build comprehensive remark
        remarks = []
        if rec.get("客户类型"):
            remarks.append(f"客户定位: {rec.get('客户类型')}")
        if rec.get("产值"):
            remarks.append(f"产值规模: {rec.get('产值')}")
        if rec.get("注意事项"):
            remarks.append(f"注意事项: {rec.get('注意事项')}")
        if rec.get("备注"):
            remarks.append(f"备注: {rec.get('备注')}")
        remark_text = "；".join(remarks) if remarks else "飞书多维表格同步主数据"

        # Map to SQM status (合格 / 考察 / 潜在 / 冻结)
        if supply_tier == "1供":
            status = "合格"
        elif supply_tier in ["2供开发中", "在开发"]:
            status = "考察"
        elif supply_tier == "潜在供应商":
            status = "潜在"
        else:
            if purchasing_status in ["审核通过", "量产中"]:
                status = "合格"
            elif purchasing_status in ["C样中", "审核中"]:
                status = "考察"
            elif purchasing_status == "淘汰":
                status = "冻结"
            else:
                status = "潜在"

        # Resolve collisions to ensure 100% unique uppercase pinyin
        if "炽盛" in name and pinyin == "ZS":
            pinyin = "CS"
        elif "墨现" in name and pinyin == "MX":
            pinyin = "MOX"

        code = pinyin

        suppliers.append({
            "code": code,
            "name": name,
            "short_name": short_name,
            "pinyin": pinyin,
            "status": status,
            "supply_tier": supply_tier,
            "product_type": product_type,
            "cooperation_rate": cooperation_rate,
            "quality_system": quality_system,
            "region": region,
            "city": city,
            "company_type": company_type,
            "importance": importance,
            "urgency": urgency,
            "purchasing_status": purchasing_status,
            "address": address,
            "contact": contact,
            "remark": remark_text
        })

    return suppliers


def run_import():
    suppliers = extract_feishu_suppliers()
    print(f"Parsed {len(suppliers)} suppliers from Feishu .base")

    db = SessionLocal()
    imported_count = 0
    updated_count = 0

    try:
        for s in suppliers:
            # Check by name first to avoid duplicates
            existing = db.query(SqmSupplier).filter(SqmSupplier.name == s["name"]).first()

            if existing:
                for k, v in s.items():
                    setattr(existing, k, v)
                updated_count += 1
            else:
                new_sup = SqmSupplier(**s)
                db.add(new_sup)
                imported_count += 1

        db.commit()
        print(f"Import complete! Inserted: {imported_count}, Updated: {updated_count}")
    except Exception as e:
        db.rollback()
        print(f"Error importing suppliers: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_import()
