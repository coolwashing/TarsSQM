import re
import html
import json
import uuid
import urllib.parse
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Set

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.core.config import settings
from app.core.database import get_db, Base, engine
from app.models.fmea import SqmFmeaBoard, SqmFmeaItem
from app.models.main_data import SqmPart, SqmSupplier, SqmProject
from app.models.sqm_quality import SqmQualityIssue
from app.models.ctq import SqmCtq
from app.schemas.fmea import (
    FmeaBoardCreate,
    FmeaBoardUpdate,
    FmeaGroupRenameReq,
    FmeaBoardDuplicateReq,
    SubBoardRollupStat,
    WhereUsedRefOut,
    SharedUnitOptionOut,
    FmeaBomChildSummary,
    FmeaBoardSummaryOut,
    FmeaBoardGroupNode,
    FmeaBoardTreeResp,
    FmeaBoardDetailOut,
    FmeaItemCreate,
    FmeaItemUpdate,
    FmeaItemOut,
    FmeaItemPageResult,
    SoftRefSuggestItem,
    SoftRefResolveReq,
    SoftRefSnapshotOut,
    FmeaAiParseReq,
    FmeaAiParseDraft,
    FmeaAiParseResp,
    DepositFromQualityIssueReq,
    FmeaLinkedRefSchema,
)

router = APIRouter(prefix="/api/fmea", tags=["6. FMEA 视觉风险画板与经验库"])

# 启动自动确保 FMEA 双表存在
Base.metadata.create_all(bind=engine)


# ==============================================================================
# 内部工具函数
# ==============================================================================

def _svg_uri(svg_markup: str) -> str:
    compact = re.sub(r"\s+", " ", svg_markup.strip())
    return f"data:image/svg+xml;utf8,{urllib.parse.quote(compact)}"


def _strip_html(raw: Optional[str]) -> str:
    if not raw:
        return ""
    text_val = re.sub(r"<[^>]+>", " ", raw)
    text_val = re.sub(r"\s+", " ", text_val)
    return html.unescape(text_val).strip()


def _extract_img_urls_from_html(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', raw, flags=re.IGNORECASE)


def _generate_board_code(db: Session) -> str:
    prefix = "BRD-"
    count = db.query(SqmFmeaBoard).count() + 1
    candidate = f"{prefix}{datetime.now().strftime('%m%d')}-{str(count).zfill(2)}"
    if db.query(SqmFmeaBoard).filter(SqmFmeaBoard.board_code == candidate).first():
        return f"{prefix}{uuid.uuid4().hex[:6].upper()}"
    return candidate


def _generate_fmea_code(db: Session) -> str:
    prefix = datetime.now().strftime("FMEA-%Y%m-")
    last_item = (
        db.query(SqmFmeaItem)
        .filter(SqmFmeaItem.fmea_code.like(f"{prefix}%"))
        .order_by(SqmFmeaItem.id.desc())
        .first()
    )
    if not last_item or not last_item.fmea_code:
        return f"{prefix}001"
    try:
        seq = int(last_item.fmea_code.split("-")[-1]) + 1
        candidate = f"{prefix}{str(seq).zfill(3)}"
        if db.query(SqmFmeaItem).filter(SqmFmeaItem.fmea_code == candidate).first():
            return f"{prefix}{uuid.uuid4().hex[:4].upper()}"
        return candidate
    except Exception:
        return f"{prefix}{uuid.uuid4().hex[:4].upper()}"


def _normalize_refs_and_index(refs_raw: Optional[List[Any]]) -> Tuple[List[Dict[str, Any]], str]:
    if not refs_raw:
        return [], ""
    normalized: List[Dict[str, Any]] = []
    tokens: List[str] = []
    seen = set()
    for r in refs_raw:
        d = r.model_dump() if hasattr(r, "model_dump") else dict(r)
        r_type = str(d.get("type") or "free").strip().lower()
        code = str(d.get("code") or "").strip() or None
        label = str(d.get("label") or code or "").strip()
        if not label:
            continue
        ref_id = d.get("ref_id")
        dedup_key = f"{r_type}:{code or ''}:{label}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        normalized.append({
            "type": r_type,
            "ref_id": int(ref_id) if isinstance(ref_id, int) or (isinstance(ref_id, str) and ref_id.isdigit()) else None,
            "code": code,
            "label": label,
        })
        if code:
            tokens.append(code)
        tokens.append(label)
    return normalized, " ".join(tokens)[:495]


def _normalize_photos(photos_raw: Optional[List[Any]]) -> List[Dict[str, Any]]:
    if not photos_raw:
        return []
    out: List[Dict[str, Any]] = []
    for idx, p in enumerate(photos_raw):
        d = p.model_dump() if hasattr(p, "model_dump") else dict(p)
        url = str(d.get("url") or "").strip()
        if not url:
            continue
        tag = str(d.get("tag") or "NG").upper()
        if tag not in ("NG", "OK"):
            tag = "NG"
        out.append({
            "id": d.get("id") or f"ph_{idx + 1}_{uuid.uuid4().hex[:4]}",
            "attachment_id": d.get("attachment_id"),
            "url": url,
            "tag": tag,
            "caption": str(d.get("caption") or "").strip()[:120],
        })
    return out


def _compute_sod_and_risk(
    explicit_risk: Optional[str],
    s: Optional[int],
    o: Optional[int],
    d: Optional[int],
) -> Tuple[str, Optional[int]]:
    rpn: Optional[int] = None
    if s is not None and o is not None and d is not None:
        rpn = int(s) * int(o) * int(d)

    clean_risk = (explicit_risk or "").strip().upper()
    if clean_risk in ("HIGH", "MED", "LOW"):
        return clean_risk, rpn

    if rpn is not None:
        if rpn >= 100 or (s is not None and s >= 9):
            return "HIGH", rpn
        if rpn >= 40 or (s is not None and s >= 6):
            return "MED", rpn
        return "LOW", rpn

    return "MED", None


