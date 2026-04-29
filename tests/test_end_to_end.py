#!/usr/bin/env python3
"""RagLab 端到端测试脚本：验证 OpenRouter 配置、Embedding 生成、评测全流程"""

import os
import tempfile
import numpy as np
from pathlib import Path

# 临时数据库文件，不影响用户现有配置
temp_db = tempfile.mktemp(suffix='.db', prefix='raglab_test_')
os.environ['RAGLAB_DB_PATH'] = temp_db

print("🧪 开始 RagLab 端到端测试...")
print(f"🗄️  临时数据库: {temp_db}")

# 导入模块
from raglab.storage.db import Database
from raglab.core.embedder import Embedder
from raglab.core.scorer import dense_score, sparse_score
from raglab.core.splitter import split_by_recursive

# --- 1. 初始化数据库 ---
db = Database(temp_db)
print("✅ 数据库初始化完成")

# --- 2. 配置 OpenRouter 供应商（替换为你的API Key）---
# 注意：测试时会自动读取环境变量 OPENROUTER_API_KEY，如果没有会提示
API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-xxx")
BASE_URL = "https://openrouter.ai/api/v1"

if API_KEY == "sk-or-xxx":
    print("\n⚠️  请设置环境变量 OPENROUTER_API_KEY 为你的 OpenRouter 密钥：")
    print("   export OPENROUTER_API_KEY=sk-or-xxx")
    print("   然后重新运行测试脚本")
    os.unlink(temp_db)
    exit(1)

# 添加供应商
provider_id = db.add_provider("openrouter", API_KEY, BASE_URL)
print(f"✅ 添加 OpenRouter 供应商成功，ID: {provider_id}")

# --- 3. 添加 Perplexity embedding 模型 ---
model_id = db.add_model(provider_id, "perplexity/pplx-embed-v1-4b")
print(f"✅ 添加 Perplexity 模型成功，ID: {model_id}")

# --- 4. 测试 Embedding 生成 ---
print("\n🧪 测试 Embedding 生成...")
embedder = Embedder()
embedder.configure("openrouter", API_KEY, "perplexity/pplx-embed-v1-4b", BASE_URL)

# 单文本测试
embedding = embedder.embed("测试文本")
print(f"✅ 单文本 Embedding 生成成功，维度: {len(embedding)}, 类型: {type(embedding)}")

# 批量文本测试
embeddings = embedder.embed(["文本1", "文本2", "文本3"])
print(f"✅ 批量 Embedding 生成成功，形状: {embeddings.shape}")

# 验证向量非零
assert np.all(embedding != 0), "Embedding 全零，生成失败"
assert embeddings.shape == (3, len(embedding)), "批量 Embedding 形状错误"
print("✅ Embedding 有效性验证通过")

# --- 5. 测试相似度计算 ---
print("\n🧪 测试相似度计算...")
chunks = [
    "人工智能是计算机科学的一个分支",
    "机器学习是人工智能的一个子领域",
    "深度学习是机器学习的一种方法",
    "自然语言处理是人工智能的重要应用",
    "Python是一种广泛使用的编程语言"
]

# 生成所有chunk的embedding
chunk_embeddings = embedder.embed(chunks)
print(f"✅ 批量 Chunk Embedding 生成成功，形状: {chunk_embeddings.shape}")

# 测试 dense_score
results = dense_score(
    query="人工智能的子领域有哪些",
    chunks=chunks,
    embedder=embedder,
    metric="cosine",
    top_k=3
)
print("✅ Dense 相似度计算完成，结果:")
for i, res in enumerate(results):
    print(f"  {i+1}. 得分: {res['score']:.4f} | 文本: {res['text'][:20]}...")

# 验证结果合理性
assert len(results) == 3, "Top-K 结果数量错误"
assert results[0]["score"] >= results[1]["score"] >= results[2]["score"], "结果未按得分排序"

# --- 6. 测试稀疏算法 ---
print("\n🧪 测试稀疏算法（BM25/TF-IDF）...")
# BM25
bm25_results = sparse_score(
    query="人工智能的子领域有哪些",
    chunks=chunks,
    algorithm="bm25",
    top_k=3
)
print("✅ BM25 计算完成，结果:")
for i, res in enumerate(bm25_results):
    print(f"  {i+1}. 得分: {res['score']:.4f} | 文本: {res['text'][:20]}...")

# TF-IDF
tfidf_results = sparse_score(
    query="人工智能的子领域有哪些",
    chunks=chunks,
    algorithm="tfidf",
    top_k=3
)
print("✅ TF-IDF 计算完成，结果:")
for i, res in enumerate(tfidf_results):
    print(f"  {i+1}. 得分: {res['score']:.4f} | 文本: {res['text'][:20]}...")

# --- 7. 测试文本切块 ---
print("\n🧪 测试文本切块...")
long_text = """
人工智能（Artificial Intelligence，简称AI）是指由人制造出来的机器所表现出来的智能，
通常是指通过普通计算机程序来呈现人类智能的技术。该领域的研究包括机器人、语言识别、
图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，
应用领域也不断扩大，可以设想，未来人工智能带来的科技产品，将会是人类智慧的“容器”。
人工智能可以对人的意识、思维的信息过程的模拟。人工智能不是人的智能，但能像人那样思考、
也可能超过人的智能。
"""
chunks = split_by_recursive(long_text, chunk_size=100, chunk_overlap=20)
print(f"✅ 文本切块完成，共 {len(chunks)} 块")
for i, chunk in enumerate(chunks[:3]):
    print(f"  块 {i+1}: {chunk.strip()[:50]}...")

# --- 测试完成 ---
print("\n🎉 所有测试通过！RagLab 全流程功能正常。")
print(f"🗑️  清理临时数据库: {temp_db}")
os.unlink(temp_db)

print("\n📝 使用说明：")
print("1. 在 RagLab 设置页添加供应商：")
print(f"   - 名称: openrouter")
print(f"   - API Key: {API_KEY[:10]}...")
print(f"   - Base URL: {BASE_URL}")
print("2. 添加模型：perplexity/pplx-embed-v1-4b")
print("3. 即可在评测页使用该模型进行 Embedding 相似度评测")
