import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

# 确保在 Windows 控制台输出中文时不报编码错误
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
OUTPUT_DIR = PACKAGE_DIR / "output"
DIST_DIR = PACKAGE_DIR / "dist"
BUILD_DIR = PACKAGE_DIR / "build"


def log(msg):
    print(f"\n======================================================\n[SQM 打包] {msg}\n======================================================")


def build_frontend():
    log("第一步：构建 Vue3 前端生产静态资源 (npm run build)...")
    if not (FRONTEND_DIR / "package.json").exists():
        raise FileNotFoundError(f"未找到前端项目: {FRONTEND_DIR}")

    cmd = "npm.cmd run build" if os.name == "nt" else "npm run build"
    print(f"正在执行: {cmd} (在 {FRONTEND_DIR})")
    ret = subprocess.run(cmd, cwd=str(FRONTEND_DIR), shell=True)
    if ret.returncode != 0:
        raise RuntimeError("前端构建失败，请检查控制台错误信息！")

    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if not dist_index.exists():
        raise FileNotFoundError(f"前端构建产物缺失: {dist_index}")
    print("[成功] 前端构建完成，dist/ 产物已就绪！")


def run_pyinstaller():
    log("第二步：调用 PyInstaller 打包为独立免安装可执行程序 (.exe)...")
    
    frontend_dist_path = FRONTEND_DIR / "dist"
    server_app_path = PACKAGE_DIR / "server_app.py"
    launcher_path = PACKAGE_DIR / "launcher.py"

    # 准备 datas
    datas = [
        f"{frontend_dist_path};frontend/dist",
        f"{BACKEND_DIR / 'app'};app",
        f"{server_app_path};."
    ]

    # 关键隐藏导入
    hidden_imports = [
        "uvicorn",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "fastapi",
        "fastapi.staticfiles",
        "starlette",
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.mysql",
        "pymysql",
        "python_multipart",
        "multipart",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
        "configparser",
        "server_app",
        "app.models.main_data",
        "app.models.sqm_quality",
        "app.models.ctq",
        "app.models.attachment",
        "app.routers.r_maindata",
        "app.routers.r_sqm",
        "app.routers.r_ctq",
        "app.routers.r_storage",
        "app.routers.r_excel",
        "app.common.excel_configs",
        "app.common.excel_engine",
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.worksheet",
        "openpyxl.worksheet.datavalidation",
        "openpyxl.comments",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "SQM质量管理系统",
        "--onefile",              # 单文件模式：复制一个 .exe 文件到任何电脑即可运行！
        "--noconsole",            # 启动器自带 Tkinter 控制台，隐藏黑框命令行
        "--workpath", str(BUILD_DIR),
        "--distpath", str(OUTPUT_DIR),
        "--paths", str(BACKEND_DIR),
        "--paths", str(PROJECT_ROOT),
    ]

    for d in datas:
        cmd.extend(["--add-data", d])

    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    cmd.append(str(launcher_path))

    print("执行 PyInstaller 打包命令...")
    ret = subprocess.run(cmd, cwd=str(PACKAGE_DIR))
    if ret.returncode != 0:
        raise RuntimeError("PyInstaller 打包失败！")

    exe_path = OUTPUT_DIR / "SQM质量管理系统.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"未找到生成的可执行文件: {exe_path}")

    print(f"\n[成功] 单文件打包成功！可执行文件位于:\n{exe_path}")


def prepare_distribution():
    log("第三步：组织分发交付件 (单文件 Exe 与 绿色免安装 Zip 包)...")
    exe_file = OUTPUT_DIR / "SQM质量管理系统.exe"
    
    # 生成默认说明与示例配置
    example_config = OUTPUT_DIR / "config.ini.example"
    with open(example_config, "w", encoding="utf-8") as f:
        f.write("""[server]
host = 0.0.0.0
port = 8010

[database]
# 默认使用《SQM项目.doc》规定的 MySQL 数据库架构
type = mysql
mysql_host = 127.0.0.1
mysql_port = 3306
mysql_user = root
mysql_password = Tars123451
mysql_database = sqm

# 离线备用单机模式（若目标机器无 MySQL 环境时使用）：
sqlite_path = data/sqm_data.db

[storage]
root_path = storage
""")

    # 制作一份一键分发 Zip 压缩包
    zip_path = OUTPUT_DIR / "SQM质量管理系统_开箱即用版.zip"
    print(f"正在创建分发压缩包: {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_file, arcname="SQM质量管理系统.exe")
        zf.write(example_config, arcname="config.ini.example")
        if (PACKAGE_DIR / "README.md").exists():
            zf.write(PACKAGE_DIR / "README.md", arcname="使用说明.md")

    log("[成功] 全部打包流程顺利完成！")
    print(f"1. 独立单文件 (只需复制这 1 个文件到任意电脑直接运行):")
    print(f"   -> {exe_file}")
    print(f"2. 分发便携压缩包 (包含说明与配置模板):")
    print(f"   -> {zip_path}\n")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        build_frontend()
        run_pyinstaller()
        prepare_distribution()
    except Exception as e:
        print(f"\n[错误] 打包出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