def _item_to_out(
    item: SqmFmeaItem,
    board_name: Optional[str] = None,
    board_group: Optional[str] = None,
) -> FmeaItemOut:
    resolved_bname = board_name or (item.board.name if item.board else None)
    resolved_bgroup = board_group or (item.board.group_name if item.board else None)
    if item.target_kind == "shared_unit" and not resolved_bname:
        resolved_bname = f"共用单元 ({item.target_id or '-'})"
        resolved_bgroup = "跨画板共用经验"

    return FmeaItemOut(
        id=item.id,
        fmea_code=item.fmea_code,
        board_id=item.board_id,
        board_name=resolved_bname,
        board_group=resolved_bgroup,
        target_kind=item.target_kind or "unassigned",
        target_id=item.target_id,
        target_title_snapshot=item.target_title_snapshot,
        fmea_type=item.fmea_type or "DFMEA",
        failure_mode=item.failure_mode,
        failure_mech=item.failure_mech,
        failure_effect=item.failure_effect,
        control_measure=item.control_measure,
        prevention_measure=item.prevention_measure,
        detection_measure=item.detection_measure,
        risk_level=item.risk_level or "MED",
        severity=item.severity,
        occurrence=item.occurrence,
        detection=item.detection,
        rpn=item.rpn,
        photos=item.photos if isinstance(item.photos, list) else [],
        linked_refs=item.linked_refs if isinstance(item.linked_refs, list) else [],
        ref_codes_text=item.ref_codes_text,
        source_issue_no=item.source_issue_no,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _extract_board_unit_codes(canvas_data: Any) -> Set[str]:
    if not isinstance(canvas_data, dict):
        return set()
    codes: Set[str] = set()
    for nd in canvas_data.get("nodes") or []:
        if isinstance(nd, dict):
            uc = str(nd.get("unit_code") or "").strip()
            if uc:
                codes.add(uc)
    return codes


def _extract_board_sub_ids(canvas_data: Any) -> Set[int]:
    if not isinstance(canvas_data, dict):
        return set()
    sub_ids: Set[int] = set()
    for nd in canvas_data.get("nodes") or []:
        if isinstance(nd, dict) and nd.get("sub_board_id"):
            try:
                sub_ids.add(int(nd["sub_board_id"]))
            except Exception:
                pass
    return sub_ids


def _compute_board_effective_stats(
    boards: List[SqmFmeaBoard],
    db: Session,
) -> Dict[int, Dict[str, int]]:
    """
    计算每张画板的有效机理统计（自身局部卡片 + 画板上引用共用单元 unit_code 关联的本体卡片）。
    """
    all_rows = db.query(
        SqmFmeaItem.board_id,
        SqmFmeaItem.target_kind,
        SqmFmeaItem.target_id,
        SqmFmeaItem.risk_level,
        SqmFmeaItem.photos,
    ).all()

    local_map: Dict[int, Dict[str, int]] = {}
    shared_unit_map: Dict[str, Dict[str, int]] = {}

    for b_id, t_kind, t_id, r_lvl, phs in all_rows:
        ph_cnt = len(phs) if isinstance(phs, list) else 0
        if t_kind == "shared_unit" and t_id:
            ust = shared_unit_map.setdefault(str(t_id), {"total": 0, "high": 0, "photos": 0})
            ust["total"] += 1
            if r_lvl == "HIGH":
                ust["high"] += 1
            ust["photos"] += ph_cnt
        elif b_id:
            st = local_map.setdefault(int(b_id), {"total": 0, "high": 0, "photos": 0})
            st["total"] += 1
            if r_lvl == "HIGH":
                st["high"] += 1
            st["photos"] += ph_cnt

    effective: Dict[int, Dict[str, int]] = {}
    for b in boards:
        base = dict(local_map.get(b.id, {"total": 0, "high": 0, "photos": 0}))
        for uc in _extract_board_unit_codes(b.canvas_data):
            ust = shared_unit_map.get(uc)
            if ust:
                base["total"] += ust["total"]
                base["high"] += ust["high"]
                base["photos"] += ust["photos"]
        effective[b.id] = base
    return effective


def _validate_no_bom_cycle(board_id: int, new_canvas_data: Dict[str, Any], db: Session) -> None:
    direct_subs = _extract_board_sub_ids(new_canvas_data)
    if not direct_subs:
        return
    if board_id in direct_subs:
        raise HTTPException(status_code=400, detail="不能将当前画板自身作为子模块嵌入（防止循环嵌套）")

    all_boards = db.query(SqmFmeaBoard.id, SqmFmeaBoard.canvas_data).all()
    adj: Dict[int, Set[int]] = {
        b_id: _extract_board_sub_ids(cdata)
        for b_id, cdata in all_boards
    }
    adj[board_id] = direct_subs

    visited: Set[int] = set()
    stack = list(direct_subs)
    while stack:
        curr = stack.pop()
        if curr == board_id:
            raise HTTPException(status_code=400, detail="检测到多级 BOM 画板循环嵌套，不能将上级父画板嵌入子画板")
        if curr in visited:
            continue
        visited.add(curr)
        stack.extend(adj.get(curr, set()))


# ==============================================================================
# 预置示范画板种子数据与多父级 BOM 增量升级
# ==============================================================================

_BOM_DEMO_CHECKED = False


def _ensure_bom_demo_upgrade(db: Session, force: bool = False) -> None:
    """
    确保预置示范数据具备完整的多父级 BOM 借用与子画板下钻示范：
    1) 共用件本体单元 (unit_code = 'PRT-109' 交叉滚子轴承等) 与跨画板本体机理卡 FMEA-SHARED-109；
    2) 顶层总成画板『00_整机与分系统总成 / 双足下肢执行系统总成 (BRD-SYS-LEG)』，
       内含髋/膝两个『二代旋转关节模组』子画板节点（支持双击下钻）及共用『踝部交叉滚子轴承』。
    """
    global _BOM_DEMO_CHECKED
    if _BOM_DEMO_CHECKED and not force:
        return
    _BOM_DEMO_CHECKED = True

    b_act = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.board_code == "BRD-ACT-G2").first()
    if not b_act:
        return

    # 0. 确保一条真实的设计极限-制造工艺冲突质量问题单 (QI-20261018-001)
    q_issue = db.query(SqmQualityIssue).filter(SqmQualityIssue.issue_no == "QI-20261018-001").first()
    if not q_issue:
        q_issue = SqmQualityIssue(
            issue_no="QI-20261018-001",
            title="柔轮齿根成型刀具异常磨损致微裂纹超差批次报废",
            severity="严重",
            status="已验证",
            issue_desc="试制批铣削加工中，因柔轮图纸标注 R0.15 极小过渡圆角（已逼近金刚石涂层专用铣刀刀尖物理强度极限），连续铣削至第 42 件后刀具微崩钝化，造成齿根显微撕裂纹与应力集中，现场加工报废 12 件。",
            solution="【工艺临时对策】缩短对刀与强制换刀周期至每 30 件一次；【设计与工艺协同】发起 DFM 评审，建议将非啮合段过渡圆角放宽至 R0.25+大圆角，或改用缓进给成型磨削工艺替代普通铣齿。",
            responsible="张工 (工艺组)",
            defect_qty=12,
            batch_qty=60,
        )
        db.add(q_issue)
        db.flush()

    changed = False
    if isinstance(b_act.canvas_data, dict):
        cdata = json.loads(json.dumps(b_act.canvas_data))
        node_mut = False
        for nd in cdata.get("nodes") or []:
            if nd.get("sub") in ("PRT-109", "PRT-102", "PRT-115", "PRT-205") and not nd.get("unit_code"):
                nd["unit_code"] = nd["sub"]
                node_mut = True

        # 图纸设计极限标记：柔轮齿根过渡圆角 (pin_1)
        for ib in cdata.get("image_boards") or []:
            for p in ib.get("pins") or []:
                if p.get("id") == "pin_1" and not p.get("is_limit"):
                    p["is_limit"] = True
                    p["limit_spec"] = "R0.15 极小过渡圆角 (专用成型铣刀极限)"
                    node_mut = True

        # 工序节点与制程挑战连线
        nodes = cdata.setdefault("nodes", [])
        if not any(n.get("id") == "nd_mill" for n in nodes):
            nodes.append({
                "id": "nd_mill",
                "title": "柔轮精密铣齿工序",
                "sub": "OP-FLEX-MILL",
                "x": 790,
                "y": 44,
            })
            node_mut = True

        edges = cdata.setdefault("edges", [])
        if not any(e.get("id") == "ed_limit_challenge" for e in edges):
            edges.append({
                "id": "ed_limit_challenge",
                "from": "nd_flex",
                "fromPort": "right",
                "to": "nd_mill",
                "toPort": "left",
                "label": "极限圆角致刀具微崩",
                "sub": "R0.15成型刀刃口极限磨损超差",
                "kind": "process_challenge",
            })
            node_mut = True

        if node_mut:
            b_act.canvas_data = cdata
            changed = True

    # 挂接至 pin_1 对应的 FMEA 机理卡
    it_pin1 = (
        db.query(SqmFmeaItem)
        .filter(SqmFmeaItem.board_id == b_act.id, SqmFmeaItem.target_id == "pin_1")
        .first()
    )
    if it_pin1:
        it_pin1.source_issue_no = "QI-20261018-001"
        curr_refs = list(it_pin1.linked_refs or [])
        if not any(r.get("code") == "QI-20261018-001" for r in curr_refs):
            curr_refs.append({
                "type": "issue",
                "ref_id": q_issue.id if q_issue else None,
                "code": "QI-20261018-001",
                "label": "柔轮齿根成型刀具异常磨损致微裂纹超差批次报废",
            })
            it_pin1.linked_refs, it_pin1.ref_codes_text = _normalize_refs_and_index(curr_refs)
            changed = True

    has_shared_109 = (
        db.query(SqmFmeaItem)
        .filter(SqmFmeaItem.target_kind == "shared_unit", SqmFmeaItem.target_id == "PRT-109")
        .first()
    )
    if not has_shared_109:
        refs_109, txt_109 = _normalize_refs_and_index([
            {"type": "part", "ref_id": None, "code": "PRT-109", "label": "交叉滚子轴承"},
            {"type": "free", "ref_id": None, "code": None, "label": "跨模组共用轴承本体防错"},
        ])
        db.add(SqmFmeaItem(
            fmea_code="FMEA-SHARED-109",
            board_id=None,
            target_kind="shared_unit",
            target_id="PRT-109",
            target_title_snapshot="交叉滚子轴承 (共用本体)",
            fmea_type="DFMEA",
            failure_mode="滚道高频微摆动假性布氏压痕剥落",
            failure_mech="小角度往复微动工况下油膜破裂，接触区产生微动磨损与次表层疲劳剥落。",
            failure_effect="关节回转阻尼增大、轴向倾覆刚度下降并伴随异响。",
            control_measure="滚道渗碳淬火 HRC58-62 + 极压抗微动润滑脂；所有借用该轴承的模组每 20h 安排全行程润脂摆动。",
            risk_level="HIGH",
            severity=8,
            occurrence=4,
            detection=4,
            rpn=128,
            photos=[],
            linked_refs=refs_109,
            ref_codes_text=txt_109,
        ))
        changed = True

    b_leg = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.board_code == "BRD-SYS-LEG").first()
    if not b_leg and (force or db.query(SqmFmeaBoard).count() <= 3):
        b_leg = SqmFmeaBoard(
            board_code="BRD-SYS-LEG",
            group_name="00_整机与分系统总成",
            name="双足下肢执行系统总成",
            board_type="DFMEA",
            description="系统级多父集 BOM 画板：内嵌髋/膝『二代旋转关节模组』子画板（双击下钻）并跨画板共用 PRT-109 轴承",
            sort_order=0,
            canvas_data={
                "viewport": {"panX": 48, "panY": 44, "zoom": 1.0},
                "image_boards": [],
                "nodes": [
                    {
                        "id": "nd_pwr_bus",
                        "title": "48V下肢主控配电板",
                        "sub": "PRT-801",
                        "x": 64,
                        "y": 124,
                    },
                    {
                        "id": "nd_hip_sub",
                        "title": "髋关节·旋转模组",
                        "sub": "BRD-ACT-G2",
                        "sub_board_id": b_act.id,
                        "x": 356,
                        "y": 48,
                    },
                    {
                        "id": "nd_knee_sub",
                        "title": "膝关节·旋转模组",
                        "sub": "BRD-ACT-G2",
                        "sub_board_id": b_act.id,
                        "x": 356,
                        "y": 198,
                    },
                    {
                        "id": "nd_ankle_brg",
                        "title": "踝部交叉滚子轴承",
                        "sub": "PRT-109",
                        "unit_code": "PRT-109",
                        "x": 652,
                        "y": 124,
                    },
                ],
                "edges": [
                    {
                        "id": "ed_bus_surge",
                        "from": "nd_pwr_bus",
                        "fromPort": "right",
                        "to": "nd_hip_sub",
                        "toPort": "left",
                        "label": "反电势浪涌",
                        "sub": "急停制动母线电压泵升接口",
                    },
                    {
                        "id": "ed_can_sync",
                        "from": "nd_pwr_bus",
                        "fromPort": "right",
                        "to": "nd_knee_sub",
                        "toPort": "left",
                        "label": "运动帧抖动",
                        "sub": "EtherCAT/CANFD菊花链线束",
                    },
                    {
                        "id": "ed_impact_load",
                        "from": "nd_knee_sub",
                        "fromPort": "right",
                        "to": "nd_ankle_brg",
                        "toPort": "left",
                        "label": "落地冲击",
                        "sub": "足端着地轴向冲击力传递",
                    },
                ],
            },
        )
        db.add(b_leg)
        db.flush()

        refs_leg, txt_leg = _normalize_refs_and_index([
            {"type": "part", "ref_id": None, "code": "PRT-801", "label": "48V下肢主控配电板"},
            {"type": "free", "ref_id": None, "code": None, "label": "TVS泄放斩波回路"},
        ])
        db.add(SqmFmeaItem(
            fmea_code="FMEA-SYS-001",
            board_id=b_leg.id,
            target_kind="edge",
            target_id="ed_bus_surge",
            target_title_snapshot="反电势浪涌",
            fmea_type="DFMEA",
            failure_mode="髋膝双关节同时急停再生制动击穿母线MOS",
            failure_mech="下坡急停时再生能量回灌 48V 母线瞬间泵升至 68V，超过驱动板 60V 耐压极限。",
            failure_effect="下肢掉电失力摔倒，主控驱动烧毁。",
            control_measure="配电板增设 56V 主动泄放斩波电阻回路 + 软硬件母线过压分级限扭保护。",
            risk_level="HIGH",
            severity=9,
            occurrence=3,
            detection=4,
            rpn=108,
            photos=[],
            linked_refs=refs_leg,
            ref_codes_text=txt_leg,
        ))
        changed = True

    if changed:
        db.commit()


