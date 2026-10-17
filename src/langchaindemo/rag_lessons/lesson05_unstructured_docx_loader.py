"""
Lesson 05: 重量级 Docx 文档加载方案 (UnstructuredWordDocumentLoader) - 结构感知版

【优点】
1. 深度语义解析，理论上能识别标题、正文、列表等元素。
2. 元数据丰富，自带 element_id 等溯源信息。
3. 使用 mode='elements' 可直接拆分到语义粒度。

【缺点】
1. 依赖极重（unstructured + nltk + python-magic），Windows 下易卡死。
2. 元数据冗余（element_id、file_directory 等）。
3. 对于未使用 Word 规范标题样式的文档，结构识别会失效，退化为按行/句暴力拆分。

【优化方案】
借鉴 lesson03 的栈算法思想，但不依赖 unstructured 的 category 字段，
改用正则判断文本内容是否为「第X编/分编/章/节」，重建章节层级。
"""
import re
import warnings
from collections import Counter

# 屏蔽 python-magic 库的历史遗留警告
warnings.filterwarnings("ignore", category=SyntaxWarning)

from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_core.documents import Document
from langchaindemo.config import ROOT_DIR


# ==== 章节标题正则（按层级从高到低） ====
TITLE_PATTERNS = [
    (0, re.compile(r'^第[一二三四五六七八九十]+编\s+\S+')),
    (1, re.compile(r'^第[一二三四五六七八九十]+分编\s+\S+')),
    (2, re.compile(r'^第[一二三四五六七八九十百零]+章\s+\S+')),
    (3, re.compile(r'^第[一二三四五六七八九十百零]+节\s+\S+')),
    (0, re.compile(r'^附\s*则$')),
]


def detect_title_level(text: str) -> int | None:
    """检测文本是否为章节标题，返回层级（0-3），否则返回 None"""
    for level, pattern in TITLE_PATTERNS:
        if pattern.match(text.strip()):
            return level
    return None


def inject_title_path_by_content(document_list: list[Document]) -> list[Document]:
    """
    用「正则 + 栈」重建章节层级（不依赖 unstructured 的 category 字段）。
    输入的碎片元素会被重组：标题元素被吸收为层级路径，正文元素被拼接章节路径。
    """
    title_stack: list[tuple[int, str]] = []
    enriched_list: list[Document] = []

    for doc in document_list:
        content = doc.page_content.strip()
        if not content:
            continue

        level = detect_title_level(content)
        if level is not None:
            # 遇到标题：更新栈
            while title_stack and title_stack[-1][0] >= level:
                title_stack.pop()
            title_stack.append((level, content))
        else:
            # 遇到正文：拼接章节路径
            title_path = " > ".join([t for _, t in title_stack]) if title_stack else ""
            doc.page_content = (
                f"【所属章节】: {title_path}\n【正文】: {content}" if title_path else content
            )
            doc.metadata["title_path"] = title_path
            enriched_list.append(doc)

    return enriched_list


def load_docx_unstructured() -> list[Document]:
    file_path = ROOT_DIR / "data" / "sample.docx"
    print(f"1. 正在处理文件: {file_path}")

    print("2. 正在初始化 UnstructuredWordDocumentLoader...")
    loader = UnstructuredWordDocumentLoader(
        file_path=str(file_path),
        encoding="utf-8",
        mode="elements",
    )

    print("3. 开始解析文档 (如果卡住，说明 python-magic 或 NLTK 环境有问题)...")
    docs = loader.load()
    print(f"4. 文档解析完成！共解析出 {len(docs)} 个元素。\n")

    # ==================== 统计各 category 的分布 ====================
    print("===== 【诊断 1】原始元素的 category 分布 =====")
    categories = Counter(d.metadata.get("category", "Unknown") for d in docs)
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")
    print()

    # ==================== 正则 + 栈 处理 ====================
    print("5. 正在用正则 + 栈算法重建章节层级...")
    enriched = inject_title_path_by_content(docs)
    print(f"6. 处理后共 {len(enriched)} 个正文块（已吸收标题元素）。\n")

    # ==================== 输出多个区间的样本 ====================
    def preview(docs_list, start, end, label):
        print(f"===== {label} (第 {start+1} - {end} 条) =====")
        for i, doc in enumerate(docs_list[start:end]):
            print(f"--- 块 {start + i + 1} (长度: {len(doc.page_content)}) ---")
            print(f"元数据 title_path: {doc.metadata.get('title_path', '(空)')}")
            # 内容只截取前 150 字，避免刷屏
            print(f"内容预览: {doc.page_content[:150]}...")
            print("-" * 40)
        print()

    preview(enriched, 0, 5, "【前 5 条】")
    preview(enriched, len(enriched) // 2, len(enriched) // 2 + 5, "【中间 5 条】")
    preview(enriched, len(enriched) - 5, len(enriched), "【最后 5 条】")

    # ==================== 抽样对比：搜索“买卖合同”章节 ====================
    print("===== 【诊断 2】搜索包含“买卖合同”章节的块 =====")
    found = 0
    for i, doc in enumerate(enriched):
        if "买卖合同" in doc.metadata.get("title_path", ""):
            print(f"--- 块 {i+1} (长度: {len(doc.page_content)}) ---")
            print(f"章节路径: {doc.metadata['title_path']}")
            print(f"内容: {doc.page_content[:200]}...")
            print("-" * 40)
            found += 1
            if found >= 3:  # 只展示前 3 条
                break
    if found == 0:
        print("  ⚠️ 未找到任何属于“买卖合同”章节的块！")
    print()

    return enriched


if __name__ == '__main__':
    load_docx_unstructured()