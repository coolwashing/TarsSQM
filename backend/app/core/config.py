import os
from pathlib import Path
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict

# 定位工程根目录中的 .env 文件
# 当前文件在 backend/app/core/config.py，往上三层即为工程根目录
CORE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CORE_DIR.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    # 兼容直接在 backend 目录下放 .env 的场景
    ALT_ENV = BACKEND_DIR / ".env"
    if ALT_ENV.exists():
        ENV_FILE = ALT_ENV


class Settings(BaseSettings):
    """
    系统全局运行配置
    支持从 .env 自动加载，并对环境变量进行强类型校验
    """
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 项目基础信息
    PROJECT_NAME: str = "SQM 供应商与质量管理系统"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库连接配置 (MySQL)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "Zhang19830310"
    DB_NAME: str = "sqm"

    # 顶级动态附件存储路径 (默认为工程根目录下的 storage/)
    STORAGE_ROOT_PATH: str = "../storage"

    # 服务监听配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8010

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """
        组装标准 SQLAlchemy MySQL 连接 URL，对密码进行安全 URL 转义
        """
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{encoded_password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def ABSOLUTE_STORAGE_PATH(self) -> Path:
        """
        计算动态附件存储库的绝对物理路径，确保跨目录启动时解析一致
        """
        p = Path(self.STORAGE_ROOT_PATH)
        if p.is_absolute():
            return p.resolve()
        # 相对 backend 目录计算
        return (BACKEND_DIR / p).resolve()


settings = Settings()
