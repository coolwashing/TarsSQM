import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport

# 确保 backend 位于 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


async def run_sqm_api_tests():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 测试单号自动生成预检
        res = await client.get("/api/sqm/issues/next-no")
        assert res.status_code == 200, f"Next issue no failed: {res.text}"
        data = res.json()
        assert "next_issue_no" in data
        assert data["next_issue_no"].startswith("QI-")
        print(f"[OK] Next Issue No: {data['next_issue_no']}")

        # 2. 准备基础数据：供应商、项目与零件
        sup_res = await client.post("/api/maindata/suppliers", json={
            "code": "TEST-SUP-SQM-001",
            "name": "SQM集成验证供应商",
            "status": "合格",
            "contact": "王工",
            "phone": "13800000001"
        })
        assert sup_res.status_code in [201, 200], f"Create supplier failed: {sup_res.text}"
        sup_id = sup_res.json()["id"]

        prj_res = await client.post("/api/maindata/projects", json={
            "project_code": "TEST-PRJ-SQM-001",
            "name": "SQM人形机器人验证项目",
            "platform": "双足具身",
            "status": "开发中"
        })
        assert prj_res.status_code in [201, 200], f"Create project failed: {prj_res.text}"
        prj_id = prj_res.json()["id"]

        part_res = await client.post("/api/maindata/parts", json={
            "part_no": "TEST-PART-SQM-001",
            "name": "高精度谐波减速机传动轴",
            "project_id": prj_id,
            "category": "驱动执行器",
            "drawing_version": "B.0",
            "engineer": "李工"
        })
        assert part_res.status_code in [201, 200], f"Create part failed: {part_res.text}"
        part_id = part_res.json()["id"]

        # 3. 测试 2.1 零件开发看板 (PartDev CRUD)
        dev_create_res = await client.post("/api/sqm/part-devs", json={
            "part_id": part_id,
            "supplier_id": sup_id,
            "dev_phase": "OTS",
            "status": "进行中",
            "target_date": "2026-11-30",
            "sample_qty": 5,
            "responsible": "李工",
            "remark": "首批样件试制送检"
        })
        assert dev_create_res.status_code == 201, f"Create part_dev failed: {dev_create_res.text}"
        dev_data = dev_create_res.json()
        dev_id = dev_data["id"]
        assert dev_data["dev_phase"] == "OTS"
        assert dev_data["part_no"] == "TEST-PART-SQM-001"
        assert dev_data["supplier_name"] == "SQM集成验证供应商"
        print(f"[OK] Created PartDev ID {dev_id}: {dev_data['part_no']} <-> {dev_data['supplier_name']}")

        # 查询开发看板列表
        dev_list_res = await client.get("/api/sqm/part-devs", params={"keyword": "谐波减速机", "dev_phase": "OTS"})
        assert dev_list_res.status_code == 200
        assert dev_list_res.json()["total"] >= 1
        print(f"[OK] Queried PartDev list, total: {dev_list_res.json()['total']}")

        # 更新开发阶段至 PPAP
        dev_update_res = await client.put(f"/api/sqm/part-devs/{dev_id}", json={
            "dev_phase": "PPAP",
            "status": "已批准",
            "sample_qty": 50,
            "remark": "PPAP资料审核通过，具备小批量试生产条件"
        })
        assert dev_update_res.status_code == 200
        assert dev_update_res.json()["dev_phase"] == "PPAP"
        assert dev_update_res.json()["status"] == "已批准"
        print(f"[OK] Updated PartDev ID {dev_id} to phase PPAP / 已批准")

        # 4. 测试 2.2 质量问题台账 (QualityIssue CRUD)
        issue_create_res = await client.post("/api/sqm/issues", json={
            "title": "装配齿圈外径同轴度超差 0.03mm",
            "part_id": part_id,
            "supplier_id": sup_id,
            "severity": "严重",
            "status": "登记",
            "issue_desc": "<p>首检发现齿圈表面外圆跳动超标，影响减速机回差装配精度</p>",
            "responsible": "张工",
            "occurred_date": "2026-10-18"
        })
        assert issue_create_res.status_code == 201, f"Create issue failed: {issue_create_res.text}"
        issue_data = issue_create_res.json()
        issue_id = issue_data["id"]
        assert issue_data["issue_no"].startswith("QI-")
        assert issue_data["severity"] == "严重"
        assert issue_data["part_name"] == "高精度谐波减速机传动轴"
        print(f"[OK] Created QualityIssue ID {issue_id}: {issue_data['issue_no']} - {issue_data['title']}")

        # 查询问题列表
        issue_list_res = await client.get("/api/sqm/issues", params={"severity": "严重", "status": "登记"})
        assert issue_list_res.status_code == 200
        assert issue_list_res.json()["total"] >= 1
        print(f"[OK] Queried QualityIssue list, total: {issue_list_res.json()['total']}")

        # 获取问题详情 (含附件插槽)
        detail_res = await client.get(f"/api/sqm/issues/{issue_id}")
        assert detail_res.status_code == 200
        assert "attachments" in detail_res.json()
        print(f"[OK] Fetched QualityIssue detail: attachments={len(detail_res.json()['attachments'])}")

        # 更新整改方案并闭环
        issue_update_res = await client.put(f"/api/sqm/issues/{issue_id}", json={
            "solution": "<p>调整磨齿机定位夹具同心度，增设在线三坐标100%全检工序</p>",
            "status": "闭环"
        })
        assert issue_update_res.status_code == 200
        updated_issue = issue_update_res.json()
        assert updated_issue["status"] == "闭环"
        assert updated_issue["closed_date"] is not None
        print(f"[OK] Updated QualityIssue to 闭环 with closed_date={updated_issue['closed_date']}")

        # 5. 清理测试数据
        del_issue_res = await client.delete(f"/api/sqm/issues/{issue_id}")
        assert del_issue_res.status_code == 200

        del_dev_res = await client.delete(f"/api/sqm/part-devs/{dev_id}")
        assert del_dev_res.status_code == 200

        await client.delete(f"/api/maindata/parts/{part_id}")
        await client.delete(f"/api/maindata/projects/{prj_id}")
        await client.delete(f"/api/maindata/suppliers/{sup_id}")
        print("\n>>> [PASS] All SQM 2.1 & 2.2 APIs verified with 100% success! <<<")


if __name__ == "__main__":
    asyncio.run(run_sqm_api_tests())
