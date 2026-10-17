"""
Lesson 14: Milvus 标量检索（Scalar Query）实战

说明：
在 RAG 中，标量检索（Metadata Filtering）通常用于：
1. 在向量检索前缩小搜索范围（如：只查某个特定文件的片段）。
2. 直接根据关键词或属性查找特定的文本块（如：查包含“三公经费”的段落）。

流程：
1. 连接 Milvus
2. 针对 `text` 字段进行模糊查询 (VARCHAR like)
3. 针对 `metadata` JSON 字段进行过滤 (JSON 表达式)
4. 结合 limit 和 offset 演示分页
"""
import os
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

from pymilvus import MilvusClient
from langchaindemo.config import ROOT_DIR

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"


def get_milvus_client() -> MilvusClient:
    uri = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
    print(f"1. 正在连接 Milvus: {uri}")
    return MilvusClient(uri=uri, token="")


def print_results(title: str, results: list):
    """通用的格式化打印函数（截断长文本防刷屏）"""
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)
    if not results:
        print("⚠️ 未查询到任何数据")
        return

    for i, row in enumerate(results, start=1):
        # 提取并截断 text 字段
        text = row.get("text", "")
        clean_text = text.replace("\n", " ")
        preview = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text

        # 提取 metadata 中的章节信息
        title_path = row.get("metadata", {}).get("title_path", "无章节信息")

        print(f"[{i}] ID: {row.get('id')}")
        print(f"    所属章节: {title_path}")
        if text:
            print(f"    文本内容: {preview}")
    print("=" * 55)


def query_by_text_like(client: MilvusClient, keyword: str = "三公"):
    """1. VARCHAR 字段模糊查询：在 `text` 中搜索包含特定关键词的块"""
    try:
        print(f"\n--- 正在执行 text 字段模糊检索: like '%{keyword}%' ---")
        res = client.query(
            collection_name=COLLECTION_NAME,
            filter=f'text like "%{keyword}%"',
            output_fields=["id", "text", "metadata"],  # 修正：补全了 metadata
            limit=3,  # 限制返回 3 条
        )
        print_results(f"text like '%{keyword}%' 结果", res)
    except Exception as e:
        print(f"❌ VARCHAR 过滤失败: {e}")


def query_by_metadata_json(client: MilvusClient, chapter_keyword: str = "支出"):
    """2. JSON 字段过滤：在 metadata 的 title_path 中搜索包含特定章节的块"""
    try:
        # Milvus JSON 字段过滤语法：metadata["key"] like "%value%"
        json_filter = f'metadata["title_path"] like "%{chapter_keyword}%"'
        print(f"\n--- 正在执行 JSON 字段过滤: {json_filter} ---")
        res = client.query(
            collection_name=COLLECTION_NAME,
            filter=json_filter,
            output_fields=["id", "metadata"],
            limit=3,
        )
        print_results(f"metadata['title_path'] like '%{chapter_keyword}%' 结果", res)
    except Exception as e:
        print(f"❌ JSON 过滤失败（可能 metadata 结构不匹配或不支持该表达式）: {e}")


def query_with_pagination(client: MilvusClient, offset: int = 0, limit: int = 2):
    """3. 进阶：结合 limit 和 offset 进行分页查询"""
    try:
        print(f"\n--- 正在执行分页查询: limit={limit}, offset={offset} ---")
        res = client.query(
            collection_name=COLLECTION_NAME,
            filter='id > 0',  # 匹配所有
            output_fields=["id", "metadata"],
            limit=limit,
            offset=offset,
            # 注意：Milvus 的 query 返回是无序的，通常配合主键排序或指定排序字段
        )
        print_results(f"分页查询 (offset={offset}, limit={limit}) 结果", res)
    except Exception as e:
        print(f"❌ 分页查询失败: {e}")


if __name__ == "__main__":
    client = get_milvus_client()

    # 1. 测试 text 字段模糊查询（检索与“三公”相关的文本）
    query_by_text_like(client, keyword="三公")

    # 2. 测试 metadata JSON 字段查询（检索属于“支出”相关章节的块）
    query_by_metadata_json(client, chapter_keyword="支出")

    # 3. 测试分页查询
    query_with_pagination(client, offset=0, limit=2)