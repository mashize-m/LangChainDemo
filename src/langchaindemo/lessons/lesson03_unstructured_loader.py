"""
Lesson 03: 基于 UnstructuredMarkdownLoader 的重量级语义解析方案

核心策略：
1. 加载器：使用 mode='elements'，将 Markdown 拆分为最细粒度的语义元素。
2. 栈算法：`inject_title_path` 动态追踪元素层级，手动将标题拼回正文前。

备注：该方案依赖 nltk 和 python-magic 等重量级库，Windows 下易卡死，仅作学习栈算法与 Unstructured 库的参考，生产环境请首选 Lesson 02。
"""

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document
from langchaindemo.config import ROOT_DIR


def load_md_elements() -> list[Document]:
    """
    使用 UnstructuredMarkdownLoader 加载 Markdown 文件。
    采用 mode='elements' 模式，将文档按语义元素（标题、段落、列表等）拆分为独立的 Document。
    """
    file_path = ROOT_DIR / "data" / "sample.md"
    print(f"1. 准备加载文件: {file_path}")

    print("2. 正在初始化 UnstructuredMarkdownLoader...")
    # encoding 指定 utf-8 避免中文乱码（注意不是 encodings）
    loader = UnstructuredMarkdownLoader(
        file_path=str(file_path),
        encoding='utf-8',
        mode='elements'
    )

    print("3. 开始解析文档 (如果卡在这里，说明 python-magic 仍未生效)...")
    docs = loader.load()
    print(f"4. 文档解析完成！共解析出 {len(docs)} 个元素。\n")

    return docs


def inject_title_path(document_list: list[Document]) -> list[dict]:
    """
    利用栈结构，追踪当前所处的标题层级，并将标题路径拼接到正文前面。
    例如：将 {'Header 1': 'A', 'Header 2': 'B'} 的正文 -> 'A > B\n正文内容'
    """
    # 栈：用来存放历史的标题 [(category_depth, title)]
    title_stack = []
    enriched_list = []

    for doc in document_list:
        # 使用 .get 避免某些元素缺少 category 属性导致程序崩溃
        if doc.metadata.get('category') == "Title":
            category_depth = doc.metadata.get('category_depth', 0)
            # 如果当前标题深度 <= 栈顶标题深度，说明进入了新的同级或更高级章节，弹出旧标题
            while title_stack and title_stack[-1][0] >= category_depth:
                title_stack.pop()
            title_stack.append((category_depth, doc.page_content))
        else:
            # 遇到正文时，将当前栈中所有标题拼接成路径
            title_path = " > ".join([title for _, title in title_stack])

            # 避免栈为空时（文档没有标题），正文开头多出一个空行
            if title_path:
                content = f"{title_path}\n{doc.page_content}"
            else:
                content = doc.page_content

            enriched_list.append({
                "meta_data": doc.metadata,
                "content": content
            })

    return enriched_list


if __name__ == '__main__':
    print("========== 阶段 1：原始 Unstructured 加载结果 ==========")
    document = load_md_elements()
    # 为防止控制台刷屏，仅打印前 3 个元素进行预览
    for doc in document:
        print(f"类型: {doc.metadata.get('category')}")
        print(f"内容: {doc.page_content}...")  # 截取前100字
        print("=" * 50)

    print("\n========== 阶段 2：inject_title_path 拼接标题后结果 ==========")
    enrich_doc_list = inject_title_path(document)
    # 同样仅打印前 3 条
    for doc_dict in enrich_doc_list:
        print(doc_dict['content'])
        print("=" * 50)