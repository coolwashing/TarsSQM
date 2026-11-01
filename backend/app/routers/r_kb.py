import re
import html
import json
import time
from typing import List, Optional
import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, text, func

from app.core.config import settings
from app.core.database import get_db
from app.models.kb import SqmKbDoc
from app.common.kb_workspace import collect_assets, file_metadata, retrieve, unlink_assets
from app.schemas.kb import (
    KbDocTreeNode,
    KbDocDetail,
    KbDocCreate,
    KbDocUpdate,
    KbDocMove,
    KbDocSearchResult,
    KbAiCopilotRequest,
    KbPromptPresetItem,
    KbPromptPresetSave,
    KbExplorerItem,
    KbBreadcrumbNode,
    KbFolderCreate,
    KbDocFastCreate,
    KbShortcutCreate,
    KbItemRename,
    KbItemMove,
    KbItemStatusUpdate,
    KbItemIconUpdate
)
from pathlib import Path

router = APIRouter(prefix="/api/kb", tags=["质量知识库与技术文档"])


def strip_html_tags(text: Optional[str]) -> str:
    """
    纯原生正则与 HTML 反转义清洗长文本，提取纯文本供 RAG 与全文检索
    零外部依赖，极速高效
    """
    if not text:
        return ""
    clean = re.compile(r"<[^>]+>")
    cleantext = re.sub(clean, " ", text)
    # 合并多余空白符
    cleantext = re.sub(r"\s+", " ", cleantext)
    return html.unescape(cleantext).strip()


def seed_initial_kb_docs(db: Session):
    """
    当知识库为空时，自动预置标准飞书式质量规范种子数据
    """
    # Serialize the empty-table check and seed insert across concurrent requests.
    # The revision row exists after migrations and is locked until commit.
    db.execute(text("SELECT version_num FROM alembic_version FOR UPDATE")).scalar()
    if db.query(SqmKbDoc).count() > 0:
        # 兼容已有库：若全库无任何标星项，默认将首个核心规范标星，便于直接体现标星特性
        has_fav = db.query(SqmKbDoc).filter(SqmKbDoc.is_favorite == True).first()
        if not has_fav:
            first_doc = db.query(SqmKbDoc).filter(SqmKbDoc.is_folder == False).first()
            if first_doc:
                first_doc.is_favorite = True
        db.commit()
        return

    # 分组 1: 01_供应商准入与审核管理
    folder_1 = SqmKbDoc(
        title="01_供应商准入与审核管理",
        icon="📁",
        is_folder=True,
        sort_order=1
    )
    db.add(folder_1)
    db.flush()

    doc_1_1 = SqmKbDoc(
        parent_id=folder_1.id,
        title="供应商准入审核标准规范 (V2.0)",
        icon="📄",
        is_folder=False,
        is_favorite=True,  # 默认标星关注
        sort_order=1,
        content_html="""<div style="background:#f0f7ff;border-left:4px solid #3370ff;border-radius:4px;padding:12px 16px;margin:16px 0;color:#1e3a8a;"><strong>核心准则提示：</strong><br>本规范作为 SQM 供应商开发阶段（SVP）的法定审核依据。对于动力模块、关节模组等核心关键件供应商，必须达到 <strong>85 分（B级及以上）</strong>方可准予签署量产供应协议。</div><h2>一、 资质审核维度与打分权重</h2><p>对潜在与开发中供应商的审核涵盖质量管理体系、工程开发能力、过程制程控制、关键设备保全及供应链交付韧性五大支柱。</p><ul><li><strong>体系认证</strong>：IATF 16949 或 ISO 9001 体系有效性（20分）</li><li><strong>CTQ 制程能力</strong>：关键特性的 Cpk ≥ 1.33 保证度（30分）</li><li><strong>设备与检具</strong>：测量系统分析 MSA 与校准计划（25分）</li><li><strong>异常响应</strong>：24h 内遏制，48h 内输出 8D 分析（25分）</li></ul><h2>二、 现场审核重点检查清单</h2><p>☑️ 来料检验（IQC）是否具备全套受控图纸及标准 SOP<br>☑️ 关键工序机台是否具备防错（Poka-Yoke）报警机制<br>☑️ 不良品隔离区是否有清晰物理标识与门禁管理</p>""",
        author="张建平 (SQM质量部)"
    )
    doc_1_1.content_text = strip_html_tags(doc_1_1.content_html)
    db.add(doc_1_1)

    # 分组 2: 02_来料检验 (IQC) 对齐基准
    folder_2 = SqmKbDoc(
        title="02_来料检验 (IQC) 对齐基准",
        icon="📁",
        is_folder=True,
        sort_order=2
    )
    db.add(folder_2)
    db.flush()

    doc_2_1 = SqmKbDoc(
        parent_id=folder_2.id,
        title="IQC 来料抽样检验基准表",
        icon="📄",
        is_folder=False,
        sort_order=1,
        content_html="""<h2>一、 抽样方案与接收质量限 (AQL)</h2><p>严格按照 GB/T 2828.1-2012 / ISO 2859-1 正常检验一次抽样方案执行：</p><table style="width:100%;border-collapse:collapse;" border="1"><thead><tr><th>缺陷等级</th><th>定义说明</th><th>AQL 允收基准</th><th>处置准则</th></tr></thead><tbody><tr><td><strong>致命缺陷 (CRI)</strong></td><td>影响电气绝缘安全、机械干涉断裂</td><td>0</td><td>全批退货并立即拉响警报</td></tr><tr><td><strong>主要缺陷 (MAJ)</strong></td><td>影响装配精度、关键尺寸超出公差</td><td>0.40</td><td>加严检验，提报8D改善</td></tr><tr><td><strong>次要缺陷 (MIN)</strong></td><td>外观轻微划伤、包装箱轻度变形</td><td>1.00</td><td>特采或供应商现场全检</td></tr></tbody></table>""",
        author="SQE 专家组"
    )
    doc_2_1.content_text = strip_html_tags(doc_2_1.content_html)
    db.add(doc_2_1)

    # 分组 3: 03_关键质量特性 (CTQ) 控制规程
    folder_3 = SqmKbDoc(
        title="03_关键质量特性 (CTQ) 控制规程",
        icon="📁",
        is_folder=True,
        sort_order=3
    )
    db.add(folder_3)
    db.flush()

    doc_3_1 = SqmKbDoc(
        parent_id=folder_3.id,
        title="减速机 CTQ 反向间隙控制规程",
        icon="📄",
        is_folder=False,
        sort_order=1,
        content_html="""<div style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:4px;padding:12px 16px;margin:16px 0;color:#1e40af;"><strong>质量红线准则：</strong>减速机反向间隙（Backlash）必须保持 ≤ 1.0 arcmin，任何批次出厂检验超标直接触发一票否决。</div><h2>一、 减速机来料检验流程</h2><p>1. 恒温 20℃±2℃ 环境静置 2 小时；<br>2. 高精度双光栅测试台加压 100% 顺逆双向转矩测试；<br>3. 自动生成正反向齿隙迟滞回线。</p>""",
        author="系统管理员"
    )
    doc_3_1.content_text = strip_html_tags(doc_3_1.content_html)
    db.add(doc_3_1)

    db.commit()


