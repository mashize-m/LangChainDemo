"""
Lesson 11: RAG 索引全过程（从本地文件到 Milvus 入库）

⚠️ 数据源说明：
本代码的数据源并非直接读取原始 PDF，而是读取【PDF 经 MinerU 解析后的 Markdown 文件】。
因为 MinerU 已经将 PDF 中的表格转成了 HTML、公式转成了 LaTeX，且保留了良好的结构。
如果你要换成直接读 .docx，只需替换“第一步”中的读取逻辑即可。

完整流程：
1. 数据加载：从本地已解压的 MinerU 目录读取 full.md。
2. 文本切分：使用 Markdown 标题切分 + 长度切分。包含【表格保护】（防止大表被切碎）和【大表按行拆分】。
3. 数据清洗：过滤目录块、封面纯图块，规范化图片语法。
4. 向量化：使用 BGE-M3 模型，同时生成稠密向量（1024维）和稀疏向量。
5. 实体封装：组装为 Milvus 所需的字典格式。
6. 批量存储：存入远程 Milvus 数据库。
"""

import os
import re
import shutil
import zipfile
from pathlib import Path

import requests
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pymilvus import MilvusClient
from FlagEmbedding import BGEM3FlagModel

from langchaindemo.config import ROOT_DIR

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"  # B电脑的IP
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"
BGE_M3_MODEL_PATH = ROOT_DIR / "data" / "models" / "bge-m3"

# MinerU 数据源目录
MINERU_OUTPUT_DIR = ROOT_DIR / "data" / "mineru_output"
MAX_TABLE_CHARS = 1500  # 大表拆分的阈值


