"""Playground page: Query vs Chunks and Chunk vs Chunk views."""

import asyncio
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nicegui import ui
from raglab.storage.db import Database
from raglab.core.embedder import Embedder
from raglab.core.scorer import dense_score, sparse_score
from raglab.core.metrics import get_metric
from raglab.core.splitter import split_by_recursive


def _db() -> Database:
    return Database()


def render_playground(page_state: dict) -> None:
    view = page_state.get("view", "query_vs_chunks")
    if view == "query_vs_chunks":
        _render_query_vs_chunks()
    else:
        _render_chunk_vs_chunk()


# ---------------------------------------------------------------------------
# Query vs Chunks
# ---------------------------------------------------------------------------

def _render_query_vs_chunks() -> None:
    state = {
        "chunks": [],
        "case_id": None,
        "adhoc_mode": True,
    }

    with ui.element("div").style(
        "display:grid;grid-template-columns:3fr 6fr 3fr;gap:16px;"
        "padding:16px;height:100%;overflow:hidden;"
    ):
        # ---- Left: Retrieval Configuration ----
        left = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with left:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;"
                "border-bottom:1px solid #2D2D2D;padding-bottom:12px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--primary);">Retrieval Configuration</span>')

            models = _db().list_models()
            providers = {p[0]: p[1] for p in _db().list_providers()}
            model_opts = {str(m[0]): f"{providers.get(m[1], '?')}/{m[2]}" for m in models}
            model_sel = ui.select(
                label="Embedding Model", options=model_opts, with_input=True
            ).props("outlined dense").classes("w-full")

            with ui.element("div").style("display:flex;flex-direction:column;gap:4px;"):
                ui.html('<span class="rl-label">Retrieval Strategy</span>')
                strategy_state = {"value": "dense"}
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;"
                    "border:1px solid #2D2D2D;border-radius:4px;overflow:hidden;"
                ):
                    dense_btn = ui.element("button").style(
                        "padding:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;"
                        "background:var(--surface-high);color:var(--on-surface);transition:all 0.15s;"
                    )
                    with dense_btn:
                        ui.html("Dense")
                    bm25_btn = ui.element("button").style(
                        "padding:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;"
                        "background:transparent;color:var(--on-surface-variant);transition:all 0.15s;"
                    )
                    with bm25_btn:
                        ui.html("BM25")

                    def _set_dense():
                        strategy_state["value"] = "dense"
                        dense_btn.style("background:var(--surface-high);color:var(--on-surface);")
                        bm25_btn.style("background:transparent;color:var(--on-surface-variant);")

                    def _set_bm25():
                        strategy_state["value"] = "bm25"
                        bm25_btn.style("background:var(--surface-high);color:var(--on-surface);")
                        dense_btn.style("background:transparent;color:var(--on-surface-variant);")

                    dense_btn.on("click", _set_dense)
                    bm25_btn.on("click", _set_bm25)

            topk_val = ui.label("5").style("color:var(--primary);font-family:monospace;font-size:13px;")
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"):
                ui.html('<span class="rl-label">Top-K Results</span>')
                topk_val
            topk_slider = ui.slider(min=1, max=20, value=5).props("color=primary").classes("w-full")
            topk_slider.on("update:model-value", lambda e: topk_val.set_text(str(int(e.args))))

            thresh_val = ui.label("0.00").style("color:var(--primary);font-family:monospace;font-size:13px;")
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"):
                ui.html('<span class="rl-label">Similarity Threshold</span>')
                thresh_val
            thresh_slider = ui.slider(min=0, max=1, step=0.01, value=0.0).props("color=primary").classes("w-full")
            thresh_slider.on("update:model-value", lambda e: thresh_val.set_text(f"{float(e.args):.2f}"))

            run_btn = ui.element("button").classes("rl-btn-primary").style("margin-top:auto;")
            with run_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:20px;">refresh</span> Re-run Query')

        # ---- Center: Query + Chunks ----
        center = ui.element("section").style(
            "display:flex;flex-direction:column;gap:16px;"
            "height:calc(100vh - 80px);overflow:hidden;"
        )
        with center:
            query_card = ui.element("div").classes("rl-card").style("flex-shrink:0;")
            with query_card:
                with ui.element("div").style("display:flex;align-items:center;gap:8px;margin-bottom:8px;"):
                    ui.html('<span class="material-symbols-outlined" style="font-size:16px;color:var(--on-surface-variant);">search</span>')
                    ui.html('<span class="rl-label">Test Query</span>')
                with ui.element("div").style("position:relative;"):
                    query_input = ui.textarea(
                        placeholder="Enter query to test retrieval..."
                    ).props("outlined rows=3").classes("w-full")
                    send_btn = ui.element("button").style(
                        "position:absolute;bottom:8px;right:8px;background:var(--primary);"
                        "color:#000;border:none;border-radius:4px;padding:4px;cursor:pointer;"
                    )
                    with send_btn:
                        ui.html('<span class="material-symbols-outlined">send</span>')

            chunks_card = ui.element("div").classes("rl-card").style(
                "flex:1;overflow:hidden;display:flex;flex-direction:column;"
            )
            with chunks_card:
                with ui.element("div").style(
                    "display:flex;justify-content:space-between;align-items:center;"
                    "border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:12px;flex-shrink:0;"
                ):
                    with ui.element("div").style("display:flex;align-items:center;gap:8px;"):
                        ui.html('<span class="material-symbols-outlined">format_list_bulleted</span>')
                        ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Top-Retrieved Chunks</span>')
                    results_badge = ui.element("span").style(
                        "background:rgba(142,213,255,0.1);border:1px solid var(--primary);"
                        "color:var(--primary);padding:2px 8px;border-radius:4px;"
                        "font-size:11px;font-weight:700;"
                    )
                    results_badge.text = "0 Results"

                with ui.element("div").classes("rl-adhoc-tab"):
                    adhoc_tab = ui.element("button").classes("rl-adhoc-tab-btn active")
                    with adhoc_tab:
                        ui.html("Ad-hoc")
                    dataset_tab = ui.element("button").classes("rl-adhoc-tab-btn")
                    with dataset_tab:
                        ui.html("Dataset")

                adhoc_area = ui.element("div").style("flex-shrink:0;")
                dataset_area = ui.element("div").style("display:none;flex-shrink:0;")

                with adhoc_area:
                    adhoc_input = ui.textarea(
                        placeholder="Paste multiple text chunks here, separated by double newlines..."
                    ).props("outlined rows=4").classes("w-full")
                    chunks_detected = ui.html(
                        '<span style="font-size:12px;color:var(--on-surface-variant);">0 Chunks Detected</span>'
                    )

                    def _on_adhoc_change(e):
                        text = adhoc_input.value or ""
                        raw = [c.strip() for c in text.split("\n\n") if c.strip()]
                        state["chunks"] = raw
                        state["case_id"] = None
                        chunks_detected.content = (
                            f'<span style="font-size:12px;color:var(--on-surface-variant);">'
                            f'{len(raw)} Chunks Detected</span>'
                        )

                    adhoc_input.on("update:model-value", _on_adhoc_change)

                with dataset_area:
                    cases = _db().list_cases()
                    case_opts = {str(c[0]): c[1] for c in cases}
                    case_sel = ui.select(
                        label="Select Dataset", options=case_opts, with_input=True
                    ).props("outlined dense").classes("w-full")

                    def _on_case_select(e):
                        val = case_sel.value
                        if not val:
                            return
                        cid = int(val)
                        rows = _db().get_chunks(cid)
                        state["chunks"] = [r[3] for r in rows]
                        state["case_id"] = cid
                        chunks_detected.content = (
                            f'<span style="font-size:12px;color:var(--on-surface-variant);">'
                            f'{len(state["chunks"])} Chunks Loaded</span>'
                        )

                    case_sel.on("update:model-value", _on_case_select)

                def _switch_to_adhoc():
                    state["adhoc_mode"] = True
                    adhoc_area.style("display:block;")
                    dataset_area.style("display:none;")
                    adhoc_tab.classes("rl-adhoc-tab-btn active")
                    dataset_tab.classes("rl-adhoc-tab-btn")

                def _switch_to_dataset():
                    state["adhoc_mode"] = False
                    adhoc_area.style("display:none;")
                    dataset_area.style("display:block;")
                    adhoc_tab.classes("rl-adhoc-tab-btn")
                    dataset_tab.classes("rl-adhoc-tab-btn active")

                adhoc_tab.on("click", _switch_to_adhoc)
                dataset_tab.on("click", _switch_to_dataset)

                results_list = ui.element("div").style(
                    "flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:12px;margin-top:12px;"
                )

        # ---- Right: Analytics ----
        right = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with right:
            stats_grid = ui.element("div").style(
                "display:grid;grid-template-columns:1fr 1fr;gap:16px;flex-shrink:0;"
            )
            with stats_grid:
                time_card = ui.element("div").classes("rl-card")
                with time_card:
                    ui.html('<span class="rl-label">Retrieval Time</span>')
                    time_val = ui.html(
                        '<div style="display:flex;align-items:flex-end;gap:4px;margin-top:4px;">'
                        '<span style="font-size:32px;font-weight:700;color:var(--primary);">—</span>'
                        '<span style="font-size:13px;color:var(--on-surface-variant);margin-bottom:4px;">ms</span></div>'
                    )

                chunks_card2 = ui.element("div").classes("rl-card")
                with chunks_card2:
                    ui.html('<span class="rl-label">Chunks</span>')
                    chunks_val = ui.html(
                        '<span style="font-size:32px;font-weight:700;color:var(--on-surface);">0</span>'
                    )

            dist_card = ui.element("div").classes("rl-card").style("flex-shrink:0;")
            with dist_card:
                ui.html('<span class="rl-label">Similarity Distribution</span>')
                dist_plot_area = ui.element("div").style("margin-top:8px;")

            tsne_card = ui.element("div").classes("rl-card").style(
                "flex:1;display:flex;flex-direction:column;min-height:200px;"
            )
            with tsne_card:
                ui.html('<span class="rl-label">t-SNE Projection</span>')
                tsne_plot_area = ui.element("div").style("flex:1;margin-top:8px;")

        # ---- Wire up run ----
        async def _run():
            query = query_input.value.strip()
            if not query:
                ui.notify("Enter a query first", type="warning")
                return
            chunks = state["chunks"]
            if not chunks:
                ui.notify("No chunks loaded", type="warning")
                return

            run_btn.props("loading")
            t0 = time.time()

            try:
                strategy = strategy_state["value"]
                top_k = int(topk_slider.value)
                threshold = float(thresh_slider.value)

                if strategy == "dense":
                    mid_str = model_sel.value
                    if not mid_str:
                        ui.notify("Select an embedding model", type="warning")
                        return
                    models_list = _db().list_models()
                    providers_list = _db().list_providers()
                    prov_map = {p[0]: p for p in providers_list}
                    model_info = next((m for m in models_list if str(m[0]) == mid_str), None)
                    if not model_info:
                        ui.notify("Model not found", type="negative")
                        return
                    pid, mname = model_info[1], model_info[2]
                    p = prov_map.get(pid)
                    if not p:
                        ui.notify("Provider not found", type="negative")
                        return
                    _, pname, api_key, base_url, _ = p
                    emb = Embedder()
                    emb.configure(pname, api_key, mname, base_url)
                    results = await asyncio.to_thread(dense_score, query, chunks, emb, "cosine", top_k)
                    results = [r for r in results if r["score"] >= threshold]
                    all_embeddings = await asyncio.to_thread(emb.embed_batch, chunks)
                    query_emb = await asyncio.to_thread(emb.embed, query)
                else:
                    results = await asyncio.to_thread(sparse_score, query, chunks, "bm25", top_k)
                    results = [r for r in results if r["score"] >= threshold]
                    all_embeddings = None
                    query_emb = None

                elapsed_ms = int((time.time() - t0) * 1000)

                time_val.content = (
                    f'<div style="display:flex;align-items:flex-end;gap:4px;margin-top:4px;">'
                    f'<span style="font-size:32px;font-weight:700;color:var(--primary);">{elapsed_ms}</span>'
                    f'<span style="font-size:13px;color:var(--on-surface-variant);margin-bottom:4px;">ms</span></div>'
                )
                chunks_val.content = (
                    f'<span style="font-size:32px;font-weight:700;color:var(--on-surface);">{len(results)}</span>'
                )
                results_badge.text = f"{len(results)} Results"

                results_list.clear()
                with results_list:
                    for i, r in enumerate(results):
                        score = r["score"]
                        is_top = i == 0
                        badge_cls = "rl-score-high" if score >= 0.8 else "rl-score-mid"
                        item = ui.element("div").classes(f"rl-chunk-item{'  top' if is_top else ''}")
                        with item:
                            with ui.element("div").style(
                                "display:flex;justify-content:space-between;align-items:center;"
                            ):
                                ui.html(
                                    f'<span style="font-family:monospace;font-size:11px;'
                                    f'color:var(--on-surface-variant);">chunk_{r["index"]:04d}</span>'
                                )
                                ui.html(f'<span class="rl-score-badge {badge_cls}">{score:.3f}</span>')
                            ui.html(
                                f'<p style="font-size:13px;color:var(--on-surface);margin:4px 0 0;'
                                f'overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;'
                                f'-webkit-box-orient:vertical;">{r["text"][:300]}</p>'
                            )

                if results:
                    scores = [r["score"] for r in results]
                    dist_plot_area.clear()
                    with dist_plot_area:
                        _render_distribution_chart(scores)

                if all_embeddings is not None and len(all_embeddings) >= 3:
                    tsne_plot_area.clear()
                    await asyncio.to_thread(
                        _render_tsne_chart_sync, tsne_plot_area, all_embeddings, query_emb
                    )

            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")
            finally:
                run_btn.props(remove="loading")

        run_btn.on("click", _run)
        send_btn.on("click", _run)


