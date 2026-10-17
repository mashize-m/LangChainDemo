"""
Lesson 15: RAG 问答闭环（检索 + 生成）

说明：
这是 RAG 的最终环节。我们将之前 Lesson 13 的混合检索（Hybrid Search）
与大模型（LLM）结合，让大模型基于检索到的真实文档回答问题。

流程：
1. 初始化 Milvus 客户端和 BGE-M3 向量模型。
2. 初始化大语言模型（复用 Lesson 01 的配置，兼容 DeepSeek/OpenAI）。
3. 接收用户问题，执行 Milvus 混合检索（Top 3）。
4. 提取检索结果中的文本和章节元数据，组装成高质量的 Prompt 上下文。
5. 调用大模型生成答案，并打印。
"""

import warnings

warnings.filterwarnings("ignore")

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from pymilvus import MilvusClient, AnnSearchRequest, RRFRanker
from FlagEmbedding import BGEM3FlagModel

from langchaindemo.config import (
    ROOT_DIR,
    OPENAI_MODEL,
)

# 如果你的 config.py 里有 OPENAI_BASE_URL 和 OPENAI_API_KEY，可以按需传入，
# 这里使用 init_chat_model 会自动读取环境变量或 config 中的默认值。

# ================= 环境配置 =================
MILVUS_HOST = "192.168.1.9"
MILVUS_PORT = "19530"
COLLECTION_NAME = "demo_collection"
BGE_M3_MODEL_PATH = ROOT_DIR / "data" / "models" / "bge-m3"


# ================= 初始化 =================
def get_milvus_client() -> MilvusClient:
    return MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", token="")


def get_llm():
    """复用 Lesson 01 的方式加载大模型"""
    return init_chat_model(
        model=OPENAI_MODEL,
        model_provider="openai",
        temperature=0.1,  # RAG 场景建议温度调低，降低幻觉，让模型更忠于原文
    )


def encode_query(model: BGEM3FlagModel, query: str):
    """向量化查询"""
    res = model.encode([query], return_dense=True, return_sparse=True)
    dense_vec = res["dense_vecs"][0].tolist()
    sparse_vec = {int(k): float(v) for k, v in res["lexical_weights"][0].items()}
    return dense_vec, sparse_vec


# ================= RAG 核心逻辑 =================
def rag_demo(client: MilvusClient, model: BGEM3FlagModel, llm, query: str):
    print(f"\n🔍 用户提问: {query}")

    # 1. 执行混合检索 (复用 Lesson 13 的逻辑)
    dense_vec, sparse_vec = encode_query(model, query)

    dense_req = AnnSearchRequest(
        data=[dense_vec], anns_field="dense_vector",
        param={"metric_type": "COSINE"}, limit=3
    )
    sparse_req = AnnSearchRequest(
        data=[sparse_vec], anns_field="sparse_vector",
        param={"metric_type": "IP"}, limit=3
    )

    results = client.hybrid_search(
        collection_name=COLLECTION_NAME,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(k=60),
        limit=3,
        output_fields=["text", "metadata"],
    )

    hits = results[0]
    if not hits:
        print("⚠️ 未检索到相关内容，直接回复默认话术。")
        return

    # 2. 构建高质量的 Context（包含章节信息）
    context_list = []
    for i, hit in enumerate(hits):
        entity = hit.get("entity", {})
        text = entity.get("text", "")
        title_path = entity.get("metadata", {}).get("title_path", "未知章节")

        # 将章节信息与正文拼接到一起，给大模型提供更丰富的上下文
        context_list.append(f"【参考片段 {i + 1}】\n所属章节：{title_path}\n内容：{text}")

    context = "\n\n".join(context_list)
    print(f"\n📄 检索到 {len(hits)} 个相关片段，准备提交给大模型...")
    # 如果想看检索到了什么，可以解除下面两行的注释
    # print("="*20 + " 检索到的上下文 " + "="*20)
    # print(context)

    # 3. 组装 Prompt
    system_prompt = (
        "你是一个专业的数据分析助手。请严格根据下面提供的参考资料（包含所属章节和正文）来回答用户问题。\n"
        "要求：\n"
        "1. 回答必须完全基于参考资料，不得凭空捏造。\n"
        "2. 如果参考资料中有表格数据，请尽量提取出准确的数字。\n"
        "3. 如果参考资料完全无法回答该问题，请直接回答：“根据提供的参考资料，无法回答该问题。”\n"
    )

    user_prompt = f"参考资料：\n{context}\n\n用户问题：{query}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    # 4. 调用大模型生成
    print("\n🤖 大模型正在生成回答...")
    resp = llm.invoke(messages)

    print("\n" + "=" * 20 + " 最终回答 " + "=" * 20)
    print(resp.content)
    print("=" * 50)


if __name__ == "__main__":
    print("1. 正在初始化系统...")
    client = get_milvus_client()
    bge_model = BGEM3FlagModel(model_name_or_path=str(BGE_M3_MODEL_PATH), use_fp16=True)
    llm = get_llm()

    # 测试问题 1：需要从表格中提取具体数字
    query_1 = "2023年三公经费的具体金额是多少？"
    rag_demo(client, bge_model, llm, query_1)

    # 测试问题 2：需要总结文本段落
    query_2 = "中国科学院国家天文台的机构设置是怎样的？"
    rag_demo(client, bge_model, llm, query_2)