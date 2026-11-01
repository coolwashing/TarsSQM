import json
import time
from pathlib import Path
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.schemas.dev import TeleprompterPresetItem, TeleprompterPresetSave

router = APIRouter(prefix="/api/dev", tags=["开发套件与提词器"])

# 配置文件绝对路径 (跨平台且由 Git 追踪)
PRESETS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "teleprompter_presets.json"


def _read_presets_file() -> list:
    if not PRESETS_FILE.exists():
        return []
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_presets_file(data: list) -> bool:
    try:
        PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


@router.get("/teleprompter/prompts", response_model=List[TeleprompterPresetItem], summary="获取提词器指令预设 (从 data/teleprompter_presets.json)")
def get_teleprompter_presets():
    return _read_presets_file()


@router.post("/teleprompter/prompts", response_model=TeleprompterPresetItem, summary="收藏或新增提词器指令 (持久化至 json)")
def save_teleprompter_preset(payload: TeleprompterPresetSave):
    presets = _read_presets_file()
    target_id = payload.id or f"custom_{int(time.time() * 1000)}"

    existing = next((p for p in presets if p.get("id") == target_id), None)
    if existing:
        existing["title"] = payload.title.strip()
        existing["prompt"] = payload.prompt.strip()
        item = existing
    else:
        item = {
            "id": target_id,
            "title": payload.title.strip(),
            "prompt": payload.prompt.strip(),
            "isCustom": True
        }
        presets.append(item)

    _write_presets_file(presets)
    return item


@router.post("/teleprompter/prompts/batch", response_model=List[TeleprompterPresetItem], summary="批量同步或迁移自定义提词指令")
def batch_save_teleprompter_presets(items: List[TeleprompterPresetItem]):
    presets = _read_presets_file()
    existing_ids = {p.get("id") for p in presets}
    changed = False

    for item in items:
        if item.id not in existing_ids:
            presets.append(item.model_dump())
            existing_ids.add(item.id)
            changed = True

    if changed:
        _write_presets_file(presets)
    return presets


@router.delete("/teleprompter/prompts/{preset_id}", summary="删除自定义提词器指令")
def delete_teleprompter_preset(preset_id: str):
    presets = _read_presets_file()
    filtered = [p for p in presets if p.get("id") != preset_id]
    if len(filtered) != len(presets):
        _write_presets_file(filtered)
        return {"message": "指令已移除", "id": preset_id}
    return {"message": "未找到指定指令", "id": preset_id}


# ========================================================
# 数据库探针、异机连接向导与数据字典管理 API
# ========================================================

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
from app.core.config import settings, save_db_config_to_env
from app.core.database import get_db, check_db_alive, reconnect_engine, test_db_params
from app.schemas.dev import (
    DbConfigReq,
    DbConfigStatus,
    DbTableInfo,
    DbColumnInfo,
    DbColumnCommentUpdate,
    DbRowUpdate,
    DbRowCreate,
    DbTableDoc,
    DbTableDocUpdate
)

# 数据表架构设计文档目录 (支持离线直接在 data/table_docs/ 中配置与 Git 协同)
TABLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "table_docs"
TABLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)


KNOWN_TABLE_COMMENTS = {
    "sqm_supplier": "供应商主数据表 (基础资质与准入评级)",
    "sqm_part": "零部件基础档案表 (图号/版本/规格公差)",
    "sqm_project": "车型/工程项目主表 (量产开发节点)",
    "sqm_part_dev": "零件 APQP 质量开发管控表 (OTS/PPAP试制)",
    "sqm_quality_issue": "质量异常与 8D 遏制改善表 (问题闭环追溯)",
    "sqm_ctq_line": "CTQ 关键质量特性表 (工程上下限与Cpk)",
    "sqm_kb_doc": "质量技术规程与工程知识库 (Windows风格目录树)",
    "sqm_attachment": "工程附件元数据存储表 (多租户物理映射)"
}