@router.get("/tree", response_model=List[KbDocTreeNode], summary="获取知识库树形目录")
def get_kb_tree(db: Session = Depends(get_db)):
    """
    获取全局自关联文档树形结构
    """
    seed_initial_kb_docs(db)

    docs = db.query(SqmKbDoc).order_by(SqmKbDoc.sort_order.asc(), SqmKbDoc.id.asc()).all()

    # 递归组织成树形结构
    node_map = {}
    for d in docs:
        metadata = file_metadata(db, d)
        node_map[d.id] = KbDocTreeNode(
            id=d.id,
            parent_id=d.parent_id,
            title=d.title,
            icon=d.icon,
            is_folder=d.is_folder,
            is_favorite=bool(d.is_favorite),
            sort_order=d.sort_order,
            type="folder" if d.is_folder else "file" if metadata else "shortcut" if d.biz_type == "SHORTCUT" else "doc",
            target_id=d.biz_id if d.biz_type == "SHORTCUT" else None,
            file_url=metadata.get("file_url"),
            children=[]
        )

    root_nodes: List[KbDocTreeNode] = []
    for d in docs:
        node = node_map[d.id]
        if d.parent_id and d.parent_id in node_map:
            node_map[d.parent_id].children.append(node)
        else:
            root_nodes.append(node)

    return root_nodes


@router.get("/docs/{doc_id}", response_model=KbDocDetail, summary="读取单篇文档完整内容")
def get_kb_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档记录不存在")
    return doc