def seed_initial_fmea_boards(db: Session, force_missing: bool = False) -> None:
    if not force_missing and db.query(SqmFmeaBoard).count() > 0:
        _ensure_bom_demo_upgrade(db, force=False)
        return

    existing_codes = {r[0] for r in db.query(SqmFmeaBoard.board_code).all()}

    joint_blueprint_svg = _svg_uri("""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 340">
      <rect width="520" height="340" rx="12" fill="#0f172a"/>
      <g stroke="#1e293b" stroke-width="1">
        <line x1="0" y1="170" x2="520" y2="170" stroke="#334155" stroke-dasharray="6 4"/>
        <rect x="44" y="48" width="432" height="244" rx="8" fill="none" stroke="#334155"/>
      </g>
      <rect x="66" y="78" width="28" height="184" rx="4" fill="#064e3b" stroke="#10b981" stroke-width="1.5"/>
      <text x="80" y="68" fill="#6ee7b7" font-size="11" font-family="sans-serif" text-anchor="middle">磁编/驱动</text>
      <rect x="118" y="84" width="136" height="62" rx="5" fill="#1e1b4b" stroke="#818cf8" stroke-width="1.5"/>
      <line x1="118" y1="84" x2="254" y2="146" stroke="#6366f1" stroke-width="1.2"/>
      <line x1="254" y1="84" x2="118" y2="146" stroke="#6366f1" stroke-width="1.2"/>
      <rect x="118" y="194" width="136" height="62" rx="5" fill="#1e1b4b" stroke="#818cf8" stroke-width="1.5"/>
      <line x1="118" y1="194" x2="254" y2="256" stroke="#6366f1" stroke-width="1.2"/>
      <line x1="254" y1="194" x2="118" y2="256" stroke="#6366f1" stroke-width="1.2"/>
      <text x="186" y="72" fill="#a5b4fc" font-size="11" font-family="sans-serif" text-anchor="middle">无框电机定子绕组</text>
      <path d="M278 92 H356 V142 H302 V198 H356 V248 H278 Z" fill="#0c4a6e" stroke="#38bdf8" stroke-width="1.6"/>
      <text x="318" y="78" fill="#7dd3fc" font-size="11" font-family="sans-serif" text-anchor="middle">柔轮啮合杯体</text>
      <rect x="374" y="86" width="76" height="66" rx="6" fill="#422006" stroke="#f59e0b" stroke-width="1.5"/>
      <circle cx="412" cy="119" r="18" fill="none" stroke="#fbbf24" stroke-width="1.5"/>
      <rect x="374" y="188" width="76" height="66" rx="6" fill="#422006" stroke="#f59e0b" stroke-width="1.5"/>
      <circle cx="412" cy="221" r="18" fill="none" stroke="#fbbf24" stroke-width="1.5"/>
      <text x="412" y="72" fill="#fcd34d" font-size="11" font-family="sans-serif" text-anchor="middle">交叉滚子/油封</text>
      <rect x="96" y="152" width="356" height="36" rx="4" fill="#1e293b" stroke="#64748b" stroke-width="1.4"/>
      <text x="462" y="316" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">ASSY-ROT-JOINT-G2</text>
    </svg>
    """)

    ng_crack_svg = _svg_uri("""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">
      <rect width="320" height="180" fill="#18181b"/>
      <path d="M36 144 H140 Q152 144 152 132 V52 H268" fill="none" stroke="#71717a" stroke-width="4"/>
      <path d="M150 136 L168 118 L162 106 L184 90 L179 76" fill="none" stroke="#ef4444" stroke-width="3" stroke-linecap="round"/>
      <circle cx="164" cy="112" r="26" fill="none" stroke="#f87171" stroke-width="1.5" stroke-dasharray="4 3"/>
      <text x="24" y="32" fill="#fca5a5" font-size="12" font-family="sans-serif">R0.15 尖角应力集中微裂纹</text>
    </svg>
    """)

    ok_fillet_svg = _svg_uri("""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">
      <rect width="320" height="180" fill="#052e16"/>
      <path d="M36 144 H122 Q164 144 164 102 V52 H268" fill="none" stroke="#34d399" stroke-width="4"/>
      <circle cx="152" cy="116" r="28" fill="none" stroke="#6ee7b7" stroke-width="1.5" stroke-dasharray="4 3"/>
      <text x="24" y="32" fill="#a7f3d0" font-size="12" font-family="sans-serif">R≥0.30 大圆角 + 喷丸强化</text>
    </svg>
    """)

    ng_grease_svg = _svg_uri("""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">
      <rect width="320" height="180" fill="#1f1726"/>
      <circle cx="160" cy="94" r="52" fill="none" stroke="#94a3b8" stroke-width="6" stroke-dasharray="10 6"/>
      <circle cx="182" cy="76" r="14" fill="#f59e0b" opacity="0.85"/>
      <circle cx="198" cy="96" r="9" fill="#ef4444" opacity="0.9"/>
      <circle cx="168" cy="106" r="7" fill="#fbbf24" opacity="0.8"/>
      <text x="22" y="30" fill="#fda4af" font-size="12" font-family="sans-serif">高速运转润滑脂甩入码盘区</text>
    </svg>
    """)

    if "BRD-ACT-G2" not in existing_codes:
        b1 = SqmFmeaBoard(
            board_code="BRD-ACT-G2",
            group_name="关节执行器系统",
            name="二代旋转关节模组",
            board_type="DFMEA",
            description="人形机器人髋/膝旋转执行器总成：涵盖谐波柔轮、无框电机、交叉滚子轴承及双圈磁编接口防错",
            sort_order=1,
            canvas_data={
                "viewport": {"panX": 28, "panY": 28, "zoom": 1.0},
                "image_boards": [
                    {
                        "id": "ib_joint_sec",
                        "title": "二代旋转关节总成剖面图",
                        "img_url": joint_blueprint_svg,
                        "x": 40,
                        "y": 48,
                        "w": 410,
                        "h": 272,
                        "pins": [
                            {
                                "id": "pin_1",
                                "num": 1,
                                "rx": 0.63,
                                "ry": 0.37,
                                "title": "柔轮齿根过渡圆角",
                                "sub": "剖面热点 #1",
                            },
                            {
                                "id": "pin_2",
                                "num": 2,
                                "rx": 0.79,
                                "ry": 0.66,
                                "title": "输出端油封唇口",
                                "sub": "剖面热点 #2",
                            },
                        ],
                    }
                ],
                "nodes": [
                    {"id": "nd_flex", "title": "谐波减速器柔轮", "sub": "PRT-102", "unit_code": "PRT-102", "x": 520, "y": 44},
                    {"id": "nd_bearing", "title": "交叉滚子轴承", "sub": "PRT-109", "unit_code": "PRT-109", "x": 520, "y": 176},
                    {"id": "nd_encoder", "title": "双圈磁编读头", "sub": "PRT-115", "unit_code": "PRT-115", "x": 790, "y": 176},
                    {"id": "nd_stator", "title": "无框力矩电机定子", "sub": "PRT-205", "unit_code": "PRT-205", "x": 520, "y": 304},
                ],
                "edges": [
                    {
                        "id": "ed_grease",
                        "from": "nd_bearing",
                        "fromPort": "right",
                        "to": "nd_encoder",
                        "toPort": "left",
                        "label": "油脂飞溅",
                        "sub": "动密封至编码器光磁间隙",
                    },
                    {
                        "id": "ed_heat",
                        "from": "nd_stator",
                        "fromPort": "top",
                        "to": "nd_bearing",
                        "toPort": "bottom",
                        "label": "温升串扰",
                        "sub": "定子铜损热传导路径",
                    },
                ],
            },
        )
        db.add(b1)
        db.flush()

        seed_items_b1 = [
            (
                "FMEA-202611-001",
                "pin",
                "pin_1",
                "柔轮齿根过渡圆角",
                "DFMEA",
                "柔轮齿根交变疲劳微裂纹",
                "过渡圆角仅 R0.15 产生 2.4 倍应力集中，峰值冲击扭矩 20h 后萌生晶界裂纹。",
                "关节周期异响，极端工况下柔轮杯体撕裂导致关节卡死。",
                "图纸强标齿根圆角 R≥0.30 + 喷丸残余压应力管控；DV 台架正反转峰值冲击 200h 零裂纹。",
                "HIGH",
                9, 4, 4,
                [
                    {"id": "p1", "url": ng_crack_svg, "tag": "NG", "caption": "金相裂纹实拍 (NG)"},
                    {"id": "p2", "url": ok_fillet_svg, "tag": "OK", "caption": "R0.30圆角防错标准 (OK)"},
                ],
                [
                    {"type": "part", "ref_id": None, "code": "PRT-102", "label": "谐波减速器柔轮"},
                    {"type": "supplier", "ref_id": None, "code": "SUP-008", "label": "绿的谐波"},
                    {"type": "issue", "ref_id": None, "code": "QI-20261018-001", "label": "老化20h柔轮齿根裂纹"},
                    {"type": "free", "ref_id": None, "code": None, "label": "三代轻量化柔轮(预研)"},
                ],
            ),
            (
                "FMEA-202611-002",
                "edge",
                "ed_grease",
                "油脂飞溅",
                "DFMEA",
                "高温析油污染磁编码盘致多圈跳变",
                "连续高负载温升超 85℃ 时润滑脂基础油析出，经轴承间隙甩入读头感应面吸附铁屑。",
                "上电零位偏移或运行中报位置跟随超差急停。",
                "增设迷宫式挡油环 + 选用低析油率聚脲基润滑脂；组装注脂量定额称重管控 3.2±0.2g。",
                "HIGH",
                8, 4, 4,
                [{"id": "p3", "url": ng_grease_svg, "tag": "NG", "caption": "码盘油污吸附实拍 (NG)"}],
                [
                    {"type": "part", "ref_id": None, "code": "PRT-109", "label": "交叉滚子轴承"},
                    {"type": "part", "ref_id": None, "code": "PRT-115", "label": "双圈磁编读头"},
                ],
            ),
            (
                "FMEA-202611-003",
                "node",
                "nd_flex",
                "谐波减速器柔轮",
                "DFMEA",
                "柔轮杯底法兰螺栓孔微动磨损松动",
                "法兰端面平面度超 0.015mm 且未涂厌氧胶，交变弯矩下预紧力衰减。",
                "传动回差增大 > 2 arcmin，定位精度劣化。",
                "端面跳动严控 ≤0.008mm，采用 12.9 级螺钉点涂乐泰 243 并执行扭矩+转角监控。",
                "MED",
                6, 3, 3,
                [],
                [{"type": "part", "ref_id": None, "code": "PRT-102", "label": "谐波减速器柔轮"}],
            ),
            (
                "FMEA-202611-004",
                "node",
                "nd_stator",
                "无框力矩电机定子",
                "DFMEA",
                "定子引出线根部灌封胶边缘振动割裂绝缘皮",
                "环氧灌封胶收口呈锐边，高频谐振下硅胶线护套疲劳破损。",
                "定子相线对机壳耐压击穿短路。",
                "引线出口增设氟橡胶护线套缓冲过渡，耐压测试 AC 1500V / 1mA 全检。",
                "HIGH",
                9, 3, 4,
                [],
                [
                    {"type": "part", "ref_id": None, "code": "PRT-205", "label": "无框力矩电机定子"},
                    {"type": "supplier", "ref_id": None, "code": "SUP-015", "label": "步科电气"},
                ],
            ),
            (
                "FMEA-202611-007",
                "node",
                "nd_flex",
                "谐波减速器柔轮",
                "DFMEA",
                "柔轮薄壁杯体在交变过载弯矩下疲劳屈服与椭圆变形",
                "极端加速冲击工况下杯体长径比区域剪应力超过材料屈服极限，产生永久微塑性形变。",
                "柔轮与刚轮啮合干涉，传动阻力剧增甚至扫齿。",
                "有限元瞬态动力学仿真校核杯壁厚度梯度，选用高纯净度马氏体时效钢；激光干涉仪全行程圆度全检。",
                "HIGH",
                9, 3, 4,
                [],
                [{"type": "part", "ref_id": None, "code": "PRT-102", "label": "谐波减速器柔轮"}],
            ),
            (
                "FMEA-202611-008",
                "node",
                "nd_flex",
                "谐波减速器柔轮",
                "DFMEA",
                "柔轮内壁与波发生器轴承外圈微动跑圈磨损",
                "柔轮内孔公差偏大且润滑脂被挤出，波发生器旋转时产生相对滑移微动磨损。",
                "柔轮发生径向偏磨，运动传递波动超差。",
                "内壁增加抗微动耐磨涂层，严控柔轮内径公差等级为 H6；三坐标测量机抽检内孔圆柱度与粗糙度 Ra≤0.4。",
                "MED",
                7, 3, 4,
                [],
                [{"type": "part", "ref_id": None, "code": "PRT-102", "label": "谐波减速器柔轮"}],
            ),
            (
                "FMEA-202611-009",
                "node",
                "nd_encoder",
                "双圈磁编读头",
                "DFMEA",
                "双圈磁编读头感应面贴装微倾角超差致正交相位解调失真",
                "读头安装定位凸台平面度与基准同轴度超差，读头与磁鼓气隙不均导致正弦/余弦信号畸变。",
                "多圈编码器绝对位置跳变，伺服报超速飞车或失步报警停机。",
                "基座增加精定位销孔，贴装治具配备千分表在线调平；出厂进行 360° 全行程解调李萨如图形检测。",
                "HIGH",
                8, 3, 3,
                [],
                [
                    {"type": "part", "ref_id": None, "code": "PRT-115", "label": "双圈磁编读头"},
                    {"type": "supplier", "ref_id": None, "code": "SUP-021", "label": "禹衡光学"},
                ],
            ),
            (
                "FMEA-202611-010",
                "node",
                "nd_encoder",
                "双圈磁编读头",
                "DFMEA",
                "驱动端屏蔽接地不良致空间电磁脉冲串扰读数跳变",
                "高速 PWM 逆变开关噪声通过屏蔽层缝隙耦合进入差分信号引线，瞬态共模抑制比不足。",
                "编码器通信偶发 CRC 校验错误，关节伺服指令抖动。",
                "读头线缆采用双层编织屏蔽并就近 360° 环接接地；驱动器增加共模扼流圈与数字滤波算法。",
                "MED",
                7, 3, 3,
                [],
                [{"type": "part", "ref_id": None, "code": "PRT-115", "label": "双圈磁编读头"}],
            ),
        ]

        for code, t_kind, t_id, t_snap, f_type, mode, mech, eff, ctrl, r_lvl, s, o, d, phs, refs in seed_items_b1:
            norm_refs, ref_txt = _normalize_refs_and_index(refs)
            _, rpn_val = _compute_sod_and_risk(r_lvl, s, o, d)
            db.add(SqmFmeaItem(
                fmea_code=code,
                board_id=b1.id,
                target_kind=t_kind,
                target_id=t_id,
                target_title_snapshot=t_snap,
                fmea_type=f_type,
                failure_mode=mode,
                failure_mech=mech,
                failure_effect=eff,
                control_measure=ctrl,
                prevention_measure=ctrl.split("；")[0] if "；" in ctrl else ctrl,
                detection_measure=ctrl.split("；")[1] if "；" in ctrl else "",
                risk_level=r_lvl,
                severity=s,
                occurrence=o,
                detection=d,
                rpn=rpn_val,
                photos=phs,
                linked_refs=norm_refs,
                ref_codes_text=ref_txt,
            ))

    if "BRD-HND-G1" not in existing_codes:
        b2 = SqmFmeaBoard(
            board_code="BRD-HND-G1",
            group_name="灵巧手与末端系统",
            name="五指灵巧手总成",
            board_type="DFMEA",
            description="微型空心杯推杆、超高分子量聚乙烯腱绳传动与指尖多维触觉传感器接口风险图谱",
            sort_order=1,
            canvas_data={
                "viewport": {"panX": 48, "panY": 44, "zoom": 1.0},
                "image_boards": [],
                "nodes": [
                    {"id": "nd_cup_motor", "title": "微型空心杯电机", "sub": "PRT-301", "x": 80, "y": 96},
                    {"id": "nd_pulley", "title": "腱绳导向滑轮组", "sub": "PRT-308", "x": 360, "y": 96},
                    {"id": "nd_tactile", "title": "指尖触觉FPC阵列", "sub": "PRT-316", "x": 640, "y": 96},
                ],
                "edges": [
                    {
                        "id": "ed_tendon",
                        "from": "nd_cup_motor",
                        "fromPort": "right",
                        "to": "nd_pulley",
                        "toPort": "left",
                        "label": "张力磨损",
                        "sub": "腱绳包角摩擦发热接口",
                    },
                    {
                        "id": "ed_fpc",
                        "from": "nd_pulley",
                        "fromPort": "right",
                        "to": "nd_tactile",
                        "toPort": "left",
                        "label": "弯折疲劳",
                        "sub": "指节90°往复走线通道",
                    },
                ],
            },
        )
        db.add(b2)
        db.flush()

        refs_b2, txt_b2 = _normalize_refs_and_index([
            {"type": "part", "ref_id": None, "code": "PRT-308", "label": "腱绳导向滑轮组"},
            {"type": "free", "ref_id": None, "code": None, "label": "UHMWPE编织腱绳"},
        ])
        db.add(SqmFmeaItem(
            fmea_code="FMEA-202611-005",
            board_id=b2.id,
            target_kind="edge",
            target_id="ed_tendon",
            target_title_snapshot="张力磨损",
            fmea_type="DFMEA",
            failure_mode="腱绳在滑轮出口棱边起毛断股",
            failure_mech="滑轮绳槽粗糙度 Ra > 0.8μm 且偏角超 6°，5 万次抓握循环后纤维磨断。",
            failure_effect="手指失力无法闭合抓取。",
            control_measure="滑轮陶瓷化镜面抛光 Ra≤0.2μm + 出绳口喇叭口 R1.5 包络引导。",
            risk_level="HIGH",
            severity=8,
            occurrence=4,
            detection=4,
            rpn=128,
            photos=[],
            linked_refs=refs_b2,
            ref_codes_text=txt_b2,
        ))

    if "BRD-EOL-01" not in existing_codes:
        b3 = SqmFmeaBoard(
            board_code="BRD-EOL-01",
            group_name="制造与测试产线",
            name="关节总装EOL产线",
            board_type="PFMEA",
            description="关节模组洁净装配与下线全检工序链：压装、定量注脂、激光焊线与EOL空载/带载测试",
            sort_order=1,
            canvas_data={
                "viewport": {"panX": 48, "panY": 44, "zoom": 1.0},
                "image_boards": [],
                "nodes": [
                    {"id": "op_press", "title": "OP10 轴承伺服压装", "sub": "PFMEA-10", "x": 72, "y": 110},
                    {"id": "op_grease", "title": "OP20 定量自动涂脂", "sub": "PFMEA-20", "x": 352, "y": 110},
                    {"id": "op_eol", "title": "OP40 EOL综合测试台", "sub": "PFMEA-40", "x": 632, "y": 110},
                ],
                "edges": [
                    {
                        "id": "ed_clean",
                        "from": "op_press",
                        "fromPort": "right",
                        "to": "op_grease",
                        "toPort": "left",
                        "label": "除油流转",
                        "sub": "螺栓螺纹孔防油污染传递",
                    },
                    {
                        "id": "ed_preload",
                        "from": "op_grease",
                        "fromPort": "right",
                        "to": "op_eol",
                        "toPort": "left",
                        "label": "偏载卡滞",
                        "sub": "压装同轴度传递至启动电流",
                    },
                ],
            },
        )
        db.add(b3)
        db.flush()

        refs_b3, txt_b3 = _normalize_refs_and_index([
            {"type": "part", "ref_id": None, "code": "PRT-109", "label": "交叉滚子轴承"},
            {"type": "free", "ref_id": None, "code": None, "label": "伺服压机曲线窗口"},
        ])
        db.add(SqmFmeaItem(
            fmea_code="FMEA-202611-006",
            board_id=b3.id,
            target_kind="node",
            target_id="op_press",
            target_title_snapshot="OP10 轴承伺服压装",
            fmea_type="PFMEA",
            failure_mode="端盖轴承歪斜压入导致空载启动电流超标",
            failure_mech="工装导向套磨损间隙超 0.05mm，压装末段产生切屑垫入端面。",
            failure_effect="EOL 测试启动摩擦力矩波动 > 18%，返修报废。",
            control_measure="启用伺服压机『位移-压力』包络窗口联锁报警 + 每 2000 件定检导向套同轴度。",
            risk_level="MED",
            severity=7,
            occurrence=3,
            detection=3,
            rpn=63,
            photos=[],
            linked_refs=refs_b3,
            ref_codes_text=txt_b3,
        ))

    db.commit()
    _ensure_bom_demo_upgrade(db, force=True)


