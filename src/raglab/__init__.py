__version__ = "0.1.0"

from .core import (
    # Metrics
    cosine_similarity,
    euclidean_distance,
    dot_product,
    manhattan_distance,
    get_metric,
    # Splitters
    split_lines,
    split_by_char,
    split_by_recursive,
    # Embedding
    Embedder
)
from .logging_config import setup_logging, get_logger

__all__ = [
    "cosine_similarity",
    "euclidean_distance",
    "dot_product",
    "manhattan_distance",
    "get_metric",
    "split_lines",
    "split_by_char",
    "split_by_recursive",
    "Embedder",
    "setup_logging",
    "get_logger"
]

