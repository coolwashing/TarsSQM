"""
通用 Excel 导入、导出与校验路由 API
包含：
- GET  /api/excel/template/{biz_key} : 下载实体规范模板
- POST /api/excel/validate/{biz_key} : 上传 Excel 进行深度校验并返回行级检查报告
- POST /api/excel/commit/{biz_key}   : 确认入库并事务性批量持久化
"""
import urllib.parse
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.common.excel_configs import get_excel_config
from app.common.excel_engine import (
    build_template_bytes,
    validate_uploaded_file,
    commit_import_data
)

router = APIRouter(
    prefix="/api/excel",
    tags=["Excel 通用数据导入与模板中心"]
)


@router.get("/template/{biz_key}", summary="下载标准 Excel 导入模板")
def download_excel_template(biz_key: str):
    """
    根据业务关键字（如 supplier, part, project, part_dev, quality_issue, ctq）
    动态生成带有表头样式、字段批注、数据下拉校验规则的 .xlsx 模板
    """
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的模板配置")

    try:
        content_bytes = build_template_bytes(biz_key)
        filename = f"SQM_{config['title']}_导入模板.xlsx"
        quoted_filename = urllib.parse.quote(filename)

        return Response(
            content=content_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模板生成失败: {str(e)}")


@router.post("/validate/{biz_key}", summary="上传 Excel 进行 5 层纵深校验")
async def validate_excel_data(
    biz_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    接收上传的 Excel 文件，进行表头比对、必填检测、枚举匹配、类型转换、
    文件内与数据库排重、外键自动解析，返回详细的行级校验结果报告
    """
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的导入配置")

    # 校验文件扩展名
    filename = file.filename or ""
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="请上传标准 Excel 格式文件 (.xlsx 或 .xls)")

    try:
        content = await file.read()
        report = validate_uploaded_file(biz_key, content, db)
        return report
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据解析与校验失败: {str(e)}")


@router.post("/commit/{biz_key}", summary="确认批量入库")
def commit_imported_records(
    biz_key: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    将已通过校验的有效数据记录进行批量原子提交入库
    """
    config = get_excel_config(biz_key)
    if not config:
        raise HTTPException(status_code=404, detail=f"未找到业务实体 [{biz_key}] 的导入配置")

    rows: List[Dict[str, Any]] = payload.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="没有待入库的有效数据行")

    try:
        result = commit_import_data(biz_key, rows, db)
        return result
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"入库提交异常: {str(e)}")