# ==============================================================================
# 1. 画板、系统分组管理与多父级 BOM 关系 API
# ==============================================================================

@router.get("/boards/tree", response_model=FmeaBoardTreeResp, summary="获取左侧按系统分组的模块画板目录树")
def get_fmea_board_tree(
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    seed_initial_fmea_boards(db, force_missing=False)

    q = db.query(SqmFmeaBoard)
    if not include_archived:
        q = q.filter(SqmFmeaBoard.is_archived == False)
    boards = q.order_by(
        SqmFmeaBoard.group_name.asc(),
        SqmFmeaBoard.sort_order.asc(),
        SqmFmeaBoard.id.asc(),
    ).all()

    effective_stats = _compute_board_effective_stats(boards, db)
    board_by_id = {b.id: b for b in boards}

    flat_summaries: List[FmeaBoardSummaryOut] = []
    group_dict: Dict[str, List[FmeaBoardSummaryOut]] = {}

    for b in boards:
        st = effective_stats.get(b.id, {"total": 0, "high": 0, "photos": 0})
        cdata = b.canvas_data if isinstance(b.canvas_data, dict) else {}
        node_cnt = len(cdata.get("nodes") or []) + sum(
            len(ib.get("pins") or []) for ib in (cdata.get("image_boards") or [])
        )

        bom_children: List[FmeaBomChildSummary] = []
        inst_counts: Dict[Any, int] = {}
        for nd in (cdata.get("nodes") or []):
            if not isinstance(nd, dict):
                continue
            sub_id = nd.get("sub_board_id")
            unit_c = nd.get("unit_code")
            if sub_id:
                try:
                    s_id = int(sub_id)
                except Exception:
                    s_id = None
                if s_id and s_id in board_by_id:
                    target_b = board_by_id[s_id]
                    inst_counts[s_id] = inst_counts.get(s_id, 0) + 1
                    t_st = effective_stats.get(s_id, {"total": 0, "high": 0})
                    bom_children.append(
                        FmeaBomChildSummary(
                            node_id=str(nd.get("id") or ""),
                            title=str(nd.get("title") or target_b.name),
                            ref_type="sub_board",
                            sub_board_id=target_b.id,
                            sub_board_code=target_b.board_code,
                            sub_board_name=target_b.name,
                            instance_index=inst_counts[s_id],
                            high_risk_count=t_st["high"],
                            total_items=t_st["total"],
                        )
                    )
            elif unit_c:
                uc_str = str(unit_c)
                inst_counts[uc_str] = inst_counts.get(uc_str, 0) + 1
                bom_children.append(
                    FmeaBomChildSummary(
                        node_id=str(nd.get("id") or ""),
                        title=str(nd.get("title") or uc_str),
                        ref_type="shared_unit",
                        unit_code=uc_str,
                        instance_index=inst_counts[uc_str],
                        high_risk_count=0,
                        total_items=0,
                    )
                )

        summary = FmeaBoardSummaryOut(
            id=b.id,
            board_code=b.board_code,
            group_name=b.group_name or "未分组系统",
            name=b.name,
            board_type=b.board_type or "MIXED",
            description=b.description,
            sort_order=b.sort_order or 0,
            is_archived=bool(b.is_archived),
            total_items=st["total"],
            high_risk_count=st["high"],
            photo_count=st["photos"],
            node_count=node_cnt,
            bom_children=bom_children,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        flat_summaries.append(summary)
        group_dict.setdefault(summary.group_name, []).append(summary)

    groups = [
        FmeaBoardGroupNode(group_name=g_name, boards=b_list)
        for g_name, b_list in group_dict.items()
    ]
    return FmeaBoardTreeResp(groups=groups, boards=flat_summaries)


@router.get("/boards/{board_id}", response_model=FmeaBoardDetailOut, summary="获取单张画板空间骨架、共享机理卡及多父级BOM上下文")
def get_fmea_board_detail(board_id: int, db: Session = Depends(get_db)):
    board = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="未找到指定的 FMEA 模块画板")

    default_canvas = {
        "viewport": {"panX": 40, "panY": 40, "zoom": 1.0},
        "image_boards": [],
        "nodes": [],
        "edges": [],
    }
    cdata = board.canvas_data if isinstance(board.canvas_data, dict) and board.canvas_data else default_canvas
    unit_codes = _extract_board_unit_codes(cdata)
    sub_board_ids = _extract_board_sub_ids(cdata)

    # 1) 查询当前画板直属机理卡 + 当前画板引用的共用件本体机理卡 (shared_unit)
    if unit_codes:
        item_filter = or_(
            SqmFmeaItem.board_id == board.id,
            and_(SqmFmeaItem.target_kind == "shared_unit", SqmFmeaItem.target_id.in_(list(unit_codes))),
        )
    else:
        item_filter = SqmFmeaItem.board_id == board.id

    items = (
        db.query(SqmFmeaItem)
        .filter(item_filter)
        .order_by(
            desc(SqmFmeaItem.risk_level == "HIGH"),
            desc(SqmFmeaItem.rpn),
            SqmFmeaItem.id.asc(),
        )
        .all()
    )

    # 2) 计算多父级 BOM 上下文：子画板汇总风险、当前画板被哪些上级父画板嵌入、共用件在哪些画板借用
    all_active_boards = (
        db.query(SqmFmeaBoard)
        .filter(SqmFmeaBoard.is_archived == False)
        .order_by(SqmFmeaBoard.group_name.asc(), SqmFmeaBoard.id.asc())
        .all()
    )
    effective_stats = _compute_board_effective_stats(all_active_boards, db)
    board_lookup = {b.id: b for b in all_active_boards}

    sub_board_stats: Dict[str, SubBoardRollupStat] = {}
    for sb_id in sub_board_ids:
        sb = board_lookup.get(sb_id)
        if sb:
            st = effective_stats.get(sb.id, {"total": 0, "high": 0, "photos": 0})
            sub_board_stats[str(sb.id)] = SubBoardRollupStat(
                board_id=sb.id,
                board_code=sb.board_code,
                group_name=sb.group_name or "未分组系统",
                name=sb.name,
                total_items=st["total"],
                high_risk_count=st["high"],
                photo_count=st["photos"],
            )

    parent_boards: List[WhereUsedRefOut] = []
    unit_where_used: Dict[str, List[WhereUsedRefOut]] = {uc: [] for uc in unit_codes}

    for ob in all_active_boards:
        ob_cdata = ob.canvas_data if isinstance(ob.canvas_data, dict) else {}
        for nd in ob_cdata.get("nodes") or []:
            if not isinstance(nd, dict):
                continue
            # 检查是否将当前 board 嵌入为子模块
            if ob.id != board.id and nd.get("sub_board_id"):
                try:
                    if int(nd["sub_board_id"]) == board.id:
                        parent_boards.append(WhereUsedRefOut(
                            board_id=ob.id,
                            board_name=ob.name,
                            group_name=ob.group_name or "未分组系统",
                            node_id=nd.get("id"),
                            node_title=nd.get("title"),
                        ))
                except Exception:
                    pass
            # 检查共用件借用反查 (Where-Used)
            nd_uc = str(nd.get("unit_code") or "").strip()
            if nd_uc and nd_uc in unit_where_used:
                unit_where_used[nd_uc].append(WhereUsedRefOut(
                    board_id=ob.id,
                    board_name=ob.name,
                    group_name=ob.group_name or "未分组系统",
                    node_id=nd.get("id"),
                    node_title=nd.get("title"),
                ))

    return FmeaBoardDetailOut(
        id=board.id,
        board_code=board.board_code,
        group_name=board.group_name,
        name=board.name,
        board_type=board.board_type,
        description=board.description,
        canvas_data=cdata,
        sort_order=board.sort_order,
        is_archived=board.is_archived,
        items=[
            _item_to_out(
                it,
                board.name if it.board_id == board.id else None,
                board.group_name if it.board_id == board.id else None,
            )
            for it in items
        ],
        sub_board_stats=sub_board_stats,
        parent_boards=parent_boards,
        unit_where_used=unit_where_used,
        created_at=board.created_at,
        updated_at=board.updated_at,
    )


@router.post("/boards", response_model=FmeaBoardDetailOut, status_code=status.HTTP_201_CREATED, summary="新建模块画板")
def create_fmea_board(payload: FmeaBoardCreate, db: Session = Depends(get_db)):
    code = (payload.board_code or "").strip() or _generate_board_code(db)
    if db.query(SqmFmeaBoard).filter(SqmFmeaBoard.board_code == code).first():
        code = _generate_board_code(db)

    default_canvas = payload.canvas_data or {
        "viewport": {"panX": 48, "panY": 48, "zoom": 1.0},
        "image_boards": [],
        "nodes": [
            {"id": f"nd_{uuid.uuid4().hex[:6]}", "title": f"{payload.name.strip()}核心单元", "sub": "", "x": 140, "y": 120}
        ],
        "edges": [],
    }

    board = SqmFmeaBoard(
        board_code=code,
        group_name=(payload.group_name or "默认系统分组").strip(),
        name=payload.name.strip(),
        board_type=(payload.board_type or "MIXED").strip().upper(),
        description=payload.description,
        canvas_data=default_canvas,
        sort_order=payload.sort_order,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return get_fmea_board_detail(board.id, db)


@router.post("/boards/{board_id}/duplicate", response_model=FmeaBoardDetailOut, status_code=status.HTTP_201_CREATED, summary="复制画板及本地机理卡（创建变体）")
def duplicate_fmea_board(
    board_id: int,
    payload: FmeaBoardDuplicateReq,
    db: Session = Depends(get_db),
):
    src = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == board_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="源画板不存在")

    new_name = (payload.new_name or "").strip() or f"{src.name} (副本)"
    new_group = (payload.group_name or "").strip() or src.group_name
    cloned_canvas = json.loads(json.dumps(src.canvas_data)) if isinstance(src.canvas_data, dict) else {
        "viewport": {"panX": 48, "panY": 48, "zoom": 1.0},
        "image_boards": [],
        "nodes": [],
        "edges": [],
    }

    dup_board = SqmFmeaBoard(
        board_code=_generate_board_code(db),
        group_name=new_group,
        name=new_name[:145],
        board_type=src.board_type,
        description=src.description,
        canvas_data=cloned_canvas,
        sort_order=(src.sort_order or 0) + 1,
    )
    db.add(dup_board)
    db.flush()

    local_items = db.query(SqmFmeaItem).filter(SqmFmeaItem.board_id == src.id).order_by(SqmFmeaItem.id.asc()).all()
    for it in local_items:
        db.add(SqmFmeaItem(
            fmea_code=_generate_fmea_code(db),
            board_id=dup_board.id,
            target_kind=it.target_kind,
            target_id=it.target_id,
            target_title_snapshot=it.target_title_snapshot,
            fmea_type=it.fmea_type,
            failure_mode=it.failure_mode,
            failure_mech=it.failure_mech,
            failure_effect=it.failure_effect,
            control_measure=it.control_measure,
            risk_level=it.risk_level,
            severity=it.severity,
            occurrence=it.occurrence,
            detection=it.detection,
            rpn=it.rpn,
            photos=json.loads(json.dumps(it.photos)) if isinstance(it.photos, list) else [],
            linked_refs=json.loads(json.dumps(it.linked_refs)) if isinstance(it.linked_refs, list) else [],
            ref_codes_text=it.ref_codes_text,
            source_issue_no=it.source_issue_no,
        ))
        db.flush()

    db.commit()
    db.refresh(dup_board)
    return get_fmea_board_detail(dup_board.id, db)


@router.put("/groups/rename", summary="批量重命名左侧目录系统分组")
def rename_fmea_group(payload: FmeaGroupRenameReq, db: Session = Depends(get_db)):
    old_n = payload.old_name.strip()
    new_n = payload.new_name.strip()
    if not old_n or not new_n:
        raise HTTPException(status_code=400, detail="分组名称不能为空")
    updated = (
        db.query(SqmFmeaBoard)
        .filter(SqmFmeaBoard.group_name == old_n)
        .update({"group_name": new_n}, synchronize_session=False)
    )
    db.commit()
    return {"message": "系统分组已重命名", "updated_count": updated, "group_name": new_n}


@router.delete("/groups", summary="解散分组（旗下画板安全移入未分组系统，不丢数据）")
def dissolve_fmea_group(
    group_name: str = Query(..., description="待解散的分组名"),
    db: Session = Depends(get_db),
):
    g_name = group_name.strip()
    if not g_name:
        raise HTTPException(status_code=400, detail="分组名称不能为空")
    moved = (
        db.query(SqmFmeaBoard)
        .filter(SqmFmeaBoard.group_name == g_name)
        .update({"group_name": "未分组系统"}, synchronize_session=False)
    )
    db.commit()
    return {"message": "分组已解散，画板已移至未分组系统", "moved_count": moved}


@router.get("/shared-units", response_model=List[SharedUnitOptionOut], summary="获取跨画板共用零件/标准单元候选列表")
def list_shared_units(
    q: str = Query("", description="过滤编码或名称"),
    db: Session = Depends(get_db),
):
    kw = q.strip().lower()
    boards = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.is_archived == False).all()

    unit_info: Dict[str, Dict[str, Any]] = {}
    for b in boards:
        cdata = b.canvas_data if isinstance(b.canvas_data, dict) else {}
        seen_in_board: Set[str] = set()
        for nd in cdata.get("nodes") or []:
            if not isinstance(nd, dict):
                continue
            uc = str(nd.get("unit_code") or "").strip()
            if not uc:
                continue
            entry = unit_info.setdefault(uc, {"title": str(nd.get("title") or uc), "boards": 0, "items": 0})
            if uc not in seen_in_board:
                entry["boards"] += 1
                seen_in_board.add(uc)

    # 统计每个共用单元的本体机理卡数
    shared_items = (
        db.query(SqmFmeaItem.target_id, SqmFmeaItem.target_title_snapshot)
        .filter(SqmFmeaItem.target_kind == "shared_unit")
        .all()
    )
    for t_id, t_snap in shared_items:
        if not t_id:
            continue
        uc = str(t_id).strip()
        entry = unit_info.setdefault(uc, {"title": str(t_snap or uc), "boards": 0, "items": 0})
        entry["items"] += 1

    # 融合零件主数据清单方便一键引用建档零件
    for p in db.query(SqmPart).order_by(SqmPart.id.desc()).limit(80).all():
        if p.part_no:
            uc = p.part_no.strip()
            if uc not in unit_info:
                unit_info[uc] = {"title": p.name or uc, "boards": 0, "items": 0}

    results: List[SharedUnitOptionOut] = []
    for uc, meta in unit_info.items():
        if kw and kw not in uc.lower() and kw not in str(meta["title"]).lower():
            continue
        results.append(SharedUnitOptionOut(
            unit_code=uc,
            title=meta["title"],
            used_board_count=meta["boards"],
            shared_item_count=meta["items"],
        ))

    results.sort(key=lambda x: (-x.used_board_count, -x.shared_item_count, x.unit_code))
    return results[:40]


