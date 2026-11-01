import os
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_db

# 初始化 FastAPI 实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="完全独立的轻量级供应商与质量管理系统（SQM）后端服务",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 注册 CORS 跨域中间件 (支持免密直进工作台与本地开发无缝对接)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载顶级动态流式存储目录 (如果目录存在则挂载为静态安全下载通道)
storage_path = settings.ABSOLUTE_STORAGE_PATH
storage_path.mkdir(parents=True, exist_ok=True)
files_storage_path = storage_path / "files"
files_storage_path.mkdir(parents=True, exist_ok=True)

app.mount(
    "/static/storage",
    StaticFiles(directory=str(files_storage_path)),
    name="storage"
)


from app.routers import r_storage, r_maindata, r_sqm, r_ctq, r_excel, r_kb, r_dev

# 挂载业务功能路由
app.include_router(r_storage.router)
app.include_router(r_maindata.router)
app.include_router(r_sqm.router)
app.include_router(r_ctq.router)
app.include_router(r_excel.router)
app.include_router(r_kb.router)
app.include_router(r_dev.router)



@app.get("/")
def root():
    """
    服务入口状态说明
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "online",
        "docs": "/docs",
        "storage_root": str(settings.ABSOLUTE_STORAGE_PATH)
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """
    系统健康体检接口：校验数据库连通性与存储可用性
    """
    db_status = "error"
    db_version = ""
    try:
        result = db.execute(text("SELECT VERSION()")).scalar()
        db_status = "connected"
        db_version = str(result)
    except Exception as e:
        db_status = f"failed: {str(e)}"

    storage_writable = os.access(str(settings.ABSOLUTE_STORAGE_PATH), os.W_OK)

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": {
            "status": db_status,
            "version": db_version,
            "schema": settings.DB_NAME,
            "host": f"{settings.DB_HOST}:{settings.DB_PORT}"
        },
        "storage": {
            "path": str(settings.ABSOLUTE_STORAGE_PATH),
            "writable": storage_writable
        }
    }
