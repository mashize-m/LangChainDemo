"""
Lesson 04: 轻量级 Docx 文档加载方案 (Docx2txtLoader) - 结构感知版

参考 md 方案，为纯文本的 docx 加载加上“章节结构追踪”。
核心思路：把 Word 中的“第X编/章/节”视作 Markdown 的 # 标题，用栈追踪层级。

【优点】
1. 依赖极轻，速度快，跨平台，无卡死风险。
2. 保留 Word 原生的编/分编/章/节结构，每个文本块带【所属章节】路径。
3. 目录区域被自动“吸收”，不会污染检索结果。
4. 目录和附则等特殊层级被正确处理。

【缺点】
1. 依赖 Word 文档章节标题格式的规范性（必须是“第X编/分编/章/节”）。
2. 无法提取图片、表格等非文本元素。
"""
import re
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchaindemo.config import ROOT_DIR


# ==== 章节标题正则（按层级从高到低） ====
# 说明：层级数字越小，级别越高。附则和编同为最高级（0），保证遇到附则时会清空栈。
TITLE_PATTERNS = [
    (0, re.compile(r'^第[一二三四五六七八九十]+编\s+\S+')),      # 编
    (1, re.compile(r'^第[一二三四五六七八九十]+分编\s+\S+')),    # 分编
    (2, re.compile(r'^第[一二三四五六七八九十百零]+章\s+\S+')),  # 章
    (3, re.compile(r'^第[一二三四五六七八九十百零]+节\s+\S+')),  # 节
    (0, re.compile(r'^附\s*则$')),                              # 附则作为最高层级
]


def detect_title_level(line: str) -> int | None:
    """检测行是否为章节标题，返回层级（0-3），否则返回 None"""
    for level, pattern in TITLE_PATTERNS:
        if pattern.match(line):
            return level
    return None


def clean_text(text: str) -> str:
    """清洗 Word 提取后的排版噪音"""
    # 1. 修复单字换行：将 "第\n六\n百\n条" 还原为 "第六百条"
    text = re.sub(r'(?<=\n)(\S)\n(?=\S)', r'\1', text)
    # 2. 去除页码噪音："－201－"
    text = re.sub(r'－\d+－', '', text)
    # 3. 去除独立成行的"目录"标记（避免产生只有"目录"两字的空块）
    text = re.sub(r'^目\s*录$', '', text, flags=re.MULTILINE)
    # 4. 连续多余换行压缩为单换行
    text = re.sub(r'\n{2,}', '\n', text)
    # 5. 逐行 trim 并丢弃空行
    text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
    return text


def split_by_structure(text: str) -> list[Document]:
    """
    一级切分：按章节结构切分，用栈追踪标题路径。
    目录区域因没有正文跟随，会被自动跳过。
    """
    lines = text.split('\n')
    stack: list[tuple[int, str]] = []  # 标题栈：[(level, title)]
    docs: list[Document] = []
    current_content: list[str] = []

    def flush():
        """将当前积累的正文打包为一个 Document"""
        if current_content:
            content_text = '\n'.join(current_content).strip()
            if content_text:
                title_path = ' > '.join([t for _, t in stack]) if stack else ''
                docs.append(Document(
                    page_content=content_text,
                    metadata={"title_path": title_path}
                ))
        current_content.clear()

    for line in lines:
        level = detect_title_level(line)
        if level is not None:
            # 遇到标题：先输出之前的正文块
            flush()
            # 弹出栈中同级或更低级别的标题
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, line))
        else:
            current_content.append(line)

    flush()
    return docs


def load_docx_lightweight() -> list[Document]:
    """完整流程：加载 → 清洗 → 一级结构切分 → 二级长度切分 → 拼接标题路径"""
    file_path = ROOT_DIR / "data" / "sample.docx"
    print(f"1. 正在处理文件: {file_path}")

    # 加载
    loader = Docx2txtLoader(file_path=str(file_path))
    raw_docs = loader.load()
    print(f"2. 加载完毕，共 {len(raw_docs)} 个原始 Document。")

    # 清洗
    print("3. 正在清洗文本...")
    for doc in raw_docs:
        doc.page_content = clean_text(doc.page_content)
    print(f"4. 清洗完毕，文档总长度: {len(raw_docs[0].page_content)} 字符。")

    # 一级切分：按章节结构
    print("5. 正在进行一级切分（按章节结构 + 标题路径追踪）...")
    structured_docs = split_by_structure(raw_docs[0].page_content)
    print(f"6. 一级切分完毕，共 {len(structured_docs)} 个章节块。")

    # 二级切分：按长度
    print("7. 正在进行二级切分（按 500 字符长度）...")
    separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=separators,
    )
    final_docs = text_splitter.split_documents(structured_docs)
    print(f"8. 二级切分完毕，最终共 {len(final_docs)} 个文档块。\n")

    # 拼接标题路径到正文前
    print("9. 正在拼接标题路径...")
    for doc in final_docs:
        title_path = doc.metadata.get("title_path", "")
        if title_path:
            doc.page_content = f"【所属章节】: {title_path}\n【正文】: {doc.page_content}"

    # ==== 预览前 3 个块 ====
    print("\n===== 预览前 3 个块 =====")
    for i, doc in enumerate(final_docs[:3]):
        print(f"--- 块 {i + 1} (长度: {len(doc.page_content)}) ---")
        print(f"元数据: {doc.metadata}")
        print(f"内容:\n{doc.page_content}")
        print("=" * 50)

    # ==== 预览中间部分（第 30-32 个块，已进入正文深处）=====
    print("\n===== 预览第 30-32 个块 =====")
    for i, doc in enumerate(final_docs[29:32]):
        print(f"--- 块 {i + 30} (长度: {len(doc.page_content)}) ---")
        print(f"元数据: {doc.metadata}")
        print(f"内容:\n{doc.page_content}")
        print("=" * 50)

    # ==== 预览“附则”块（应当属于最后一小部分）=====
    print("\n===== 预览“附则”相关的块 =====")
    for i, doc in enumerate(final_docs):
        if "附则" in doc.metadata.get("title_path", ""):
            print(f"--- 块 {i + 1} (长度: {len(doc.page_content)}) ---")
            print(f"元数据: {doc.metadata}")
            print(f"内容:\n{doc.page_content}")
            print("=" * 50)
            break

    return final_docs


if __name__ == '__main__':
    load_docx_lightweight()