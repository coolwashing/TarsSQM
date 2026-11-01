import sys
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List

# 保证在 Windows GBK 终端下打印 UTF-8 符号与 Emoji 正常
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8010"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log_step(name: str):
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}==> [TEST STEP] {name}{Colors.ENDC}")

def log_success(msg: str):
    print(f"  {Colors.OKGREEN}✓ PASS:{Colors.ENDC} {msg}")

def log_fail(msg: str):
    print(f"  {Colors.FAIL}✗ FAIL:{Colors.ENDC} {msg}")


def http_get(path: str, params: Dict[str, Any] = None) -> Any:
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SQM-TestRunner/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"HTTP GET {path} failed with code {resp.status}"
        return json.loads(resp.read().decode('utf-8'))


def http_put(path: str, data: Dict[str, Any] = None) -> Any:
    url = f"{BASE_URL}{path}"
    payload = json.dumps(data or {}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "SQM-TestRunner/1.0"},
        method="PUT"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"HTTP PUT {path} failed with code {resp.status}"
        return json.loads(resp.read().decode('utf-8'))


def http_post(path: str, data: Dict[str, Any]) -> Any:
    url = f"{BASE_URL}{path}"
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "SQM-TestRunner/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status in (200, 201), f"HTTP POST {path} failed with code {resp.status}"
        return json.loads(resp.read().decode('utf-8'))


def http_delete(path: str) -> Any:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SQM-TestRunner/1.0"},
        method="DELETE"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"HTTP DELETE {path} failed with code {resp.status}"
        return json.loads(resp.read().decode('utf-8'))


def test_tc_kb_01_tree_favorite_field():
    """
    TC-KB-01: 验证知识库树形目录接口包含 is_favorite 字段，且正确区分目录与文档
    """
    log_step("TC-KB-01: 验证 /api/kb/tree 树形接口的 is_favorite 字段序列化完整性")
    tree = http_get("/api/kb/tree")
    assert isinstance(tree, list), "树结构必须为列表"
    assert len(tree) > 0, "知识库树不可为空"

    doc_count = 0
    folder_count = 0
    starred_count = 0

    def check_node(node):
        nonlocal doc_count, folder_count, starred_count
        assert "is_favorite" in node, f"节点 [{node.get('title')}] 缺少 is_favorite 字段"
        assert isinstance(node["is_favorite"], bool), f"节点 [{node.get('title')}] is_favorite 必须为布尔值"

        if node.get("is_folder"):
            folder_count += 1
        else:
            doc_count += 1
            if node["is_favorite"]:
                starred_count += 1

        for child in node.get("children", []):
            check_node(child)

    for root_node in tree:
        check_node(root_node)

    log_success(f"树形结构校验通过: 总文件夹数={folder_count}, 总规程文档数={doc_count}, 标星关注文档数={starred_count}")
    return starred_count


def test_tc_kb_02_favorites_aggregation():
    """
    TC-KB-02: 验证 /api/kb/explorer/favorites 全库标星规程聚合查询与归属工程目录展示
    """
    log_step("TC-KB-02: 验证 /api/kb/explorer/favorites 全库标星规程跨目录聚合与归属展示")
    fav_items = http_get("/api/kb/explorer/favorites")
    assert isinstance(fav_items, list), "返回必须为列表"

    log_success(f"获取全库标星规程成功，共 {len(fav_items)} 项")
    for item in fav_items:
        assert item.get("is_favorite") is True, f"非标星项目混入 favorites 列表: {item.get('name')}"
        assert item.get("type") in ("doc", "shortcut"), f"文件夹不能混入标星列表: {item.get('name')}"
        assert item.get("proj", "").startswith("📁"), f"归属工程项目必须标明来源父目录: {item.get('proj')}"
        log_success(f"  -> 标星规程: [{item['id']}] {item['icon']} {item['name']} | 归属: {item['proj']} | 规模: {item['size']}")

    # 验证 /api/kb/explorer/items?only_favorites=true 一致性
    compat_items = http_get("/api/kb/explorer/items", {"only_favorites": "true"})
    assert len(compat_items) == len(fav_items), "only_favorites 参数与专用接口返回数量必须一致"
    log_success("专用接口与通用 items 参数 only_favorites=true 数据一致性校验通过")


