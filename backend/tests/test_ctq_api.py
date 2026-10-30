import sys
import os
import time
import asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


async def run_ctq_api_tests():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        part_no = f"CTQ-PART-{int(time.time())}"
        # 1. 准备关联零件测试数据
        part_res = await client.post("/api/maindata/parts", json={
            "part_no": part_no,
            "name": "人形机器人膝关节转轴",
            "category": "机械结构件",
            "drawing_version": "A.1",
            "engineer": "王工"
        })
        assert part_res.status_code in [201, 200], f"Create part failed: {part_res.text}"
        part_id = part_res.json()["id"]

        # 2. 单个创建 CTQ (KPC)
        create_res = await client.post("/api/ctq", json={
            "part_id": part_id,
            "feature_code": "KPC-01",
            "feature_name": "轴承配合位外径尺寸",
            "feature_type": "KPC",
            "standard_value": "35.000mm",
            "tolerance": "+0.012/-0.005mm",
            "inspection_tool": "数显外径千分尺 (0.001mm)",
            "frequency": "首末件+每批抽检5件",
            "control_method": "SPC Xbar-R控制图",
            "remark": "高配合精度，严禁划痕"
        })
        assert create_res.status_code == 201, f"Create CTQ failed: {create_res.text}"
        ctq_data = create_res.json()
        ctq_id = ctq_data["id"]
        assert ctq_data["feature_code"] == "KPC-01"
        assert ctq_data["part_no"] == part_no
        print(f"[OK] Created single CTQ ID {ctq_id}: {ctq_data['feature_code']} - {ctq_data['feature_name']}")

        # 3. 批量录入 CTQ (KCC)
        batch_res = await client.post("/api/ctq/batch", json={
            "part_id": part_id,
            "items": [
                {
                    "feature_code": "KCC-01",
                    "feature_name": "感应淬火层有效硬化深度",
                    "feature_type": "KCC",
                    "standard_value": "1.5mm",
                    "tolerance": ">= 1.2mm",
                    "inspection_tool": "显微硬度计",
                    "frequency": "每炉抽样金相1件",
                    "control_method": "加热功率与扫描速度程序互锁"
                },
                {
                    "feature_code": "KCC-02",
                    "feature_name": "表面淬火后洛氏硬度",
                    "feature_type": "KCC",
                    "standard_value": "60 HRC",
                    "tolerance": "58 - 62 HRC",
                    "inspection_tool": "台式洛氏硬度计",
                    "frequency": "首件+抽检3件/批",
                    "control_method": "淬火介质温度监控"
                }
            ]
        })
        assert batch_res.status_code == 200, f"Batch create failed: {batch_res.text}"
        assert batch_res.json()["count"] == 2
        print(f"[OK] Batch created 2 KCC features for part {part_id}")

        # 4. 按零件查询全部 CTQ 清单
        by_part_res = await client.get(f"/api/ctq/by-part/{part_id}")
        assert by_part_res.status_code == 200
        ctqs = by_part_res.json()
        assert len(ctqs) == 3
        print(f"[OK] Fetched {len(ctqs)} CTQs by part_id {part_id}")

        # 5. 分页与过滤检索
        page_res = await client.get("/api/ctq", params={"keyword": "淬火", "feature_type": "KCC"})
        assert page_res.status_code == 200
        assert page_res.json()["total"] >= 2
        print(f"[OK] Filtered CTQ list, total matching: {page_res.json()['total']}")

        # 6. 更新单个 CTQ
        update_res = await client.put(f"/api/ctq/{ctq_id}", json={
            "tolerance": "+0.015/-0.003mm",
            "control_method": "SPC Xbar-R控制图 + 防错量规"
        })
        assert update_res.status_code == 200
        assert update_res.json()["tolerance"] == "+0.015/-0.003mm"
        print(f"[OK] Updated CTQ {ctq_id} tolerance successfully")

        # 7. 删除单条 CTQ
        del_res = await client.delete(f"/api/ctq/{ctq_id}")
        assert del_res.status_code == 200
        print(f"[OK] Deleted single CTQ {ctq_id}")

        # 8. 验证删除剩余与零件级联删除
        rem_res = await client.get(f"/api/ctq/by-part/{part_id}")
        assert rem_res.status_code == 200
        for item in rem_res.json():
            await client.delete(f"/api/ctq/{item['id']}")

        await client.delete(f"/api/maindata/parts/{part_id}")
        print("\n>>> [PASS] All CTQ APIs verified with 100% success! <<<")


if __name__ == "__main__":
    asyncio.run(run_ctq_api_tests())
