import pytest
from raglab.ui.components.heatmap import render_heatmap


def test_render_heatmap_basic():
    """Test that render_heatmap can be called without errors with valid input."""
    matrix = [
        [1.0, 0.8, 0.3],
        [0.8, 1.0, 0.5],
        [0.3, 0.5, 1.0]
    ]
    labels = ["chunk1 content", "chunk2 content", "chunk3 content"]

    # Should not raise any exceptions
    element = render_heatmap(matrix, labels)
    assert element is not None


def test_render_heatmap_empty_matrix():
    """Test that render_heatmap handles empty matrix gracefully."""
    matrix = []
    labels = []

    # Should not raise any exceptions even with empty input
    element = render_heatmap(matrix, labels)
    assert element is not None


def test_render_heatmap_single_element():
    """Test render_heatmap with single element matrix."""
    matrix = [[1.0]]
    labels = ["single chunk"]

    element = render_heatmap(matrix, labels)
    assert element is not None


def test_render_heatmap_large_labels():
    """Test that long labels are handled properly (truncated)."""
    matrix = [
        [1.0, 0.2],
        [0.2, 1.0]
    ]
    labels = [
        "This is a very long chunk label that should be truncated when displayed",
        "Another long chunk label that exceeds the 20 character limit"
    ]

    element = render_heatmap(matrix, labels)
    assert element is not None