def test_tc_kb_03_toggle_favorite_bidirectional():
    """
    TC-KB-03: 验证标星与取消标星的双向切换、数据库持久化及全库标星数动态联动
    """
    log_step("TC-KB-03: 验证 PUT /api/kb/explorer/favorite/{id} 标星状态双向切换与响应式联动")
    # 获取任意一篇规程文档
    tree = http_get("/api/kb/tree")
    target_doc = None
    for root in tree:
        for child in root.get("children", []):
            if not child.get("is_folder"):
                target_doc = child
                break
        if target_doc:
            break

    assert target_doc is not None, "未找到可用于测试标星切换的规程文档"
    doc_id = target_doc["id"]
    orig_state = target_doc["is_favorite"]
    log_success(f"选定测试文档: ID={doc_id}, 标题='{target_doc['title']}', 当前标星状态={orig_state}")

    # 第 1 次切换：反转状态
    res1 = http_put(f"/api/kb/explorer/favorite/{doc_id}")
    new_state1 = res1.get("is_favorite")
    assert new_state1 != orig_state, f"标星切换失败，状态未改变: {res1}"
    log_success(f"第 1 次切换成功: {orig_state} -> {new_state1}")

    # 验证 favorites 列表联动
    favs1 = http_get("/api/kb/explorer/favorites")
    fav_ids1 = [x["id"] for x in favs1]
    if new_state1:
        assert doc_id in fav_ids1, f"标星后在 /favorites 列表中未查到文档 ID={doc_id}"
        log_success(f"标星生效: 文档 ID={doc_id} 已立即出现在全库标星规程列表中")
    else:
        assert doc_id not in fav_ids1, f"取消标星后在 /favorites 列表中依然存在文档 ID={doc_id}"
        log_success(f"取消标星生效: 文档 ID={doc_id} 已立即从全库标星规程列表中移出")

    # 第 2 次切换：恢复原始状态
    res2 = http_put(f"/api/kb/explorer/favorite/{doc_id}")
    new_state2 = res2.get("is_favorite")
    assert new_state2 == orig_state, f"恢复原始状态失败: {res2}"
    log_success(f"第 2 次切换恢复成功: {new_state1} -> {new_state2} (与原始状态完全一致)")


def test_tc_kb_04_icon_update():
    """
    TC-KB-04: 验证标准业务图标更新接口 PUT /api/kb/explorer/icon 与持久化
    """
    log_step("TC-KB-04: 验证标准业务图标更新接口 PUT /api/kb/explorer/icon 与持久化")
    tree = http_get("/api/kb/tree")
    test_node = tree[0]
    node_id = test_node["id"]
    orig_icon = test_node["icon"]

    new_test_icon = "🎯" if orig_icon != "🎯" else "⚙️"
    res = http_put("/api/kb/explorer/icon", {"id": node_id, "icon": new_test_icon})
    assert res.get("icon") == new_test_icon, f"更新图标返回不一致: {res}"

    # 从数据库中重新拉取验证
    tree_after = http_get("/api/kb/tree")
    node_after = next((n for n in tree_after if n["id"] == node_id), None)
    assert node_after and node_after["icon"] == new_test_icon, "数据库未持久化新图标"
    log_success(f"业务图标修改成功并持久化: [{node_id}] {orig_icon} -> {new_test_icon}")

    # 恢复原图标
    http_put("/api/kb/explorer/icon", {"id": node_id, "icon": orig_icon})
    log_success(f"原图标恢复成功: {new_test_icon} -> {orig_icon}")