def _render_distribution_chart(scores: list) -> None:
    fig, ax = plt.subplots(figsize=(4, 2.5))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#050505")
    ax.hist(scores, bins=min(10, len(scores)), color="#38bdf8", alpha=0.8, edgecolor="#2D2D2D")
    ax.tick_params(colors="#bdc8d1", labelsize=8)
    ax.spines[:].set_color("#2D2D2D")
    ax.set_xlabel("Score", color="#bdc8d1", fontsize=8)
    ax.set_ylabel("Count", color="#bdc8d1", fontsize=8)
    plt.tight_layout(pad=0.5)
    ui.pyplot(fig)
    plt.close(fig)


def _render_tsne_chart_sync(container, embeddings: np.ndarray, query_emb: np.ndarray) -> None:
    from sklearn.manifold import TSNE
    n = len(embeddings)
    perplexity = min(30, max(2, n - 1))
    all_vecs = np.vstack([embeddings, query_emb.reshape(1, -1)])
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42, n_iter=300)
    coords = tsne.fit_transform(all_vecs)
    chunk_coords = coords[:-1]
    query_coord = coords[-1]

    fig, ax = plt.subplots(figsize=(4, 3.5))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#050505")
    ax.scatter(chunk_coords[:, 0], chunk_coords[:, 1], c="#bdc8d1", s=20, alpha=0.6)
    ax.scatter([query_coord[0]], [query_coord[1]], c="#8ed5ff", s=80, zorder=5, marker="*")
    ax.tick_params(colors="#bdc8d1", labelsize=7)
    ax.spines[:].set_color("#2D2D2D")
    plt.tight_layout(pad=0.5)
    with container:
        ui.pyplot(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Chunk vs Chunk
# ---------------------------------------------------------------------------

def _render_chunk_vs_chunk() -> None:
    state = {
        "chunks": [],
        "adhoc_mode": True,
    }

    with ui.element("div").style(
        "display:grid;grid-template-columns:3fr 6fr 3fr;gap:16px;"
        "padding:16px;height:100%;overflow:hidden;"
    ):
        # ---- Left: Model Configuration ----
        left = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with left:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;"
                "border-bottom:1px solid #2D2D2D;padding-bottom:12px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--primary);">Model Configuration</span>')

            models = _db().list_models()
            providers = {p[0]: p[1] for p in _db().list_providers()}
            model_opts = {str(m[0]): f"{providers.get(m[1], '?')}/{m[2]}" for m in models}
            model_sel = ui.select(
                label="Embedding Model", options=model_opts, with_input=True
            ).props("outlined dense").classes("w-full")

            with ui.element("div").style("display:flex;flex-direction:column;gap:4px;"):
                ui.html('<span class="rl-label">Retrieval Strategy</span>')
                strategy_state = {"value": "dense"}
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;"
                    "border:1px solid #2D2D2D;border-radius:4px;overflow:hidden;"
                ):
                    dense_btn = ui.element("button").style(
                        "padding:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;"
                        "background:var(--surface-high);color:var(--on-surface);"
                    )
                    with dense_btn:
                        ui.html("Dense")
                    bm25_btn = ui.element("button").style(
                        "padding:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;"
                        "background:transparent;color:var(--on-surface-variant);"
                    )
                    with bm25_btn:
                        ui.html("BM25")

                    def _set_dense():
                        strategy_state["value"] = "dense"
                        dense_btn.style("background:var(--surface-high);color:var(--on-surface);")
                        bm25_btn.style("background:transparent;color:var(--on-surface-variant);")

                    def _set_bm25():
                        strategy_state["value"] = "bm25"
                        bm25_btn.style("background:var(--surface-high);color:var(--on-surface);")
                        dense_btn.style("background:transparent;color:var(--on-surface-variant);")

                    dense_btn.on("click", _set_dense)
                    bm25_btn.on("click", _set_bm25)

            matrix_size = ui.number(
                label="Max Matrix Size", value=30, min=2, max=100
            ).props("outlined dense").classes("w-full")

            run_btn = ui.element("button").classes("rl-btn-primary").style("margin-top:auto;")
            with run_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:20px;">play_arrow</span> Run Analysis')

        # ---- Center: Chunks input ----
        center = ui.element("section").style(
            "display:flex;flex-direction:column;gap:16px;"
            "height:calc(100vh - 80px);overflow:hidden;"
        )
        with center:
            center_card = ui.element("div").classes("rl-card").style(
                "flex:1;overflow:hidden;display:flex;flex-direction:column;"
            )
            with center_card:
                with ui.element("div").style(
                    "display:flex;align-items:center;gap:8px;"
                    "border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:12px;flex-shrink:0;"
                ):
                    ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                    ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Chunks Input</span>')

                with ui.element("div").classes("rl-adhoc-tab"):
                    adhoc_tab = ui.element("button").classes("rl-adhoc-tab-btn active")
                    with adhoc_tab:
                        ui.html("Ad-hoc")
                    dataset_tab = ui.element("button").classes("rl-adhoc-tab-btn")
                    with dataset_tab:
                        ui.html("Dataset")

                adhoc_area = ui.element("div").style(
                    "flex:1;display:flex;flex-direction:column;gap:8px;"
                )
                dataset_area = ui.element("div").style("display:none;")

                with adhoc_area:
                    adhoc_input = ui.textarea(
                        placeholder="Paste multiple text chunks here, separated by double newlines..."
                    ).props("outlined rows=12").classes("w-full")
                    chunks_detected = ui.html(
                        '<span style="font-size:12px;color:var(--on-surface-variant);">0 Chunks Detected</span>'
                    )

                    def _on_adhoc_change(e):
                        text = adhoc_input.value or ""
                        raw = [c.strip() for c in text.split("\n\n") if c.strip()]
                        state["chunks"] = raw
                        chunks_detected.content = (
                            f'<span style="font-size:12px;color:var(--on-surface-variant);">'
                            f'{len(raw)} Chunks Detected</span>'
                        )

                    adhoc_input.on("update:model-value", _on_adhoc_change)

                with dataset_area:
                    cases = _db().list_cases()
                    case_opts = {str(c[0]): c[1] for c in cases}
                    case_sel = ui.select(
                        label="Select Dataset", options=case_opts, with_input=True
                    ).props("outlined dense").classes("w-full")

                    def _on_case_select(e):
                        val = case_sel.value
                        if not val:
                            return
                        rows = _db().get_chunks(int(val))
                        state["chunks"] = [r[3] for r in rows]
                        chunks_detected.content = (
                            f'<span style="font-size:12px;color:var(--on-surface-variant);">'
                            f'{len(state["chunks"])} Chunks Loaded</span>'
                        )

                    case_sel.on("update:model-value", _on_case_select)

                def _switch_adhoc():
                    state["adhoc_mode"] = True
                    adhoc_area.style("flex:1;display:flex;flex-direction:column;gap:8px;")
                    dataset_area.style("display:none;")
                    adhoc_tab.classes("rl-adhoc-tab-btn active")
                    dataset_tab.classes("rl-adhoc-tab-btn")

                def _switch_dataset():
                    state["adhoc_mode"] = False
                    adhoc_area.style("display:none;")
                    dataset_area.style("display:block;")
                    adhoc_tab.classes("rl-adhoc-tab-btn")
                    dataset_tab.classes("rl-adhoc-tab-btn active")

                adhoc_tab.on("click", _switch_adhoc)
                dataset_tab.on("click", _switch_dataset)

        # ---- Right: Heatmap ----
        right = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with right:
            ui.html('<span class="rl-label">Similarity Heatmap</span>')
            heatmap_area = ui.element("div").style("flex:1;margin-top:8px;")

        # ---- Wire up run ----
        async def _run():
            chunks = state["chunks"]
            if not chunks:
                ui.notify("No chunks loaded", type="warning")
                return

            strategy = strategy_state["value"]
            max_n = int(matrix_size.value)
            chunks_n = chunks[:max_n]

            run_btn.props("loading")
            try:
                if strategy == "dense":
                    mid_str = model_sel.value
                    if not mid_str:
                        ui.notify("Select an embedding model", type="warning")
                        return
                    models_list = _db().list_models()
                    providers_list = _db().list_providers()
                    prov_map = {p[0]: p for p in providers_list}
                    model_info = next((m for m in models_list if str(m[0]) == mid_str), None)
                    if not model_info:
                        ui.notify("Model not found", type="negative")
                        return
                    pid, mname = model_info[1], model_info[2]
                    p = prov_map.get(pid)
                    if not p:
                        ui.notify("Provider not found", type="negative")
                        return
                    _, pname, api_key, base_url, _ = p
                    emb = Embedder()
                    emb.configure(pname, api_key, mname, base_url)
                    embeddings = await asyncio.to_thread(emb.embed_batch, chunks_n)
                    metric_fn = get_metric("cosine")
                    n = len(chunks_n)
                    matrix = [
                        [float(metric_fn(embeddings[i], embeddings[j])) for j in range(n)]
                        for i in range(n)
                    ]
                else:
                    from raglab.core.scorer import bm25_score
                    n = len(chunks_n)
                    matrix = [[0.0] * n for _ in range(n)]
                    for i in range(n):
                        results = await asyncio.to_thread(
                            bm25_score, chunks_n[i], chunks_n, n
                        )
                        for r in results:
                            j = r["index"]
                            matrix[i][j] = float(r["score"])

                labels = [c[:20] + "..." if len(c) > 20 else c for c in chunks_n]
                heatmap_area.clear()
                with heatmap_area:
                    _render_heatmap(matrix, labels)

            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")
            finally:
                run_btn.props(remove="loading")

        run_btn.on("click", _run)


def _render_heatmap(matrix: list, labels: list) -> None:
    n = len(labels)
    fig, ax = plt.subplots(figsize=(max(5, n * 0.4), max(4, n * 0.35)))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#050505")
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax).ax.tick_params(colors="#bdc8d1", labelsize=7)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7, color="#bdc8d1")
    ax.set_yticklabels(labels, fontsize=7, color="#bdc8d1")
    ax.spines[:].set_color("#2D2D2D")
    if n <= 10:
        for i in range(n):
            for j in range(n):
                ax.text(
                    j, i, f"{matrix[i][j]:.2f}",
                    ha="center", va="center", fontsize=6,
                    color="white" if matrix[i][j] > 0.6 else "black"
                )
    plt.tight_layout(pad=0.5)
    ui.pyplot(fig)
    plt.close(fig)
