"""Scoring engine for dense and sparse retrieval.

This module provides functions for scoring text chunks against queries using
both dense embedding-based methods and sparse statistical methods (BM25, TF-IDF).
"""

import logging
import math
import re
from typing import List, Dict, Callable
import numpy as np

from .metrics import get_metric
from .embedder import Embedder

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Tokenize text with handling for Chinese and English.

    Chinese characters are split individually, while English words are split by whitespace.
    Punctuation is preserved as separate tokens.

    Args:
        text: Input text to tokenize

    Returns:
        List of tokens
    """
    # Pattern to match Chinese characters, English words, and punctuation
    pattern = re.compile(
        r'([\u4e00-\u9fff])|'  # Chinese characters
        r'([a-zA-Z]+)|'  # English words
        r'([^\u4e00-\u9ffa-zA-Z\s])'  # Punctuation and other symbols
    )

    tokens = []
    for match in pattern.finditer(text):
        if match.group(1):  # Chinese character
            tokens.append(match.group(1))
        elif match.group(2):  # English word
            tokens.append(match.group(2))
        elif match.group(3):  # Punctuation
            tokens.append(match.group(3))

    # If no matches (e.g., only whitespace), fall back to splitting by whitespace
    if not tokens:
        return text.split()

    return tokens


def dense_score(
    query: str,
    chunks: List[str],
    embedder: Embedder,
    metric: str,
    top_k: int
) -> List[Dict]:
    """Score chunks using dense embedding similarity.

    Args:
        query: Query string
        chunks: List of text chunks to score
        embedder: Embedder instance for generating embeddings
        metric: Name of the similarity metric to use (from core.metrics)
        top_k: Number of top results to return

    Returns:
        List of dictionaries with keys "index", "score", "text", sorted by score descending
    """
    logger.info(f"Dense scoring: query='{query[:50]}...', chunks={len(chunks)}, metric={metric}, top_k={top_k}")

    if not chunks:
        return []

    # Get metric function
    metric_fn = get_metric(metric)

    # Embed query and chunks
    logger.debug("Embedding query...")
    query_embedding = embedder.embed(query)
    logger.debug(f"Query embedding shape: {query_embedding.shape}")

    logger.debug(f"Embedding {len(chunks)} chunks...")
    chunk_embeddings = embedder.embed_batch(chunks)
    logger.debug(f"Chunk embeddings shape: {chunk_embeddings.shape}")

    # Calculate scores for all chunks
    results = []
    for idx, (chunk, chunk_embedding) in enumerate(zip(chunks, chunk_embeddings)):
        score = metric_fn(query_embedding, chunk_embedding)
        results.append({
            "index": idx,
            "score": score,
            "text": chunk
        })

    # Sort by score descending and take top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"Dense scoring completed, returning top {top_k} results")
    return results[:top_k]


def bm25_score(
    query: str,
    chunks: List[str],
    top_k: int = 10,
    k1: float = 1.5,
    b: float = 0.75
) -> List[Dict]:
    """Score chunks using BM25 algorithm.

    Args:
        query: Query string
        chunks: List of text chunks to score
        top_k: Number of top results to return, default 10
        k1: BM25 k1 parameter, controls term frequency saturation, default 1.5
        b: BM25 b parameter, controls document length normalization, default 0.75

    Returns:
        List of dictionaries with keys "index", "score", "text", sorted by score descending
    """
    if not chunks:
        return []

    # Tokenize query and chunks
    query_tokens = _tokenize(query)
    chunk_tokens = [_tokenize(chunk) for chunk in chunks]

    # Calculate average document length
    avg_doc_len = np.mean([len(tokens) for tokens in chunk_tokens])
    num_docs = len(chunks)

    # Calculate document frequency for each query term
    doc_freq = {}
    for term in query_tokens:
        df = sum(1 for tokens in chunk_tokens if term in tokens)
        doc_freq[term] = df

    # Calculate BM25 score for each chunk
    results = []
    for idx, (chunk, tokens) in enumerate(zip(chunks, chunk_tokens)):
        doc_len = len(tokens)
        score = 0.0

        for term in query_tokens:
            # Term frequency in current document
            tf = tokens.count(term)
            if tf == 0:
                continue

            # Document frequency
            df = doc_freq.get(term, 0)
            if df == 0:
                continue

            # IDF calculation (with smoothing to avoid division by zero)
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)

            # BM25 term score
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
            term_score = idf * (numerator / denominator)

            score += term_score

        results.append({
            "index": idx,
            "score": score,
            "text": chunk
        })

    # Sort by score descending and take top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def tfidf_score(
    query: str,
    chunks: List[str],
    top_k: int = 10
) -> List[Dict]:
    """Score chunks using TF-IDF algorithm.

    Args:
        query: Query string
        chunks: List of text chunks to score
        top_k: Number of top results to return, default 10

    Returns:
        List of dictionaries with keys "index", "score", "text", sorted by score descending
    """
    if not chunks:
        return []

    # Tokenize query and chunks
    query_tokens = _tokenize(query)
    chunk_tokens = [_tokenize(chunk) for chunk in chunks]

    num_docs = len(chunks)

    # Calculate document frequency for each query term
    doc_freq = {}
    for term in query_tokens:
        df = sum(1 for tokens in chunk_tokens if term in tokens)
        doc_freq[term] = df

    # Calculate TF-IDF score for each chunk
    results = []
    for idx, (chunk, tokens) in enumerate(zip(chunks, chunk_tokens)):
        doc_len = len(tokens)
        score = 0.0

        for term in query_tokens:
            # Term frequency in current document (normalized by document length)
            tf = tokens.count(term) / doc_len if doc_len > 0 else 0
            if tf == 0:
                continue

            # Document frequency
            df = doc_freq.get(term, 0)
            if df == 0:
                continue

            # IDF calculation
            idf = math.log(num_docs / df) + 1.0

            # TF-IDF term score
            term_score = tf * idf

            score += term_score

        results.append({
            "index": idx,
            "score": score,
            "text": chunk
        })

    # Sort by score descending and take top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def sparse_score(
    query: str,
    chunks: List[str],
    algorithm: str,
    top_k: int = 10
) -> List[Dict]:
    """Route sparse scoring requests to the appropriate algorithm.

    Args:
        query: Query string
        chunks: List of text chunks to score
        algorithm: Name of the sparse algorithm to use ("bm25" or "tfidf")
        top_k: Number of top results to return, default 10

    Returns:
        List of dictionaries with keys "index", "score", "text", sorted by score descending

    Raises:
        ValueError: If the algorithm is not recognized
    """
    logger.info(f"Sparse scoring: query='{query[:50]}...', chunks={len(chunks)}, algorithm={algorithm}, top_k={top_k}")

    if algorithm == "bm25":
        return bm25_score(query, chunks, top_k)
    elif algorithm == "tfidf":
        return tfidf_score(query, chunks, top_k)
    else:
        logger.error(f"Unknown algorithm: {algorithm}")
        raise ValueError(
            f"Unknown algorithm: {algorithm}. Valid algorithms: ['bm25', 'tfidf']"
        )


def _normalize_scores(results: List[Dict]) -> List[Dict]:
    """Min-max normalize scores to [0, 1] for hybrid combination."""
    if not results:
        return results
    scores = [r["score"] for r in results]
    min_s, max_s = min(scores), max(scores)
    span = max_s - min_s
    if span == 0:
        return [{**r, "score": 1.0 / len(results)} for r in results]
    return [{**r, "score": (r["score"] - min_s) / span} for r in results]


def hybrid_score(
    query: str,
    chunks: List[str],
    embedder: Embedder,
    metric: str,
    top_k: int,
    dense_weight: float = 0.5,
) -> List[Dict]:
    """Combine dense embedding similarity with BM25 using weighted fusion.

    Scores from each method are min-max normalized to [0, 1] before blending.

    Args:
        query: Query string
        chunks: List of text chunks to score
        embedder: Embedder instance
        metric: Similarity metric for dense scoring (e.g. "cosine")
        top_k: Number of top results to return
        dense_weight: Weight for dense scores (0 = pure BM25, 1 = pure dense)

    Returns:
        List of dicts with "index", "score", "text", sorted descending
    """
    logger.info(f"Hybrid scoring: query='{query[:50]}...', chunks={len(chunks)}, dense_weight={dense_weight}")

    dense_results = dense_score(query, chunks, embedder, metric, top_k=len(chunks))
    bm25_results = bm25_score(query, chunks, top_k=len(chunks))

    dense_norm = _normalize_scores(dense_results)
    bm25_norm = _normalize_scores(bm25_results)

    # Build lookup by index
    dense_map = {r["index"]: r["score"] for r in dense_norm}
    bm25_map = {r["index"]: r["score"] for r in bm25_norm}

    combined = []
    for idx, chunk in enumerate(chunks):
        d = dense_map.get(idx, 0.0)
        b = bm25_map.get(idx, 0.0)
        score = dense_weight * d + (1 - dense_weight) * b
        combined.append({"index": idx, "score": score, "text": chunk})

    combined.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"Hybrid scoring completed, returning top {top_k}")
    return combined[:top_k]