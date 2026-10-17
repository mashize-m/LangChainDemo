"""
Lesson 07: 将 MinerU 解析的 PDF 结果转化为 LangChain Document

流程：
1. 下载 lesson06 返回的 zip 文件
2. 解压 zip（内部包含 full.md、content_list.json、images/ 等）
3. 读取 full.md（MinerU 输出的 Markdown 全文）
4. 切分前保护 HTML 表格（避免被长度切分器腰斩）
5. 大表格按行拆分（避免单块超过 Embedding Token 上限）
6. 复用 lesson02 的两级切分策略（Markdown 标题 + 长度切分）
7. 清洗切分后的块（过滤目录块、纯图片块，规范化图片语法）
8. 输出带有【所属章节】路径的 List[Document]

输入依赖：lesson06 输出的 zip_url
"""

import re
import shutil
import zipfile
from pathlib import Path

import requests
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from langchaindemo.config import ROOT_DIR

# MinerU 输出目录
MINERU_OUTPUT_DIR = ROOT_DIR / "data" / "mineru_output"

# 单张表格的最大字符数，超过则按行拆分
MAX_TABLE_CHARS = 1500


# ==================== 下载与解压 ====================
def download_zip(zip_url: str, save_path: Path) -> bool:
    """下载 zip 文件到指定路径"""
    print(f"1. 正在下载: {zip_url}")
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(zip_url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = downloaded / total_size * 100
                    print(f"  下载进度: {percent:.1f}%", end="\r")

        print(f"\n2. 下载完成，保存至: {save_path}")
        return True
    except requests.RequestException as e:
        print(f"❌ 下载失败: {e}")
        return False


def unzip_file(zip_path: Path, extract_dir: Path) -> bool:
    """解压 zip 文件"""
    print(f"3. 正在解压至: {extract_dir}")

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
        print(f"4. 解压完成，文件列表：")
        for f in sorted(extract_dir.rglob("*")):
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                print(f"   - {f.relative_to(extract_dir)} ({size_kb:.1f} KB)")
        return True
    except zipfile.BadZipFile as e:
        print(f"❌ 解压失败: {e}")
        return False


def find_full_md(extract_dir: Path) -> Path | None:
    """在解压目录中查找 full.md"""
    for path in extract_dir.rglob("full.md"):
        return path
    md_files = list(extract_dir.rglob("*.md"))
    if md_files:
        print(f"⚠️ 未找到 full.md，使用第一个 .md 文件: {md_files[0].name}")
        return md_files[0]
    return None


# ==================== 大表格拆分 ====================
def split_large_table(table_html: str, max_chars: int) -> list[str]:
    """
    将大表格按 <tr> 行拆分为多个子表格。
    - 每个子表格会补上 <table> 和 </table> 标签，保证结构完整。
    - 表头（第一个 <tr>）会被复制到每个子表格里，保持语义完整。
    """
    rows = re.findall(r'<tr>.*?</tr>', table_html, re.DOTALL)
    if not rows:
        return [table_html]

    header = rows[0]
    body_rows = rows[1:]

    sub_tables: list[str] = []
    current_rows = [header]
    current_len = len(header)

    for row in body_rows:
        if current_len + len(row) > max_chars and len(current_rows) > 1:
            sub_tables.append("<table>" + "".join(current_rows) + "</table>")
            current_rows = [header]
            current_len = len(header)
        current_rows.append(row)
        current_len += len(row)

    if len(current_rows) > 1:
        sub_tables.append("<table>" + "".join(current_rows) + "</table>")

    return sub_tables if sub_tables else [table_html]


# ==================== 切分逻辑（含表格保护 + 大表拆分） ====================
def split_markdown(markdown_text: str) -> list[Document]:
    """
    两级切分策略 + HTML 表格保护 + 大表按行拆分。
    """
    # ============ 1. 抽取 HTML 表格，用占位符替换 ============
    table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
    tables: list[str] = []

    def replace_table(match):
        tables.append(match.group(0))
        return f"__TABLE_PLACEHOLDER_{len(tables) - 1}__"

    text_without_tables = table_pattern.sub(replace_table, markdown_text)
    if tables:
        print(f"   [表格保护] 从 Markdown 中抽取了 {len(tables)} 个 HTML 表格。")

    # ============ 2. 一级切分：按 Markdown 标题 ============
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    md_header_splits = markdown_splitter.split_text(text_without_tables)

    # ============ 3. 二级切分：按字符长度 ============
    separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=separators,
    )
    final_docs = text_splitter.split_documents(md_header_splits)

    # ============ 4. 拼接章节路径 + 还原表格 + 大表拆分 ============
    placeholder_pattern = re.compile(r'__TABLE_PLACEHOLDER_(\d+)__')
    restored_docs: list[Document] = []

    for doc in final_docs:
        # 4.1 拼接章节路径
        h1 = doc.metadata.get("Header 1", "")
        h2 = doc.metadata.get("Header 2", "")
        h3 = doc.metadata.get("Header 3", "")
        title_path = " > ".join(filter(None, [h1, h2, h3]))
        doc.metadata["title_path"] = title_path

        content = doc.page_content
        placeholder_matches = list(placeholder_pattern.finditer(content))

        if not placeholder_matches:
            # 不含表格：直接加前缀
            if title_path:
                doc.page_content = f"【所属章节】: {title_path}\n【正文】: {content}"
            restored_docs.append(doc)
            continue

        # 4.2 含表格：按占位符位置切开，逐段处理
        last_end = 0
        for match in placeholder_matches:
            # 表格前置正文
            text_before = content[last_end:match.start()].strip()
            if text_before:
                restored_docs.append(Document(
                    page_content=(
                        f"【所属章节】: {title_path}\n【正文】: {text_before}"
                        if title_path else text_before
                    ),
                    metadata={**doc.metadata, "content_type": "text"}
                ))

            # 表格本体
            table_html = tables[int(match.group(1))]
            last_end = match.end()

            if len(table_html) <= MAX_TABLE_CHARS:
                restored_docs.append(Document(
                    page_content=(
                        f"【所属章节】: {title_path}\n【正文】(表格)\n{table_html}"
                        if title_path else table_html
                    ),
                    metadata={**doc.metadata, "content_type": "table"}
                ))
            else:
                sub_tables = split_large_table(table_html, MAX_TABLE_CHARS)
                for idx, sub_table in enumerate(sub_tables):
                    restored_docs.append(Document(
                        page_content=(
                            f"【所属章节】: {title_path}\n"
                            f"【正文】(表格 part {idx + 1}/{len(sub_tables)})\n{sub_table}"
                            if title_path else sub_table
                        ),
                        metadata={
                            **doc.metadata,
                            "content_type": "table",
                            "table_part": f"{idx + 1}/{len(sub_tables)}"
                        }
                    ))

        # 4.3 表格后的剩余正文
        text_after = content[last_end:].strip()
        if text_after:
            restored_docs.append(Document(
                page_content=(
                    f"【所属章节】: {title_path}\n【正文】: {text_after}"
                    if title_path else text_after
                ),
                metadata={**doc.metadata, "content_type": "text"}
            ))

    return restored_docs


