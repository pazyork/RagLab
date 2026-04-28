import numpy as np
import pytest
from raglab.core.metrics import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    manhattan_distance,
    get_metric
)


def test_cosine_similarity():
    # Test identical vectors
    a = np.array([1, 2, 3])
    b = np.array([1, 2, 3])
    assert cosine_similarity(a, b) == pytest.approx(1.0)

    # Test orthogonal vectors
    a = np.array([1, 0])
    b = np.array([0, 1])
    assert cosine_similarity(a, b) == pytest.approx(0.0)

    # Test known value
    a = np.array([1, 0])
    b = np.array([1, 1])
    assert cosine_similarity(a, b) == pytest.approx(1 / np.sqrt(2))

    # Test zero vectors
    a = np.array([0, 0, 0])
    b = np.array([1, 2, 3])
    assert cosine_similarity(a, b) == pytest.approx(0.0)

    a = np.array([1, 2, 3])
    b = np.array([0, 0, 0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)

    a = np.array([0, 0, 0])
    b = np.array([0, 0, 0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)

    # Test negative values (should be clipped to 0 per requirement)
    a = np.array([-1, -2])
    b = np.array([1, 2])
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_euclidean_distance():
    # Test identical vectors
    a = np.array([1, 2, 3])
    b = np.array([1, 2, 3])
    assert euclidean_distance(a, b) == pytest.approx(0.0)

    # Test known value
    a = np.array([0, 0])
    b = np.array([3, 4])
    assert euclidean_distance(a, b) == pytest.approx(5.0)

    # Test negative values
    a = np.array([-1, -2])
    b = np.array([1, 2])
    assert euclidean_distance(a, b) == pytest.approx(np.sqrt((2)**2 + (4)**2))

    # Test zero vectors
    a = np.array([0, 0, 0])
    b = np.array([0, 0, 0])
    assert euclidean_distance(a, b) == pytest.approx(0.0)


def test_dot_product():
    # Test known value
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])
    assert dot_product(a, b) == pytest.approx(1*4 + 2*5 + 3*6)  # 32

    # Test orthogonal vectors
    a = np.array([1, 0])
    b = np.array([0, 1])
    assert dot_product(a, b) == pytest.approx(0.0)

    # Test negative values
    a = np.array([-1, 2])
    b = np.array([3, -4])
    assert dot_product(a, b) == pytest.approx((-1)*3 + 2*(-4))  # -11

    # Test zero vectors
    a = np.array([0, 0, 0])
    b = np.array([1, 2, 3])
    assert dot_product(a, b) == pytest.approx(0.0)


def test_manhattan_distance():
    # Test identical vectors
    a = np.array([1, 2, 3])
    b = np.array([1, 2, 3])
    assert manhattan_distance(a, b) == pytest.approx(0.0)

    # Test known value
    a = np.array([0, 0])
    b = np.array([3, 4])
    assert manhattan_distance(a, b) == pytest.approx(3 + 4)  # 7

    # Test negative values
    a = np.array([-1, -2])
    b = np.array([1, 2])
    assert manhattan_distance(a, b) == pytest.approx(2 + 4)  # 6

    # Test zero vectors
    a = np.array([0, 0, 0])
    b = np.array([1, 2, 3])
    assert manhattan_distance(a, b) == pytest.approx(1 + 2 + 3)  # 6


def test_get_metric():
    # Test valid metric names
    assert get_metric("cosine") is cosine_similarity
    assert get_metric("euclidean") is euclidean_distance
    assert get_metric("dot") is dot_product
    assert get_metric("manhattan") is manhattan_distance

    # Test invalid metric name
    with pytest.raises(ValueError, match="Unknown metric"):
        get_metric("invalid_metric")


def test_metric_accepts_different_shapes():
    # Test 1D arrays
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])

    assert cosine_similarity(a, b) == pytest.approx(0.974631846)
    assert euclidean_distance(a, b) == pytest.approx(5.196152423)
    assert dot_product(a, b) == pytest.approx(32)
    assert manhattan_distance(a, b) == pytest.approx(9)

    # Test 2D arrays (should flatten)
    a_2d = np.array([[1, 2, 3]])
    b_2d = np.array([[4, 5, 6]])

    assert cosine_similarity(a_2d, b_2d) == pytest.approx(0.974631846)
    assert euclidean_distance(a_2d, b_2d) == pytest.approx(5.196152423)
    assert dot_product(a_2d, b_2d) == pytest.approx(32)
    assert manhattan_distance(a_2d, b_2d) == pytest.approx(9)
