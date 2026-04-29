#!/usr/bin/env python3
"""RagLab 本地逻辑端到端测试（不依赖外部 API）"""

import os
import tempfile
import numpy as np

# 临时数据库
temp_db = tempfile.mktemp(suffix='.db', prefix='raglab_local_')

print("🧪 RagLab 本地逻辑端到端测试（不依赖外部 API）")
print(f"🗄️  临时数据库: {temp_db}")

from raglab.storage.db import Database
from raglab.core.splitter import split_lines, split_by_char, split_by_recursive
from raglab.core.metrics import get_metric
from raglab.core.scorer import sparse_score
from raglab.core.embedder import Embedder

# --- 1. 数据库 CRUD 测试 ---
print("\n--- 1. 数据库 CRUD 测试 ---")
db = Database(temp_db)

# Provider CRUD
pid = db.add_provider("test_provider", "test_key", "http://test.com")
providers = db.list_providers()
assert len(providers) == 1, f"Provider 数量错误: {len(providers)}"
assert providers[0][1] == "test_provider", f"Provider 名称错误: {providers[0][1]}"
print("✅ Provider CRUD 通过")

# Model CRUD
mid = db.add_model(pid, "test-model", "embedding")
models = db.list_models()
assert len(models) == 1, f"Model 数量错误: {len(models)}"
assert models[0][2] == "test-model", f"Model 名称错误: {models[0][2]}"
print("✅ Model CRUD 通过")

# Case CRUD
cid = db.add_case("test_case", "测试用例")
cases = db.list_cases()
assert len(cases) == 1, f"Case 数量错误: {len(cases)}"
print("✅ Case CRUD 通过")

# Chunk CRUD
test_chunks = ["第一块文本", "第二块文本", "第三块文本"]
db.add_chunks(cid, test_chunks)
chunks = db.get_chunks(cid)
assert len(chunks) == 3, f"Chunk 数量错误: {len(chunks)}"
assert chunks[0][3] == "第一块文本", f"Chunk 内容错误: {chunks[0][3]}"
print("✅ Chunk CRUD 通过")

# Config CRUD
db.set_config("chunk_size", 512)
db.set_config("overlap", 50)
db.set_config("metric", "cosine")
assert db.get_config("chunk_size") == 512, "Config 读取错误"
assert db.get_config("overlap") == 50, "Config 读取错误"
assert db.get_config("metric") == "cosine", "Config 读取错误"
print("✅ Config CRUD 通过")

# Run & Score
rid = db.add_run(cid, "test_run", "test-model", "cosine")
scores = [(0, 0.9, 1), (1, 0.7, 2), (2, 0.5, 3)]
db.add_scores(rid, scores)
db.update_run_status(rid, "completed")
runs = db.list_runs()
assert len(runs) == 1, f"Run 数量错误: {len(runs)}"
assert runs[0][6] == "completed", f"Run 状态错误: {runs[0][6]}"
print("✅ Run & Score CRUD 通过")

# --- 2. 文本切块测试 ---
print("\n--- 2. 文本切块测试 ---")
test_text = """第一行内容。
第二行内容。
第三行内容。

人工智能是计算机科学的一个分支，研究如何使计算机能够执行通常需要人类智能才能完成的任务。机器学习是人工智能的一个子领域。深度学习是机器学习的一种方法。"""

# 按行切分
line_chunks = split_lines(test_text)
assert len(line_chunks) == 4, f"按行切分数量错误: {len(line_chunks)}"
print(f"✅ 按行切分: {len(line_chunks)} 块")

# 固定字符切分
char_chunks = split_by_char(test_text, chunk_size=50, overlap=10)
assert len(char_chunks) > 0, "固定字符切分失败"
print(f"✅ 固定字符切分: {len(char_chunks)} 块")

# 递归切分
rec_chunks = split_by_recursive(test_text, chunk_size=100, chunk_overlap=20)
assert len(rec_chunks) > 0, "递归切分失败"
print(f"✅ 递归切分: {len(rec_chunks)} 块")

# --- 3. 相似度度量测试 ---
print("\n--- 3. 相似度度量测试 ---")
vec1 = np.array([1.0, 0.0, 0.0])
vec2 = np.array([0.0, 1.0, 0.0])
vec3 = np.array([0.707, 0.707, 0.0])

# Cosine
cos_fn = get_metric("cosine")
cos_sim = cos_fn(vec1, vec3)
assert 0.0 <= cos_sim <= 1.0, f"余弦相似度越界: {cos_sim}"
assert abs(cos_sim - 0.707) < 0.01, f"余弦相似度计算错误: {cos_sim}"
print(f"✅ Cosine: {cos_sim:.4f}")

