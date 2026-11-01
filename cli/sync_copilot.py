#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQM AI 智写 CLI 同步工具 (CLI for AI Copilot Preview Sync)
功能：将 IDE、Agent 或本地编写的 Markdown/HTML 规程秒级推送到前端 Web 浮窗进行审查与定点写入。
零依赖：使用 Python 标准库 (urllib, json, re, argparse)。
"""

import sys
import os
import re
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# 确保在 Windows 控制台 (GBK / CP936) 下正常输出 UTF-8 字符，防止 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def markdown_to_html(md_text: str) -> str:
    """
    轻量自包含 Markdown 转标准 HTML 规程转换器
    支持：多级标题、表格、代码块、列表、引用块、粗斜体、行内代码
    若输入已为 HTML，直接原样透传。
    """
    text = md_text.strip()
    if not text:
        return ""

    # 如果明显已经是 HTML 片段（含标签），则直接返回
    if re.search(r"<(?:h[1-6]|p|table|div|ul|ol|blockquote|pre)[\s>]", text, re.IGNORECASE):
        return text

    lines = text.splitlines()
    html_lines = []
    in_code_block = False
    in_list = False
    list_type = None  # 'ul' or 'ol'
    in_table = False
    table_headers = []
    table_rows = []

    def flush_table():
        nonlocal in_table, table_headers, table_rows
        if not in_table:
            return
        tbl_html = ['<table>']
        if table_headers:
            tbl_html.append('  <thead><tr>')
            for h in table_headers:
                tbl_html.append(f'    <th>{inline_format(h)}</th>')
            tbl_html.append('  </tr></thead>')
        if table_rows:
            tbl_html.append('  <tbody>')
            for row in table_rows:
                tbl_html.append('    <tr>')
                for cell in row:
                    tbl_html.append(f'      <td>{inline_format(cell)}</td>')
                tbl_html.append('    </tr>')
            tbl_html.append('  </tbody>')
        tbl_html.append('</table>')
        html_lines.append("\n".join(tbl_html))
        in_table = False
        table_headers = []
        table_rows = []

    def flush_list():
        nonlocal in_list, list_type
        if in_list and list_type:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def inline_format(s: str) -> str:
        # 代码
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # 粗体
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        # 斜体
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        return s

    i = 0
    while i < len(lines):
        line = lines[i]
        trimmed = line.strip()

        # 1. 代码块
        if trimmed.startswith("```"):
            if not in_code_block:
                flush_table()
                flush_list()
                in_code_block = True
                lang = trimmed[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">' if lang else '<pre><code>')
            else:
                in_code_block = False
                html_lines.append("</code></pre>")
            i += 1
            continue

        if in_code_block:
            # 转义 html 特殊字符
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_lines.append(escaped)
            i += 1
            continue

        # 2. 表格行判断 (带 | )
        if trimmed.startswith("|") and trimmed.endswith("|"):
            flush_list()
            cells = [c.strip() for c in trimmed.strip("|").split("|")]
            # 检查是否为分隔行 |-|-|-|
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                # 表头分隔线，忽略
                i += 1
                continue
            if not in_table:
                in_table = True
                table_headers = cells
            else:
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        # 3. 空行
        if not trimmed:
            flush_list()
            i += 1
            continue

        # 4. 标题判断 (# ~ ######)
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", trimmed)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1))
            content = inline_format(heading_match.group(2))
            html_lines.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        # 5. 引用块 (> )
        if trimmed.startswith(">"):
            flush_list()
            quote_text = inline_format(trimmed[1:].strip())
            html_lines.append(f"<blockquote><p>{quote_text}</p></blockquote>")
            i += 1
            continue

        # 6. 分隔线 (--- or ***)
        if re.match(r"^(\-{3,}|\*{3,})$", trimmed):
            flush_list()
            html_lines.append("<hr />")
            i += 1
            continue

        # 7. 无序列表 (- or *)
        ul_match = re.match(r"^[\*\-]\s+(.*)$", trimmed)
        if ul_match:
            if not in_list or list_type != "ul":
                flush_list()
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            html_lines.append(f"  <li>{inline_format(ul_match.group(1))}</li>")
            i += 1
            continue

        # 8. 有序列表 (1. 2. )
        ol_match = re.match(r"^\d+\.\s+(.*)$", trimmed)
        if ol_match:
            if not in_list or list_type != "ol":
                flush_list()
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            html_lines.append(f"  <li>{inline_format(ol_match.group(1))}</li>")
            i += 1
            continue

        # 9. 常规段落
        flush_list()
        html_lines.append(f"<p>{inline_format(trimmed)}</p>")
        i += 1

    flush_table()
    flush_list()
    return "\n".join(html_lines)


def push_preview(api_base: str, doc_id: str, html_content: str):
    url = f"{api_base.rstrip('/')}/api/kb/copilot/preview"
    payload = {
        "doc_id": str(doc_id),
        "html": html_content
    }
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)
    except urllib.error.URLError as e:
        print(f"\n❌ 连接后端失败: {e}", file=sys.stderr)
        print(f"   请确保后端 FastAPI 服务已在 {api_base} 正常运行！\n", file=sys.stderr)
        sys.exit(1)


def get_preview_status(api_base: str, doc_id: str):
    url = f"{api_base.rstrip('/')}/api/kb/copilot/preview?doc_id={doc_id}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)
    except urllib.error.URLError as e:
        print(f"\n❌ 连接后端失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SQM AI 智写 CLI 推送工具 (推送规程到网页端浮窗审查)"
    )
    parser.add_argument(
        "--doc", "-d",
        default="default",
        help="目标规程文档 ID (如 9 或 2，默认 'default' 全局通用)"
    )
    parser.add_argument(
        "--file", "-f",
        help="待推送的 Markdown (.md) 或 HTML 文件路径"
    )
    parser.add_argument(
        "--text", "-t",
        help="待推送的文本或 HTML 字符串内容"
    )
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8010",
        help="后端服务地址，默认 http://127.0.0.1:8010"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看当前后端中转缓存中的内容概览"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空当前文档的预览审查缓存"
    )

    args = parser.parse_args()

    # 1. 状态查看
    if args.status:
        st = get_preview_status(args.api, args.doc)
        html = st.get("html", "")
        updated = st.get("updated_at")
        print("\n📊 预览缓存状态：")
        print(f"   目标文档 ID: {args.doc}")
        print(f"   最后更新时间戳: {updated}")
        print(f"   内容字符数: {len(html)} 字")
        if html:
            preview_snippet = re.sub(r"<[^>]+>", " ", html)[:120].strip()
            print(f"   内容摘要: {preview_snippet}...\n")
        else:
            print("   (当前缓存为空)\n")
        return

    # 2. 清空缓存
    if args.clear:
        res = push_preview(args.api, args.doc, "")
        print(f"\n🧹 已清空文档 [{args.doc}] 的预览缓存: {res}\n")
        return

    # 3. 提取内容
    raw_content = ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 错误: 文件不存在 {args.file}", file=sys.stderr)
            sys.exit(1)
        raw_content = file_path.read_text(encoding="utf-8")
        print(f"📖 读取文件: {file_path.resolve()} ({len(raw_content)} 字符)")
    elif args.text:
        raw_content = args.text
    elif not sys.stdin.isatty():
        raw_content = sys.stdin.read()
    else:
        print("❌ 错误: 请指定 --file 或 --text 或通过管道标准输入提供内容！", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if not raw_content.strip():
        print("⚠️ 警告: 传入内容为空，未执行推送。")
        return

    # 4. 转为标准 HTML
    html_output = markdown_to_html(raw_content)

    # 5. 推送到后端 (同时推送指定 ID 和 default，确保前端随时可用)
    res = push_preview(args.api, args.doc, html_output)
    if args.doc != "default":
        push_preview(args.api, "default", html_output)

    print("\n✅ 推送成功！")
    print(f"   目标文档 ID: {args.doc}")
    print(f"   HTML 大小: {len(html_output)} 字符")
    print(f"   后端响应: {res}")
    print("👉 请在浏览器中查看：网页端已自动/可立即拉取最新规程，支持就地审查与一键填入正文！\n")


if __name__ == "__main__":
    main()
