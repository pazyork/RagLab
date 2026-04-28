"""
Vector similarity and distance metrics module.

This module provides pure functions for calculating various similarity and distance
metrics between vectors, commonly used in information retrieval and machine learning.
"""

import numpy as np
from typing import Callable


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate the cosine similarity between two vectors.

    Cosine similarity is the cosine of the angle between two vectors in an
    inner product space, ranging from -1 to 1. This implementation clips the
    result to [0, 1] as per the requirement.

    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)

    Returns:
        float: Cosine similarity in [0, 1]. Returns 0 if either vector is zero.
    """
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    dot = np.dot(a, b)
    similarity = dot / (norm_a * norm_b)

    # Clip to [0, 1] range as required
    return float(np.clip(similarity, 0.0, 1.0))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate the Euclidean distance between two vectors.

    Euclidean distance is the L2 norm of the difference between two vectors,
    representing the straight-line distance between them in Euclidean space.

    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)

    Returns:
        float: Euclidean distance >= 0
    """
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()

    return float(np.linalg.norm(a - b))


def dot_product(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate the dot product (inner product) of two vectors.

    The dot product is the sum of the products of corresponding elements
    of the two vectors.

    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)

    Returns:
        float: Dot product (can be any real number)
    """
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()

    return float(np.dot(a, b))


def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate the Manhattan distance between two vectors.

    Manhattan distance (L1 distance) is the sum of the absolute differences
    of their corresponding coordinates.

    Args:
        a: First vector (numpy array)
        b: Second vector (numpy array)

    Returns:
        float: Manhattan distance >= 0
    """
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()

    return float(np.sum(np.abs(a - b)))


def get_metric(name: str) -> Callable:
    """
    Get a metric function by name.

    Args:
        name: Name of the metric to retrieve.
              Valid options: "cosine", "euclidean", "dot", "manhattan"

    Returns:
        Callable: The corresponding metric function

    Raises:
        ValueError: If the metric name is not recognized
    """
    metrics = {
        "cosine": cosine_similarity,
        "euclidean": euclidean_distance,
        "dot": dot_product,
        "manhattan": manhattan_distance
    }

    if name not in metrics:
        raise ValueError(f"Unknown metric: {name}. Valid metrics: {list(metrics.keys())}")

    return metrics[name]
