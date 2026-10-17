"""
Lesson 08: Embedding 向量化

流程：
1. 复用 lesson07 的解析结果（从本地已解压的 MinerU 目录读取 full.md）
2. 初始化 BGE 中文向量化模型（本地）
3. 对文档块进行批量向量化
4. 打印验证向量维度、数量、示例向量
5. 相似度快速验证（可选）

依赖：
- langchain-huggingface
- sentence-transformers
- 本地 BGE 模型文件（data/models/bge-base-zh-v1.5）
"""

from pathlib import Path

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from langchaindemo.config import ROOT_DIR
from langchaindemo.rag_lessons.lesson07_mineru_zip_to_docs import (
    split_markdown,
    clean_docs,
)

# 路径配置
BGE_MODEL_PATH = ROOT_DIR / "data" / "models" / "bge-base-zh-v1.5"
MINERU_OUTPUT_DIR = ROOT_DIR / "data" / "mineru_output"


def check_model_files(model_path: Path) -> bool:
    """检查 BGE 模型关键文件是否齐全"""
    if not model_path.exists():
        print(f"❌ 模型目录不存在: {model_path}")
        return False

    # 关键文件：config 必须存在，权重文件（safetensors 或 pytorch_model.bin）至少有一个
    required_files = ["config.json", "modules.json"]
    weight_files = ["model.safetensors", "pytorch_model.bin"]

    for f in required_files:
        if not (model_path / f).exists():
            print(f"❌ 缺少关键文件: {f}")
            return False

    if not any((model_path / w).exists() for w in weight_files):
        print(f"❌ 缺少权重文件: {weight_files} 中至少需要一个")
        return False

    # 打印使用的权重文件类型
    for w in weight_files:
        if (model_path / w).exists():
            print(f"   ✓ 检测到权重文件: {w}")
    return True


def load_final_docs_from_local() -> list[Document]:
    """
    从本地已解压的 MinerU 目录直接读取 full.md，跳过下载和解压。
    这样每次跑 lesson08 只需 1 秒。
    """
    if not MINERU_OUTPUT_DIR.exists():
        print(f"❌ MinerU 输出目录不存在: {MINERU_OUTPUT_DIR}")
        return []

    # 找最新的解压目录
    extract_dirs = [d for d in MINERU_OUTPUT_DIR.iterdir() if d.is_dir()]
    if not extract_dirs:
        print("❌ 未找到任何已解压的 MinerU 目录，请先运行 lesson06/07")
        return []

    latest_dir = max(extract_dirs, key=lambda d: d.stat().st_mtime)
    md_path = latest_dir / "full.md"
    if not md_path.exists():
        print(f"❌ full.md 不存在: {md_path}")
        return []

    print(f"   从本地读取: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    docs = split_markdown(markdown_text)
    docs = clean_docs(docs)
    for doc in docs:
        doc.metadata["source"] = str(md_path)
    return docs


def embedding_demo():
    # ============ 1. 加载文档 ============
    print("1. 正在加载 lesson07 的 final_docs...")
    final_docs = load_final_docs_from_local()
    if not final_docs:
        print("❌ 没有文档可向量化")
        return None
    print(f"   共 {len(final_docs)} 个文档块")

    # ============ 2. 检查模型文件 ============
    print(f"\n2. 正在检查 BGE 模型文件: {BGE_MODEL_PATH}")
    if not check_model_files(BGE_MODEL_PATH):
        print("\n   请先下载模型：")
        print(f"   huggingface-cli download BAAI/bge-base-zh-v1.5 "
              f"--local-dir {BGE_MODEL_PATH}")
        print("   或设置镜像：set HF_ENDPOINT=https://hf-mirror.com")
        return None

    # ============ 3. 初始化模型 ============
    print(f"\n3. 正在加载 BGE 模型（首次加载约 5-10 秒）...")
    embed_model = HuggingFaceEmbeddings(
        model_name=str(BGE_MODEL_PATH),
        model_kwargs={"device": "cpu"},                # 有 GPU 可改成 "cuda"
        encode_kwargs={
            "normalize_embeddings": True,              # BGE 推荐：L2 归一化
            "batch_size": 32,                          # 批量编码，节省内存
        },
    )

    # ============ 4. 单文本测试 ============
    print("\n4. 单文本嵌入测试...")
    query = "中国科学院国家天文台"
    query_result = embed_model.embed_query(query)
    print(f"   查询: {query}")
    print(f"   向量维度: {len(query_result)}")
    print(f"   前 5 维: {[round(v, 4) for v in query_result[:5]]}")

    # ============ 5. 批量向量化所有文档块 ============
    print(f"\n5. 正在批量向量化 {len(final_docs)} 个文档块...")
    texts = [doc.page_content for doc in final_docs]
    vectors = embed_model.embed_documents(texts)

    print(f"   向量总数: {len(vectors)}")
    print(f"   每个向量维度: {len(vectors[0])}")

    # ============ 6. 抽样验证 ============
    print("\n6. 抽样验证（前 3 个块）...")
    for i in range(min(3, len(final_docs))):
        preview = final_docs[i].page_content[:40].replace("\n", " ")
        print(f"   块 {i + 1} (长度 {len(final_docs[i].page_content)}): "
              f"向量前 3 维 = {[round(v, 4) for v in vectors[i][:3]]}")
        print(f"      内容预览: {preview}...")

    # ============ 7. 相似度快速验证（可选）============
    print("\n7. 相似度快速验证...")
    query_vec = np.array(query_result)
    vec_matrix = np.array(vectors)
    # 已 L2 归一化，点积即余弦相似度
    sims = vec_matrix @ query_vec
    top3_idx = np.argsort(sims)[::-1][:3]

    print(f"   查询「{query}」最相似的 3 个块：")
    for rank, idx in enumerate(top3_idx, 1):
        preview = final_docs[idx].page_content[:60].replace("\n", " ")
        print(f"   {rank}. 相似度={sims[idx]:.4f} | {preview}...")

    print("\n✅ 向量化完成！")
    return {
        "model": embed_model,
        "docs": final_docs,
        "vectors": vectors,
    }


if __name__ == '__main__':
    embedding_demo()