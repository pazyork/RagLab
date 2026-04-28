"""Leaderboard component for RagLab."""

from nicegui import ui


_MODEL_COLORS = [
    "#4C78A8", "#E45756", "#F58518", "#72B7B2", "#54A24B",
    "#EECA3B", "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC",
]


def render_leaderboard(results: list[dict], models: list[str],
                       top_k: int = 10) -> None:
    """Render a scoring leaderboard to the current NiceGUI page.

    Args:
        results: List of {model: str, scores: [{index, score, text}]}.
        models: List of model names to display.
        top_k: Number of top results per model.
    """
    if not results:
        ui.label("No results to display").classes("text-gray-500")
        return

    # Build a unified table: Rank | Chunk | model1_score | model2_score | ...
    max_len = max(len(r["scores"]) for r in results)
    rows = []
    for rank in range(min(top_k, max_len)):
        row = {"rank": rank + 1, "chunk": ""}
        for r in results:
            model = r["model"]
            if rank < len(r["scores"]):
                s = r["scores"][rank]
                if rank == 0:
                    row["chunk"] = s["text"][:50] + ("..." if len(s["text"]) > 50 else "")
                row[model] = f"{s['score']:.4f}"
            else:
                row[model] = "-"
        rows.append(row)

    columns = [
        {"name": "rank", "label": "#", "field": "rank", "align": "center",
         "style": "width: 40px"},
        {"name": "chunk", "label": "Chunk", "field": "chunk", "align": "left"},
    ]
    for model in models:
        columns.append({
            "name": model, "label": model, "field": model,
            "align": "center",
        })

    ui.table(columns=columns, rows=rows, row_key="rank").classes("w-full")
