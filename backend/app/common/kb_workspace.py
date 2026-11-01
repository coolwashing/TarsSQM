"""Local attachment indexes and task files; originals stay outside the database."""
import hashlib
import html
import json
import math
import os
import re
import uuid
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attachment import SysAttachment
from app.models.kb import SqmKbDoc

MAX_TEXT_BYTES = 60000
MAX_CHUNKS = 800


def bounded_text(text: str, limit: int = MAX_TEXT_BYTES) -> str:
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def index_path(doc_id: int) -> Path:
    return settings.ABSOLUTE_STORAGE_PATH / "kb-index" / f"{doc_id}.json"


def read_index(doc_id: int) -> dict:
    try:
        return json.loads(index_path(doc_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "pending", "message": "尚未建立正文索引", "chunks": []}


def attachment_path(attachment: SysAttachment) -> Path:
    root = (settings.ABSOLUTE_STORAGE_PATH / "files").resolve()
    path = (root / attachment.file_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("附件路径不在存储目录内")
    return path


def source_doc(db: Session, doc: SqmKbDoc) -> SqmKbDoc:
    if doc.biz_type == "SHORTCUT" and doc.biz_id:
        return db.get(SqmKbDoc, doc.biz_id) or doc
    return doc


def file_metadata(db: Session, doc: SqmKbDoc) -> dict:
    source = source_doc(db, doc)
    if source.biz_type != "FILE":
        return {}
    attachment = db.get(SysAttachment, source.biz_id) if source.biz_id else None
    index = read_index(source.id)
    return {
        "file_url": f"/api/kb/files/{source.id}/download",
        "file_size": attachment.file_size if attachment else 0,
        "attachment_id": attachment.id if attachment else None,
        "index_status": index["status"],
        "index_message": index["message"],
        "chunk_count": len(index.get("chunks", [])),
    }


def chunks_for_text(text: str, location: str) -> list[dict]:
    text = text.strip()
    return [{"text": text[start:start + 900], "location": location}
            for start in range(0, len(text), 780) if text[start:start + 900].strip()]


def build_file_index(doc: SqmKbDoc, path: Path) -> dict:
    chunks = []
    extension = path.suffix.lower()
    message = "已建立正文索引"
    state = "indexed"
    try:
        if extension in (".xlsx", ".xlsm", ".docx"):
            with zipfile.ZipFile(path) as archive:
                if sum(info.file_size for info in archive.infolist()) > 64 * 1024 * 1024:
                    raise ValueError("解压后超过正文解析上限")
        if extension in (".xlsx", ".xlsm"):
            from openpyxl import load_workbook
            from openpyxl.utils import get_column_letter
            workbook = load_workbook(path, read_only=True, data_only=True)
            try:
                for sheet in workbook:
                    for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                        cells = [f"{get_column_letter(i)}{row_number}: {str(value)[:1000]}"
                                 for i, value in enumerate(row[:200], start=1) if value is not None]
                        if cells:
                            chunks.append({"text": " | ".join(cells)[:3000],
                                           "location": f"工作表 {sheet.title} · 第 {row_number} 行"})
                        if len(chunks) >= MAX_CHUNKS or row_number >= 50000:
                            break
                    if len(chunks) >= MAX_CHUNKS:
                        break
            finally:
                workbook.close()
        elif extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise ValueError("加密 PDF 暂不解析")
            for number, page in enumerate(reader.pages[:300], start=1):
                chunks.extend(chunks_for_text(page.extract_text() or "", f"第 {number} 页"))
                if len(chunks) >= MAX_CHUNKS:
                    break
        elif extension == ".docx":
            from docx import Document
            document = Document(path)
            for number, paragraph in enumerate(document.paragraphs, start=1):
                chunks.extend(chunks_for_text(paragraph.text, f"第 {number} 段"))
                if len(chunks) >= MAX_CHUNKS:
                    break
            for number, table in enumerate(document.tables[:100], start=1):
                for row in table.rows[:1000]:
                    chunks.extend(chunks_for_text(" | ".join(cell.text for cell in row.cells), f"表格 {number}"))
                    if len(chunks) >= MAX_CHUNKS:
                        break
        elif extension in (".txt", ".md", ".csv"):
            raw = path.read_bytes()[:2 * 1024 * 1024]
            try:
                content = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = raw.decode("gb18030", errors="replace")
            chunks = chunks_for_text(content, "文件正文")
        else:
            state, message = "unsupported", "原件已保存，此格式暂不解析；旧版 Excel 可另存为 xlsx 后上传"
        if state == "indexed" and not chunks:
            state, message = "empty", "原件已保存，未提取到文字；扫描 PDF 暂需先做文字识别"
        if len(chunks) >= MAX_CHUNKS:
            message = "已索引前 800 个片段，超出部分仍保留在原件中"
    except ImportError:
        state, message = "failed", "原件已保存，缺少解析依赖；请重启后端安装依赖后重新索引"
    except Exception:
        state, message = "failed", "原件已保存，正文解析失败；请检查文件格式、加密状态或文件大小"
    result = {"status": state, "message": message, "chunks": chunks[:MAX_CHUNKS]}
    write_json(index_path(doc.id), result)
    doc.content_text = bounded_text("\n".join(chunk["text"] for chunk in result["chunks"]))
    return result


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value or "")
    return "".join(parser.parts).strip()


def query_terms(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", query.lower())
    terms = set(words)
    for word in words:
        if re.fullmatch(r"[\u4e00-\u9fff]{3,}", word):
            terms.update(word[i:i + 2] for i in range(len(word) - 1))
    return sorted(terms, key=len, reverse=True)[:64]


def retrieve(db: Session, query: str, folder_id=None, limit=8, doc_id=None) -> list[dict]:
    terms = query_terms(query)
    if not terms:
        return []
    all_docs = db.query(SqmKbDoc).all()
    allowed = None
    if folder_id is not None:
        allowed = {folder_id}
        for _ in range(len(all_docs)):
            additions = {d.id for d in all_docs if d.parent_id in allowed} - allowed
            if not additions:
                break
            allowed.update(additions)
    results = []
    for doc in all_docs:
        if doc.is_folder or doc.biz_type == "SHORTCUT" or (allowed is not None and doc.id not in allowed):
            continue
        chunks = read_index(doc.id).get("chunks", []) if doc.biz_type == "FILE" else chunks_for_text(doc.content_text or "", "文档正文")
        if not chunks:
            chunks = [{"text": doc.title, "location": "文件名称"}]
        for number, chunk in enumerate(chunks):
            text = chunk["text"].lower()
            hits = [(term, text.count(term)) for term in terms]
            score = sum((1 + math.log(count)) * min(len(term), 8) for term, count in hits if count)
            score += sum(min(len(term), 8) * 2 for term in terms if term in doc.title.lower())
            if doc.id == doc_id and score:
                score *= 1.15
            if not score:
                continue
            first = next((text.find(term) for term in terms if term in text), 0)
            snippet = chunk["text"][max(0, first - 100):max(0, first - 100) + 600]
            results.append({"id": doc.id, "title": doc.title, "icon": doc.icon,
                            "location": chunk["location"], "snippet": snippet,
                            "chunk_id": f"{doc.id}:{number}", "score": round(score, 3),
                            "kind": "file" if doc.biz_type == "FILE" else "doc",
                            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None})
    results.sort(key=lambda item: (-item["score"], item["id"], item["chunk_id"]))
    return results[:limit]


class SafeHtml(HTMLParser):
    tags = {"p", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i",
            "u", "s", "br", "hr", "ul", "ol", "li", "blockquote", "pre", "code", "table", "thead",
            "tbody", "tfoot", "tr", "th", "td", "caption", "sup", "sub", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "object"):
            self.hidden += 1
        if self.hidden or tag not in self.tags:
            return
        allowed = "".join(f' {key}="{value}"' for key, value in attrs
                          if key in ("colspan", "rowspan") and value and value.isdigit() and len(value) <= 3)
        if tag == "img":
            source = next((value for key, value in attrs if key == "src"), "") or ""
            if not re.fullmatch(r"/api/storage/file/[0-9]+", source):
                return
            allowed = f' src="{source}"'
        self.output.append(f"<{tag}{allowed}>")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "object"):
            self.hidden = max(0, self.hidden - 1)
            return
        if not self.hidden and tag in self.tags and tag not in ("br", "hr", "img"):
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.hidden:
            self.output.append(html.escape(data))


def safe_html(value: str) -> str:
    parser = SafeHtml()
    parser.feed(value)
    return "".join(parser.output)


def content_hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def collect_assets(db: Session, docs: list[SqmKbDoc]) -> list[Path]:
    """Delete owned metadata transactionally; caller unlinks paths after commit."""
    paths = [index_path(doc.id) for doc in docs]
    for doc in docs:
        if doc.biz_type == "FILE" and doc.biz_id:
            attachment = db.get(SysAttachment, doc.biz_id)
            if attachment and attachment.biz_type == "kb" and attachment.biz_id == doc.id:
                paths.append(attachment_path(attachment))
                db.delete(attachment)
    return paths


def unlink_assets(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
