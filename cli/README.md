# Tars SQM CLI 命令行工具集

本目录 (`cli/`) 收纳系统中所有本地脚本与自动化中继工具，供开发者、质量工程师及 IDE AI 助手直接调用。

---

## 🛠️ 工具清单

### 1. `sync_copilot.py` (AI 智写规程秒级推送中继)
用于将 IDE 中生成的 Markdown 方案、架构草稿或 HTML 片段直接推送到 Web 端「AI 智写」浮窗，免去手工复制粘贴。

#### 常用命令示例：

```bash
# 1. 将设计文档推送到当前文档 (如 doc_id 为 9)
python cli/sync_copilot.py --doc 9 --file design/task-center-architecture-and-plan.md

# 2. 直接推送一段文本或提示词
python cli/sync_copilot.py --doc 9 --text "<h2>8D 应急遏制措施</h2><p>立即阻断生产线...</p>"

# 3. 查看当前文档在后端的预览中转缓存状态
python cli/sync_copilot.py --doc 9 --status

# 4. 清空预览缓存
python cli/sync_copilot.py --doc 9 --clear

# 5. 支持管道标准输入 (Pipe)
cat any_report.md | python cli/sync_copilot.py --doc 9
```

#### 参数说明：
- `--doc`, `-d`：目标文档 ID（默认 `default`，即对所有打开该浮窗的页面生效）；
- `--file`, `-f`：本地文件路径（支持 `.md`、`.html`、`.txt`）；
- `--text`, `-t`：直接传入字符串内容；
- `--api`：后端地址（默认 `http://127.0.0.1:8010`）；
- `--status`：查看后端缓存内容概况；
- `--clear`：清空当前缓存。

---

## 💡 特性
- **零外部依赖**：基于 Python 3 原生标准库编写，开箱即用；
- **Markdown 智能编译**：自动将 Markdown 表格、分级标题、代码块、引用块编译为标准 ProseMirror/Tiptap 兼容的 HTML 格式；
- **Windows 控制台编码适配**：内置 UTF-8 重定向，杜绝 Windows CMD/PowerShell 下常见的 GBK 字符集报错。