@router.put("/boards/{board_id}", response_model=FmeaBoardDetailOut, summary="更新画板基础信息或保存画布空间布局")
def update_fmea_board(board_id: int, payload: FmeaBoardUpdate, db: Session = Depends(get_db)):
    board = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="画板不存在")

    if payload.group_name is not None:
        board.group_name = payload.group_name.strip() or "未分组系统"
    if payload.name is not None and payload.name.strip():
        board.name = payload.name.strip()
    if payload.board_type is not None:
        board.board_type = payload.board_type.strip().upper()
    if payload.description is not None:
        board.description = payload.description
    if payload.sort_order is not None:
        board.sort_order = payload.sort_order
    if payload.is_archived is not None:
        board.is_archived = payload.is_archived

    if payload.canvas_data is not None:
        _validate_no_bom_cycle(board.id, payload.canvas_data, db)
        board.canvas_data = payload.canvas_data
        # 自动同步画布内元素改名至机理卡快照，保证全局台账展示一致
        title_lookup: Dict[Tuple[str, str], str] = {}
        for ib in payload.canvas_data.get("image_boards") or []:
            for p in ib.get("pins") or []:
                if p.get("id") and p.get("title"):
                    title_lookup[("pin", str(p["id"]))] = str(p["title"])[:145]
        for nd in payload.canvas_data.get("nodes") or []:
            if nd.get("id") and nd.get("title"):
                title_lookup[("node", str(nd["id"]))] = str(nd["title"])[:145]
        for ed in payload.canvas_data.get("edges") or []:
            if ed.get("id") and ed.get("label"):
                title_lookup[("edge", str(ed["id"]))] = str(ed["label"])[:145]

        if title_lookup:
            board_items = db.query(SqmFmeaItem).filter(SqmFmeaItem.board_id == board.id).all()
            for it in board_items:
                new_snap = title_lookup.get((it.target_kind or "", it.target_id or ""))
                if new_snap and it.target_title_snapshot != new_snap:
                    it.target_title_snapshot = new_snap

    db.commit()
    db.refresh(board)
    return get_fmea_board_detail(board.id, db)


@router.delete("/boards/{board_id}", summary="删除指定画板")
def delete_fmea_board(
    board_id: int,
    delete_items: bool = Query(False, description="是否一并删除旗下本地 FMEA 卡片；默认 False 保留至全局台账"),
    db: Session = Depends(get_db),
):
    board = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="画板不存在")

    # 解除上级父画板对该子画板的 sub_board_id 引用，防止悬挂指针
    other_boards = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id != board_id).all()
    for ob in other_boards:
        if isinstance(ob.canvas_data, dict):
            cdata = json.loads(json.dumps(ob.canvas_data))
            mut = False
            for nd in cdata.get("nodes") or []:
                if isinstance(nd, dict) and nd.get("sub_board_id") == board_id:
                    nd.pop("sub_board_id", None)
                    mut = True
            if mut:
                ob.canvas_data = cdata

    if delete_items:
        db.query(SqmFmeaItem).filter(SqmFmeaItem.board_id == board.id).delete(synchronize_session=False)
    else:
        db.query(SqmFmeaItem).filter(SqmFmeaItem.board_id == board.id).update(
            {"board_id": None, "target_kind": "unassigned", "target_id": None},
            synchronize_session=False,
        )

    db.delete(board)
    db.commit()
    return {"message": "画板已移除", "id": board_id}