@router.post("/docs", response_model=KbDocDetail, status_code=status.HTTP_201_CREATED, summary="新建文档或分类")
def create_kb_doc(payload: KbDocCreate, db: Session = Depends(get_db)):
    max_sort = db.query(SqmKbDoc.sort_order).filter(SqmKbDoc.parent_id == payload.parent_id).order_by(desc(SqmKbDoc.sort_order)).first()
    next_sort = (max_sort[0] + 1) if max_sort else 1

    doc = SqmKbDoc(
        parent_id=payload.parent_id,
        title=payload.title.strip() if payload.title else "新建文档",
        icon=payload.icon or ("📁" if payload.is_folder else "📄"),
        is_folder=payload.is_folder,
        sort_order=payload.sort_order if payload.sort_order else next_sort,
        biz_type=payload.biz_type,
        biz_id=payload.biz_id,
        content_html="<p>请输入文档正文内容...</p>",
        content_text="请输入文档正文内容..."
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.put("/docs/{doc_id}", response_model=KbDocDetail, summary="更新文档 (0.5s 静默保存)")
def update_kb_doc(doc_id: int, payload: KbDocUpdate, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档记录不存在")

    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.icon is not None:
        doc.icon = payload.icon
    if payload.author is not None:
        doc.author = payload.author
    if payload.content_html is not None:
        if doc.biz_type == "FILE":
            raise HTTPException(status_code=400, detail="附件原件不能作为在线文档覆写")
        doc.content_html = payload.content_html
        # 同步清洗出纯文本供 RAG 和全文检索
        doc.content_text = strip_html_tags(payload.content_html)

    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/docs/{doc_id}", summary="删除文档或分类 (级联删除)")
def delete_kb_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档记录不存在")

    # 递归删除所有子孙节点
    def collect_descendants(pid: int, ids_to_delete: list):
        children = db.query(SqmKbDoc).filter(SqmKbDoc.parent_id == pid).all()
        for child in children:
            ids_to_delete.append(child.id)
            collect_descendants(child.id, ids_to_delete)

    all_delete_ids = [doc.id]
    collect_descendants(doc.id, all_delete_ids)

    assets = collect_assets(db, db.query(SqmKbDoc).filter(SqmKbDoc.id.in_(all_delete_ids)).all())
    db.flush()
    db.query(SqmKbDoc).filter(SqmKbDoc.id.in_(all_delete_ids)).delete(synchronize_session=False)
    db.commit()
    unlink_assets(assets)
    return {"message": "文档及子目录删除成功", "deleted_ids": all_delete_ids}


def _move_kb_item(
    db: Session,
    doc: SqmKbDoc,
    target_folder_id: Optional[int],
    sort_order: Optional[int] = None,
    reference_id: Optional[int] = None,
    placement: str = "inside",
) -> None:
    reference = None
    if placement in ("before", "after"):
        if reference_id is None:
            raise HTTPException(status_code=400, detail="请选择同级移动的参照位置")
        reference = db.get(SqmKbDoc, reference_id)
        if reference is None:
            raise HTTPException(status_code=404, detail="参照位置不存在，请刷新目录")
        if reference.id == doc.id:
            raise HTTPException(status_code=400, detail="不能以自身作为移动参照")
        target_folder_id = reference.parent_id

    if target_folder_id is not None:
        target = db.get(SqmKbDoc, target_folder_id)
        if target is None:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")
        if not target.is_folder:
            raise HTTPException(status_code=400, detail="目标位置必须是文件夹")

        ancestor = target
        visited = set()
        while ancestor is not None:
            if ancestor.id == doc.id:
                raise HTTPException(status_code=400, detail="不能移入自身或子文件夹")
            if ancestor.id in visited:
                raise HTTPException(status_code=400, detail="目标目录结构存在循环")
            visited.add(ancestor.id)
            ancestor = db.get(SqmKbDoc, ancestor.parent_id) if ancestor.parent_id is not None else None

    if reference is not None:
        siblings = db.query(SqmKbDoc).filter(
            SqmKbDoc.parent_id == target_folder_id,
            SqmKbDoc.id != doc.id,
        ).order_by(SqmKbDoc.sort_order.asc(), SqmKbDoc.id.asc()).all()
        reference_index = next(i for i, sibling in enumerate(siblings) if sibling.id == reference.id)
        siblings.insert(reference_index + (1 if placement == "after" else 0), doc)
        doc.parent_id = target_folder_id
        for index, sibling in enumerate(siblings, start=1):
            sibling.sort_order = index
        db.commit()
        return

    if doc.parent_id == target_folder_id and (sort_order is None or doc.sort_order == sort_order):
        return
    if doc.parent_id != target_folder_id and sort_order is None:
        last_order = db.query(func.max(SqmKbDoc.sort_order)).filter(SqmKbDoc.parent_id == target_folder_id).scalar()
        doc.sort_order = (last_order or 0) + 1
    elif sort_order is not None:
        doc.sort_order = sort_order
    doc.parent_id = target_folder_id
    db.commit()


@router.post("/docs/{doc_id}/move", summary="调整文档节点层级与排序")
def move_kb_doc(doc_id: int, payload: KbDocMove, db: Session = Depends(get_db)):
    doc = db.get(SqmKbDoc, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档记录不存在")
    _move_kb_item(db, doc, payload.target_parent_id, payload.sort_order)
    return {"message": "文档移动更新成功"}


@router.get("/search", response_model=List[KbDocSearchResult], summary="知识库快速/RAG 检索")
def search_kb_docs(q: str = Query(..., min_length=1, max_length=1000, description="检索标题、正文及附件文字"),
                   folder_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    results = retrieve(db, q, folder_id=folder_id, limit=60)
    seen = set()
    out = []
    for item in results:
        if item["id"] not in seen:
            seen.add(item["id"])
            out.append(KbDocSearchResult(**{**item, "snippet": html.escape(item["snippet"])}))
        if len(out) >= 20:
            break
    return out


_preview_cache = {}


@router.post("/copilot/preview", summary="IDE/外部写入审查预览缓存")
def set_copilot_preview(payload: dict):
    doc_id = str(payload.get("doc_id", "default"))
    html_content = payload.get("html", "")
    _preview_cache[doc_id] = {
        "html": html_content,
        "updated_at": time.time()
    }
    return {"message": "预览缓存已更新", "doc_id": doc_id}


@router.get("/copilot/preview", summary="获取审查预览缓存")
def get_copilot_preview(doc_id: str = "default"):
    item = _preview_cache.get(str(doc_id))
    if not item:
        item = _preview_cache.get("default")
    if not item:
        return {"html": "", "updated_at": None}
    return item


# 指令预设配置文件路径 (Git 自动追踪跨电脑同步)
PROMPTS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "kb_prompt_presets.json"


def _read_prompts_file() -> list:
    if not PROMPTS_FILE.exists():
        return []
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_prompts_file(data: list) -> bool:
    try:
        PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


@router.get("/prompts", response_model=List[KbPromptPresetItem], summary="获取AI智写预设指令列表 (从 data/kb_prompt_presets.json 同步)")
def get_prompt_presets():
    return _read_prompts_file()


@router.post("/prompts", response_model=KbPromptPresetItem, summary="收藏或更新AI智写指令 (持久化至 data/kb_prompt_presets.json)")
def save_prompt_preset(payload: KbPromptPresetSave):
    prompts = _read_prompts_file()
    target_id = payload.id or f"p_custom_{int(time.time())}"
    
    # 检查是否已存在
    existing = next((p for p in prompts if p.get("id") == target_id), None)
    if existing:
        existing["name"] = payload.name.strip()
        existing["prompt"] = payload.prompt.strip()
        item = existing
    else:
        item = {
            "id": target_id,
            "name": payload.name.strip(),
            "prompt": payload.prompt.strip(),
            "is_system": False
        }
        prompts.append(item)
        
    _write_prompts_file(prompts)
    return item


@router.delete("/prompts/{prompt_id}", summary="删除自定义AI智写指令")
def delete_prompt_preset(prompt_id: str):
    prompts = _read_prompts_file()
    prompts = [p for p in prompts if p.get("id") != prompt_id]
    _write_prompts_file(prompts)
    return {"message": "指令已删除", "id": prompt_id}


@router.post("/ai-copilot", summary="网页端 AI 智写与 RAG 检索生成 (流式 SSE)")
def ai_copilot_stream(payload: KbAiCopilotRequest, db: Session = Depends(get_db)):
    """
    网页端直接交互知识库：
    1. RAG 知识检索：自动根据用户指令和所选文本在 sqm_kb_doc 中检索强相关的条款；
    2. 上下文拼装：将检索到的质量标准注入系统提示词；
    3. 流式回传：通过 SSE 逐字向网页端吐出生成结果（带参考文档元数据）；
    4. 兜底保护：若大模型服务未启动或连接超时，自动切换为内置 SQM 专家智能模板引擎。
    """
    # 1. 自动提取关键词进行 RAG 检索
    prompt_keywords = [w.strip() for w in re.split(r"[\s,，。、；;]+", payload.prompt) if len(w.strip()) > 1]
    matched_docs = []
    if prompt_keywords:
        conditions = [or_(SqmKbDoc.title.like(f"%{kw}%"), SqmKbDoc.content_text.like(f"%{kw}%")) for kw in prompt_keywords[:4]]
        matched_docs = db.query(SqmKbDoc).filter(SqmKbDoc.is_folder == False, or_(*conditions)).limit(3).all()

    # 如果指定了 doc_id 且不在匹配列表中，优先把当前文档加入参考上下文
    if payload.doc_id:
        curr = db.query(SqmKbDoc).filter(SqmKbDoc.id == payload.doc_id).first()
        if curr and curr not in matched_docs:
            matched_docs.insert(0, curr)

    ref_titles = [d.title for d in matched_docs]
    context_chunks = [f"【参考条款《{d.title}》】\n{d.content_text[:500]}" for d in matched_docs]
    context_str = "\n\n".join(context_chunks) if context_chunks else "暂无强关联特定标准，请依照常规 SQM 与 IATF 16949 质量工程规范输出。"

    def event_stream():
        # 发送第一帧：元数据告知前端参考了哪些文档
        yield f"data: {json.dumps({'type': 'meta', 'references': ref_titles})}\n\n"

        # 尝试调用大模型服务 (OpenAI-compatible / Ollama / DeepSeek)
        llm_success = False
        api_url = f"{settings.AI_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.AI_API_KEY}"
        }
        scope_desc = f"【靶向作用范围】：{payload.scope_name or '全篇规程整体'}\n注意：仅需生成该局部范围内的内容，其余章节将受物理隔离保护不覆盖！\n" if payload.scope and payload.scope != "ALL" else ""
        body = {
            "model": settings.AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一位资深的工业制造与供应商质量管理(SQM)技术专家。根据提供的质量知识库标准条款，"
                        "为用户生成专业、严谨、排版规范的质量技术规程、检验步骤或处置分析。"
                        "要求：输出必须使用规范优雅的 HTML 格式（例如 <h2>、<p>、<table border='1'>、<ul> 等），"
                        "确保可直接一键填入富文本编辑器中。不要输出额外的包裹说明，只输出 HTML 片段。"
                    )
                },
                {
                    "role": "user",
                    "content": f"{scope_desc}【质量知识库参考条款】\n{context_str}\n\n【选中文本】\n{payload.selected_text or '无'}\n\n【用户需求】\n{payload.prompt}"
                }
            ],
            "temperature": settings.AI_TEMPERATURE,
            "stream": True
        }

        try:
            resp = requests.post(api_url, headers=headers, json=body, timeout=(3.0, 30.0), stream=True)
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith('data: ') and decoded != 'data: [DONE]':
                            try:
                                chunk_json = json.loads(decoded[6:])
                                delta = chunk_json.get('choices', [{}])[0].get('delta', {})
                                content = delta.get('content')
                                if content:
                                    llm_success = True
                                    yield f"data: {json.dumps({'type': 'chunk', 'text': content})}\n\n"
                            except Exception:
                                pass
        except Exception:
            llm_success = False

        # 如果未配大模型或连接未成功，启用高保真 SQM 智能专家模板引擎 (兜底保障)
        if not llm_success:
            ref_badge = f"<div style='background:#f0fdf4;border-left:4px solid #16a34a;border-radius:4px;padding:10px 14px;margin:12px 0;color:#166534;'><strong>已自动对齐知识库标准：</strong><br>{'、'.join(ref_titles) if ref_titles else 'SQM 通用质量标准基准'}</div>"
            
            # 若靶向目标为表格，直接输出规范表格结构，方便无缝替换
            if payload.scope == "TABLES":
                fallback_html = f"""
<table class="ctq-spec-table" style="width:100%;border-collapse:collapse;margin:12px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th>控制项目 / 尺寸</th>
      <th>图纸公差标称值</th>
      <th>公差上限 (USL)</th>
      <th>公差下限 (LSL)</th>
      <th>检测量具与抽样</th>
      <th>判定准则 (Cpk)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>CTQ-01 法兰盘外径</strong></td>
      <td>Ø45.00 mm</td>
      <td>+0.015 mm</td>
      <td>-0.010 mm</td>
      <td>三坐标 / 5件/批</td>
      <td>Cpk ≥ 1.33</td>
    </tr>
    <tr>
      <td><strong>CTQ-02 安装孔同轴度</strong></td>
      <td>0.02 mm</td>
      <td>0.025 mm</td>
      <td>0.000 mm</td>
      <td>气动量仪 / 100% 全检</td>
      <td>零缺陷接收</td>
    </tr>
    <tr>
      <td><strong>CTQ-03 关键齿面粗糙度</strong></td>
      <td>Ra 0.4 μm</td>
      <td>0.40 μm</td>
      <td>0.00 μm</td>
      <td>粗糙度仪 / 3件/批</td>
      <td>均值 ≤ 0.35 μm</td>
    </tr>
  </tbody>
</table>
"""
            # 若靶向目标为特定章节，直接输出该章节正文，不输出冗余的全局大标题
            elif payload.scope and payload.scope.startswith("heading_"):
                clean_heading = payload.scope_name or payload.scope.split("_", 2)[-1]
                fallback_html = f"""
<p>针对<strong>【{clean_heading}】</strong>核心控制要求，结合用户指令「{payload.prompt}」，实施以下细化规范：</p>
<ul>
  <li><strong>标准合规验证：</strong>操作人员需持有合格上岗资质，严格按照最新批准的作业指导书执行；</li>
  <li><strong>首检与过程巡检：</strong>每班次开机前必须完成首件三检，并如实录入质量追溯系统；</li>
  <li><strong>SPC 趋势监控：</strong>关键尺寸建立 Xbar-R 控制图，一旦连续 7 点处于中心线同侧即触发异常响应。</li>
</ul>
<table style="width:100%;border-collapse:collapse;margin:10px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th>核查要素</th>
      <th>验收判据</th>
      <th>抽样频次</th>
      <th>异常阻断动作</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>工艺参数合规性</td>
      <td>严格按最新批准的 SOP/WI 参数卡运行</td>
      <td>每班首检</td>
      <td>超差停机报修</td>
    </tr>
    <tr>
      <td>量具计量有效性</td>
      <td>量具在校准有效期内，绿标状态完好</td>
      <td>开工前确认</td>
      <td>超期立即停用</td>
    </tr>
  </tbody>
</table>
"""
            
            p_upper = payload.prompt.upper()
            if "8D" in p_upper or "纠正" in payload.prompt or "客诉" in payload.prompt:
                fallback_html = f"""
{ref_badge}
<h2>【8D 质量问题根本原因分析与纠正防范报告】</h2>
<p>针对质量异常「<strong>{payload.prompt}</strong>」，启动 8D 应急排查规程：</p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th style="width:18%;">8D 步骤</th>
      <th>行动内容与工程要求</th>
      <th style="width:18%;">责任人 / 期限</th>
      <th style="width:15%;">验证状态</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>D1/D2 问题定义</strong></td>
      <td>明确失效物料批次、不良率、5W2H 现象描述</td>
      <td>SQE / 4H 内</td>
      <td>已完成初步复现</td>
    </tr>
    <tr>
      <td><strong>D3 紧急遏制 (ICA)</strong></td>
      <td>库房全检隔离、产线在制品排查、在途品通知追回，启动临时防错</td>
      <td>仓库/生产 / 24H 内</td>
      <td>库存品 100% 冻结</td>
    </tr>
    <tr>
      <td><strong>D4 根本原因 (RCA)</strong></td>
      <td>通过人机料法环 5-Why 鱼骨图定位制造/设计与流出真因</td>
      <td>供应商质量部 / 48H 内</td>
      <td>关键尺寸超差点已锁定</td>
    </tr>
    <tr>
      <td><strong>D5/D6 永久纠正 (PCA)</strong></td>
      <td>模具维修加固、更新作业指导书、验证 Cpk ≥ 1.67</td>
      <td>工装治具组 / 7D 内</td>
      <td>小批量试跑验证中</td>
    </tr>
    <tr>
      <td><strong>D7 预防再发生</strong></td>
      <td>横向展开排查同系列模具，更新 PFMEA 与控制计划 (CP)</td>
      <td>体系与工程部 / 14D 内</td>
      <td>文档已签发</td>
    </tr>
  </tbody>
</table>
"""
            elif "FMEA" in p_upper or "失效" in payload.prompt or "风险" in payload.prompt:
                fallback_html = f"""
{ref_badge}
<h2>【PFMEA 过程潜在失效模式及后果分析】</h2>
<p>分析对象：<strong>{payload.prompt}</strong></p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th>工序与要求</th>
      <th>潜在失效模式</th>
      <th>潜在失效后果</th>
      <th>S (严重度)</th>
      <th>现有预防/探测控制</th>
      <th>O (频度)</th>
      <th>D (探测度)</th>
      <th>RPN 风险数</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>关键齿面装配</td>
      <td>反向间隙超差 (>1.0 arcmin)</td>
      <td>减速机运行异响、传动精度下降</td>
      <td><strong>8</strong></td>
      <td>高精度千分表 100% 测量，CCD 视觉比对</td>
      <td>3</td>
      <td>2</td>
      <td><strong>48 (受控)</strong></td>
    </tr>
    <tr>
      <td>轴承压装工序</td>
      <td>压装压力未到位或倾斜</td>
      <td>运转卡顿、发热温升超标、寿命锐减</td>
      <td><strong>7</strong></td>
      <td>智能伺服压机实时位移-压力监控曲线</td>
      <td>2</td>
      <td>2</td>
      <td><strong>28 (低风险)</strong></td>
    </tr>
  </tbody>
</table>
"""
            elif "抽样" in payload.prompt or "AQL" in p_upper or "2828" in payload.prompt:
                fallback_html = f"""
{ref_badge}
<h2>【GB/T 2828.1 进料抽样检验标准与判定准则】</h2>
<p>依据标准条款：<strong>{payload.prompt}</strong></p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th>批量范围 (Lot Size)</th>
      <th>检验水平</th>
      <th>样本量 (n)</th>
      <th>致命缺陷 (CRI) AQL 0</th>
      <th>主要缺陷 (MAJ) AQL 0.40</th>
      <th>次要缺陷 (MIN) AQL 1.0</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>501 ~ 1200 件</td>
      <td>一般检验水平 II</td>
      <td>80 件</td>
      <td>[0 接收, 1 拒收]</td>
      <td>[1 接收, 2 拒收]</td>
      <td>[2 接收, 3 拒收]</td>
    </tr>
    <tr>
      <td>1201 ~ 3200 件</td>
      <td>一般检验水平 II</td>
      <td>125 件</td>
      <td>[0 接收, 1 拒收]</td>
      <td>[1 接收, 2 拒收]</td>
      <td>[3 接收, 4 拒收]</td>
    </tr>
  </tbody>
</table>
<div style="background:#fef2f2;border:1px solid #fecaca;padding:10px;border-radius:4px;color:#991b1b;margin-top:10px;">
  <strong>质量红线准则：</strong>凡出现安全特性的致命缺陷 (CRI)，整批无条件判退 (Re=1)，并立即对供应商开具 CAR 纠正通知书。
</div>
"""
            else:
                fallback_html = f"""
{ref_badge}
<h2>【质量作业指引与控制规程】</h2>
<p>针对「<strong>{payload.prompt}</strong>」的执行要求，结合知识库质量基准，制定以下标准化实施细则：</p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;" border="1">
  <thead>
    <tr style="background:#f8fafc;">
      <th>工序环节</th>
      <th>关键控制要素 (CTQ)</th>
      <th>检验标准与公差</th>
      <th>处置与阻断动作</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1. 首件确认 (FAI)</strong></td>
      <td>关键尺寸、装配间隙、原厂COA</td>
      <td>Cpk ≥ 1.33 / 100% 合格</td>
      <td>首件未通过严禁批量开机</td>
    </tr>
    <tr>
      <td><strong>2. 制程抽检 (IPQC)</strong></td>
      <td>运行转矩、温升、表面缺陷</td>
      <td>符合图纸与检验作业指导书</td>
      <td>发现连续2件不良立即停线遏制</td>
    </tr>
    <tr>
      <td><strong>3. 批次放行 (OQC)</strong></td>
      <td>出厂报告与批次条码一致性</td>
      <td>AQL 0.40 允收标准</td>
      <td>不合格批次全数锁仓隔离并提报8D</td>
    </tr>
  </tbody>
</table>
<h2>二、 现场核查与防错清单 (Poka-Yoke)</h2>
<ul>
  <li>机台校准标签是否在有效校验周期内；</li>
  <li>不良品隔离箱是否上锁并附红牌警示；</li>
  <li>关键参数测量数据是否已录入 SPC 控制图。</li>
</ul>
<p></p>
"""
            # 模拟打字机流式输出 (以每片 18 字符打字平滑吐出)
            step_size = 18
            for i in range(0, len(fallback_html), step_size):
                chunk = fallback_html[i:i+step_size]
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                time.sleep(0.02)

        # 结束帧
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ========================================================
# Windows 资源管理器风格交互 API
# ========================================================

