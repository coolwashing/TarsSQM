import os
import sys
import time
import socket
import threading
import webbrowser
import configparser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# 确定运行路径 (兼容 PyInstaller 冻结打包环境)
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_ROOT = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    APP_ROOT = BUNDLE_DIR

sys.path.insert(0, str(BUNDLE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CONFIG_FILE = APP_ROOT / "config.ini"


def get_default_config():
    cfg = configparser.ConfigParser()
    cfg.add_section("server")
    cfg.set("server", "host", "0.0.0.0")
    cfg.set("server", "port", "8010")

    cfg.add_section("database")
    # 默认连接 SQM项目.doc 规定的 MySQL 数据库
    cfg.set("database", "type", "mysql")
    cfg.set("database", "sqlite_path", "data/sqm_data.db")
    cfg.set("database", "mysql_host", "127.0.0.1")
    cfg.set("database", "mysql_port", "3306")
    cfg.set("database", "mysql_user", "root")
    cfg.set("database", "mysql_password", "Zhang19830310")
    cfg.set("database", "mysql_database", "sqm")

    cfg.add_section("storage")
    cfg.set("storage", "root_path", "storage")
    return cfg


def load_config():
    cfg = get_default_config()
    if CONFIG_FILE.exists():
        try:
            cfg.read(CONFIG_FILE, encoding="utf-8")
        except Exception:
            cfg.read(CONFIG_FILE)
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


class LogRedirector:
    """重定向 stdout/stderr 到 Tkinter ScrolledText 控件，兼容标准文件流接口"""
    def __init__(self, text_widget, original_stream=None):
        self.text_widget = text_widget
        self.original_stream = original_stream

    def write(self, string):
        if self.original_stream:
            try:
                self.original_stream.write(string)
            except Exception:
                pass
        try:
            self.text_widget.after(0, self._append, string)
        except Exception:
            pass

    def _append(self, string):
        try:
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
        except Exception:
            pass

    def flush(self):
        if self.original_stream and hasattr(self.original_stream, "flush"):
            try:
                self.original_stream.flush()
            except Exception:
                pass

    def isatty(self):
        """防止 uvicorn / logging 的 ColourizedFormatter 探测终端彩色时报错"""
        return False

    def fileno(self):
        if self.original_stream and hasattr(self.original_stream, "fileno"):
            try:
                return self.original_stream.fileno()
            except Exception:
                pass
        raise OSError("fileno not supported")

    @property
    def encoding(self):
        return "utf-8"


class SQMLauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SQM 供应商与质量管理系统 · 桌面控制台")
        self.geometry("820x620")
        self.minsize(760, 560)
        self.configure(bg="#0f172a")

        self.cfg = load_config()
        self.server_thread = None
        self.server_instance = None
        self.is_running = False

        self._init_styles()
        self._build_ui()

        # 重定向日志（保留原始底层输出并在 Tkinter 显示）
        sys.stdout = LogRedirector(self.log_text, getattr(sys, "__stdout__", None))
        sys.stderr = LogRedirector(self.log_text, getattr(sys, "__stderr__", None))

        self.log(f"[系统就绪] 工作根目录: {APP_ROOT}")
        self.log(f"[配置状态] 端口: {self.cfg.get('server', 'port')} | 数据库模式: {self.cfg.get('database', 'type').upper()}")
        self.log("[提示] 点击上方『启动系统』按钮即可一键运行并自动开启浏览器！\n")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        
        style.configure("TLabel", background="#0f172a", foreground="#e2e8f0", font=("Microsoft YaHei", 9))
        style.configure("Card.TLabel", background="#1e293b", foreground="#cbd5e1", font=("Microsoft YaHei", 9))
        style.configure("Title.TLabel", background="#0f172a", foreground="#ffffff", font=("Microsoft YaHei", 14, "bold"))
        style.configure("SubTitle.TLabel", background="#0f172a", foreground="#94a3b8", font=("Microsoft YaHei", 9))

        style.configure("Primary.TButton", font=("Microsoft YaHei", 10, "bold"), background="#4f46e5", foreground="#ffffff", padding=6)
        style.map("Primary.TButton", background=[("active", "#4338ca")])

        style.configure("Success.TButton", font=("Microsoft YaHei", 10, "bold"), background="#059669", foreground="#ffffff", padding=6)
        style.map("Success.TButton", background=[("active", "#047857")])

        style.configure("Danger.TButton", font=("Microsoft YaHei", 10, "bold"), background="#dc2626", foreground="#ffffff", padding=6)
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        style.configure("Tool.TButton", font=("Microsoft YaHei", 9), background="#334155", foreground="#f8fafc", padding=5)
        style.map("Tool.TButton", background=[("active", "#475569")])

    def _build_ui(self):
        # 1. 顶部 Header 品牌区
        header = ttk.Frame(self, padding=(20, 16, 20, 12))
        header.pack(fill=tk.X)

        title_box = ttk.Frame(header)
        title_box.pack(side=tk.LEFT)

        ttk.Label(title_box, text="SQM 供应商与质量管理系统", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_box, text="企业轻量化质量协同工作台 · 独立便携运行套件 (Python + Vue3)", style="SubTitle.TLabel").pack(anchor=tk.W)

        # 状态微章
        self.status_badge = tk.Label(
            header,
            text="● 服务未启动",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#334155",
            fg="#94a3b8",
            padx=12,
            pady=4,
            relief="flat"
        )
        self.status_badge.pack(side=tk.RIGHT)

        # 2. 快捷操作工具条
        action_bar = ttk.Frame(self, padding=(20, 4, 20, 10))
        action_bar.pack(fill=tk.X)

        self.btn_start = ttk.Button(action_bar, text="🚀 启动系统", style="Success.TButton", command=self.start_server)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_browser = ttk.Button(action_bar, text="🌐 打开工作台", style="Primary.TButton", state=tk.DISABLED, command=self.open_browser)
        self.btn_browser.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ttk.Button(action_bar, text="🛑 停止服务", style="Danger.TButton", state=tk.DISABLED, command=self.stop_server)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_config = ttk.Button(action_bar, text="⚙️ 系统配置", style="Tool.TButton", command=self.open_config_dialog)
        self.btn_config.pack(side=tk.RIGHT)

        # 3. 日志与运行监控卡片
        log_frame = ttk.Frame(self, padding=(20, 6, 20, 16))
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_head = ttk.Frame(log_frame)
        log_head.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(log_head, text="🖥️ 运行控制台与实时日志", font=("Microsoft YaHei", 10, "bold"), foreground="#cbd5e1").pack(side=tk.LEFT)
        
        btn_copy = ttk.Button(log_head, text="复制访问地址", style="Tool.TButton", command=self.copy_url)
        btn_copy.pack(side=tk.RIGHT, padx=(4, 0))

        btn_clear = ttk.Button(log_head, text="清空日志", style="Tool.TButton", command=self.clear_log)
        btn_clear.pack(side=tk.RIGHT)

        # 日志输出文本框 (黑客深色终端风格)
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg="#020617",
            fg="#38bdf8",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, text_msg):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_text.insert(tk.END, timestamp + text_msg + "\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def copy_url(self):
        port = self.cfg.get("server", "port", fallback="8010")
        url = f"http://localhost:{port}"
        self.clipboard_clear()
        self.clipboard_append(url)
        messagebox.showinfo("提示", f"已复制工作台访问地址:\n{url}")

    def get_server_url(self):
        port = self.cfg.get("server", "port", fallback="8010")
        return f"http://localhost:{port}"

    def start_server(self):
        if self.is_running:
            return

        self.btn_start.config(state=tk.DISABLED)
        self.status_badge.config(text="● 正在启动服务...", bg="#d97706", fg="#ffffff")
        self.log("[启动中] 正在拉起 FastAPI + Uvicorn 后端服务器...")

        def run_uvicorn():
            import uvicorn
            from server_app import app

            host = self.cfg.get("server", "host", fallback="0.0.0.0")
            port = int(self.cfg.get("server", "port", fallback="8010"))

            # 设置 log_config=None 彻底跳过 uvicorn 内部日志重写，绝不探测 isatty
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_config=None,
                access_log=False
            )
            self.server_instance = uvicorn.Server(config)
            self.server_instance.run()

        self.server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        self.server_thread.start()

        # 后台轮询检查服务是否就绪
        threading.Thread(target=self._wait_until_ready, daemon=True).start()

    def _wait_until_ready(self):
        port = int(self.cfg.get("server", "port", fallback="8010"))
        max_retries = 30
        connected = False

        for _ in range(max_retries):
            time.sleep(0.3)
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    connected = True
                    break
            except Exception:
                pass

        if connected:
            self.is_running = True
            self.after(0, self._on_server_started)
        else:
            self.after(0, self._on_server_start_failed)

    def _on_server_started(self):
        url = self.get_server_url()
        self.status_badge.config(text=f"● 运行中 ({url})", bg="#059669", fg="#ffffff")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_browser.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_config.config(state=tk.DISABLED)

        self.log(f"[服务就绪] SQM 系统已在 {url} 成功就绪！")
        self.log("[网页联动] 正在自动调起默认浏览器打开工作台...")
        self.open_browser()

    def _on_server_start_failed(self):
        self.status_badge.config(text="● 启动失败", bg="#dc2626", fg="#ffffff")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_browser.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_config.config(state=tk.NORMAL)
        self.log("[错误] 服务启动超时，请检查端口是否被占用或配置是否正确！")
        messagebox.showerror("启动失败", "无法启动后端服务，可能端口被占用，请在『系统配置』中更改端口后再试。")

    def open_browser(self):
        url = self.get_server_url()
        webbrowser.open(url)

    def stop_server(self):
        if not self.is_running or not self.server_instance:
            return

        self.log("[停止中] 正在平稳终止 Uvicorn 服务...")
        self.server_instance.should_exit = True
        self.is_running = False

        self.status_badge.config(text="● 服务已停止", bg="#334155", fg="#94a3b8")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_browser.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_config.config(state=tk.NORMAL)
        self.log("[已停止] 后端服务已安全停止。\n")

    def open_config_dialog(self):
        ConfigDialog(self)

    def on_close(self):
        if self.is_running:
            if messagebox.askyesno("退出提示", "服务正在运行中，关闭窗口将同时停止系统服务。\n确认退出吗？"):
                self.stop_server()
                self.destroy()
        else:
            self.destroy()


class ConfigDialog(tk.Toplevel):
    def __init__(self, parent: SQMLauncherApp):
        super().__init__(parent)
        self.parent = parent
        self.title("系统运行参数配置")
        self.geometry("540x520")
        self.resizable(False, False)
        self.configure(bg="#0f172a")
        self.transient(parent)
        self.grab_set()

        self.cfg = self.parent.cfg
        self._build_form()

    def _build_form(self):
        pad_opts = {"padx": 20, "pady": 12}
        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. 基础网络设置
        net_group = tk.LabelFrame(container, text="1. 网络与端口", bg="#1e293b", fg="#f8fafc", font=("Microsoft YaHei", 9, "bold"), padx=12, pady=10)
        net_group.pack(fill=tk.X, pady=(0, 14))

        row1 = tk.Frame(net_group, bg="#1e293b")
        row1.pack(fill=tk.X, pady=4)
        tk.Label(row1, text="监听端口：", bg="#1e293b", fg="#cbd5e1", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.ent_port = tk.Entry(row1, bg="#0f172a", fg="#ffffff", insertbackground="#fff", relief="flat")
        self.ent_port.insert(0, self.cfg.get("server", "port", fallback="8010"))
        self.ent_port.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row2 = tk.Frame(net_group, bg="#1e293b")
        row2.pack(fill=tk.X, pady=4)
        tk.Label(row2, text="允许局域网：", bg="#1e293b", fg="#cbd5e1", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.var_lan = tk.BooleanVar(value=self.cfg.get("server", "host", fallback="0.0.0.0") == "0.0.0.0")
        chk_lan = tk.Checkbutton(row2, text="开启局域网共享 (0.0.0.0，其他设备可通过 IP 访问)", variable=self.var_lan, bg="#1e293b", fg="#cbd5e1", selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#ffffff")
        chk_lan.pack(side=tk.LEFT)

        # 2. 数据库配置
        db_group = tk.LabelFrame(container, text="2. 数据库存储模式", bg="#1e293b", fg="#f8fafc", font=("Microsoft YaHei", 9, "bold"), padx=12, pady=10)
        db_group.pack(fill=tk.X, pady=(0, 14))

        self.db_mode_var = tk.StringVar(value=self.cfg.get("database", "type", fallback="sqlite").lower())

        r1 = tk.Radiobutton(db_group, text="单机便携模式 (SQLite，开箱即用，无需配置数据库服务)", variable=self.db_mode_var, value="sqlite", command=self._toggle_db_inputs, bg="#1e293b", fg="#34d399", selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#ffffff")
        r1.pack(anchor=tk.W, pady=2)

        r2 = tk.Radiobutton(db_group, text="企业远程模式 (MySQL 数据库，支持多端团队网络协同)", variable=self.db_mode_var, value="mysql", command=self._toggle_db_inputs, bg="#1e293b", fg="#60a5fa", selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#ffffff")
        r2.pack(anchor=tk.W, pady=2)

        self.mysql_box = tk.Frame(db_group, bg="#1e293b", pady=6)
        self.mysql_box.pack(fill=tk.X)

        fields = [
            ("主机 IP:", "mysql_host", "127.0.0.1"),
            ("端 口:", "mysql_port", "3306"),
            ("用 户:", "mysql_user", "root"),
            ("密 码:", "mysql_password", "Tars123451"),
            ("数据库名:", "mysql_database", "sqm")
        ]
        self.mysql_entries = {}
        for label_text, key, default_val in fields:
            f_row = tk.Frame(self.mysql_box, bg="#1e293b", pady=2)
            f_row.pack(fill=tk.X)
            tk.Label(f_row, text=label_text, bg="#1e293b", fg="#94a3b8", width=10, anchor=tk.W).pack(side=tk.LEFT)
            ent = tk.Entry(f_row, bg="#0f172a", fg="#ffffff", insertbackground="#fff", relief="flat")
            if "password" in key:
                ent.config(show="*")
            ent.insert(0, self.cfg.get("database", key, fallback=default_val))
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.mysql_entries[key] = ent

        self._toggle_db_inputs()

        # 底部按钮栏
        btn_box = tk.Frame(container, bg="#0f172a")
        btn_box.pack(fill=tk.X, pady=(10, 0))

        btn_test = ttk.Button(btn_box, text="测试 MySQL 连通性", style="Tool.TButton", command=self.test_mysql)
        btn_test.pack(side=tk.LEFT)

        btn_save = ttk.Button(btn_box, text="💾 保存配置", style="Primary.TButton", command=self.save_and_close)
        btn_save.pack(side=tk.RIGHT, padx=(8, 0))

        btn_cancel = ttk.Button(btn_box, text="取消", style="Tool.TButton", command=self.destroy)
        btn_cancel.pack(side=tk.RIGHT)

    def _toggle_db_inputs(self):
        is_mysql = self.db_mode_var.get() == "mysql"
        for ent in self.mysql_entries.values():
            ent.config(state=tk.NORMAL if is_mysql else tk.DISABLED)

    def test_mysql(self):
        import pymysql

        host = self.mysql_entries["mysql_host"].get().strip()
        port = int(self.mysql_entries["mysql_port"].get().strip() or "3306")
        user = self.mysql_entries["mysql_user"].get().strip()
        pwd = self.mysql_entries["mysql_password"].get().strip()
        db = self.mysql_entries["mysql_database"].get().strip()

        try:
            # 1. 先连 MySQL 实例，检验连通性
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=pwd,
                charset="utf8mb4",
                connect_timeout=3
            )
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
                # 2. 如果 schema 不存在，自动创建 schema
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()

            messagebox.showinfo(
                "连接成功",
                f"成功连接至 MySQL 服务器！\n数据库版本: {version}\nSchema 数据库 `{db}` 检验通过 (不存在已自动建库)"
            )
        except Exception as e:
            messagebox.showerror("连接失败", f"无法连接到 MySQL 数据库:\n{str(e)}")

    def save_and_close(self):
        port = self.ent_port.get().strip()
        if not port.isdigit():
            messagebox.showerror("错误", "端口必须为有效数字 (如 8010)")
            return

        self.cfg.set("server", "port", port)
        self.cfg.set("server", "host", "0.0.0.0" if self.var_lan.get() else "127.0.0.1")

        db_type = self.db_mode_var.get()
        self.cfg.set("database", "type", db_type)

        for key, ent in self.mysql_entries.items():
            self.cfg.set("database", key, ent.get().strip())

        save_config(self.cfg)
        self.parent.log(f"[配置更新] 端口已设为 {port} | 数据库模式: {db_type.upper()}")
        messagebox.showinfo("成功", "配置已成功保存！\n下次启动服务时将采用新配置。")
        self.destroy()


def main():
    app = SQMLauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
