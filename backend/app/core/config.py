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

    # AI 智写与 RAG 检索大模型通用配置 (兼容 OpenAI / Ollama / DeepSeek / 通义千问等协议)
    AI_API_BASE: str = "http://localhost:11434/v1"
    AI_API_KEY: str = "ollama"
    AI_MODEL: str = "qwen2.5:7b"
    AI_TEMPERATURE: float = 0.3

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


def save_db_config_to_env(host: str, port: int, user: str, password: str, db_name: str) -> bool:
    """
    将用户在前端配置的数据库连接参数安全保存至本地 .env 文件
    避免异机克隆后由于密码不一致导致无法连接
    """
    lines = []
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    keys_to_update = {
        "DB_HOST": host,
        "DB_PORT": str(port),
        "DB_USER": user,
        "DB_PASSWORD": password,
        "DB_NAME": db_name
    }

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in keys_to_update:
                new_lines.append(f"{key}={keys_to_update[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in keys_to_update.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 保持 settings 对象不变，让已导入它的模块也能读到新配置。
    refreshed_settings = Settings()
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(refreshed_settings, field_name))
    return True