@router.get("/explorer/favorites", response_model=List[KbExplorerItem], summary="获取全库所有已标星规程文档 (跨目录全量聚合)")
def get_explorer_favorites(db: Session = Depends(get_db)):
    seed_initial_kb_docs(db)
    # 查找全库所有标星且非文件夹的项目
    records = db.query(SqmKbDoc).filter(
        SqmKbDoc.is_favorite == True,
        SqmKbDoc.is_folder == False
    ).order_by(desc(SqmKbDoc.updated_at)).all()

    # 预加载父目录名称做归属展示
    parent_ids = [r.parent_id for r in records if r.parent_id]
    parent_map = {}
    if parent_ids:
        parents = db.query(SqmKbDoc).filter(SqmKbDoc.id.in_(parent_ids)).all()
        parent_map = {p.id: p.title for p in parents}

    items = []
    for r in records:
        is_shortcut = (r.biz_type == "SHORTCUT") and (r.biz_id is not None)
        target_doc = None
        if is_shortcut:
            target_doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == r.biz_id).first()

        metadata = file_metadata(db, r)
        item_type = "file" if metadata else "shortcut" if is_shortcut else "doc"
        content_html = target_doc.content_html if target_doc else r.content_html
        content_text = target_doc.content_text if target_doc else r.content_text

        # 归属目录信息
        parent_title = parent_map.get(r.parent_id, "知识库根目录")
        proj_str = f"📁 {parent_title}"

        items.append(KbExplorerItem(
            id=r.id,
            name=r.title,
            type=item_type,
            icon=r.icon or "📄",
            date=r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else "",
            proj=proj_str,
            size=f"{len(content_text or '')} 字",
            is_favorite=True,
            status=r.status or "ACTIVE",
            is_shortcut=is_shortcut,
            target_id=r.biz_id if is_shortcut else None,
            author=target_doc.author if target_doc else r.author,
            content_html=content_html,
            content_text=content_text,
            **metadata
        ))
    return items


