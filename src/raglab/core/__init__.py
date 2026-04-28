"""Core modules for RagLab."""

from .metrics import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    manhattan_distance,
    get_metric
)
from .splitter import (
    split_lines,
    split_by_char,
    split_by_recursive
)
from .embedder import Embedder

__all__ = [
    "cosine_similarity",
    "euclidean_distance",
    "dot_product",
    "manhattan_distance",
    "get_metric",
    "split_lines",
    "split_by_char",
    "split_by_recursive",
    "Embedder"
]
