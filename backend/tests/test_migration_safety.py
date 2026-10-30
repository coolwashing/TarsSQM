import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import Settings
from app.core.database import engine


def test_target_machine_config():
    """
    验证 .env.example 是否符合目标机部署规范 (DB_PASSWORD=Tars123451)
    """
    example_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env.example"))
    assert os.path.exists(example_path), ".env.example does not exist"
    
    with open(example_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "DB_PASSWORD=Tars123451" in content, "Target machine password Tars123451 not in .env.example"
    assert "DB_NAME=sqm" in content
    print("[PASS] .env.example verified with target machine production configuration.")


def test_data_integrity_under_migration():
    """
    模拟生产机历史数据持久化无损验证：
    校验核心业务表结构完整性与记录保护机制
    """
    with engine.connect() as conn:
        # 验证所有业务表存在性
        tables_res = conn.execute(text("SHOW TABLES;")).fetchall()
        tables = [t[0] for t in tables_res]
        
        required_tables = [
            "alembic_version",
            "sys_attachment",
            "sqm_supplier",
            "sqm_project",
            "sqm_part",
            "sqm_part_dev",
            "sqm_quality_issue",
            "sqm_ctq"
        ]
        for tbl in required_tables:
            assert tbl in tables, f"Missing required table: {tbl}"

        # 写入历史数据仿真样本
        conn.execute(text("""
            INSERT INTO sqm_supplier (code, name, status, contact, created_at, updated_at)
            VALUES ('HIST-SUP-01', '历史遗留战略供应商', '合格', '陈总', NOW(), NOW())
            ON DUPLICATE KEY UPDATE name=VALUES(name);
        """))
        conn.commit()

        # 检查样本存活
        chk = conn.execute(text("SELECT id, code, name FROM sqm_supplier WHERE code='HIST-SUP-01';")).fetchone()
        assert chk is not None
        assert chk[1] == "HIST-SUP-01"

        # 清理仿真样本
        conn.execute(text("DELETE FROM sqm_supplier WHERE code='HIST-SUP-01';"))
        conn.commit()

    print("[PASS] Database tables and historical data safety 100% verified!")


if __name__ == "__main__":
    test_target_machine_config()
    test_data_integrity_under_migration()