@router.post("/boards/seed-demo", summary="补充恢复缺失的示范画板及多级BOM示例")
def restore_demo_boards(db: Session = Depends(get_db)):
    seed_initial_fmea_boards(db, force_missing=True)
    return {"message": "示范画板与多级 BOM 示范已就绪"}


# ==============================================================================
# 2. FMEA 失效机理卡 CRUD (同源服务：画板浮层 / 图鉴墙 / 全局台账)
# ==============================================================================

@router.get("/items", response_model=FmeaItemPageResult, summary="多维分页检索 FMEA 失效机理卡")
def list_fmea_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    keyword: Optional[str] = None,
    board_id: Optional[int] = None,
    fmea_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    has_photo: Optional[bool] = None,
    ref_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(SqmFmeaItem, SqmFmeaBoard.name.label("b_name"), SqmFmeaBoard.group_name.label("b_group"))
        .outerjoin(SqmFmeaBoard, SqmFmeaItem.board_id == SqmFmeaBoard.id)
    )

    if board_id is not None:
        b_obj = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == board_id).first()
        b_ucs = _extract_board_unit_codes(b_obj.canvas_data) if b_obj else set()
        if b_ucs:
            q = q.filter(
                or_(
                    SqmFmeaItem.board_id == board_id,
                    and_(SqmFmeaItem.target_kind == "shared_unit", SqmFmeaItem.target_id.in_(list(b_ucs))),
                )
            )
        else:
            q = q.filter(SqmFmeaItem.board_id == board_id)

    if fmea_type and fmea_type != "ALL":
        q = q.filter(SqmFmeaItem.fmea_type == fmea_type)

    if risk_level and risk_level != "ALL":
        q = q.filter(SqmFmeaItem.risk_level == risk_level)

    if ref_code and ref_code.strip():
        rc = f"%{ref_code.strip()}%"
        q = q.filter(
            or_(
                SqmFmeaItem.ref_codes_text.like(rc),
                and_(SqmFmeaItem.target_kind == "shared_unit", SqmFmeaItem.target_id.like(rc)),
            )
        )

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        q = q.filter(
            or_(
                SqmFmeaItem.fmea_code.like(kw),
                SqmFmeaItem.failure_mode.like(kw),
                SqmFmeaItem.failure_mech.like(kw),
                SqmFmeaItem.failure_effect.like(kw),
                SqmFmeaItem.control_measure.like(kw),
                SqmFmeaItem.target_title_snapshot.like(kw),
                SqmFmeaItem.target_id.like(kw),
                SqmFmeaItem.ref_codes_text.like(kw),
                SqmFmeaBoard.name.like(kw),
            )
        )

    rows_all = (
        q.order_by(
            desc(SqmFmeaItem.risk_level == "HIGH"),
            desc(SqmFmeaItem.updated_at),
            desc(SqmFmeaItem.id),
        )
        .all()
    )

    if has_photo:
        rows_all = [
            (it, bn, bg)
            for (it, bn, bg) in rows_all
            if isinstance(it.photos, list) and len(it.photos) > 0
        ]

    total = len(rows_all)
    sliced = rows_all[(page - 1) * page_size : page * page_size]

    return FmeaItemPageResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[_item_to_out(it, bn, bg) for (it, bn, bg) in sliced],
    )


@router.post("/items", response_model=FmeaItemOut, status_code=status.HTTP_201_CREATED, summary="新建 FMEA 失效机理卡")
def create_fmea_item(payload: FmeaItemCreate, db: Session = Depends(get_db)):
    code = (payload.fmea_code or "").strip() or _generate_fmea_code(db)
    if db.query(SqmFmeaItem).filter(SqmFmeaItem.fmea_code == code).first():
        code = _generate_fmea_code(db)

    risk_lvl, rpn_val = _compute_sod_and_risk(
        payload.risk_level, payload.severity, payload.occurrence, payload.detection
    )
    norm_refs, ref_txt = _normalize_refs_and_index(payload.linked_refs)
    norm_photos = _normalize_photos(payload.photos)

    t_kind = payload.target_kind or "unassigned"
    effective_board_id = None if t_kind == "shared_unit" else payload.board_id

    ctrl_measure = payload.control_measure
    if not ctrl_measure and (payload.prevention_measure or payload.detection_measure):
        parts = []
        if payload.prevention_measure:
            parts.append(f"【预防】{payload.prevention_measure.strip()}")
        if payload.detection_measure:
            parts.append(f"【探测】{payload.detection_measure.strip()}")
        ctrl_measure = "\n".join(parts)

    item = SqmFmeaItem(
        fmea_code=code,
        board_id=effective_board_id,
        target_kind=t_kind,
        target_id=payload.target_id,
        target_title_snapshot=payload.target_title_snapshot,
        fmea_type=(payload.fmea_type or "DFMEA").upper(),
        failure_mode=payload.failure_mode.strip(),
        failure_mech=payload.failure_mech,
        failure_effect=payload.failure_effect,
        control_measure=ctrl_measure,
        prevention_measure=payload.prevention_measure,
        detection_measure=payload.detection_measure,
        risk_level=risk_lvl,
        severity=payload.severity,
        occurrence=payload.occurrence,
        detection=payload.detection,
        rpn=rpn_val,
        photos=norm_photos,
        linked_refs=norm_refs,
        ref_codes_text=ref_txt,
        source_issue_no=payload.source_issue_no,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_out(item)


@router.put("/items/{item_id}", response_model=FmeaItemOut, summary="编辑更新 FMEA 失效机理卡")
def update_fmea_item(item_id: int, payload: FmeaItemUpdate, db: Session = Depends(get_db)):
    item = db.query(SqmFmeaItem).filter(SqmFmeaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到指定的 FMEA 机理卡")

    if payload.target_kind is not None:
        item.target_kind = payload.target_kind
        if payload.target_kind == "shared_unit":
            item.board_id = None
    if payload.board_id is not None and item.target_kind != "shared_unit":
        item.board_id = payload.board_id if payload.board_id > 0 else None
    if payload.target_id is not None:
        item.target_id = payload.target_id or None
    if payload.target_title_snapshot is not None:
        item.target_title_snapshot = payload.target_title_snapshot
    if payload.fmea_type is not None:
        item.fmea_type = payload.fmea_type.upper()
    if payload.failure_mode is not None and payload.failure_mode.strip():
        item.failure_mode = payload.failure_mode.strip()
    if payload.failure_mech is not None:
        item.failure_mech = payload.failure_mech
    if payload.failure_effect is not None:
        item.failure_effect = payload.failure_effect
    if payload.prevention_measure is not None:
        item.prevention_measure = payload.prevention_measure
    if payload.detection_measure is not None:
        item.detection_measure = payload.detection_measure
    if payload.control_measure is not None:
        item.control_measure = payload.control_measure
    elif payload.prevention_measure is not None or payload.detection_measure is not None:
        parts = []
        if item.prevention_measure:
            parts.append(f"【预防】{item.prevention_measure.strip()}")
        if item.detection_measure:
            parts.append(f"【探测】{item.detection_measure.strip()}")
        if parts:
            item.control_measure = "\n".join(parts)

    if payload.clear_sod:
        item.severity = None
        item.occurrence = None
        item.detection = None
        item.rpn = None
        if payload.risk_level:
            item.risk_level = payload.risk_level.upper()
    else:
        s = payload.severity if payload.severity is not None else item.severity
        o = payload.occurrence if payload.occurrence is not None else item.occurrence
        d = payload.detection if payload.detection is not None else item.detection
        sod_changed = any(x is not None for x in (payload.severity, payload.occurrence, payload.detection))
        item.severity = s
        item.occurrence = o
        item.detection = d
        explicit_risk = payload.risk_level if payload.risk_level is not None else (None if sod_changed else item.risk_level)
        risk_lvl, rpn_val = _compute_sod_and_risk(explicit_risk, s, o, d)
        item.risk_level = risk_lvl
        item.rpn = rpn_val

    if payload.photos is not None:
        item.photos = _normalize_photos(payload.photos)

    if payload.linked_refs is not None:
        norm_refs, ref_txt = _normalize_refs_and_index(payload.linked_refs)
        item.linked_refs = norm_refs
        item.ref_codes_text = ref_txt

    db.commit()
    db.refresh(item)
    return _item_to_out(item)


@router.delete("/items/{item_id}", summary="删除单条 FMEA 失效机理卡")
def delete_fmea_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(SqmFmeaItem).filter(SqmFmeaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FMEA 机理卡不存在")
    db.delete(item)
    db.commit()
    return {"message": "已删除 FMEA 机理卡", "id": item_id}


# ==============================================================================
# 3. 双态非硬外键软关联联想、实时快照穿透与跨模块计数
# ==============================================================================

@router.get("/refs/suggest", response_model=List[SoftRefSuggestItem], summary="跨业务域聚合联想搜索主数据短码")
def suggest_soft_refs(
    q: str = Query("", description="搜索图号/供应商码/质量问题单号/名称"),
    types: str = Query("part,supplier,issue,project,ctq", description="逗号分隔检索域"),
    limit: int = Query(18, ge=1, le=50),
    db: Session = Depends(get_db),
):
    allowed = {t.strip().lower() for t in types.split(",") if t.strip()}
    kw = f"%{q.strip()}%" if q and q.strip() else None
    results: List[SoftRefSuggestItem] = []

    if "part" in allowed:
        pq = db.query(SqmPart)
        if kw:
            pq = pq.filter(or_(SqmPart.part_no.like(kw), SqmPart.name.like(kw)))
        for p in pq.order_by(SqmPart.id.desc()).limit(6).all():
            results.append(SoftRefSuggestItem(
                type="part",
                ref_id=p.id,
                code=p.part_no,
                label=p.name,
                sub_info=f"版本 {p.drawing_version or '-'}",
                status=None,
            ))

    if "supplier" in allowed:
        sq = db.query(SqmSupplier)
        if kw:
            sq = sq.filter(or_(SqmSupplier.code.like(kw), SqmSupplier.name.like(kw), SqmSupplier.short_name.like(kw)))
        for s in sq.order_by(SqmSupplier.id.desc()).limit(5).all():
            results.append(SoftRefSuggestItem(
                type="supplier",
                ref_id=s.id,
                code=s.code,
                label=s.short_name or s.name,
                sub_info=s.name,
                status=s.status,
            ))

    if "issue" in allowed:
        iq = db.query(SqmQualityIssue)
        if kw:
            iq = iq.filter(or_(SqmQualityIssue.issue_no.like(kw), SqmQualityIssue.title.like(kw)))
        for iss in iq.order_by(SqmQualityIssue.id.desc()).limit(5).all():
            results.append(SoftRefSuggestItem(
                type="issue",
                ref_id=iss.id,
                code=iss.issue_no,
                label=iss.title,
                sub_info=f"{iss.severity} · {iss.status}",
                status=iss.status,
            ))

    if "project" in allowed:
        prjq = db.query(SqmProject)
        if kw:
            prjq = prjq.filter(or_(SqmProject.project_code.like(kw), SqmProject.name.like(kw)))
        for prj in prjq.order_by(SqmProject.id.desc()).limit(4).all():
            results.append(SoftRefSuggestItem(
                type="project",
                ref_id=prj.id,
                code=prj.project_code,
                label=prj.name,
                sub_info=prj.status,
                status=prj.status,
            ))

    if "ctq" in allowed:
        cq = db.query(SqmCtq)
        if kw:
            cq = cq.filter(or_(SqmCtq.feature_code.like(kw), SqmCtq.feature_name.like(kw)))
        for c in cq.order_by(SqmCtq.id.desc()).limit(4).all():
            results.append(SoftRefSuggestItem(
                type="ctq",
                ref_id=c.id,
                code=c.feature_code,
                label=c.feature_name,
                sub_info=f"{c.feature_type} · {c.standard_value or ''} {c.tolerance or ''}".strip(),
                status=c.feature_type,
            ))

    return results[:limit]


@router.post("/refs/resolve", response_model=List[SoftRefSnapshotOut], summary="批量解析软关联胶囊的实时主数据状态快照")
def resolve_soft_ref_snapshots(payload: SoftRefResolveReq, db: Session = Depends(get_db)):
    out: List[SoftRefSnapshotOut] = []
    for r in payload.refs:
        r_type = (r.type or "free").lower()
        key = f"{r_type}:{r.code or ''}:{r.label}"

        if r_type == "part":
            part = None
            if r.ref_id:
                part = db.query(SqmPart).filter(SqmPart.id == r.ref_id).first()
            if not part and r.code:
                part = db.query(SqmPart).filter(SqmPart.part_no == r.code).first()
            if part:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="part",
                    exists=True,
                    ref_id=part.id,
                    code=part.part_no,
                    label=part.name,
                    status=f"图纸版本 {part.drawing_version or 'A0'}",
                    detail_lines=[
                        f"零件图号：{part.part_no}",
                        f"零件名称：{part.name}",
                        f"规格/备注：{part.spec or part.remark or '已建档受控零部件'}",
                    ],
                    jump_route="/maindata/part",
                    jump_keyword=part.part_no,
                ))
            else:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="part",
                    exists=False,
                    code=r.code,
                    label=r.label,
                    status="未建档 / 历史快照",
                    detail_lines=[
                        f"快照图号：{r.code or '-'}",
                        f"快照名称：{r.label}",
                        "当前零件清单尚未录入此编码，软关联不受外键阻断，建档后将自动点亮关联。",
                    ],
                    jump_route="/maindata/part",
                    jump_keyword=r.code or r.label,
                ))

        elif r_type == "supplier":
            sup = None
            if r.ref_id:
                sup = db.query(SqmSupplier).filter(SqmSupplier.id == r.ref_id).first()
            if not sup and r.code:
                sup = db.query(SqmSupplier).filter(SqmSupplier.code == r.code).first()
            if sup:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="supplier",
                    exists=True,
                    ref_id=sup.id,
                    code=sup.code,
                    label=sup.short_name or sup.name,
                    status=sup.status,
                    detail_lines=[
                        f"供应商编码：{sup.code}",
                        f"企业全称：{sup.name}",
                        f"准入状态：{sup.status} · 联系人：{sup.contact or '-'}",
                    ],
                    jump_route="/maindata/supplier",
                    jump_keyword=sup.code,
                ))
            else:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="supplier",
                    exists=False,
                    code=r.code,
                    label=r.label,
                    status="未建档 / 历史快照",
                    detail_lines=[
                        f"快照编码：{r.code or '-'} · {r.label}",
                        "供应商主数据暂未匹配到该编码，可在供应商清单建档后自动对齐。",
                    ],
                    jump_route="/maindata/supplier",
                    jump_keyword=r.code or r.label,
                ))

        elif r_type == "issue":
            iss = None
            if r.ref_id:
                iss = db.query(SqmQualityIssue).filter(SqmQualityIssue.id == r.ref_id).first()
            if not iss and r.code:
                iss = db.query(SqmQualityIssue).filter(SqmQualityIssue.issue_no == r.code).first()
            if iss:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="issue",
                    exists=True,
                    ref_id=iss.id,
                    code=iss.issue_no,
                    label=iss.title,
                    status=f"{iss.severity} · {iss.status}",
                    detail_lines=[
                        f"异常单号：{iss.issue_no}",
                        f"问题标题：{iss.title}",
                        f"闭环状态：{iss.status}（责任人：{iss.responsible or '-'}）",
                    ],
                    jump_route="/sqm/quality-issue",
                    jump_keyword=iss.issue_no,
                ))
            else:
                out.append(SoftRefSnapshotOut(
                    key=key,
                    type="issue",
                    exists=False,
                    code=r.code,
                    label=r.label,
                    status="历史问题快照",
                    detail_lines=[
                        f"问题单快照：{r.code or '-'} {r.label}",
                        "台账中暂未检索到该单号记录。",
                    ],
                    jump_route="/sqm/quality-issue",
                    jump_keyword=r.code or r.label,
                ))

        elif r_type == "project":
            prj = None
            if r.ref_id:
                prj = db.query(SqmProject).filter(SqmProject.id == r.ref_id).first()
            if not prj and r.code:
                prj = db.query(SqmProject).filter(SqmProject.project_code == r.code).first()
            out.append(SoftRefSnapshotOut(
                key=key,
                type="project",
                exists=bool(prj),
                ref_id=prj.id if prj else None,
                code=prj.project_code if prj else r.code,
                label=prj.name if prj else r.label,
                status=prj.status if prj else "项目快照",
                detail_lines=[
                    f"项目代号：{(prj.project_code if prj else r.code) or '-'}",
                    f"项目名称：{prj.name if prj else r.label}",
                ],
                jump_route="/maindata/project",
                jump_keyword=(prj.project_code if prj else r.code) or r.label,
            ))

        elif r_type == "ctq":
            ctq = None
            if r.ref_id:
                ctq = db.query(SqmCtq).filter(SqmCtq.id == r.ref_id).first()
            if not ctq and r.code:
                ctq = db.query(SqmCtq).filter(SqmCtq.feature_code == r.code).first()
            ctq_std = f"{ctq.standard_value or ''} {ctq.tolerance or ''}".strip() if ctq else r.label
            out.append(SoftRefSnapshotOut(
                key=key,
                type="ctq",
                exists=bool(ctq),
                ref_id=ctq.id if ctq else None,
                code=ctq.feature_code if ctq else r.code,
                label=ctq.feature_name if ctq else r.label,
                status=ctq.feature_type if ctq else "特性快照",
                detail_lines=[
                    f"特性编号：{(ctq.feature_code if ctq else r.code) or '-'}",
                    f"公差基准：{ctq_std}",
                ],
                jump_route="/ctq/list",
                jump_keyword=(ctq.feature_code if ctq else r.code) or r.label,
            ))

        else:
            out.append(SoftRefSnapshotOut(
                key=key,
                type="free",
                exists=False,
                code=None,
                label=r.label,
                status="自由预研标签",
                detail_lines=[
                    f"自由标签：{r.label}",
                    "适用于预研新结构、外部竞品教训或尚未正式立项的零件；后续建档后可随时替换为正式短码。",
                ],
                jump_route=None,
            ))

    return out