@router.get("/explorer/items", response_model=List[KbExplorerItem], summary="获取指定文件夹下的文件与子目录列表 (Windows资源管理器风格)")
def get_explorer_items(
    folder_id: Optional[int] = Query(None, description="文件夹ID，为空时返回根目录"),
    only_favorites: bool = Query(False, description="仅返回所有标星/收藏文档"),
    db: Session = Depends(get_db)
):
    if only_favorites:
        return get_explorer_favorites(db)

    seed_initial_kb_docs(db)
    query = db.query(SqmKbDoc)
    if folder_id is None:
        query = query.filter(SqmKbDoc.parent_id.is_(None))
    else:
        query = query.filter(SqmKbDoc.parent_id == folder_id)

    # 与导航树保持一致，刷新后保留拖放确定的同级顺序。
    records = query.order_by(SqmKbDoc.sort_order.asc(), SqmKbDoc.id.asc()).all()

    items = []
    for r in records:
        is_shortcut = (r.biz_type == "SHORTCUT") and (r.biz_id is not None)
        target_doc = None
        if is_shortcut:
            target_doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == r.biz_id).first()

        metadata = file_metadata(db, r)
        item_type = "folder" if r.is_folder else "file" if metadata else ("shortcut" if is_shortcut else "doc")

        # 内容与大小计算
        content_html = target_doc.content_html if target_doc else r.content_html
        content_text = target_doc.content_text if target_doc else r.content_text

        if r.is_folder:
            size_str = None
            proj_str = r.biz_type or "工程目录"
        elif is_shortcut:
            size_str = f"软引用 ({len(content_text or '')} 字)"
            proj_str = f"🔗 引用自: {target_doc.title}" if target_doc else "⚠️ 失效快捷方式"
        else:
            size_str = f"{len(content_text or '')} 字"
            proj_str = r.biz_type or "质量规范"

        items.append(KbExplorerItem(
            id=r.id,
            name=r.title,
            type=item_type,
            icon=r.icon or ("📁" if r.is_folder else "📄"),
            date=r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else "",
            proj=proj_str,
            size=size_str,
            is_favorite=bool(r.is_favorite),
            status=r.status or "ACTIVE",
            is_shortcut=is_shortcut,
            target_id=r.biz_id if is_shortcut else None,
            author=target_doc.author if target_doc else r.author,
            content_html=content_html,
            content_text=content_text,
            **metadata
        ))
    return items


