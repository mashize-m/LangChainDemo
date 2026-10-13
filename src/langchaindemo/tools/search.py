from langchain_core.tools import tool


@tool
def search_web(query: str) -> str:
    """搜索网络上的信息。"""
    # 这里先占位，后面接真实的搜索 API
    return f"搜索结果：{query}"