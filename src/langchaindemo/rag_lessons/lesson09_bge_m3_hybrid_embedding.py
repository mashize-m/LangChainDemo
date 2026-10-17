"""
Lesson 09: BGE-M3 混合向量（稠密 + 稀疏）演示

流程：
1. 加载本地的 BGE-M3 模型（支持多语言、8192 长文本）。
2. 输入一段中文文本，同时生成稠密向量（Dense）和稀疏向量（Sparse/Lexical）。
3. 将稀疏向量的 token_id 还原为可读的 token，验证其关键词匹配能力。

说明：
- 稠密向量（Dense）：固定 1024 维，擅长语义模糊匹配。
- 稀疏向量（Sparse）：长度不固定（字典结构），擅长关键词精确匹配。
"""

import warnings
# 屏蔽 Hugging Face 的分词器性能警告
warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*")

from FlagEmbedding import BGEM3FlagModel
from langchaindemo.config import ROOT_DIR

# 本地 BGE-M3 模型路径
BGE_M3_MODEL_PATH = ROOT_DIR / "data" / "models" / "bge-m3"


def hybrid_embedding_demo():
    print(f"1. 正在加载 BGE-M3 模型: {BGE_M3_MODEL_PATH}")
    model = BGEM3FlagModel(
        model_name_or_path=str(BGE_M3_MODEL_PATH),
        use_fp16=True
    )

    texts = ["标量字段通常用来存储一些元数据，并可以在搜索时通过元数据进行过滤"]

    print("\n2. 开始生成混合向量...")
    res = model.encode(
        texts,
        return_sparse=True,
        return_dense=True
    )

    # ============ 3. 打印稠密向量 ============
    print("\n【3. 稠密向量 (Dense Vectors)】")
    dense_vec = res["dense_vecs"][0]
    print(f"向量维度: {len(dense_vec)}")
    print(f"前 5 维数据: {[round(float(v), 5) for v in dense_vec[:5]]}") # 美化输出
    print(f"说明: 每个字/词都没有具体含义，是模型压缩的抽象语义特征。")

    # ============ 4. 打印稀疏向量 (原始 ID) ============
    print("\n【4. 稀疏向量 (Sparse Vectors) - 原始 ID】")
    lexical_weights = res["lexical_weights"][0]
    print(f"非零元素个数: {len(lexical_weights)}")
    # 美化输出：将 np.float32 转为普通 float
    items = [(k, float(v)) for k, v in list(lexical_weights.items())[:5]]
    print(f"前 5 个 token_id 及权重: {items}")
    print(f"说明: 字典存储，没出现的词权重为 0。")

    # ============ 5. 打印稀疏向量 (转换为 Token) ============
    print("\n【5. 稀疏向量 (Sparse Vectors) - 转换为 Token】")
    token_weights = model.convert_id_to_token(lexical_weights)
    # 过滤掉可能存在的空字符串（通常是特殊 token）
    for token, weight in list(token_weights.items())[:10]:
        if token.strip():
            print(f"  Token: '{token}' -> 权重: {float(weight):.4f}")
    print("说明: XLMRoberta 分词器对中文按单字/子词切分，权重高的词代表其重要性。")


if __name__ == '__main__':
    hybrid_embedding_demo()