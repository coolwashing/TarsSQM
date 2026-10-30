"""
通用 Excel 导入校验与数据落地执行引擎
基于 openpyxl 实现：
1. 规范化模板生成（带表头样式、列宽自适应、批注提示、下拉数据校验 DataValidation）
2. 5层纵深校验（空行过滤、必填检查、枚举合规、文件内唯一性、数据库唯一性、外键自然键解析转换）
3. 事务性批量入库提交
"""
import io
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment
from sqlalchemy.orm import Session

from app.common.excel_configs import get_excel_config
from app.models.main_data import SqmSupplier, SqmPart, SqmProject


def build_template_bytes(biz_key: str) -> bytes:
    """
    生成对应业务实体的 Excel 录入模板
    内置企业级蓝白样式、字段批注提示、下拉数据约束及示范行
    """
    config = get_excel_config(biz_key)
    if not config:
        raise ValueError(f"未找到业务实体 [{biz_key}] 的导入配置")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = config["sheet_name"]
    ws.views.sheetView[0].showGridLines = True

    # 样式配置
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    sample_font = Font(name="微软雅黑", size=10, italic=True, color="595959")
    sample_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    sample_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    fields: List[Dict[str, Any]] = config["fields"]

    # 设置行高
    ws.row_dimensions[1].height = 36
    ws.row_dimensions[2].height = 26

    for col_idx, field in enumerate(fields, start=1):
        col_letter = get_column_letter(col_idx)

        # 表头文本 (必填项添加红星标示)
        is_required = field.get("required", False)
        header_text = f"{field['label']} *" if is_required else field["label"]

        header_cell = ws.cell(row=1, column=col_idx, value=header_text)
        header_cell.font = header_font
        header_cell.fill = header_fill
        header_cell.alignment = header_align
        header_cell.border = thin_border

        # 批注提示
        comment_lines = []
        if is_required:
            comment_lines.append("【必填字段】")
        else:
            comment_lines.append("【选填字段】")

        if field.get("comment"):
            comment_lines.append(f"说明: {field['comment']}")
        if field.get("enums"):
            comment_lines.append(f"可选值: {' / '.join(field['enums'])}")
        if field.get("sample"):
            comment_lines.append(f"格式示范: {field['sample']}")

        comment_text = "\n".join(comment_lines)
        cell_comment = Comment(comment_text, "SQM系统")
        cell_comment.width = 240
        cell_comment.height = 90
        header_cell.comment = cell_comment

        # 下拉列表约束 DataValidation
        enums = field.get("enums")
        if enums:
            dv = DataValidation(
                type="list",
                formula1=f'"{",".join(enums)}"',
                allow_blank=not is_required
            )
            dv.error = f"输入无效，请从下拉列表中选择：{', '.join(enums)}"
            dv.errorTitle = "数据格式错误"
            dv.prompt = f"请选择：{'/'.join(enums)}"
            dv.promptTitle = f"{field['label']}选项"
            ws.add_data_validation(dv)
            dv.add(f"{col_letter}2:{col_letter}2000")

        # 写入示范数据行（行2）
        sample_val = field.get("sample", "")
        sample_cell = ws.cell(row=2, column=col_idx, value=sample_val)
        sample_cell.font = sample_font
        sample_cell.fill = sample_fill
        sample_cell.alignment = sample_align
        sample_cell.border = thin_border

        # 列宽自适应
        calc_width = max(len(field["label"]) * 3.5 + 6, 18)
        ws.column_dimensions[col_letter].width = calc_width

    # 导出字节流
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _normalize_header(text: Any) -> str:
    """清理表头文本（移除星号、空格与括号便于弹性模糊匹配）"""
    if text is None:
        return ""
    s = str(text).strip()
    s = re.sub(r"[\s\*（）\(\)]", "", s)
    return s.lower()


def _parse_date(val: Any) -> Tuple[Optional[date], Optional[str]]:
    """解析日期对象或文本，返回 (date_obj, error_msg)"""
    if val is None or str(val).strip() == "":
        return None, None
    if isinstance(val, (datetime, date)):
        return (val.date() if isinstance(val, datetime) else val), None
    
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.date(), None
        except ValueError:
            continue
    return None, f"日期格式无效 [{val_str}]，请采用 YYYY-MM-DD 格式 (如 2026-10-18)"


