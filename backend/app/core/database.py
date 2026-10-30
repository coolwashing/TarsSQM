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
