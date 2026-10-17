"""
Lesson 10: 创建 Milvus 集合 (Collection)

流程：
1. 连接远程 Milvus 服务（B 电脑）
2. 定义 Schema（包含稠密、稀疏、标量字段）
3. 定义索引（稠密使用 HNSW，稀疏使用倒排索引）
4. 创建集合，并加载到内存（Load）

注意：
- 请确保 B 电脑已启动 Milvus，且防火墙允许 19530 端口。
- B 电脑 IP 若变动，需修改 MILVUS_HOST。
"""
from pymilvus import MilvusClient, DataType, CollectionSchema

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"  # B 电脑的局域网 IP
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"


def get_milvus_client() -> MilvusClient:
    """创建并返回 Milvus 客户端"""
    uri = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
    print(f"1. 正在连接 Milvus: {uri}")
    return MilvusClient(uri=uri, token="")


def create_collection_schema(client: MilvusClient) -> CollectionSchema:
    """创建 Schema (集合结构)"""
    print("2. 正在构建 Schema...")
    return (client.create_schema(auto_id=True)
            # 主键，自动生成，无需手动传入
            .add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            # 稠密向量：BGE-M3 输出维度为 1024
            .add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
            # 稀疏向量：无需指定维度，由插入的数据动态决定
            .add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)
            # 正文文本：最大长度 65535
            .add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            # 元数据：使用 JSON 格式存储，方便过滤
            .add_field(field_name="metadata", datatype=DataType.JSON)
            )


def create_collection_index(client: MilvusClient):
    """构建索引"""
    print("3. 正在准备索引参数...")
    index_params = client.prepare_index_params()

    # 稠密向量索引
    index_params.add_index(
        field_name="dense_vector",
        index_type="HNSW",  # 分层导航小世界，检索快
        metric_type="COSINE",  # 余弦相似度（BGE 向量已 L2 归一化，用 COSINE 最准）
        params={"M": 16, "efConstruction": 200}  # HNSW 进阶参数（可选）
    )

    # 稀疏向量索引
    index_params.add_index(
        field_name="sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",  # 倒排索引
        metric_type="IP",  # 内积（稀疏向量推荐用 IP）
    )
    return index_params


def create_collection(client: MilvusClient):
    """创建集合（包含防呆逻辑与加载）"""
    # 1. 如果集合存在，先删除
    if client.has_collection(collection_name=COLLECTION_NAME):
        print(f"   ⚠️ 集合 '{COLLECTION_NAME}' 已存在，正在删除旧集合...")
        client.drop_collection(collection_name=COLLECTION_NAME)

    # 2. 创建新集合（注意：这里的缩进在最外层）
    print(f"4. 正在创建集合 '{COLLECTION_NAME}'...")
    schema = create_collection_schema(client)
    index_params = create_collection_index(client)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params
    )

    # 3. 将集合加载到内存（Milvus 搜索前提）
    print("5. 正在将集合加载到内存...")
    client.load_collection(collection_name=COLLECTION_NAME)

    # 4. 验证
    print("\n✅ 创建成功！当前集合列表:", client.list_collections())
    print("\n集合详细结构:")
    print(client.describe_collection(collection_name=COLLECTION_NAME))


if __name__ == "__main__":
    try:
        client = get_milvus_client()
        create_collection(client)
    except Exception as e:
        print(f"\n❌ 连接或创建失败，请检查 B 电脑上的 Milvus 是否正常运行，以及 IP 是否正确。")
        print(f"错误详情: {e}")