def validate_uploaded_file(biz_key: str, file_bytes: bytes, db: Session) -> Dict[str, Any]:
    """
    通用多维校验引擎：
    1. 表头智能匹配
    2. 空行过滤
    3. 必填校验
    4. 枚举值合法性校验
    5. 数据类型转换与格式校验 (Date, Int)
    6. 上传文件内唯一性查重 (防止文件内部有多行相同编号)
    7. 数据库既有数据唯一性查重 (防止撞库)
    8. 自然业务键到外键物理ID自动解析 (如 零件图号 -> part_id, 项目代号 -> project_id)
    """
    config = get_excel_config(biz_key)
    if not config:
        raise ValueError(f"未找到业务实体 [{biz_key}] 的导入配置")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    except Exception as e:
        raise ValueError(f"无法读取 Excel 文件，请确保上传合法的 .xlsx 或 .xls 文件: {str(e)}")

    ws = wb.active
    fields: List[Dict[str, Any]] = config["fields"]

    # 建立表头映射
    header_col_map: Dict[int, Dict[str, Any]] = {}
    row1_cells = [cell.value for cell in ws[1]]

    # 模糊归一化匹配
    for col_idx, raw_header in enumerate(row1_cells, start=1):
        norm_h = _normalize_header(raw_header)
        if not norm_h:
            continue
        for field in fields:
            f_norm_label = _normalize_header(field["label"])
            f_prop = field["prop"].lower()
            if norm_h == f_norm_label or norm_h == f_prop or f_norm_label in norm_h:
                header_col_map[col_idx] = field
                break

    # 检查是否有必填表头未识别到
    identified_props = {f["prop"] for f in header_col_map.values()}
    missing_required_headers = [
        f["label"] for f in fields if f.get("required") and f["prop"] not in identified_props
    ]
    if missing_required_headers:
        raise ValueError(f"Excel 模板表头缺失必要列: {', '.join(missing_required_headers)}")

    # 准备缓存以加速外键与唯一性查询
    fk_project_cache: Dict[str, Optional[int]] = {}
    fk_supplier_cache: Dict[str, Optional[int]] = {}
    fk_part_cache: Dict[str, Optional[int]] = {}

    # 文件内唯一键重复检测器
    seen_unique_values: Dict[str, Dict[str, int]] = {}
    for f in fields:
        if f.get("unique"):
            seen_unique_values[f["prop"]] = {}

    rows_report = []
    total_valid = 0
    total_invalid = 0

    # 逐行扫描校验 (从第2行开始)
    max_row = ws.max_row
    for row_num in range(2, max_row + 1):
        row_cells = [ws.cell(row=row_num, column=col_idx).value for col_idx in range(1, len(row1_cells) + 1)]
        
        # 判定是否全空行
        if all(c is None or str(c).strip() == "" for c in row_cells):
            continue

        row_errors: List[str] = []
        raw_row_data: Dict[str, Any] = {}
        clean_row_data: Dict[str, Any] = {}

        # 遍历已识别的列
        for col_idx, field in header_col_map.items():
            prop = field["prop"]
            label = field["label"]
            raw_val = ws.cell(row=row_num, column=col_idx).value

            # 字符串清洗
            str_val = str(raw_val).strip() if raw_val is not None else ""
            raw_row_data[prop] = str_val

            # 1. 必填校验
            if field.get("required") and not str_val:
                row_errors.append(f"【{label}】为必填项，不可为空")
                continue

            if not str_val:
                # 选填且为空
                default_val = field.get("default")
                if default_val is not None:
                    clean_row_data[prop] = default_val
                continue

            # 2. 枚举校验
            enums = field.get("enums")
            if enums and str_val not in enums:
                row_errors.append(f"【{label}】值 [{str_val}] 不合规，允许范围: {', '.join(enums)}")
                continue

            # 3. 日期类型校验
            field_type = field.get("type")
            if field_type == "date":
                date_val, err = _parse_date(raw_val)
                if err:
                    row_errors.append(f"【{label}】{err}")
                    continue
                clean_row_data[prop] = date_val
                continue

            # 4. 整数类型校验
            if field_type == "int":
                try:
                    clean_row_data[prop] = int(float(str_val))
                except (ValueError, TypeError):
                    row_errors.append(f"【{label}】必须为整数格式")
                    continue
                continue

            # 5. 文件内唯一性检测
            if field.get("unique"):
                tracker = seen_unique_values[prop]
                if str_val in tracker:
                    row_errors.append(f"【{label}】[{str_val}] 与第 {tracker[str_val]} 行数据重复")
                else:
                    tracker[str_val] = row_num

                # 6. 数据库已有数据查重
                model_cls = config["model"]
                exists_in_db = db.query(model_cls).filter(getattr(model_cls, prop) == str_val).first()
                if exists_in_db:
                    row_errors.append(f"【{label}】[{str_val}] 在系统数据库中已存在，不可重复导入")

            # 7. 外键关系自动解析
            fk_target = field.get("fk_target")
            fk_field = field.get("fk_field")
            if fk_target and fk_field:
                resolved_id = None
                if fk_target == "project":
                    if str_val not in fk_project_cache:
                        prj = db.query(SqmProject).filter(
                            (SqmProject.project_code == str_val) | (SqmProject.name == str_val)
                        ).first()
                        fk_project_cache[str_val] = prj.id if prj else None
                    resolved_id = fk_project_cache[str_val]
                    if not resolved_id:
                        row_errors.append(f"【{label}】项目代号 [{str_val}] 在系统中未找到，请核对或先建立项目")
                    else:
                        clean_row_data[fk_field] = resolved_id

                elif fk_target == "supplier":
                    if str_val not in fk_supplier_cache:
                        sup = db.query(SqmSupplier).filter(
                            (SqmSupplier.code == str_val) | (SqmSupplier.name == str_val)
                        ).first()
                        fk_supplier_cache[str_val] = sup.id if sup else None
                    resolved_id = fk_supplier_cache[str_val]
                    if not resolved_id:
                        row_errors.append(f"【{label}】供应商 [{str_val}] 在系统中未找到，请核对或先建立供应商")
                    else:
                        clean_row_data[fk_field] = resolved_id

                elif fk_target == "part":
                    if str_val not in fk_part_cache:
                        pt = db.query(SqmPart).filter(
                            (SqmPart.part_no == str_val) | (SqmPart.name == str_val)
                        ).first()
                        fk_part_cache[str_val] = pt.id if pt else None
                    resolved_id = fk_part_cache[str_val]
                    if not resolved_id:
                        row_errors.append(f"【{label}】零件图号 [{str_val}] 在系统中未找到，请核对或先建立零件主数据")
                    else:
                        clean_row_data[fk_field] = resolved_id

                continue

            # 普通字段直接填入
            clean_row_data[prop] = str_val

        # 判定整行状态
        is_valid = len(row_errors) == 0
        if is_valid:
            total_valid += 1
        else:
            total_invalid += 1

        rows_report.append({
            "row_num": row_num,
            "is_valid": is_valid,
            "errors": row_errors,
            "raw_data": raw_row_data,
            "clean_data": clean_row_data if is_valid else {}
        })

    return {
        "biz_key": biz_key,
        "title": config["title"],
        "total_rows": len(rows_report),
        "valid_rows_count": total_valid,
        "invalid_rows_count": total_invalid,
        "columns": [{"prop": f["prop"], "label": f["label"]} for f in fields],
        "rows": rows_report,
    }


def commit_import_data(biz_key: str, valid_rows: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
    """
    执行原子事务批量入库
    """
    config = get_excel_config(biz_key)
    if not config:
        raise ValueError(f"未找到业务实体 [{biz_key}] 的导入配置")

    model_cls = config["model"]
    valid_col_names = {c.name for c in model_cls.__table__.columns}

    instances = []
    for item in valid_rows:
        clean_dict = item.get("clean_data", {})
        if not clean_dict:
            clean_dict = item.get("raw_data", {})

        # 过滤仅属于该模型的有效字段
        filtered_payload = {k: v for k, v in clean_dict.items() if k in valid_col_names}
        instances.append(model_cls(**filtered_payload))

    try:
        db.add_all(instances)
        db.commit()
        return {
            "success": True,
            "imported_count": len(instances),
            "message": f"成功批量导入 {len(instances)} 条【{config['title']}】数据"
        }
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"批量写入数据库失败: {str(e)}")
