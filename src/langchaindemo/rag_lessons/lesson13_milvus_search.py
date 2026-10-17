"""
Lesson 13: Milvus 检索实战（稠密、稀疏、混合）

前置条件：
1. 确保 lesson11 插入过数据（当前数据为 42 条天文台预算 PDF 的切片）。
2. 确保 B 电脑 IP 仍是 192.168.1.9，且 Milvus 正常运行。

流程：
1. 初始化 Milvus 客户端和 BGE-M3 模型。
2. 测试【纯稠密向量检索】（语义匹配，使用 COSINE）。
3. 测试【纯稀疏向量检索】（关键词匹配，使用 IP）。
4. 测试【混合向量检索】（使用 RRF 算法融合两路结果）。
"""
import warnings

warnings.filterwarnings("ignore")  # 忽略 tokenizer 的黄色警告

from typing import Tuple, List, Dict
from pymilvus import MilvusClient, AnnSearchRequest, RRFRanker
from FlagEmbedding import BGEM3FlagModel
from langchaindemo.config import ROOT_DIR

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"  # B 电脑 IP
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"
BGE_M3_MODEL_PATH = ROOT_DIR / "data" / "models" / "bge-m3"


# ================= 初始化 =================
def get_milvus_client() -> MilvusClient:
    uri = f"http://{MILVUS_HOST}:{MILVUS_PORT}"
    return MilvusClient(uri=uri, token="")


def encode_query(model: BGEM3FlagModel, query: str) -> Tuple[List[float], Dict[int, float]]:
    """对查询语句进行向量化（同时生成稠密和稀疏）"""
    res = model.encode([query], return_dense=True, return_sparse=True)
    # 稠密向量转为 python list，稀疏向量转为原生字典格式
    dense_vec = res["dense_vecs"][0].tolist()
    sparse_vec = {int(k): float(v) for k, v in res["lexical_weights"][0].items()}
    return dense_vec, sparse_vec


def print_hits(title: str, hits: List[dict]):
    """打印检索结果（截断长文本，防止表格刷屏）"""
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)
    for i, hit in enumerate(hits, start=1):
        entity = hit.get("entity", {})
        text = entity.get("text", "").replace("\n", " ")
        # 截取前 80 个字符用于预览
        preview = text[:80] + "..." if len(text) > 80 else text

        print(f"[{i}] 分数: {hit.get('distance'):.4f}")
        print(f"    章节: {entity.get('metadata', {}).get('title_path', '未知')}")
        print(f"    内容: {preview}")
    print("=" * 55)


# ================= 检索方法 =================
def search_dense(client, model, query: str, limit: int = 3):
    """1. 纯稠密检索（根据语义匹配）"""
    dense_vec, _ = encode_query(model, query)
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[dense_vec],
        anns_field="dense_vector",
        limit=limit,
        # ⚠️ 注意：必须和 Lesson 10 建索引时的度量方式保持一致
        search_params={"metric_type": "COSINE"},
        output_fields=["text", "metadata"],
    )
    print_hits("【纯稠密检索 - 语义匹配】", results[0])
    return results[0]


def search_sparse(client, model, query: str, limit: int = 3):
    """2. 纯稀疏检索（根据关键词权重匹配）"""
    _, sparse_vec = encode_query(model, query)
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[sparse_vec],
        anns_field="sparse_vector",
        limit=limit,
        search_params={"metric_type": "IP"},  # 内积
        output_fields=["text", "metadata"],
    )
    print_hits("【纯稀疏检索 - 关键词匹配】", results[0])
    return results[0]


def search_hybrid(client, model, query: str, limit: int = 3):
    """3. 混合检索（RRF 融合稠密和稀疏）"""
    dense_vec, sparse_vec = encode_query(model, query)

    # 配置两路检索请求
    dense_req = AnnSearchRequest(
        data=[dense_vec], anns_field="dense_vector",
        param={"metric_type": "COSINE"}, limit=limit
    )
    sparse_req = AnnSearchRequest(
        data=[sparse_vec], anns_field="sparse_vector",
        param={"metric_type": "IP"}, limit=limit
    )

    # RRF（倒数排名融合）计算最终排名
    results = client.hybrid_search(
        collection_name=COLLECTION_NAME,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(k=60),
        limit=limit,
        output_fields=["text", "metadata"],
    )
    print_hits("【混合检索 - RRF 融合】", results[0])
    return results[0]


# ================= 主流程 =================
if __name__ == "__main__":
    print(f"1. 正在加载 Milvus 客户端和 BGE-M3 模型...")
    client = get_milvus_client()
    model = BGEM3FlagModel(model_name_or_path=str(BGE_M3_MODEL_PATH), use_fp16=True)

    # 使用与你当前数据强相关的问题进行测试
    query_text = "2023 年三公经费具体数字是多少？"
    print(f"\n查询测试问题: 「{query_text}」")

    # 分别执行三种检索
    search_dense(client, model, query_text)
    search_sparse(client, model, query_text)
    search_hybrid(client, model, query_text)