#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Studio & Environment Config Verification Test Suite
测试数据库工作台 API、异机配置与数据字典功能
"""

import sys
import json
import urllib.request
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8010/api/dev/db"

def print_result(case_name: str, passed: bool, detail: str = ""):
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_name}")
    if detail:
        print(f"       -> {detail}")

def http_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "TestClient"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post(url: str, data: dict):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "TestClient"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_put(url: str, data: dict):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "TestClient"},
        method="PUT"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_delete(url: str):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TestClient"},
        method="DELETE"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def test_suite():
    print("=" * 60)
    print(" 开始执行数据库工作台与异机配置自动化验证测试")
    print("=" * 60)

    # 1. 测试连接状态探针
    try:
        res = http_get(f"{BASE_URL}/status")
        assert "is_connected" in res
        assert "current_host" in res
        assert "masked_password" in res
        print_result("用例 1: 获取数据库存活与脱敏配置", True, f"状态: {res['is_connected']}, 主机: {res['current_host']}:{res['current_port']}, 库名: {res['current_db']}, 密码: {res['masked_password']}")
    except Exception as e:
        print_result("用例 1: 获取数据库存活与脱敏配置", False, str(e))
        return False

    # 2. 测试指定连接参数探针
    try:
        test_payload = {
            "host": res.get("current_host", "127.0.0.1"),
            "port": res.get("current_port", 3306),
            "user": res.get("current_user", "root"),
            "db_name": res.get("current_db", "sqm")
        }
        test_res = http_post(f"{BASE_URL}/test", test_payload)
        assert test_res.get("success") is True
        print_result("用例 2: 测试连接参数探针 (POST /test)", True, f"反馈: {test_res.get('message')}")
    except Exception as e:
        print_result("用例 2: 测试连接参数探针 (POST /test)", False, str(e))
        return False

    # 3. 获取所有数据表元数据及真实物理行数
    target_table = None
    try:
        tables = http_get(f"{BASE_URL}/tables")
        assert isinstance(tables, list) and len(tables) > 0
        names = [t["table_name"] for t in tables]
        assert "sqm_supplier" in names or "sqm_kb_doc" in names
        target_table = "sqm_supplier" if "sqm_supplier" in names else tables[0]["table_name"]
        t_info = next(t for t in tables if t["table_name"] == target_table)
        print_result("用例 3: 扫描数据库表结构清单 (GET /tables)", True, f"共找到 {len(tables)} 张表, 目标表 [{target_table}] 精确行数: {t_info.get('real_count', t_info['table_rows'])}, 注释: {t_info.get('comment')}")
    except Exception as e:
        print_result("用例 3: 扫描数据库表结构清单 (GET /tables)", False, str(e))
        return False

    # 4. 获取指定表的字段字典定义与主键探针
    sample_col = None
    original_comment = ""
    try:
        columns = http_get(f"{BASE_URL}/tables/{target_table}/columns")
        assert isinstance(columns, list) and len(columns) > 0
        pk_cols = [c for c in columns if c.get("is_primary")]
        assert len(pk_cols) > 0
        pk_name = pk_cols[0]["column_name"]
        
        # 寻找一个非主键文本列做修改测试
        for c in columns:
            if not c.get("is_primary") and c.get("data_type") in ["varchar", "text"]:
                sample_col = c["column_name"]
                original_comment = c.get("column_comment", "") or ""
                break
        if not sample_col:
            sample_col = columns[-1]["column_name"]
            original_comment = columns[-1].get("column_comment", "") or ""

        print_result("用例 4: 获取表字段数据字典 (GET /tables/{t}/columns)", True, f"主键: [{pk_name}], 共 {len(columns)} 个字段, 选取测试列: [{sample_col}] (原注释: '{original_comment}')")
    except Exception as e:
        print_result("用例 4: 获取表字段数据字典 (GET /tables/{t}/columns)", False, str(e))
        return False

    # 5. 测试就地更新字段数据字典注释，并安全还原
    try:
        test_comment = "【测试自动更新注释】企业主数据"
        put_res = http_put(f"{BASE_URL}/tables/{target_table}/columns/comment", {
            "column_name": sample_col,
            "comment": test_comment
        })
        assert put_res.get("success") is True
        
        # 再次拉取验证
        cols_after = http_get(f"{BASE_URL}/tables/{target_table}/columns")
        col_item = next(c for c in cols_after if c["column_name"] == sample_col)
        assert col_item["column_comment"] == test_comment

        # 还原注释
        http_put(f"{BASE_URL}/tables/{target_table}/columns/comment", {
            "column_name": sample_col,
            "comment": original_comment
        })
        print_result("用例 5: 字段数据字典注释在线修改与自动还原 (PUT /comment)", True, f"成功完成修改并已恢复为原注释: '{original_comment}'")
    except Exception as e:
        print_result("用例 5: 字段数据字典注释在线修改与自动还原 (PUT /comment)", False, str(e))
        return False

    # 6. 测试物理数据分页查询
    try:
        rows_res = http_get(f"{BASE_URL}/tables/{target_table}/rows?page=1&page_size=5")
        assert "items" in rows_res
        assert "total" in rows_res
        items = rows_res["items"]
        print_result("用例 6: 物理数据行分页检索 (GET /tables/{t}/rows)", True, f"总记录数: {rows_res['total']}, 当前获取: {len(items)} 条")
    except Exception as e:
        print_result("用例 6: 物理数据行分页检索 (GET /tables/{t}/rows)", False, str(e))
        return False

    # 7. 测试新增记录、修改记录与物理删除记录
    try:
        # 新增一条测试记录
        insert_data = {
            "code": "TEST_AUTO_001",
            "name": "自动化测试专用虚拟供应商",
            "status": "潜在",
            "supply_tier": "潜在供应商",
            "product_type": "自动化测试部件"
        }
        post_res = http_post(f"{BASE_URL}/tables/sqm_supplier/rows", {"values": insert_data})
        new_id = post_res.get("row_id")
        assert new_id is not None
        print_result("用例 7.1: 插入物理数据记录 (POST /rows)", True, f"成功创建主键 ID = {new_id}")

        # 修改该记录
        update_res = http_put(f"{BASE_URL}/tables/sqm_supplier/rows/{new_id}", {
            "values": {"short_name": "测试简称UPDATED"},
            "primary_col": "id"
        })
        assert update_res.get("success") is True
        print_result("用例 7.2: 行内/弹窗修改物理数据记录 (PUT /rows/{id})", True, f"成功更新 ID = {new_id} 字段")

        # 删除该记录
        del_res = http_delete(f"{BASE_URL}/tables/sqm_supplier/rows/{new_id}?primary_col=id")
        assert del_res.get("success") is True
        print_result("用例 7.3: 安全删除物理数据记录 (DELETE /rows/{id})", True, f"已安全清理测试记录 ID = {new_id}")
    except Exception as e:
        print_result("用例 7: 数据行增删改查生命周期", False, str(e))
        return False

    # 8. 测试数据表架构文档 (data/table_docs/*.json 读写与自动生成)
    try:
        doc_res = http_get(f"{BASE_URL}/tables/sqm_supplier/doc")
        assert doc_res.get("table_name") == "sqm_supplier"
        assert "html_content" in doc_res and len(doc_res["html_content"]) > 0
        print_result("用例 8.1: 读取数据表架构文档 (GET /doc 从 JSON)", True, f"表名: {doc_res['table_name']}, 标题: {doc_res.get('title')}, 更新时间: {doc_res.get('updated_at')}")

        # 更新文档
        update_doc_payload = {
            "title": "供应商主数据表架构设计 (测试更新)",
            "html_content": doc_res["html_content"] + "<p><strong>自动化测试追加架构修订记录</strong></p>"
        }
        put_doc_res = http_put(f"{BASE_URL}/tables/sqm_supplier/doc", update_doc_payload)
        assert put_doc_res.get("success") is True
        print_result("用例 8.2: 更新并持久化架构文档 (PUT /doc 写入 JSON)", True, put_doc_res.get("message"))

        # 验证持久化内容
        doc_verify = http_get(f"{BASE_URL}/tables/sqm_supplier/doc")
        assert "自动化测试追加架构修订记录" in doc_verify.get("html_content", "")
        print_result("用例 8.3: 验证持久化 JSON 内容一致性", True, f"成功从 data/table_docs/sqm_supplier.json 读取最新修改")
    except Exception as e:
        print_result("用例 8: 数据表架构设计文档测试", False, str(e))
        return False

    print("=" * 60)
    print(" 全部 8 项数据库工作台自动化测试 100% 通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_suite()
    sys.exit(0 if success else 1)