def test_tc_kb_05_clean_create():
    """
    TC-KB-05: 验证快速新建文档名称纯净无 .doc 扩展名，以及删除动作
    """
    log_step("TC-KB-05: 验证快速新建文档名称纯净无 .doc 扩展名及级联清理")
    create_payload = {
        "parent_id": None,
        "name": "自动化测试专用质量检验基准表",
        "icon": "📋"
    }
    created = http_post("/api/kb/explorer/doc", create_payload)
    doc_id = created["id"]
    doc_name = created["name"]

    assert not doc_name.endswith(".doc"), f"文档标题严禁带有过时的 .doc 扩展名: {doc_name}"
    assert created["icon"] == "📋", "文档图标未正确保存"
    log_success(f"规程新建成功: ID={doc_id}, 标题='{doc_name}', 图标={created['icon']}")

    # 标星此新建文档
    http_put(f"/api/kb/explorer/favorite/{doc_id}")
    favs = http_get("/api/kb/explorer/favorites")
    assert any(x["id"] == doc_id for x in favs), "新建文档标星后未聚合"
    log_success("新建规程标星全库聚合验证通过")

    # 清理测试文档
    del_res = http_delete(f"/api/kb/explorer/items/{doc_id}")
    log_success(f"测试数据清理完毕: {del_res.get('message')}")


def test_tc_kb_06_breadcrumb_path():
    """
    TC-KB-06: 验证面包屑路径链接口及根目录/子目录导航
    """
    log_step("TC-KB-06: 验证面包屑路径链 GET /api/kb/explorer/path")
    # 根路径
    root_crumbs = http_get("/api/kb/explorer/path")
    assert len(root_crumbs) == 1 and root_crumbs[0]["name"] == "质量知识库", f"根面包屑不匹配: {root_crumbs}"
    log_success(f"根路径面包屑正确: {root_crumbs[0]['name']}")

    # 子目录路径
    tree = http_get("/api/kb/tree")
    if tree and tree[0].get("is_folder"):
        sub_folder = tree[0]
        sub_crumbs = http_get("/api/kb/explorer/path", {"folder_id": sub_folder["id"]})
        assert len(sub_crumbs) >= 2, f"子目录面包屑应包含至少2级: {sub_crumbs}"
        assert sub_crumbs[-1]["name"] == sub_folder["title"], f"末级面包屑不匹配: {sub_crumbs}"
        log_success(f"子目录面包屑链路正确: {' › '.join([c['name'] for c in sub_crumbs])}")


def main():
    print(f"{Colors.BOLD}{Colors.HEADER}==================================================================")
    print(" SQM 知识库全功能自动化测试程序 (Test Suite: KB Favorites & Explorer)")
    print(f" 目标服务: {BASE_URL}")
    print(f"=================================================================={Colors.ENDC}")

    passed = 0
    total = 6
    tests = [
        ("TC-KB-01", test_tc_kb_01_tree_favorite_field),
        ("TC-KB-02", test_tc_kb_02_favorites_aggregation),
        ("TC-KB-03", test_tc_kb_03_toggle_favorite_bidirectional),
        ("TC-KB-04", test_tc_kb_04_icon_update),
        ("TC-KB-05", test_tc_kb_05_clean_create),
        ("TC-KB-06", test_tc_kb_06_breadcrumb_path),
    ]

    for code, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            log_fail(f"{code} 执行异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n{Colors.BOLD}==================================================================")
    if passed == total:
        print(f" {Colors.OKGREEN}🎉 测试全部通过！ 共执行 {total} 项测试，通过 {passed} 项，失败 0 项。{Colors.ENDC}")
    else:
        print(f" {Colors.FAIL}⚠️ 测试未全部通过！ 通过 {passed}/{total} 项。{Colors.ENDC}")
    print(f"{Colors.BOLD}=================================================================={Colors.ENDC}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