# ==================== 清洗逻辑 ====================
def clean_docs(docs: list[Document]) -> list[Document]:
    """
    清洗切分后的文档块：
    1. 过滤目录块
    2. 过滤封面页 / 纯图片块
    3. 把 Markdown 图片语法替换成可读文本
    4. 表格块跳过过滤
    """
    cleaned = []
    for doc in docs:
        text = doc.page_content
        title_path = doc.metadata.get("title_path", "")
        is_table = doc.metadata.get("content_type") == "table"

        # 图片语法转可读文本
        text = re.sub(
            r'!\[.*?\]\(.*?/([^/)]+\.(?:jpg|jpeg|png|gif))\)',
            r'[图片: \1]', text, flags=re.IGNORECASE,
        )

        # 表格块：跳过过滤，直接保留
        if is_table:
            doc.page_content = text
            cleaned.append(doc)
            continue

        # 过滤目录块
        if re.search(r'(^|[\s>:])目\s*录([\s<:]|$)', title_path):
            continue

        # 计算有效文字（去掉章节标记和图片占位符后）
        raw_text = re.sub(r'【所属章节】: .*?\n', '', text)
        raw_text = re.sub(r'【正文】: ', '', raw_text)
        raw_text = re.sub(r'\[图片: .*?\]', '', raw_text).strip()

        # ===== 更严格的过滤规则 =====
        # 规则 1：有效文字以 [图片: 开头，直接过滤（纯图片块）
        if raw_text.startswith("[图片:"):
            continue
        # 规则 2：无 title_path 且有效文字 < 80 字符（封面页/图注）
        if not title_path and len(raw_text) < 80:
            print(f"   [过滤] 封面/图注块（{len(raw_text)} 字符）")
            continue
        # 规则 3：有效文字 < 20 字符（纯噪音块）
        if len(raw_text) < 20:
            continue

        doc.page_content = text
        cleaned.append(doc)

    return cleaned
