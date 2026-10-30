import os
import sys
import logging
from pathlib import Path
from typing import Generator
import configparser

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# 确定路径基准：适配直接 Python 运行 与 PyInstaller 打包运行 (sys._MEIPASS)
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # PyInstaller 解压后的只读资源目录（内置前端 dist、模板等）
    BUNDLE_DIR = Path(sys._MEIPASS)
    # 可执行文件同级目录（存放持久化数据：db、storage、config.ini 等）
    APP_ROOT = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    APP_ROOT = BUNDLE_DIR

# 将项目目录与 backend 加入模块导入路径
sys.path.insert(0, str(BUNDLE_DIR / "backend"))
sys.path.insert(0, str(BUNDLE_DIR))

CONFIG_FILE = APP_ROOT / "config.ini"

# ---------------------------------------------------------------------------
# 读取或生成默认配置
# ---------------------------------------------------------------------------
def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        try:
            cfg.read(CONFIG_FILE, encoding="utf-8")
        except Exception:
            cfg.read(CONFIG_FILE)
    
    # 填充默认值
    if not cfg.has_section("server"):
        cfg.add_section("server")
    if not cfg.has_option("server", "host"):
        cfg.set("server", "host", "0.0.0.0")
    if not cfg.has_option("server", "port"):
        cfg.set("server", "port", "8010")

    if not cfg.has_section("database"):
        cfg.add_section("database")
    if not cfg.has_option("database", "type"):
        # 默认使用 SQM项目.doc 规定的 MySQL
        cfg.set("database", "type", "mysql")
    if not cfg.has_option("database", "sqlite_path"):
        cfg.set("database", "sqlite_path", "data/sqm_data.db")
    if not cfg.has_option("database", "mysql_host"):
        cfg.set("database", "mysql_host", "127.0.0.1")
    if not cfg.has_option("database", "mysql_port"):
        cfg.set("database", "mysql_port", "3306")
    if not cfg.has_option("database", "mysql_user"):
        cfg.set("database", "mysql_user", "root")
    if not cfg.has_option("database", "mysql_password"):
        cfg.set("database", "mysql_password", "Zhang19830310")
    if not cfg.has_option("database", "mysql_database"):
        cfg.set("database", "mysql_database", "sqm")

    if not cfg.has_section("storage"):
        cfg.add_section("storage")
    if not cfg.has_option("storage", "root_path"):
        cfg.set("storage", "root_path", "storage")

    return cfg

config = load_config()

# ---------------------------------------------------------------------------
# 数据库引擎初始化 (支持 SQLite 便携模式与 MySQL 企业模式)
# ---------------------------------------------------------------------------
def ensure_mysql_schema_and_get_password(host, port, user, configured_pwd, db_name):
    """
    1. 密码自适应探测：优先尝试配置的密码，若失败则尝试备用密码 (Tars123451, Zhang19830310)
    2. 先连 MySQL 根实例，自动执行 CREATE DATABASE IF NOT EXISTS sqm 创建 Schema
    3. 返回成功连接的有效密码
    """
    import pymysql

    candidates = []
    if configured_pwd:
        candidates.append(configured_pwd)
    for p in ["Tars123451", "Zhang19830310", "root", "123456", ""]:
        if p not in candidates:
            candidates.append(p)

    working_pwd = None
    for pwd in candidates:
        try:
            conn = pymysql.connect(
                host=host,
                port=int(port),
                user=user,
                password=pwd,
                charset="utf8mb4",
                connect_timeout=3
            )
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()
            working_pwd = pwd
            print(f"[SQM 数据库] MySQL 连通性校验与 Schema `{db_name}` 自动创建/就绪完成！")
            break
        except Exception as e:
            err_code = getattr(e, 'args', [None])[0]
            if err_code == 1045:
                # 密码不匹配，继续尝试下一个候选密码
                continue
            else:
                # 端口不通或其他错误
                break

    return working_pwd


db_type = config.get("database", "type", fallback="mysql").lower()

