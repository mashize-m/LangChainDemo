"""
Lesson 12: 删除 Milvus 中的数据

⚠️ 运行前置条件：
请确保 Lesson 11 已经执行过，demo_collection 中有 42 条数据。
（如果你之前已经跑过并打乱了数据，重新跑一次 Lesson 11 即可恢复初始状态）

流程：
1. 连接远程 Milvus
2. 验证删除前的数据总数
3. 【按主键 ID 删除】：查出前 2 条数据的真实 ID 并删除
4. 【按条件表达式删除】：利用 metadata 或 text 字段进行条件删除（如删除表格块）
5. 验证删除后的数据总数
"""
from pymilvus import MilvusClient

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"  # B 电脑的 IP
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"


def get_milvus_client() -> MilvusClient:
    """创建并返回 Milvus 客户端"""
    uri = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
    print(f"1. 正在连接 Milvus: {uri}")
    return MilvusClient(uri=uri, token="")


def get_entity_count(client: MilvusClient) -> int:
    """获取当前集合中的实时逻辑实体总数（过滤掉已标记删除的）"""
    # 使用 count(*) 聚合查询，这是获取实时数量的最准确方式
    res = client.query(
        collection_name=COLLECTION_NAME,
        filter="id > 0",           # 查询所有未被删除的数据
        output_fields=["count(*)"]
    )
    return res[0]["count(*)"]


def delete_demo(client: MilvusClient):
    """演示两种删除方式：按 ID 删除 与 按条件删除"""

    # ================= 0. 删除前验证 =================
    count_before = get_entity_count(client)
    print(f"\n2. 删除前，集合 '{COLLECTION_NAME}' 共有数据: {count_before} 条。")
    if count_before == 0:
        print("⚠️ 集合为空，请先运行 Lesson 11 插入数据。")
        return

    # ================= 1. 按主键 ID 删除 =================
    print("\n--- 场景 A：按主键 ID 删除 ---")
    # 为了安全，我们先查出真实的 ID，而不是像教程那样硬编码
    query_res = client.query(
        collection_name=COLLECTION_NAME,
        filter="id > 0",  # 随便写个条件，表示查所有
        output_fields=["id", "metadata"],
        limit=2  # 只取前 2 条
    )

    if not query_res:
        print("未查到数据")
        return

    ids_to_delete = [str(item["id"]) for item in query_res]  # 转成字符串，方便拼接 filter
    print(f"   1. 查找到的待删除 ID: {ids_to_delete}")
    for item in query_res:
        print(f"      包含的章节: {item['metadata'].get('title_path', '无')}")

    # 拼接 filter 表达式：id in [xxx, yyy]
    id_filter = f"id in [{', '.join(ids_to_delete)}]"
    print(f"   2. 执行删除，filter 表达式: {id_filter}")

    resp = client.delete(collection_name=COLLECTION_NAME, filter=id_filter)
    print(f"   3. 删除结果: {resp}")  # 预期 {'delete_count': 2}

    # ================= 2. 按条件表达式删除（进阶） =================
    print("\n--- 场景 B：按条件表达式删除 ---")
    # 业务需求：删除所有表格块（我们在 Lesson 11 存过 metadata={"content_type": "table"}）
    # 注意：Milvus 的 JSON 字段条件过滤语法
    table_filter = 'metadata["content_type"] == "table"'

    print(f"   1. 执行删除所有表格块，filter 表达式: {table_filter}")
    resp = client.delete(collection_name=COLLECTION_NAME, filter=table_filter)
    print(f"   2. 删除结果: {resp}")

    # ================= 3. 删除后验证 =================
    # 注意：Milvus 的 delete 是标记删除，实际物理内存释放需要等后台 compaction 机制。
    # 但 query 和 search 会立刻查不到它们，所以 count 会立刻减少。
    count_after = get_entity_count(client)
    print(f"\n3. 删除后，集合 '{COLLECTION_NAME}' 剩余数据: {count_after} 条。")
    print(f"   (共删除了 {count_before - count_after} 条)")


if __name__ == "__main__":
    try:
        client = get_milvus_client()
        delete_demo(client)
    except Exception as e:
        print(f"\n❌ 执行失败，请检查 Milvus 是否正常运行。错误详情: {e}")