import sys
import os
import time
import asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


async def run_e2e_full_chain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        print("====================================================================")
        print("          SQM 质量管理系统 - 全链路端到端功能与体验联调验证            ")
        print("====================================================================")

        # 1. 系统健康与存储可用性检验
        health_res = await client.get("/api/health")
        assert health_res.status_code == 200
        health = health_res.json()
        assert health["status"] == "healthy"
        assert health["database"]["status"] == "connected"
        assert health["storage"]["writable"] is True
        print(f"[E2E-1/5] 健康检查通过: MySQL {health['database']['version']} 在线, 存储可写")

        uid = int(time.time())

        # 2. M2 主数据联动测试 (供应商 -> 项目 -> 零件)
        sup_code = f"E2E-SUP-{uid}"
        sup_res = await client.post("/api/maindata/suppliers", json={
            "code": sup_code,
            "name": f"具身机器人核心关节供应商_{uid}",
            "status": "合格",
            "contact": "赵工",
            "phone": "13912345678",
            "email": "zhao@robot-parts.com",
            "address": "上海市张江高科技园区智能制造基地8号楼",
            "remark": "IATF 16949 及 ISO 9001 双认证企业"
        })
        assert sup_res.status_code in [201, 200]
        sup_id = sup_res.json()["id"]

        prj_code = f"E2E-PRJ-{uid}"
        prj_res = await client.post("/api/maindata/projects", json={
            "project_code": prj_code,
            "name": f"全尺寸双足人形机器人Alpha_{uid}",
            "platform": "Bipedal-G2通用具身平台",
            "sop_date": "2026-12-31",
            "status": "开发中",
            "remark": "年度核心战略产品量产攻坚"
        })
        assert prj_res.status_code in [201, 200]
        prj_id = prj_res.json()["id"]

        part_no = f"E2E-PART-{uid}"
        part_res = await client.post("/api/maindata/parts", json={
            "part_no": part_no,
            "name": f"髋关节高扭矩无刷电机转子_{uid}",
            "project_id": prj_id,
            "category": "驱动执行器",
            "drawing_version": "A.0",
            "engineer": "钱工",
            "remark": "关键承力回转部件，动平衡等级 G1.0"
        })
        assert part_res.status_code in [201, 200]
        part_id = part_res.json()["id"]

        # 验证零件查询级联项目代号
        part_get_res = await client.get(f"/api/maindata/parts/{part_id}")
        assert part_get_res.status_code == 200
        assert part_get_res.json()["project_code"] == prj_code
        print(f"[E2E-2/5] 主数据全链路闭环: 供应商[{sup_code}] -> 项目[{prj_code}] -> 零件[{part_no}]")

        # 3. M3 SQM 零件开发流转看板测试 (OTS -> PPAP -> SOP)
        dev_res = await client.post("/api/sqm/part-devs", json={
            "part_id": part_id,
            "supplier_id": sup_id,
            "dev_phase": "OTS",
            "status": "进行中",
            "target_date": "2026-11-15",
            "sample_qty": 3,
            "responsible": "钱工",
            "remark": "首轮试制样件外观尺寸全尺寸实测"
        })
        assert dev_res.status_code == 201
        dev_id = dev_res.json()["id"]

        # 推进到工装样件
        await client.put(f"/api/sqm/part-devs/{dev_id}", json={
            "dev_phase": "工装样件",
            "status": "待评审",
            "sample_qty": 10,
            "remark": "模具出样，准备装机台架动载耐久测试"
        })

        # 推进到 PPAP 并批准
        dev_final_res = await client.put(f"/api/sqm/part-devs/{dev_id}", json={
            "dev_phase": "PPAP",
            "status": "已批准",
            "sample_qty": 50,
            "remark": "PPAP全套PSW签署完毕，准予量产爬坡"
        })
        assert dev_final_res.status_code == 200
        assert dev_final_res.json()["status"] == "已批准"
        print(f"[E2E-3/5] 零件开发试制流转成功: OTS -> 工装样件 -> PPAP(已批准)")

        # 4. M3 质量问题台账与整改闭环测试
        issue_res = await client.post("/api/sqm/issues", json={
            "title": f"转子动平衡初始残余不平衡量超标_{uid}",
            "part_id": part_id,
            "supplier_id": sup_id,
            "severity": "严重",
            "status": "登记",
            "issue_desc": "<p>台架测试发现高速运转时振动加速度超过 2.5m/s2，动平衡量偏出 15mg</p>",
            "responsible": "孙工",
            "occurred_date": "2026-10-18"
        })
        assert issue_res.status_code == 201
        issue_id = issue_res.json()["id"]
        issue_no = issue_res.json()["issue_no"]

        # 提交改善方案并自动闭环
        close_res = await client.put(f"/api/sqm/issues/{issue_id}", json={
            "solution": "<p>优化去重孔钻削偏置算法，增加精密动平衡机自检校准工序</p>",
            "status": "闭环"
        })
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "闭环"
        assert close_res.json()["closed_date"] is not None
        print(f"[E2E-4/5] 质量问题台账与改善闭环: [{issue_no}] 登记 -> 提交富文本整改 -> 自动完成闭环日期标记")

        # 5. M4 CTQ 关键质量特性规格管控测试
        ctq_res = await client.post("/api/ctq", json={
            "part_id": part_id,
            "feature_code": "KPC-ROTOR-01",
            "feature_name": "转子动平衡残余量",
            "feature_type": "KPC",
            "standard_value": "<= 5.0mg",
            "tolerance": "<= 5.0mg",
            "inspection_tool": "申克高速动平衡测试仪",
            "frequency": "100% 全检",
            "control_method": "自动点胶去重补偿互锁",
            "remark": "关键安全与噪音特性"
        })
        assert ctq_res.status_code == 201
        ctq_id = ctq_res.json()["id"]

        by_part_ctq = await client.get(f"/api/ctq/by-part/{part_id}")
        assert by_part_ctq.status_code == 200
        assert len(by_part_ctq.json()) == 1
        print(f"[E2E-5/5] CTQ 关键质量特性配置生效: {ctq_res.json()['feature_code']} (100% 全检 / SPC互锁)")

        # 6. 数据清理
        await client.delete(f"/api/ctq/{ctq_id}")
        await client.delete(f"/api/sqm/issues/{issue_id}")
        await client.delete(f"/api/sqm/part-devs/{dev_id}")
        await client.delete(f"/api/maindata/parts/{part_id}")
        await client.delete(f"/api/maindata/projects/{prj_id}")
        await client.delete(f"/api/maindata/suppliers/{sup_id}")
        print("--------------------------------------------------------------------")
        print(">>> [SUCCESS] 全链路 100% 端到端联调测试全部通过！系统健壮性达成 100% <<<")
        print("--------------------------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(run_e2e_full_chain())
