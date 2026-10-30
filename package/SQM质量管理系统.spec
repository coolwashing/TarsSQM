# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\AIAPP\\Tars\\package\\launcher.py'],
    pathex=['D:\\AIAPP\\Tars\\backend', 'D:\\AIAPP\\Tars'],
    binaries=[],
    datas=[('D:\\AIAPP\\Tars\\frontend\\dist', 'frontend/dist'), ('D:\\AIAPP\\Tars\\backend\\app', 'app'), ('D:\\AIAPP\\Tars\\package\\server_app.py', '.')],
    hiddenimports=['uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'fastapi', 'fastapi.staticfiles', 'starlette', 'pydantic', 'pydantic_settings', 'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.mysql', 'pymysql', 'python_multipart', 'multipart', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext', 'configparser', 'server_app', 'app.models.main_data', 'app.models.sqm_quality', 'app.models.ctq', 'app.models.attachment', 'app.routers.r_maindata', 'app.routers.r_sqm', 'app.routers.r_ctq', 'app.routers.r_storage', 'app.routers.r_excel', 'app.common.excel_configs', 'app.common.excel_engine', 'openpyxl', 'openpyxl.styles', 'openpyxl.worksheet', 'openpyxl.worksheet.datavalidation', 'openpyxl.comments'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SQM质量管理系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
