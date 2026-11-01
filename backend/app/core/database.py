from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# 创建全局 SQLAlchemy 引擎
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,       # 自动探测存活连接，防止 MySQL 默认 8 小时断开
    pool_recycle=3600,        # 1 小时自动回收空闲连接
    pool_size=10,             # 连接池基础容量
    max_overflow=20,          # 连接池最大突发溢出容量
    echo=False                # 生产/调试 SQL 打印控制
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 实体基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 路由依赖注入：为每个请求提供独立的 DB 会话并在完成后自动安全关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_alive() -> tuple[bool, str]:
    """检查当前系统数据库连接是否健康"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "数据库连接正常"
    except Exception as e:
        return False, str(e)


def reconnect_engine() -> bool:
    """热重载全局数据库连接池"""
    global engine, SessionLocal
    try:
        engine.dispose()
    except Exception:
        pass

    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    SessionLocal.configure(bind=engine)
    return True


def test_db_params(host: str, port: int, user: str, password: str, db_name: str) -> tuple[bool, str]:
    """独立测试指定连接参数"""
    from urllib.parse import quote_plus
    from sqlalchemy import text
    try:
        enc_pwd = quote_plus(password)
        uri = f"mysql+pymysql://{user}:{enc_pwd}@{host}:{port}/{db_name}?charset=utf8mb4"
        test_eng = create_engine(uri, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with test_eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_eng.dispose()
        return True, "连接测试成功，数据库正常访问！"
    except Exception as e:
        err = str(e)
        if "Access denied" in err:
            return False, "连接失败：用户名或密码错误 (Access denied)"
        if "Can't connect" in err or "Connection refused" in err:
            return False, f"连接失败：无法连接至 MySQL {host}:{port}，请确认 MySQL 服务已启动"
        if "Unknown database" in err:
            return False, f"连接失败：数据库 '{db_name}' 不存在，请先核对或创建该库"
        return False, f"连接异常: {err[:120]}"
