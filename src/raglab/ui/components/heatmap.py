"""Similarity heatmap component for RagLab."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nicegui import ui


def render_heatmap(matrix: list[list[float]], labels: list[str],
                   title: str = "Similarity Matrix") -> None:
    """Render a similarity heatmap to the current NiceGUI page.

    Args:
        matrix: 2D list of similarity values [0, 1].
        labels: Chunk labels (truncated to 20 chars).
        title: Chart title.
    """
    n = len(labels)
    short_labels = [l[:20] + "..." if len(l) > 20 else l for l in labels]

    fig, ax = plt.subplots(figsize=(max(6, n * 0.5), max(5, n * 0.45)))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label="similarity")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(short_labels, fontsize=7)
    ax.set_title(title, fontsize=12)

    # Annotate cells with values if matrix is small enough
    if n <= 10:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{matrix[i][j]:.2f}",
                        ha="center", va="center", fontsize=7,
                        color="white" if matrix[i][j] > 0.6 else "black")

    plt.tight_layout()
    ui.pyplot(fig)
    plt.close(fig)