# ================= 1. 数据加载 (MinerU 产物) =================
def load_local_mineru_markdown() -> str:
    """从本地读取最新的 MinerU 解析结果 (full.md)"""
    if not MINERU_OUTPUT_DIR.exists():
        raise FileNotFoundError(f"MinerU 输出目录不存在: {MINERU_OUTPUT_DIR}")

    # 找最新的解压目录
    extract_dirs = [d for d in MINERU_OUTPUT_DIR.iterdir() if d.is_dir()]
    if not extract_dirs:
        raise FileNotFoundError("未找到已解压的 MinerU 目录，请先运行 Lesson 06/07")

    latest_dir = max(extract_dirs, key=lambda d: d.stat().st_mtime)
    md_path = latest_dir / "full.md"
    if not md_path.exists():
        raise FileNotFoundError(f"full.md 不存在: {md_path}")

    print(f"1. 正在读取本地 Markdown 文件: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


# ================= 2. 文本切分 (含表格保护与大表拆分) =================
def split_large_table(table_html: str, max_chars: int) -> list[str]:
    """将大表格按 <tr> 行拆分为多个子表格，保留表头。"""
    rows = re.findall(r'<tr>.*?</tr>', table_html, re.DOTALL)
    if not rows: return [table_html]

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


def split_markdown(markdown_text: str) -> list[Document]:
    """两级切分策略 + HTML表格保护 + 大表拆分"""
    # 1. 抽取表格，用占位符替换
    table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
    tables: list[str] = []

    def replace_table(match):
        tables.append(match.group(0))
        return f"__TABLE_PLACEHOLDER_{len(tables) - 1}__"

    text_without_tables = table_pattern.sub(replace_table, markdown_text)

    # 2. 一级切分：按 Markdown 标题
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")])
    md_header_splits = md_splitter.split_text(text_without_tables)

    # 3. 二级切分：按字符长度
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    final_docs = text_splitter.split_documents(md_header_splits)

    # 4. 还原表格 + 拼接章节路径
    placeholder_pattern = re.compile(r'__TABLE_PLACEHOLDER_(\d+)__')
    restored_docs: list[Document] = []

    for doc in final_docs:
        title_path = " > ".join(filter(None, [doc.metadata.get("Header 1", ""), doc.metadata.get("Header 2", ""),
                                              doc.metadata.get("Header 3", "")]))
        doc.metadata["title_path"] = title_path
        content = doc.page_content
        placeholder_matches = list(placeholder_pattern.finditer(content))

        if not placeholder_matches:
            if title_path: doc.page_content = f"【所属章节】: {title_path}\n【正文】: {content}"
            restored_docs.append(doc)
            continue

        last_end = 0
        for match in placeholder_matches:
            text_before = content[last_end:match.start()].strip()
            if text_before:
                restored_docs.append(Document(
                    page_content=f"【所属章节】: {title_path}\n【正文】: {text_before}" if title_path else text_before,
                    metadata={**doc.metadata, "content_type": "text"}))

            table_html = tables[int(match.group(1))]
            last_end = match.end()

            if len(table_html) <= MAX_TABLE_CHARS:
                restored_docs.append(Document(
                    page_content=f"【所属章节】: {title_path}\n【正文】(表格)\n{table_html}" if title_path else table_html,
                    metadata={**doc.metadata, "content_type": "table"}))
            else:
                sub_tables = split_large_table(table_html, MAX_TABLE_CHARS)
                for idx, sub_table in enumerate(sub_tables):
                    restored_docs.append(Document(
                        page_content=f"【所属章节】: {title_path}\n【正文】(表格 part {idx + 1}/{len(sub_tables)})\n{sub_table}" if title_path else sub_table,
                        metadata={**doc.metadata, "content_type": "table",
                                  "table_part": f"{idx + 1}/{len(sub_tables)}"}))

        text_after = content[last_end:].strip()
        if text_after:
            restored_docs.append(
                Document(page_content=f"【所属章节】: {title_path}\n【正文】: {text_after}" if title_path else text_after,
                         metadata={**doc.metadata, "content_type": "text"}))

    return restored_docs


# ================= 3. 数据清洗 =================
def clean_docs(docs: list[Document]) -> list[Document]:
    """过滤封面、目录和纯图片块，规范化图片语法。"""
    cleaned = []
    for doc in docs:
        text = doc.page_content
        title_path = doc.metadata.get("title_path", "")
        is_table = doc.metadata.get("content_type") == "table"

        text = re.sub(r'!\[.*?\]\(.*?/([^/)]+\.(?:jpg|jpeg|png|gif))\)', r'[图片: \1]', text, flags=re.IGNORECASE)

        if is_table:
            doc.page_content = text
            cleaned.append(doc)
            continue

        if re.search(r'(^|[\s>:])目\s*录([\s<:]|$)', title_path): continue

        raw_text = re.sub(r'【所属章节】: .*?\n', '', text)
        raw_text = re.sub(r'【正文】: ', '', raw_text)
        raw_text = re.sub(r'\[图片: .*?\]', '', raw_text).strip()

        if raw_text.startswith("[图片:") or (not title_path and len(raw_text) < 80) or len(raw_text) < 20:
            continue

        doc.page_content = text
        cleaned.append(doc)
    return cleaned


# ================= 4. 向量化与入库 =================
def get_milvus_client() -> MilvusClient:
    return MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", token="")


def insert_data_to_milvus():
    # ---- 1. 加载 ----
    markdown_text = load_local_mineru_markdown()

    # ---- 2. 切分 ----
    print("2. 正在切分文本（含表格保护与大表拆分）...")
    docs = split_markdown(markdown_text)

    # ---- 3. 清洗 ----
    print("3. 正在清洗无效块...")
    docs = clean_docs(docs)
    print(f"   最终得到 {len(docs)} 个有效文档块。")

    # ---- 4. 向量化 ----
    print(f"4. 正在加载 BGE-M3 模型并生成向量: {BGE_M3_MODEL_PATH}")
    model = BGEM3FlagModel(model_name_or_path=str(BGE_M3_MODEL_PATH), use_fp16=True)
    texts = [doc.page_content for doc in docs]
    res = model.encode(texts, return_sparse=True, return_dense=True, batch_size=16)

    dense_vecs = res['dense_vecs']
    sparse_vecs = res['lexical_weights']

    # ---- 5. 实体封装 ----
    print("5. 正在组装 Milvus 实体数据...")
    entities = []
    for doc, dense_vec, sparse_vec in zip(docs, dense_vecs, sparse_vecs):
        # 将 numpy 类型转换为原生 Python 类型
        sparse_dict = {int(k): float(v) for k, v in sparse_vec.items()}
        meta = dict(doc.metadata)

        entity = {
            "text": doc.page_content,
            "metadata": meta,
            "dense_vector": dense_vec.tolist(),
            "sparse_vector": sparse_dict
        }
        entities.append(entity)

    # ---- 6. 批量存储 ----
    print(f"6. 正在向 Milvus 插入 {len(entities)} 条数据...")
    client = get_milvus_client()

    try:
        insert_resp = client.insert(collection_name=COLLECTION_NAME, data=entities)
        print(f"\n✅ 数据保存成功！")
        print(f"   成功插入条数: {insert_resp['insert_count']}")
        print(f"   生成的主键 IDs (前3个): {insert_resp['ids'][:3]}")
    except Exception as e:
        print(f"\n❌ 插入失败: {e}")
        print("   请检查 Lesson 10 是否已成功创建集合。")


if __name__ == "__main__":
    insert_data_to_milvus()