@router.get("/explorer/path", response_model=List[KbBreadcrumbNode], summary="溯源获取当前文件夹的面包屑路径链")
def get_explorer_path(folder_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    crumbs = [{"id": None, "name": "质量知识库"}]
    if not folder_id:
        return crumbs

    curr_id = folder_id
    chain = []
    visited = set()
    while curr_id and curr_id not in visited:
        visited.add(curr_id)
        doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == curr_id).first()
        if not doc:
            break
        chain.append({"id": doc.id, "name": doc.title})
        curr_id = doc.parent_id

    chain.reverse()
    crumbs.extend(chain)
    return crumbs


@router.post("/explorer/folder", response_model=KbExplorerItem, summary="快速新建文件夹 (Windows风格)")
def create_explorer_folder(payload: KbFolderCreate, db: Session = Depends(get_db)):
    folder = SqmKbDoc(
        parent_id=payload.parent_id,
        title=payload.name.strip() or "新建文件夹",
        icon=payload.icon or "📁",
        is_folder=True,
        biz_type=payload.biz_type or "FOLDER"
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return KbExplorerItem(
        id=folder.id,
        name=folder.title,
        type="folder",
        icon=folder.icon,
        date=folder.updated_at.strftime("%Y-%m-%d %H:%M"),
        proj="工程目录",
        size=None,
        is_shortcut=False,
        target_id=None,
        author=folder.author
    )


@router.post("/explorer/doc", response_model=KbExplorerItem, summary="快速新建规程文档")
def create_explorer_doc(payload: KbDocFastCreate, db: Session = Depends(get_db)):
    doc = SqmKbDoc(
        parent_id=payload.parent_id,
        title=payload.name.strip() or "新建质量规程文档.doc",
        icon=payload.icon or "📄",
        is_folder=False,
        biz_type=payload.biz_type or "DOC",
        content_html="<h2>一、 编制目的与适用范围</h2><p>在此编写标准检验作业要求及控制计划...</p>",
        content_text="一、 编制目的与适用范围 在此编写标准检验作业要求及控制计划..."
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return KbExplorerItem(
        id=doc.id,
        name=doc.title,
        type="doc",
        icon=doc.icon,
        date=doc.updated_at.strftime("%Y-%m-%d %H:%M"),
        proj="质量规范",
        size="38 字",
        is_shortcut=False,
        target_id=None,
        author=doc.author,
        content_html=doc.content_html,
        content_text=doc.content_text
    )


@router.post("/explorer/shortcut", response_model=KbExplorerItem, summary="为文档创建跨项目快捷方式 (软引用)")
def create_explorer_shortcut(payload: KbShortcutCreate, db: Session = Depends(get_db)):
    target = db.query(SqmKbDoc).filter(SqmKbDoc.id == payload.target_doc_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="目标源文档不存在")

    name = payload.name.strip() if payload.name else f"{target.title} - 快捷方式.lnk"
    shortcut = SqmKbDoc(
        parent_id=payload.parent_id,
        title=name,
        icon=target.icon or "📄",
        is_folder=False,
        biz_type="SHORTCUT",
        biz_id=target.id
    )
    db.add(shortcut)
    db.commit()
    db.refresh(shortcut)

    return KbExplorerItem(
        id=shortcut.id,
        name=shortcut.title,
        type="shortcut",
        icon=shortcut.icon,
        date=shortcut.updated_at.strftime("%Y-%m-%d %H:%M"),
        proj=f"🔗 引用自: {target.title}",
        size=f"软引用 ({len(target.content_text or '')} 字)",
        is_shortcut=True,
        target_id=target.id,
        author=target.author,
        content_html=target.content_html,
        content_text=target.content_text
    )


@router.put("/explorer/rename", summary="重命名文件或文件夹")
def rename_explorer_item(payload: KbItemRename, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == payload.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="指定项目不存在")
    doc.title = payload.name.strip()
    db.commit()
    return {"message": "重命名成功", "id": doc.id, "name": doc.title}


@router.put("/explorer/icon", summary="修改文件或文件夹图标")
def update_explorer_icon(payload: KbItemIconUpdate, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == payload.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="指定项目不存在")
    doc.icon = payload.icon.strip()
    db.commit()
    return {"message": "图标更新成功", "id": doc.id, "icon": doc.icon}


@router.put("/explorer/move", summary="移动文件或文件夹至新目录")
def move_explorer_item(payload: KbItemMove, db: Session = Depends(get_db)):
    doc = db.get(SqmKbDoc, payload.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="指定项目不存在")
    _move_kb_item(
        db, doc, payload.target_folder_id,
        reference_id=payload.reference_id, placement=payload.placement,
    )
    return {"message": "移动成功", "id": doc.id, "parent_id": doc.parent_id}


@router.delete("/explorer/items/{item_id}", summary="删除文件、文件夹或快捷方式")
def delete_explorer_item(item_id: int, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == item_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="项目不存在")
    result = delete_kb_doc(item_id, db)
    return {**result, "id": item_id}


@router.put("/explorer/favorite/{item_id}", summary="切换标星/收藏状态")
def toggle_explorer_favorite(item_id: int, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == item_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="项目不存在")
    doc.is_favorite = not bool(doc.is_favorite)
    db.commit()
    return {"id": doc.id, "is_favorite": doc.is_favorite}


@router.put("/explorer/status/{item_id}", summary="修改文档生命周期状态")
def update_explorer_status(item_id: int, payload: KbItemStatusUpdate, db: Session = Depends(get_db)):
    doc = db.query(SqmKbDoc).filter(SqmKbDoc.id == item_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="项目不存在")
    doc.status = payload.status
    db.commit()
    return {"id": doc.id, "status": doc.status}



