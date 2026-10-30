import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.attachment import SysAttachment
from app.schemas.attachment import (
    AttachmentOut,
    AttachmentBindRequest,
    WangEditorUploadResponse
)

router = APIRouter(prefix="/api/storage", tags=["动态存储与附件引擎"])


def get_safe_storage_files_root() -> Path:
    """
    获取 storage/files 顶级根目录的绝对安全物理路径
    """
    p = (settings.ABSOLUTE_STORAGE_PATH / "files").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/upload", response_model=AttachmentOut, summary="通用动态流式文件上传")
async def upload_attachment(
    file: UploadFile = File(...),
    biz_type: str = Form("general"),
    biz_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    流式分片上传文件：
    1. 动态生成 files/{biz_type}/{YYYYMM}/{uuid}.ext 路径，彻底废弃写死分类；
    2. 分块写入物理磁盘；
    3. 写入 sys_attachment 纳管元数据。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="上传文件名不能为空")

    # 规范化业务域名称（仅允许字母数字下划线，防止注入）
    clean_biz_type = "".join(c for c in biz_type if c.isalnum() or c == "_") or "general"
    year_month = datetime.now().strftime("%Y%m")

    # 提取文件扩展名并生成唯一文件名
    ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"

    # 组装相对路径与绝对物理路径
    relative_path = f"{clean_biz_type}/{year_month}/{unique_filename}"
    files_root = get_safe_storage_files_root()
    target_dir = files_root / clean_biz_type / year_month
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / unique_filename

    # 流式落盘写入
    total_size = 0
    try:
        with open(target_file, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB 缓冲分块
                buffer.write(chunk)
                total_size += len(chunk)
    except Exception as e:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件流式写入失败: {str(e)}"
        )

    # 纳管数据库元数据
    mime_type = file.content_type or "application/octet-stream"
    att = SysAttachment(
        file_path=relative_path.replace("\\", "/"),
        original_name=file.filename,
        file_size=total_size,
        mime_type=mime_type,
        biz_type=clean_biz_type,
        biz_id=biz_id
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    return AttachmentOut(
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


@router.post("/editor-upload", response_model=WangEditorUploadResponse, summary="WangEditor 5 富文本专用上传适配接口")
async def upload_editor_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    适配 WangEditor 5 标准图文直传协议，返回指定格式 errno: 0 与 url
    """
    res = await upload_attachment(file=file, biz_type="editor", biz_id=None, db=db)
    return WangEditorUploadResponse(
        errno=0,
        data={
            "url": res.url,
            "alt": res.original_name,
            "href": res.url
        }
    )


@router.get("/file/{attachment_id}", summary="安全下载与预览分发")
def get_attachment_file(attachment_id: int, db: Session = Depends(get_db)):
    """
    通过附件 ID 读取元数据并进行防路径穿透安全分发
    """
    att = db.query(SysAttachment).filter(SysAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件元数据记录不存在")

    files_root = get_safe_storage_files_root()
    target_file = (files_root / att.file_path).resolve()

    # 安全检查：防止路径穿越 (Directory Traversal)
    if not str(target_file).startswith(str(files_root)):
        raise HTTPException(status_code=403, detail="非法的文件访问路径")

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="物理存储文件已丢失或不存在")

    return FileResponse(
        path=str(target_file),
        filename=att.original_name,
        media_type=att.mime_type
    )


@router.get("/attachments/{biz_type}/{biz_id}", response_model=List[AttachmentOut], summary="查询某业务关联的全部附件")
def list_business_attachments(
    biz_type: str,
    biz_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定业务实体下挂载的全部附件列表（如质量问题清单对应的所有整改报告、证据文件）
    """
    records = db.query(SysAttachment).filter(
        SysAttachment.biz_type == biz_type,
        SysAttachment.biz_id == biz_id
    ).order_by(SysAttachment.id.asc()).all()

    return [
        AttachmentOut(
            id=r.id,
            file_path=r.file_path,
            original_name=r.original_name,
            file_size=r.file_size,
            mime_type=r.mime_type,
            biz_type=r.biz_type,
            biz_id=r.biz_id,
            created_at=r.created_at,
            url=f"/api/storage/file/{r.id}"
        )
        for r in records
    ]


@router.post("/bind", summary="批量后绑定业务外键")
def bind_attachments(
    payload: AttachmentBindRequest,
    db: Session = Depends(get_db)
):
    """
    在新建业务对象（如新建质量问题单）完成拿到新生成的 ID 后，将此前预上传的附件批量绑定该 biz_id
    """
    db.query(SysAttachment).filter(
        SysAttachment.id.in_(payload.attachment_ids)
    ).update({"biz_id": payload.biz_id}, synchronize_session=False)
    db.commit()

    return {"status": "success", "bound_count": len(payload.attachment_ids), "biz_id": payload.biz_id}


@router.delete("/file/{attachment_id}", summary="安全删除附件")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """
    删除元数据记录并同步清除物理文件
    """
    att = db.query(SysAttachment).filter(SysAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    files_root = get_safe_storage_files_root()
    target_file = (files_root / att.file_path).resolve()

    if str(target_file).startswith(str(files_root)) and target_file.exists():
        try:
            target_file.unlink(missing_ok=True)
        except Exception:
            pass

    db.delete(att)
    db.commit()

    return {"status": "success", "deleted_id": attachment_id}


from pydantic import BaseModel
from urllib.parse import quote
from fastapi.responses import Response
import io
import re
import docx
from htmldocx import HtmlToDocx


class ExportDocxPayload(BaseModel):
    title: Optional[str] = "图文档案"
    html: str


@router.post("/export-docx", summary="将富文本 HTML 实时导出为 Word (.docx) 文件")
def export_html_to_docx(payload: ExportDocxPayload, db: Session = Depends(get_db)):
    """
    将富文本 HTML 直接编译为标准的 Microsoft Word (.docx) 文档
    """
    if not payload.html or not payload.html.strip():
        raise HTTPException(status_code=400, detail="富文本内容为空，无法导出为 Word 文档")

    doc = docx.Document()
    files_root = get_safe_storage_files_root()
    processed_html = payload.html

    # 处理局部图片路径：如果含有 /api/storage/file/{id}，解析为真实物理路径
    pattern = r'/api/storage/file/(\d+)'
    matches = set(re.findall(pattern, processed_html))
    for att_id_str in matches:
        try:
            att = db.query(SysAttachment).filter(SysAttachment.id == int(att_id_str)).first()
            if att:
                local_path = (files_root / att.file_path).resolve()
                if local_path.exists():
                    processed_html = processed_html.replace(
                        f"/api/storage/file/{att_id_str}",
                        str(local_path).replace("\\", "/")
                    )
        except Exception:
            pass

    # 转换 HTML 到 DOCX
    try:
        parser = HtmlToDocx()
        parser.add_html_to_document(processed_html, doc)
    except Exception:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(processed_html, "html.parser")
        doc.add_paragraph(soup.get_text())

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    docx_bytes = buf.getvalue()

    filename = f"{payload.title or '图文档案'}.docx"
    encoded_filename = quote(filename)

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        }
    )