def _serialize_cell(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:
            return f"<二进制数据: {len(val)} 字节>"
    return val


def _mask_password(pwd: str) -> str:
    if not pwd:
        return "（未设置密码）"
    if len(pwd) <= 4:
        return "****"
    return f"{pwd[:2]}****{pwd[-2:]}"


@router.get("/db/status", response_model=DbConfigStatus, summary="获取当前数据库连接健康状态与配置")
def get_db_status():
    alive, msg = check_db_alive()
    return DbConfigStatus(
        is_connected=alive,
        message=msg,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        db_name=settings.DB_NAME,
        masked_password=_mask_password(settings.DB_PASSWORD),
        current_host=settings.DB_HOST,
        current_port=settings.DB_PORT,
        current_user=settings.DB_USER,
        current_db=settings.DB_NAME
    )


@router.post("/db/test", summary="测试指定数据库连接参数")
def test_db_config(payload: DbConfigReq):
    pwd = payload.password.strip() if payload.password and payload.password.strip() else settings.DB_PASSWORD
    success, msg = test_db_params(
        payload.host.strip(),
        payload.port,
        payload.user.strip(),
        pwd,
        payload.db_name.strip()
    )
    return {"success": success, "message": msg}


@router.post("/db/save", summary="保存数据库配置至本地 .env 并即刻热重载连接池")
def save_db_config(payload: DbConfigReq):
    pwd = payload.password.strip() if payload.password and payload.password.strip() else settings.DB_PASSWORD
    # 先做连接连通性校验
    success, msg = test_db_params(
        payload.host.strip(),
        payload.port,
        payload.user.strip(),
        pwd,
        payload.db_name.strip()
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"保存失败，数据库不可达: {msg}")

    # 写入本地 .env
    save_db_config_to_env(
        host=payload.host.strip(),
        port=payload.port,
        user=payload.user.strip(),
        password=pwd,
        db_name=payload.db_name.strip()
    )

    # 热重载数据库引擎
    reconnect_engine()
    alive, alive_msg = check_db_alive()

    return {
        "success": True,
        "message": "数据库配置已写入本机 .env 并成功重新建立连接！",
        "is_connected": alive
    }


@router.get("/db/tables", response_model=List[DbTableInfo], summary="扫描全库数据表列表及基础元数据")
def list_db_tables(db: Session = Depends(get_db)):
    sql = text("""
        SELECT 
            TABLE_NAME, 
            TABLE_COMMENT, 
            TABLE_ROWS, 
            DATA_LENGTH, 
            CREATE_TIME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = :db_name
        ORDER BY TABLE_NAME ASC
    """)
    rows = db.execute(sql, {"db_name": settings.DB_NAME}).fetchall()
    tables = []
    for r in rows:
        t_name = str(r[0])
        # 若数据库中无表注释，自动匹配已知业务模型中文注释
        t_comment = (r[1] or "").strip()
        if not t_comment and t_name in KNOWN_TABLE_COMMENTS:
            t_comment = KNOWN_TABLE_COMMENTS[t_name]

        data_kb = round((r[3] or 0) / 1024, 1)
        create_t = r[4].strftime("%Y-%m-%d %H:%M") if r[4] else None

        # 如果 TABLE_ROWS 为近似估算值，对常用表进行精确 COUNT(*) 计数
        count_sql = text(f"SELECT COUNT(*) FROM `{t_name}`")
        try:
            real_count = db.execute(count_sql).scalar() or 0
        except Exception:
            real_count = r[2] or 0

        tables.append(DbTableInfo(
            name=t_name,
            table_name=t_name,
            comment=t_comment or "未注明表含义",
            row_count=int(real_count),
            real_count=int(real_count),
            table_rows=int(real_count),
            data_size_kb=data_kb,
            data_length_kb=data_kb,
            create_time=create_t,
            engine="InnoDB"
        ))
    return tables


@router.get("/db/tables/{table_name}/columns", response_model=List[DbColumnInfo], summary="获取指定数据表的字段定义字典")
def get_table_columns(table_name: str, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    sql = text("""
        SELECT 
            COLUMN_NAME, 
            COLUMN_TYPE, 
            IS_NULLABLE, 
            COLUMN_KEY, 
            COLUMN_DEFAULT, 
            COLUMN_COMMENT,
            EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :t_name
        ORDER BY ORDINAL_POSITION ASC
    """)
    rows = db.execute(sql, {"db_name": settings.DB_NAME, "t_name": table_name}).fetchall()
    columns = []
    for r in rows:
        c_name = str(r[0])
        c_type = str(r[1])
        c_nullable = (str(r[2]).upper() == "YES")
        c_pri = (str(r[3]).upper() == "PRI")
        c_def = str(r[4]) if r[4] is not None else None
        c_comment = str(r[5] or "")
        c_extra = str(r[6] or "")

        columns.append(DbColumnInfo(
            name=c_name,
            column_name=c_name,
            data_type=c_type.split("(")[0].lower(),
            column_type=c_type,
            is_nullable=c_nullable,
            is_primary=c_pri,
            default_val=c_def,
            column_default=c_def,
            comment=c_comment,
            column_comment=c_comment,
            extra=c_extra
        ))
    return columns


@router.put("/db/tables/{table_name}/columns/comment", summary="就地更新字段数据字典业务注释")
def update_column_comment(table_name: str, payload: DbColumnCommentUpdate, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum() or not payload.column_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的表名或列名")

    # 查询当前列定义
    sql_find = text("""
        SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :t_name AND COLUMN_NAME = :col_name
    """)
    col_def = db.execute(sql_find, {
        "db_name": settings.DB_NAME,
        "t_name": table_name,
        "col_name": payload.column_name
    }).fetchone()

    if not col_def:
        raise HTTPException(status_code=404, detail="未找到指定列")

    col_type = col_def[0]
    is_null = "NULL" if col_def[1] == "YES" else "NOT NULL"

    # 执行 ALTER TABLE MODIFY COLUMN ... COMMENT ...
    comment_clean = payload.comment.replace("'", "\\'")
    alter_sql = text(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{payload.column_name}` {col_type} {is_null} COMMENT '{comment_clean}'")
    db.execute(alter_sql)
    db.commit()

    return {
        "success": True,
        "message": "字段业务字典注释已成功更新！",
        "table": table_name,
        "column": payload.column_name,
        "comment": payload.comment
    }


@router.get("/db/tables/{table_name}/rows", summary="动态分页浏览数据表物理数据行")
def get_table_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    # 查主键与列清单
    col_sql = text("""
        SELECT COLUMN_NAME, COLUMN_KEY 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :t_name 
        ORDER BY ORDINAL_POSITION ASC
    """)
    col_rows = db.execute(col_sql, {"db_name": settings.DB_NAME, "t_name": table_name}).fetchall()
    all_cols = [str(r[0]) for r in col_rows]
    pk_col = next((str(r[0]) for r in col_rows if str(r[1]).upper() == "PRI"), "id" if "id" in all_cols else (all_cols[0] if all_cols else "id"))

    # 关键词过滤条件构建
    where_clauses = []
    where_params = {}
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        sub_clauses = []
        for idx, col in enumerate(all_cols[:8]):  # 限制最多检索前 8 个文本列
            p_name = f"kw_{idx}"
            sub_clauses.append(f"CAST(`{col}` AS CHAR) LIKE :{p_name}")
            where_params[p_name] = kw
        if sub_clauses:
            where_clauses.append(f"({' OR '.join(sub_clauses)})")

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # 总行数
    count_sql = text(f"SELECT COUNT(*) FROM `{table_name}` {where_str}")
    total = db.execute(count_sql, where_params).scalar() or 0

    # 排序与分页
    order_clause = ""
    if sort_field and sort_field.replace("_", "").isalnum() and sort_field in all_cols:
        direction = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
        order_clause = f"ORDER BY `{sort_field}` {direction}"
    elif pk_col:
        order_clause = f"ORDER BY `{pk_col}` DESC"

    offset = (page - 1) * page_size
    data_sql = text(f"SELECT * FROM `{table_name}` {where_str} {order_clause} LIMIT :limit OFFSET :offset")
    fetch_params = {**where_params, "limit": page_size, "offset": offset}
    res = db.execute(data_sql, fetch_params)

    serialized_rows = []
    keys = list(res.keys())
    for r in res.fetchall():
        row_dict = {}
        for idx, k in enumerate(keys):
            row_dict[k] = _serialize_cell(r[idx])
        serialized_rows.append(row_dict)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "primary_key": pk_col,
        "columns": all_cols,
        "items": serialized_rows,
        "rows": serialized_rows
    }


@router.put("/db/tables/{table_name}/rows/{row_id}", summary="行内快速保存单行数据字段")
def update_table_row(table_name: str, row_id: str, payload: DbRowUpdate, db: Session = Depends(get_db)):
    pk_col = payload.primary_col or payload.primary_key or "id"
    if not table_name.replace("_", "").isalnum() or not pk_col.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的表名或主键字段")

    row_data = payload.values if payload.values is not None else (payload.data or {})
    update_fields = []
    params = {"pk_val": row_id}
    for k, v in row_data.items():
        if k.replace("_", "").isalnum() and k != pk_col:
            update_fields.append(f"`{k}` = :{k}")
            params[k] = v

    if not update_fields:
        return {"success": True, "message": "无需要更新的字段"}

    set_clause = ", ".join(update_fields)
    sql = text(f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_col}` = :pk_val")
    db.execute(sql, params)
    db.commit()

    return {"success": True, "message": "数据行更新成功！", "id": row_id}


@router.post("/db/tables/{table_name}/rows", summary="向数据表直接插入一条新数据记录")
def insert_table_row(table_name: str, payload: DbRowCreate, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    row_data = payload.values if payload.values is not None else (payload.data or {})
    cols = []
    val_placeholders = []
    params = {}
    for k, v in row_data.items():
        if k.replace("_", "").isalnum():
            cols.append(f"`{k}`")
            val_placeholders.append(f":{k}")
            params[k] = v

    if not cols:
        raise HTTPException(status_code=400, detail="未提供有效字段数据")

    cols_str = ", ".join(cols)
    vals_str = ", ".join(val_placeholders)
    sql = text(f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({vals_str})")
    res = db.execute(sql, params)
    db.commit()

    return {"success": True, "message": "新数据行添加成功！", "row_id": res.lastrowid}


@router.delete("/db/tables/{table_name}/rows/{row_id}", summary="物理删除数据行")
def delete_table_row(
    table_name: str,
    row_id: str,
    primary_col: Optional[str] = Query("id"),
    pk_col: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    target_pk = pk_col or primary_col or "id"
    if not table_name.replace("_", "").isalnum() or not target_pk.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的表名或主键字段")

    sql = text(f"DELETE FROM `{table_name}` WHERE `{target_pk}` = :pk_val")
    db.execute(sql, {"pk_val": row_id})
    db.commit()

    return {"success": True, "message": "数据行已删除", "table": table_name, "id": row_id}


# ========================================================
# 数据表架构设计文档 (基于 data/table_docs/*.json，支持离线与前端双向同步)
# ========================================================

def _generate_default_table_doc(table_name: str, db: Session = None) -> dict:
    comment = KNOWN_TABLE_COMMENTS.get(table_name, "")
    cols_desc = []
    if db:
        try:
            col_sql = text("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_KEY, COLUMN_COMMENT 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :t_name 
                ORDER BY ORDINAL_POSITION ASC
            """)
            col_rows = db.execute(col_sql, {"db_name": settings.DB_NAME, "t_name": table_name}).fetchall()
            for r in col_rows:
                col_name = str(r[0])
                col_type = str(r[1])
                is_pk = "PRI" in str(r[2]).upper()
                c_comment = str(r[3] or "").strip()
                cols_desc.append(f"<li><code>{col_name}</code> ({col_type}{', 主键' if is_pk else ''})：{c_comment or '基础业务属性'}</li>")
        except Exception:
            pass

    cols_html = "".join(cols_desc) if cols_desc else "<li>暂无字段定义信息</li>"
    clean_title = comment.split("(")[0].strip() if comment else table_name

    html_content = f"""<h2>1. 业务定位与核心场景</h2>
<p><strong>{table_name}</strong>（{clean_title}）是制造质量管理系统（SQM）中的重要业务实体，承载工程与供应链质量管控的数据流。</p>

<h2>2. 核心架构与主键设计</h2>
<ul>
  <li><strong>物理表名：</strong><code>{table_name}</code></li>
  <li><strong>业务定义：</strong>{comment or '基础业务实体数据表'}</li>
  <li><strong>存储引擎：</strong>InnoDB（行级锁，支持事务，字符集 utf8mb4）</li>
</ul>

<h2>3. 关键字段与业务约束</h2>
<ul>
{cols_html}
</ul>

<h2>4. 上下游数据流向与关联关系</h2>
<p>本表在业务生命周期中与上下游业务模块保持强一致性联动：</p>
<ul>
  <li><strong>上游来源：</strong>主数据配置、ERP/MES 接口同步或现场作业录入。</li>
  <li><strong>下游流向：</strong>统计过程控制（SPC）、质量检验、8D 闭环整改与溯源看板。</li>
</ul>

<h2>5. 质量合规与维护规约</h2>
<p>所有对本表的写操作需遵循 APQP/PPAP 质量审计规范，核心业务变更均保留操作人与时间戳。</p>"""

    return {
        "table_name": table_name,
        "title": f"{table_name} 架构设计规范",
        "business_module": clean_title,
        "description": comment or f"关于 {table_name} 的物理架构与质量业务流程规范",
        "author": "系统架构师",
        "version": "1.0.0",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "html_content": html_content,
        "markdown_content": f"# {table_name} 架构设计规范\n\n## 业务定位\n{comment}\n"
    }


@router.get("/db/tables/{table_name}/doc", response_model=DbTableDoc, summary="获取数据表架构设计文档 (优先读取 data/table_docs/*.json)")
def get_table_doc(table_name: str, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    doc_file = TABLE_DOCS_DIR / f"{table_name}.json"
    if doc_file.exists():
        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["table_name"] = table_name
                return data
        except Exception:
            pass

    # 若不存在，自动生成预置工业级标准模板并写入持久化 JSON 文件
    default_doc = _generate_default_table_doc(table_name, db)
    try:
        TABLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        with open(doc_file, "w", encoding="utf-8") as f:
            json.dump(default_doc, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return default_doc


@router.put("/db/tables/{table_name}/doc", summary="保存或更新数据表架构设计文档 (写入 data/table_docs/*.json)")
def save_table_doc(table_name: str, payload: DbTableDocUpdate, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    doc_file = TABLE_DOCS_DIR / f"{table_name}.json"
    doc_data = {}
    if doc_file.exists():
        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                doc_data = json.load(f)
        except Exception:
            doc_data = {}

    if not doc_data:
        doc_data = _generate_default_table_doc(table_name, db)

    if payload.title is not None:
        doc_data["title"] = payload.title
    if payload.business_module is not None:
        doc_data["business_module"] = payload.business_module
    if payload.description is not None:
        doc_data["description"] = payload.description
    if payload.author is not None:
        doc_data["author"] = payload.author
    if payload.version is not None:
        doc_data["version"] = payload.version
    if payload.html_content is not None:
        doc_data["html_content"] = payload.html_content
    if payload.markdown_content is not None:
        doc_data["markdown_content"] = payload.markdown_content

    doc_data["table_name"] = table_name
    doc_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    TABLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(doc_file, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=2)

    return {"success": True, "message": f"架构文档已保存至 data/table_docs/{table_name}.json", "data": doc_data}


@router.post("/db/tables/{table_name}/doc/reset", summary="重置数据表架构设计为系统标准模板")
def reset_table_doc(table_name: str, db: Session = Depends(get_db)):
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的数据表名称")

    doc_file = TABLE_DOCS_DIR / f"{table_name}.json"
    default_doc = _generate_default_table_doc(table_name, db)

    TABLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(doc_file, "w", encoding="utf-8") as f:
        json.dump(default_doc, f, ensure_ascii=False, indent=2)

    return {"success": True, "message": "已重置为标准架构设计模板", "data": default_doc}