if db_type == "sqlite":
    sqlite_rel = config.get("database", "sqlite_path", fallback="data/sqm_data.db")
    sqlite_path = APP_ROOT / sqlite_rel
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    db_uri = f"sqlite:///{sqlite_path.as_posix()}"
    engine = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    from urllib.parse import quote_plus
    m_user = config.get("database", "mysql_user", fallback="root")
    m_pwd_raw = config.get("database", "mysql_password", fallback="Tars123451")
    m_host = config.get("database", "mysql_host", fallback="127.0.0.1")
    m_port = config.get("database", "mysql_port", fallback="3306")
    m_name = config.get("database", "mysql_database", fallback="sqm")

    valid_pwd = ensure_mysql_schema_and_get_password(m_host, m_port, m_user, m_pwd_raw, m_name)
    if valid_pwd is not None:
        m_pwd = quote_plus(valid_pwd)
        if valid_pwd != m_pwd_raw:
            try:
                config.set("database", "mysql_password", valid_pwd)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    config.write(f)
                print("[SQM 数据库] 已自动更新密码配置为有效密码！")
            except Exception:
                pass
    else:
        m_pwd = quote_plus(m_pwd_raw)

    try:
        db_uri = f"mysql+pymysql://{m_user}:{m_pwd}@{m_host}:{m_port}/{m_name}?charset=utf8mb4"
        engine = create_engine(
            db_uri,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
            echo=False
        )
        with engine.connect() as _test_conn:
            pass
        print(f"[SQM 数据库] MySQL 引擎初始化成功 ({m_host}:{m_port}/{m_name})")
    except Exception as e:
        print(f"[SQM 数据库警告] 无法连接到指定 MySQL 服务: {e}")
        print("[SQM 容灾自愈] 自动回退为单机便携 SQLite 模式，保障工作台立即可用！")
        db_type = "sqlite"
        sqlite_rel = config.get("database", "sqlite_path", fallback="data/sqm_data.db")
        sqlite_path = APP_ROOT / sqlite_rel
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        db_uri = f"sqlite:///{sqlite_path.as_posix()}"
        engine = create_engine(
            db_uri,
            connect_args={"check_same_thread": False},
            echo=False
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_package_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 覆盖原工程的 database engine 和 get_db
import app.core.database as core_db
core_db.engine = engine
core_db.SessionLocal = SessionLocal
core_db.get_db = get_package_db

# 导入所有模型并自动创建数据表（如果是新机器或 SQLite，自动完成建表）
from app.models import main_data, sqm_quality, ctq, attachment
try:
    core_db.Base.metadata.create_all(bind=engine)
    print(f"[SQM 数据库] 数据架构检验通过 ({db_type.upper()})")
except Exception as e:
    print(f"[SQM 数据库异常] 建表异常: {e}")

# ---------------------------------------------------------------------------
# 存储目录初始化
# ---------------------------------------------------------------------------
storage_rel = config.get("storage", "root_path", fallback="storage")
storage_path = (APP_ROOT / storage_rel).resolve()
storage_path.mkdir(parents=True, exist_ok=True)
files_storage_path = storage_path / "files"
files_storage_path.mkdir(parents=True, exist_ok=True)

import app.core.config as core_config
core_config.settings.STORAGE_ROOT_PATH = str(storage_path)

# ---------------------------------------------------------------------------
# 创建 FastAPI 主应用
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SQM 供应商与质量管理系统 (便携桌面版)",
    version="1.0.0",
    description="支持零依赖独立单机运行与局域网协同的轻量级质量系统",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载附件下载静态通道
app.mount(
    "/static/storage",
    StaticFiles(directory=str(files_storage_path)),
    name="storage"
)

# 导入并挂载核心业务路由
from app.routers import r_storage, r_maindata, r_sqm, r_ctq, r_excel
app.include_router(r_storage.router)
app.include_router(r_maindata.router)
app.include_router(r_sqm.router)
app.include_router(r_ctq.router)
app.include_router(r_excel.router)

# ---------------------------------------------------------------------------
# 健康体检与系统信息接口
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check(db: Session = Depends(get_package_db)):
    db_status = "error"
    db_version = ""
    try:
        if "sqlite" in str(engine.url):
            result = db.execute(text("SELECT sqlite_version()")).scalar()
            db_status = "connected"
            db_version = f"SQLite {result}"
        else:
            result = db.execute(text("SELECT VERSION()")).scalar()
            db_status = "connected"
            db_version = f"MySQL {result}"
    except Exception as e:
        db_status = f"failed: {str(e)}"

    storage_writable = os.access(str(storage_path), os.W_OK)

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": {
            "type": db_type,
            "status": db_status,
            "version": db_version,
            "engine": str(engine.url).split("@")[-1] if "@" in str(engine.url) else "sqlite_local"
        },
        "storage": {
            "path": str(storage_path),
            "writable": storage_writable
        }
    }

# ---------------------------------------------------------------------------
# 静态资源与前端单页应用 (SPA) 托管
# ---------------------------------------------------------------------------
# 查找前端构建产物目录
possible_dist_dirs = [
    BUNDLE_DIR / "frontend" / "dist",
    BUNDLE_DIR / "dist",
    APP_ROOT / "frontend" / "dist",
    APP_ROOT / "dist"
]

dist_dir = None
for p in possible_dist_dirs:
    if p.exists() and (p / "index.html").exists():
        dist_dir = p
        break

if dist_dir:
    # 挂载 assets 静态资源
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA 历史模式路由兜底
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除 API 与系统接口
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        
        target_file = dist_dir / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        
        # 默认返回 SPA index.html
        return FileResponse(str(dist_dir / "index.html"))
else:
    @app.get("/")
    def index_fallback():
        return {
            "status": "online",
            "message": "SQM 后端接口运行正常。前端静态产物尚未打包，请先执行打包脚本。",
            "api_docs": "/docs",
            "health": "/api/health"
        }
