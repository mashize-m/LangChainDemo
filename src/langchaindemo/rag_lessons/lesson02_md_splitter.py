"""
Lesson 02: Markdown 轻量级两级切分方案

核心策略：
1. 一级切分：按标题层级（#、##、###）切分，保留结构。
2. 二级切分：按字符长度（500字）二次切分，控制块大小。
3. 上下文重构：将标题路径拼接到正文前，提升检索命中率。

优势：无额外依赖、跨平台完美运行、元数据干净可控。
"""

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchaindemo.config import ROOT_DIR


def split_markdown() -> list[Document]:
    """
    采用“两级切分”策略处理 Markdown：
    第一级：按标题层级切分，保留宏观结构。
    第二级：按字符长度切分，控制单块体积，并保留标题上下文。
    """
    file_path = ROOT_DIR / "data" / "sample.md"
    print(f"1. 正在处理文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # ================= 第一级切分：按 Markdown 标题 =================
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(markdown_text)
    print(f"2. 第一级切分完毕，共 {len(md_header_splits)} 个文档块。")

    # ================= 第二级切分：按 Token/字符长度 =================
    # 针对中文优化的分隔符顺序：段落 -> 换行 -> 中文句末标点 -> 中文句内标点 -> 空格 -> 单字
    separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  # 目标块大小：500 个字符（或 Token）
        chunk_overlap=50,  # 重叠区大小：50 个字符，保持语义连贯
        length_function=len,  # 用 len 计算字符数，如果要用 Token 计算需替换
        separators=separators,  # 中文优化的分隔符
    )

    # 注意：这里使用 split_documents，因为它能继承第一级切分保留的 metadata
    final_docs = text_splitter.split_documents(md_header_splits)
    print(f"3. 第二级切分完毕，最终共 {len(final_docs)} 个文档块。\n")

    # ================= 第三步：重构上下文（拼接标题路径） =================
    # 说明：此步骤可选。它能极大提升 RAG 检索准确率，但会改变 page_content 文本。
    print("4. 开始重构上下文（将标题路径拼接到正文前）...")
    for doc in final_docs:
        # 1. 从 metadata 中提取各级标题
        h1 = doc.metadata.get("Header 1", "")
        h2 = doc.metadata.get("Header 2", "")
        h3 = doc.metadata.get("Header 3", "")

        # 2. 过滤掉空标题，并用 " > " 连接
        title_path = " > ".join(filter(None, [h1, h2, h3]))

        # 3. 保存到 metadata 中（方便后续检索时过滤或溯源）
        doc.metadata["title_path"] = title_path

        # 4. 将标题路径拼接到 page_content 的开头
        # 注：这一步相当于方案二 enrich_document_info 的核心效果，但代价极低。
        if title_path:
            doc.page_content = f"【所属章节】: {title_path}\n【正文】: {doc.page_content}"

    # ================= 打印最终结果验证 =================
    for i, doc in enumerate(final_docs):
        print(f"--- 块 {i + 1} (长度: {len(doc.page_content)}) ---")
        print(f"元数据: {doc.metadata}")
        # 为避免控制台刷屏，仅截取前 100 个字符预览
        print(f"内容预览: {doc.page_content[:100]}...")
        print("=" * 50)

    return final_docs


if __name__ == '__main__':
    split_markdown()