# Euclidean
euc_fn = get_metric("euclidean")
euc_dist = euc_fn(vec1, vec2)
assert abs(euc_dist - 1.4142135623730951) < 0.0001, f"欧氏距离计算错误: {euc_dist}"
print(f"✅ Euclidean: {euc_dist:.4f}")

# Dot
dot_fn = get_metric("dot")
dot = dot_fn(vec1, vec3)
assert abs(dot - 0.707) < 0.01, f"点积计算错误: {dot}"
print(f"✅ Dot: {dot:.4f}")

# Manhattan
man_fn = get_metric("manhattan")
man = man_fn(vec1, vec2)
assert man == 2.0, f"曼哈顿距离计算错误: {man}"
print(f"✅ Manhattan: {man:.4f}")

# --- 4. 稀疏算法测试 ---
print("\n--- 4. 稀疏算法测试 ---")
chunks = [
    "人工智能是计算机科学的一个分支",
    "机器学习是人工智能的一个子领域",
    "深度学习是机器学习的一种方法",
    "自然语言处理是人工智能的重要应用",
    "Python是一种广泛使用的编程语言"
]
query = "人工智能的子领域有哪些"

# BM25
bm25_results = sparse_score(query, chunks, "bm25", top_k=3)
assert len(bm25_results) == 3, f"BM25 Top-K 结果数量错误: {len(bm25_results)}"
assert bm25_results[0]["score"] >= bm25_results[1]["score"], "BM25 结果未排序"
print("✅ BM25 计算通过")
for i, r in enumerate(bm25_results):
    print(f"   {i+1}. 得分: {r['score']:.4f} | 文本: {r['text'][:30]}...")

# TF-IDF
tfidf_results = sparse_score(query, chunks, "tfidf", top_k=3)
assert len(tfidf_results) == 3, f"TF-IDF Top-K 结果数量错误: {len(tfidf_results)}"
assert tfidf_results[0]["score"] >= tfidf_results[1]["score"], "TF-IDF 结果未排序"
print("✅ TF-IDF 计算通过")
for i, r in enumerate(tfidf_results):
    print(f"   {i+1}. 得分: {r['score']:.4f} | 文本: {r['text'][:30]}...")

# --- 5. Dense Score 模拟测试 ---
print("\n--- 5. Dense Score 模拟测试（Mock Embedding）---")

class MockEmbedder:
    """模拟 Embedder，返回预定义向量"""
    def embed(self, text):
        # 根据文本内容返回不同向量
        vectors = {
            "人工智能": np.array([0.9, 0.8, 0.1]),
            "机器学习": np.array([0.8, 0.9, 0.1]),
            "深度学习": np.array([0.7, 0.85, 0.1]),
            "Python": np.array([0.1, 0.2, 0.9]),
        }
        for key, vec in vectors.items():
            if key in text:
                return vec
        return np.array([0.5, 0.5, 0.5])

    def embed_batch(self, texts):
        return np.array([self.embed(t) for t in texts])

mock_emb = MockEmbedder()
from raglab.core.scorer import dense_score
dense_results = dense_score(
    query="人工智能",
    chunks=chunks,
    embedder=mock_emb,
    metric="cosine",
    top_k=3
)
assert len(dense_results) == 3, f"Dense Top-K 结果数量错误: {len(dense_results)}"
assert dense_results[0]["score"] >= dense_results[1]["score"], "Dense 结果未排序"
print("✅ Dense Score 计算通过")
for i, r in enumerate(dense_results):
    print(f"   {i+1}. 得分: {r['score']:.4f} | 文本: {r['text'][:30]}...")

# --- 6. 验证 OpenRouter 模型名处理 ---
print("\n--- 6. OpenRouter 模型名处理验证 ---")
emb = Embedder()
emb.configure("openrouter", "test-key", "perplexity/pplx-embed-v1-4b", "https://openrouter.ai/api/v1")
assert emb.model == "perplexity/pplx-embed-v1-4b", f"模型名错误: {emb.model}"
assert emb.provider == "openrouter", f"提供商错误: {emb.provider}"
print("✅ OpenRouter 配置正确")

# --- 清理 ---
print(f"\n🗑️  清理临时数据库: {temp_db}")
os.unlink(temp_db)

print("\n🎉 所有本地逻辑测试通过！RagLab 核心功能运行正常。")
print("\n⚠️  注意：OpenRouter API Key 当前额度已用完，需要到 https://openrouter.ai/settings/keys")
print("   充值或更换 Key 后才能进行真实的 Embedding 模型评测。")
