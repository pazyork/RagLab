"""Test cases for the scorer module."""

import numpy as np
import pytest
from typing import List

from raglab.core.scorer import dense_score, bm25_score, tfidf_score, sparse_score
from raglab.core.embedder import Embedder


class FakeEmbedder(Embedder):
    """Fake embedder that returns deterministic random vectors for testing."""

    def __init__(self, vector_dim: int = 128, seed: int = 42):
        super().__init__()
        self.rng = np.random.RandomState(seed)
        self.vector_dim = vector_dim

    def embed(self, text: str | List[str]) -> np.ndarray:
        """Generate deterministic random embeddings based on text hash."""
        if isinstance(text, str):
            # Generate a single vector based on text hash
            hash_val = hash(text) % (2**32)
            rng = np.random.RandomState(hash_val)
            return rng.randn(self.vector_dim).astype(np.float32)
        else:
            # Generate multiple vectors
            embeddings = []
            for t in text:
                hash_val = hash(t) % (2**32)
                rng = np.random.RandomState(hash_val)
                embeddings.append(rng.randn(self.vector_dim).astype(np.float32))
            return np.array(embeddings)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Alias for embed with list input."""
        return self.embed(texts)


def test_dense_score_basic():
    """Test basic dense scoring functionality."""
    embedder = FakeEmbedder()
    query = "test query"
    chunks = [
        "first chunk about cats",
        "second chunk about dogs",
        "third chunk about birds",
        "fourth chunk about fish",
        "fifth chunk about rabbits"
    ]

    # Test with cosine similarity
    results = dense_score(query, chunks, embedder, "cosine", top_k=3)

    # Check return structure
    assert len(results) == 3
    for result in results:
        assert "index" in result
        assert "score" in result
        assert "text" in result
        assert isinstance(result["index"], int)
        assert isinstance(result["score"], float)
        assert isinstance(result["text"], str)
        assert 0 <= result["score"] <= 1  # cosine similarity is clipped to [0,1]

    # Check scores are sorted in descending order
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    # Check indices are valid
    indices = [r["index"] for r in results]
    assert all(0 <= idx < len(chunks) for idx in indices)
    assert len(set(indices)) == 3  # all indices are unique


def test_dense_score_different_metrics():
    """Test dense score with different metric types."""
    embedder = FakeEmbedder()
    query = "test query"
    chunks = ["chunk1", "chunk2", "chunk3"]

    # Test euclidean distance (lower is better, but we return sorted descending)
    euclidean_results = dense_score(query, chunks, embedder, "euclidean", top_k=3)
    assert len(euclidean_results) == 3
    euclidean_scores = [r["score"] for r in euclidean_results]
    assert euclidean_scores == sorted(euclidean_scores, reverse=True)

    # Test dot product
    dot_results = dense_score(query, chunks, embedder, "dot", top_k=3)
    assert len(dot_results) == 3
    dot_scores = [r["score"] for r in dot_results]
    assert dot_scores == sorted(dot_scores, reverse=True)

    # Test manhattan distance
    manhattan_results = dense_score(query, chunks, embedder, "manhattan", top_k=3)
    assert len(manhattan_results) == 3
    manhattan_scores = [r["score"] for r in manhattan_results]
    assert manhattan_scores == sorted(manhattan_scores, reverse=True)


def test_dense_score_empty_chunks():
    """Test dense score with empty chunks list."""
    embedder = FakeEmbedder()
    results = dense_score("query", [], embedder, "cosine", top_k=10)
    assert results == []


def test_bm25_score_basic():
    """Test basic BM25 scoring functionality."""
    query = "apple banana"
    chunks = [
        "apple banana cherry",
        "apple apple apple",
        "banana banana",
        "cherry date",
        "apple banana apple banana"
    ]

    results = bm25_score(query, chunks, top_k=3)

    # Check structure
    assert len(results) == 3
    for result in results:
        assert "index" in result
        assert "score" in result
        assert "text" in result
        assert result["score"] >= 0

    # Check scores are sorted descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

    # The chunk with most query terms should have highest score
    assert results[0]["text"] == "apple banana apple banana"


def test_bm25_score_chinese():
    """Test BM25 with Chinese text (character-level tokenization)."""
    query = "苹果香蕉"
    chunks = [
        "苹果香蕉樱桃",
        "苹果苹果苹果",
        "香蕉香蕉",
        "樱桃枣",
        "苹果香蕉苹果香蕉"
    ]

    results = bm25_score(query, chunks, top_k=3)

    assert len(results) == 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["text"] == "苹果香蕉苹果香蕉"


def test_bm25_score_custom_parameters():
    """Test BM25 with custom k1 and b parameters."""
    query = "test query"
    chunks = [
        "test query chunk",
        "another test chunk",
        "query only chunk",
        "unrelated chunk"
    ]

    results_default = bm25_score(query, chunks, top_k=4)
    results_custom = bm25_score(query, chunks, top_k=4, k1=2.0, b=0.5)

    # Results should be different with different parameters
    assert results_default != results_custom
    assert len(results_custom) == 4


def test_bm25_score_empty_chunks():
    """Test BM25 with empty chunks list."""
    results = bm25_score("query", [], top_k=10)
    assert results == []


def test_tfidf_score_basic():
    """Test basic TF-IDF scoring functionality."""
    query = "apple banana"
    chunks = [
        "apple banana cherry",
        "apple apple apple",
        "banana banana",
        "cherry date",
        "apple banana apple banana"
    ]

    results = tfidf_score(query, chunks, top_k=3)

    # Check structure
    assert len(results) == 3
    for result in results:
        assert "index" in result
        assert "score" in result
        assert "text" in result
        assert result["score"] >= 0

    # Check scores are sorted descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_tfidf_score_chinese():
    """Test TF-IDF with Chinese text (character-level tokenization)."""
    query = "苹果香蕉"
    chunks = [
        "苹果香蕉樱桃",
        "苹果苹果苹果",
        "香蕉香蕉",
        "樱桃枣",
        "苹果香蕉苹果香蕉"
    ]

    results = tfidf_score(query, chunks, top_k=3)

    assert len(results) == 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_tfidf_score_empty_chunks():
    """Test TF-IDF with empty chunks list."""
    results = tfidf_score("query", [], top_k=10)
    assert results == []


def test_sparse_score_bm25():
    """Test sparse_score routes to BM25 correctly."""
    query = "test query"
    chunks = ["test chunk 1", "test chunk 2", "other chunk"]

    results = sparse_score(query, chunks, "bm25", top_k=2)

    assert len(results) == 2
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_sparse_score_tfidf():
    """Test sparse_score routes to TF-IDF correctly."""
    query = "test query"
    chunks = ["test chunk 1", "test chunk 2", "other chunk"]

    results = sparse_score(query, chunks, "tfidf", top_k=2)

    assert len(results) == 2
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_sparse_score_invalid_algorithm():
    """Test sparse_score raises ValueError for invalid algorithm."""
    with pytest.raises(ValueError, match="Unknown algorithm"):
        sparse_score("query", ["chunk"], "invalid_algo", top_k=10)


def test_sparse_score_empty_chunks():
    """Test sparse_score with empty chunks list."""
    results_bm25 = sparse_score("query", [], "bm25", top_k=10)
    assert results_bm25 == []

    results_tfidf = sparse_score("query", [], "tfidf", top_k=10)
    assert results_tfidf == []


def test_score_top_k_larger_than_chunks():
    """Test when top_k is larger than the number of chunks."""
    query = "test"
    chunks = ["chunk1", "chunk2"]

    # BM25
    bm25_results = bm25_score(query, chunks, top_k=10)
    assert len(bm25_results) == 2

    # TF-IDF
    tfidf_results = tfidf_score(query, chunks, top_k=10)
    assert len(tfidf_results) == 2

    # Dense
    embedder = FakeEmbedder()
    dense_results = dense_score(query, chunks, embedder, "cosine", top_k=10)
    assert len(dense_results) == 2

    # Sparse
    sparse_results = sparse_score(query, chunks, "bm25", top_k=10)
    assert len(sparse_results) == 2


def test_tokenize_mixed_text():
    """Test tokenization handles mixed Chinese and English text."""
    from raglab.core.scorer import _tokenize

    # Test mixed text
    text = "苹果apple香蕉banana"
    tokens = _tokenize(text)
    # Should split Chinese characters individually, English words by space
    expected = ["苹", "果", "apple", "香", "蕉", "banana"]
    assert tokens == expected

    # Test pure English
    text = "hello world test"
    tokens = _tokenize(text)
    assert tokens == ["hello", "world", "test"]

    # Test pure Chinese
    text = "我爱人工智能"
    tokens = _tokenize(text)
    assert tokens == ["我", "爱", "人", "工", "智", "能"]

    # Test with punctuation
    text = "你好, world! 测试。"
    tokens = _tokenize(text)
    assert tokens == ["你", "好", ",", "world", "!", "测", "试", "。"]