@router.get("/refs/counts", summary="批量统计一组零件图号或供应商编码关联的 FMEA 风险数量")
def count_fmea_by_ref_codes(
    codes: str = Query("", description="逗号分隔编码列表，如 PRT-102,PRT-109"),
    db: Session = Depends(get_db),
):
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return {}

    result = {c: {"total": 0, "high": 0} for c in code_list}
    items = db.query(
        SqmFmeaItem.risk_level,
        SqmFmeaItem.target_kind,
        SqmFmeaItem.target_id,
        SqmFmeaItem.linked_refs,
        SqmFmeaItem.ref_codes_text,
    ).all()
    code_set = set(code_list)

    for risk_lvl, t_kind, t_id, l_refs, ref_txt in items:
        matched = set()
        if t_kind == "shared_unit" and t_id in code_set:
            matched.add(t_id)
        if isinstance(l_refs, list):
            for r in l_refs:
                c_val = r.get("code")
                if c_val in code_set:
                    matched.add(c_val)
        elif ref_txt:
            for c_val in code_set:
                if c_val in ref_txt:
                    matched.add(c_val)
        for mc in matched:
            result[mc]["total"] += 1
            if risk_lvl == "HIGH":
                result[mc]["high"] += 1

    return result


# ==============================================================================
# 4. 质量问题清单 (8D) -> 一键反哺沉淀至 FMEA 画板
# ==============================================================================