# ==================== 主流程 ====================
def mineru_zip_to_documents(zip_url: str) -> list[Document]:
    """完整流程：下载 → 解压 → 读取 → 切分 → 清洗 → 返回"""
    zip_name = zip_url.split("/")[-1]
    zip_path = MINERU_OUTPUT_DIR / zip_name
    extract_dir = MINERU_OUTPUT_DIR / zip_name.replace(".zip", "")

    if not download_zip(zip_url, zip_path):
        return []
    if not unzip_file(zip_path, extract_dir):
        return []

    md_path = find_full_md(extract_dir)
    if not md_path:
        print("❌ 未找到任何 Markdown 文件")
        return []

    with open(md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
    print(f"5. 读取 Markdown 成功，长度: {len(markdown_text)} 字符。")

    docs = split_markdown(markdown_text)
    print(f"6. 切分完毕（含表格还原与大表拆分），共 {len(docs)} 个文档块。")

    docs = clean_docs(docs)
    print(f"7. 清洗完毕，共 {len(docs)} 个有效文档块。")

    for doc in docs:
        doc.metadata["source"] = str(md_path)
        doc.metadata["origin_zip"] = zip_url

    return docs


if __name__ == '__main__':
    test_zip_url = (
        "https://cdn-mineru.openxlab.org.cn/pdf/2026-10-16/"
        "b660f83a-c11c-4033-bcdb-b42d66b40bee.zip"
    )

    final_docs = mineru_zip_to_documents(test_zip_url)

    # 统计
    table_count = sum(1 for d in final_docs if d.metadata.get("content_type") == "table")
    text_count = len(final_docs) - table_count
    lengths = [len(d.page_content) for d in final_docs]
    max_len = max(lengths) if lengths else 0
    avg_len = sum(lengths) / len(lengths) if lengths else 0

    print(f"\n===== 最终产出 {len(final_docs)} 个 Document 块 =====")
    print(f"   - 文本块: {text_count} 个")
    print(f"   - 表格块: {table_count} 个（已按 1500 字符拆分）")
    print(f"   - 最长块: {max_len} 字符")
    print(f"   - 平均块长: {avg_len:.0f} 字符")

    # 预览前 3 个块
    print("\n===== 前 3 个块 =====")
    for i, doc in enumerate(final_docs[:3]):
        print(f"--- 块 {i + 1} (长度: {len(doc.page_content)}) ---")
        print(f"元数据: {doc.metadata}")
        print(f"内容: {doc.page_content[:300]}...")
        print("=" * 50)

    # 验证大表拆分效果
    print("\n===== 大表拆分验证（前 2 个表格块） =====")
    table_shown = 0
    for i, doc in enumerate(final_docs):
        if doc.metadata.get("content_type") == "table":
            print(f"--- 表格块 (索引 {i + 1}, 长度: {len(doc.page_content)}) ---")
            print(f"章节路径: {doc.metadata.get('title_path', '(空)')}")
            print(f"表格分片: {doc.metadata.get('table_part', '单一表格')}")
            print(f"内容: {doc.page_content[:400]}...")
            print("=" * 50)
            table_shown += 1
            if table_shown >= 2:
                break

    # 最长块诊断
    print("\n===== 最长块诊断（Top 3 长度） =====")
    sorted_docs = sorted(final_docs, key=lambda d: len(d.page_content), reverse=True)
    for i, doc in enumerate(sorted_docs[:3]):
        print(f"--- Top {i + 1} (长度: {len(doc.page_content)}) ---")
        print(f"章节路径: {doc.metadata.get('title_path', '(空)')}")
        print(f"类型: {doc.metadata.get('content_type', 'text')}")
        print(f"内容: {doc.page_content[:200]}...")
        print("=" * 50)