@router.post("/from-quality-issue/{issue_id}", response_model=FmeaItemOut, summary="从 8D 质量问题单据一键沉淀生成 FMEA 风险卡")
def deposit_quality_issue_to_fmea(
    issue_id: int,
    payload: DepositFromQualityIssueReq,
    db: Session = Depends(get_db),
):
    issue = db.query(SqmQualityIssue).filter(SqmQualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="质量问题单不存在")

    board = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == payload.board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="目标 FMEA 画板不存在")

    part = db.query(SqmPart).filter(SqmPart.id == issue.part_id).first() if issue.part_id else None
    supplier = db.query(SqmSupplier).filter(SqmSupplier.id == issue.supplier_id).first() if issue.supplier_id else None

    cdata = dict(board.canvas_data) if isinstance(board.canvas_data, dict) else {
        "viewport": {"panX": 40, "panY": 40, "zoom": 1.0},
        "image_boards": [],
        "nodes": [],
        "edges": [],
    }
    nodes = list(cdata.get("nodes") or [])

    target_kind = payload.target_kind
    target_id = payload.target_id
    target_snap = ""

    if target_kind == "new_node" or not target_id:
        node_title = (
            (payload.new_node_title or "").strip()
            or (part.name if part else "")
            or issue.title[:16]
        )
        node_sub = part.part_no if part else issue.issue_no
        col_idx = len(nodes) % 3
        row_idx = len(nodes) // 3
        new_nd_id = f"nd_{uuid.uuid4().hex[:6]}"
        new_node_dict: Dict[str, Any] = {
            "id": new_nd_id,
            "title": node_title,
            "sub": node_sub,
            "x": 500 + col_idx * 230,
            "y": 60 + row_idx * 130,
        }
        if part and part.part_no:
            new_node_dict["unit_code"] = part.part_no
        nodes.append(new_node_dict)
        cdata["nodes"] = nodes
        board.canvas_data = cdata
        target_kind = "node"
        target_id = new_nd_id
        target_snap = node_title
    else:
        for nd in nodes:
            if nd.get("id") == target_id:
                target_snap = nd.get("title") or ""
                break
        if not target_snap:
            for ib in cdata.get("image_boards") or []:
                for p in ib.get("pins") or []:
                    if p.get("id") == target_id:
                        target_snap = p.get("title") or ""
                        break
        if not target_snap:
            for ed in cdata.get("edges") or []:
                if ed.get("id") == target_id:
                    target_snap = ed.get("label") or ""
                    break

    extracted_photos: List[Dict[str, Any]] = []
    seen_urls = set()
    for img_url in _extract_img_urls_from_html(issue.issue_desc):
        if img_url not in seen_urls:
            seen_urls.add(img_url)
            extracted_photos.append({
                "id": f"ph_{uuid.uuid4().hex[:5]}",
                "url": img_url,
                "tag": "NG",
                "caption": f"{issue.issue_no} 现场缺陷实拍",
            })
    if isinstance(issue.attachments, list):
        for att in issue.attachments:
            if isinstance(att, dict):
                u = att.get("url") or (f"/api/storage/file/{att['id']}" if att.get("id") else None)
                mime = str(att.get("mime_type") or att.get("name") or "").lower()
                if u and u not in seen_urls and any(k in mime for k in ("image", ".png", ".jpg", ".jpeg", ".webp", ".gif")):
                    seen_urls.add(u)
                    extracted_photos.append({
                        "id": f"ph_{uuid.uuid4().hex[:5]}",
                        "attachment_id": att.get("id"),
                        "url": u,
                        "tag": "NG",
                        "caption": str(att.get("original_name") or att.get("name") or "缺陷图片")[:60],
                    })

    auto_refs: List[Dict[str, Any]] = [
        {"type": "issue", "ref_id": issue.id, "code": issue.issue_no, "label": issue.title}
    ]
    if part:
        auto_refs.append({"type": "part", "ref_id": part.id, "code": part.part_no, "label": part.name})
    if supplier:
        auto_refs.append({
            "type": "supplier",
            "ref_id": supplier.id,
            "code": supplier.code,
            "label": supplier.short_name or supplier.name,
        })
    if issue.project_code:
        prj = db.query(SqmProject).filter(SqmProject.project_code == issue.project_code).first()
        auto_refs.append({
            "type": "project",
            "ref_id": prj.id if prj else None,
            "code": issue.project_code,
            "label": prj.name if prj else issue.project_code,
        })

    sev_to_risk = {"致命": "HIGH", "严重": "HIGH", "一般": "MED", "微小": "LOW"}
    final_risk = (payload.risk_level or sev_to_risk.get(issue.severity, "MED")).upper()

    norm_refs, ref_txt = _normalize_refs_and_index(auto_refs)
    clean_desc = _strip_html(issue.issue_desc)
    clean_sol = _strip_html(issue.solution)

    item = SqmFmeaItem(
        fmea_code=_generate_fmea_code(db),
        board_id=board.id,
        target_kind=target_kind,
        target_id=target_id,
        target_title_snapshot=target_snap or issue.title[:40],
        fmea_type=(payload.fmea_type or "DFMEA").upper(),
        failure_mode=(payload.failure_mode or issue.title).strip()[:250],
        failure_mech=(payload.failure_mech if payload.failure_mech is not None else clean_desc) or "待补充微观失效机理",
        failure_effect=payload.failure_effect or f"引发批次不良（缺陷数：{issue.defect_qty or 1}）",
        control_measure=(payload.control_measure if payload.control_measure is not None else clean_sol) or "待固化防错与探测规范",
        risk_level=final_risk,
        photos=extracted_photos,
        linked_refs=norm_refs,
        ref_codes_text=ref_txt,
        source_issue_no=issue.issue_no,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_out(item, board.name, board.group_name)


# ==============================================================================
# 5. AI 智能图文拆解并自动归入画布节点 / 接口连线
# ==============================================================================

def _auto_match_db_refs(text_blob: str, db: Session) -> List[FmeaLinkedRefSchema]:
    matched: List[FmeaLinkedRefSchema] = []
    if not text_blob:
        return matched
    upper_blob = text_blob.upper()

    for p in db.query(SqmPart).limit(200).all():
        if (p.part_no and p.part_no.upper() in upper_blob) or (p.name and len(p.name) >= 2 and p.name in text_blob):
            matched.append(FmeaLinkedRefSchema(type="part", ref_id=p.id, code=p.part_no, label=p.name))

    for s in db.query(SqmSupplier).limit(200).all():
        s_short = s.short_name or ""
        if (
            (s.code and s.code.upper() in upper_blob)
            or (s_short and len(s_short) >= 2 and s_short in text_blob)
            or (s.name and len(s.name) >= 3 and s.name in text_blob)
        ):
            matched.append(FmeaLinkedRefSchema(type="supplier", ref_id=s.id, code=s.code, label=s_short or s.name))

    for iss in db.query(SqmQualityIssue).limit(100).all():
        if iss.issue_no and iss.issue_no.upper() in upper_blob:
            matched.append(FmeaLinkedRefSchema(type="issue", ref_id=iss.id, code=iss.issue_no, label=iss.title))

    return matched[:6]


@router.post("/ai-parse", response_model=FmeaAiParseResp, summary="AI 智能拆解异常文本/外部JSON并自动匹配画板节点与软关联")
def ai_parse_fmea_drafts(payload: FmeaAiParseReq, db: Session = Depends(get_db)):
    raw = (payload.raw_text or "").strip()
    if not raw and not payload.photos:
        raise HTTPException(status_code=400, detail="请提供待解析的现场文本描述或失效截图")

    board = db.query(SqmFmeaBoard).filter(SqmFmeaBoard.id == payload.board_id).first() if payload.board_id else None
    board_nodes: List[Dict[str, Any]] = []
    if board and isinstance(board.canvas_data, dict):
        board_nodes = board.canvas_data.get("nodes") or []

    json_fence = re.search(r"```(?:json)?\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```", raw)
    candidate_json_str = json_fence.group(1) if json_fence else (raw if raw.startswith("[") or raw.startswith("{") else None)
    if candidate_json_str:
        try:
            parsed_obj = json.loads(candidate_json_str)
            arr = parsed_obj if isinstance(parsed_obj, list) else parsed_obj.get("drafts") or [parsed_obj]
            direct_drafts: List[FmeaAiParseDraft] = []
            for entry in arr:
                if not isinstance(entry, dict):
                    continue
                mode_val = str(entry.get("failure_mode") or entry.get("mode") or entry.get("失效模式") or "").strip()
                if not mode_val:
                    continue
                row_blob = json.dumps(entry, ensure_ascii=False)
                db_refs = _auto_match_db_refs(row_blob, db)
                raw_refs = entry.get("linked_refs") or []
                for rr in raw_refs:
                    if isinstance(rr, dict) and rr.get("label"):
                        db_refs.append(FmeaLinkedRefSchema(**rr))
                    elif isinstance(rr, str) and rr.strip():
                        db_refs.append(FmeaLinkedRefSchema(type="free", label=rr.strip()))

                direct_drafts.append(FmeaAiParseDraft(
                    fmea_type=str(entry.get("fmea_type") or entry.get("type") or "DFMEA").upper(),
                    failure_mode=mode_val,
                    failure_mech=str(entry.get("failure_mech") or entry.get("mech") or entry.get("失效机理") or ""),
                    failure_effect=str(entry.get("failure_effect") or entry.get("effect") or entry.get("失效后果") or ""),
                    control_measure=str(entry.get("control_measure") or entry.get("control") or entry.get("防错与探测") or ""),
                    risk_level=str(entry.get("risk_level") or "HIGH").upper(),
                    severity=entry.get("severity"),
                    occurrence=entry.get("occurrence"),
                    detection=entry.get("detection"),
                    suggested_target_kind=str(entry.get("suggested_target_kind") or "node"),
                    suggested_target_id=entry.get("suggested_target_id"),
                    suggested_node_title=entry.get("suggested_node_title") or entry.get("部件名称"),
                    suggested_edge_from_title=entry.get("suggested_edge_from_title"),
                    suggested_edge_to_title=entry.get("suggested_edge_to_title"),
                    suggested_edge_label=entry.get("suggested_edge_label"),
                    linked_refs=db_refs,
                ))
            if direct_drafts:
                return FmeaAiParseResp(engine_mode="json_bridge", drafts=direct_drafts)
        except Exception:
            pass

    nodes_desc = ", ".join(f"{n.get('id')}:{n.get('title')}" for n in board_nodes) or "暂无已有节点"
    sys_prompt = (
        "你是资深机器人与精密制造 DFMEA/PFMEA 质量专家。请把用户输入的现场异常/实验记录拆解为严格的 JSON 数组，"
        "不要输出任何额外解释文字。每个元素字段为："
        '{"fmea_type":"DFMEA或PFMEA","failure_mode":"简明失效模式(≤24字)","failure_mech":"微观机理与根因",'
        '"failure_effect":"失效后果","control_measure":"防错设计标准与探测规范","risk_level":"HIGH或MED或LOW",'
        '"suggested_target_kind":"node或edge","suggested_target_id":"若匹配当前画板已有节点ID则填ID否则null",'
        '"suggested_node_title":"建议挂载模块短名(≤8字)","suggested_edge_from_title":"若属两部件接口问题填源部件",'
        '"suggested_edge_to_title":"目标部件","suggested_edge_label":"4字内接口短标签如油脂飞溅"}。'
        f"\n当前画板已有模块节点：[{nodes_desc}]。"
    )

    try:
        api_url = f"{settings.AI_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.AI_API_KEY}",
        }
        resp = requests.post(
            api_url,
            headers=headers,
            json={
                "model": settings.AI_MODEL,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": raw or "请根据上传的失效实拍图生成结构化 FMEA 条目"},
                ],
                "temperature": 0.2,
                "stream": False,
            },
            timeout=(2.5, 18.0),
        )
        if resp.status_code == 200:
            content_txt = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", content_txt)
            if m:
                llm_data = json.loads(m.group(1))
                llm_list = llm_data if isinstance(llm_data, list) else [llm_data]
                llm_drafts: List[FmeaAiParseDraft] = []
                for d in llm_list:
                    if isinstance(d, dict) and d.get("failure_mode"):
                        d["linked_refs"] = _auto_match_db_refs(raw + " " + json.dumps(d, ensure_ascii=False), db)
                        llm_drafts.append(FmeaAiParseDraft(**d))
                if llm_drafts:
                    return FmeaAiParseResp(engine_mode="llm", drafts=llm_drafts)
    except Exception:
        pass

    paragraphs = [ln.strip() for ln in re.split(r"\n{2,}|(?:^|\n)\s*(?:\d+[\.、]|[-•])\s*", raw) if ln and ln.strip()]
    if not paragraphs:
        paragraphs = [raw or "现场实拍外观/结构异常"]

    fallback_drafts: List[FmeaAiParseDraft] = []
    for para in paragraphs[:6]:
        is_pfmea = any(k in para for k in ("工位", "压装", "焊接", "涂胶", "涂脂", "扭矩", "产线", "漏装", "SOP"))
        is_high = any(k in para for k in ("断裂", "卡死", "短路", "击穿", "失控", "致命", "严重", "起火", "裂纹", "跳变"))

        clauses = [c.strip() for c in re.split(r"[；;。！!\n]+", para) if c.strip()]
        mode_str = clauses[0][:40] if clauses else para[:36]
        mech_str = ""
        effect_str = ""
        ctrl_str = ""

        for cl in clauses[1:]:
            if any(k in cl for k in ("原因", "由于", "因为", "机理", "偏小", "超差", "不足", "磨损", "老化")):
                mech_str = (f"{mech_str}；{cl}" if mech_str else cl)
            elif any(k in cl for k in ("导致", "造成", "后果", "异响", "卡滞", "报废", "失效", "报警")):
                effect_str = (f"{effect_str}；{cl}" if effect_str else cl)
            elif any(k in cl for k in ("对策", "改善", "防错", "增加", "采用", "管控", "标准", "全检", "要求")):
                ctrl_str = (f"{ctrl_str}；{cl}" if ctrl_str else cl)
            elif not mech_str:
                mech_str = cl
            elif not ctrl_str:
                ctrl_str = cl

        matched_nd_id = None
        matched_nd_title = None
        for nd in board_nodes:
            nt = str(nd.get("title") or "")
            if nt and (nt in para or any(seg in para for seg in re.findall(r"[\u4e00-\u9fa5]{2,4}", nt))):
                matched_nd_id = nd.get("id")
                matched_nd_title = nt
                break

        refs = _auto_match_db_refs(para, db)
        for code_match in re.findall(r"\b(?:PRT|SUP|QI|ISS|PRJ|CTQ)-[A-Z0-9-]+\b", para.upper()):
            if not any((r.code or "").upper() == code_match for r in refs):
                refs.append(FmeaLinkedRefSchema(type="free", code=None, label=code_match))

        fallback_drafts.append(FmeaAiParseDraft(
            fmea_type="PFMEA" if is_pfmea else "DFMEA",
            failure_mode=mode_str,
            failure_mech=mech_str or f"源于现场异常输入：{para[:80]}",
            failure_effect=effect_str or "功能退化、寿命衰减或下线检测不良",
            control_measure=ctrl_str or "制定图纸防错红线与制程首检/在线监控互锁标准",
            risk_level="HIGH" if is_high else "MED",
            suggested_target_kind="node",
            suggested_target_id=matched_nd_id,
            suggested_node_title=matched_nd_title or ("关键工序节点" if is_pfmea else "待检结构单元"),
            linked_refs=refs,
        ))

    return FmeaAiParseResp(engine_mode="rule_fallback", drafts=fallback_drafts)
