"""Evaluate page: complete evaluation workflow with query, chunk selection, model comparison."""

import asyncio
from datetime import datetime

import numpy as np
from nicegui import ui

from raglab.core.scorer import dense_score, sparse_score
from raglab.core.embedder import Embedder
from raglab.core.splitter import split_lines
from raglab.core.metrics import get_metric
from raglab.storage.db import Database
from raglab.i18n import t
from raglab.ui.components.heatmap import render_heatmap
from raglab.ui.components.leaderboard import render_leaderboard


def _db() -> Database:
    """Return a fresh Database connection."""
    return Database()


def _case_options() -> dict:
    """Return {case_id_str: case_name} for the case selector."""
    return {str(c[0]): c[1] for c in _db().list_cases()}


def _model_options() -> dict:
    """Return {model_id_str: 'provider/model'} for the model selector."""
    models = _db().list_models()
    providers = {p[0]: p[1] for p in _db().list_providers()}
    opts = {}
    for m in models:
        mid, pid, mname, _mtype, _created = m
        prov_name = providers.get(pid, str(pid))
        opts[str(mid)] = f"{prov_name}/{mname}"
    return opts


def _metric_options() -> dict:
    """Return {metric_key: translated_label}."""
    return {
        "cosine": t("metric.cosine"),
        "euclidean": t("metric.euclidean"),
        "dot": t("metric.dot"),
        "manhattan": t("metric.manhattan"),
    }


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def render_evaluate() -> None:
    """Render the Evaluate page into the current NiceGUI page."""

    # Reactive state
    state: dict = {"chunks": [], "case_id": None}

    # ---- Configuration card ----
    with ui.card().classes("w-full"):
        ui.label(t("nav.evaluate")).classes("text-xl font-bold")

        # 1. Query
        query_input = ui.input(label=t("label.query")).props("dense clearable").classes("w-full")

        # 2. Chunk source
        ui.label(t("label.chunks")).classes("text-sm font-semibold mt-2")
        source_toggle = ui.toggle(
            {"upload": t("label.upload_file"), "input": t("label.manual_input"), "case": t("label.select_case")},
            value="upload",
        ).classes("mb-2")

        # -- Upload area --
        upload_col = ui.column().classes("w-full")
        with upload_col:

            async def _on_upload(e):
                content = e.content.read().decode("utf-8")
                chunks = split_lines(content)
                state["chunks"] = chunks
                # Persist as a case so add_run() has a case_id
                db = _db()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                case_id = db.add_case(f"upload_{ts}", "Uploaded via evaluate page")
                db.add_chunks(case_id, chunks)
                state["case_id"] = case_id
                chunk_status.text = f"{len(chunks)} chunks loaded"
                ui.notify(f"{len(chunks)} chunks loaded", type="positive")

            ui.upload(
                label=".txt",
                auto_upload=True,
                on_upload=_on_upload,
            ).props('accept=".txt"').classes("w-full")

        # -- Manual input area --
        input_col = ui.column().classes("w-full")
        with input_col:
            text_input = ui.textarea(
                label=t("label.enter_text"),
                placeholder="Paste or type your text content here...",
            ).props('rows=8').classes("w-full")

            def _on_text_change(e):
                content = text_input.value.strip()
                if not content:
                    state["chunks"] = []
                    state["case_id"] = None
                    chunk_status.text = ""
                    return

                chunks = split_lines(content)
                state["chunks"] = chunks
                # Persist as a case so add_run() has a case_id
                db = _db()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                case_id = db.add_case(f"input_{ts}", "Manually input via evaluate page")
                db.add_chunks(case_id, chunks)
                state["case_id"] = case_id
                chunk_status.text = f"{len(chunks)} chunks loaded"
                ui.notify(f"{len(chunks)} chunks loaded", type="positive")

            ui.button(t("btn.load_text"), on_click=_on_text_change).classes("mt-2 w-32")

        # -- Case selection --
        case_col = ui.column().classes("w-full")
        with case_col:
            case_select = ui.select(
                label=t("label.select_case"),
                options=_case_options(),
                with_input=True,
            ).props("dense").classes("w-full")
            case_select.on(
                "update:model-value",
                lambda e: _on_case_change(e, state, chunk_status),
            )

        # Toggle visibility
        upload_col.bind_visibility_from(source_toggle, "value", value="upload")
        input_col.bind_visibility_from(source_toggle, "value", value="input")
        case_col.bind_visibility_from(source_toggle, "value", value="case")

        # Shared chunk status
        chunk_status = ui.label("").classes("text-sm text-gray-500 mt-1")

        # 3. Model selection (multiple)
        model_select = ui.select(
            label=t("label.model"),
            options=_model_options(),
            multiple=True,
            with_input=True,
        ).props("dense").classes("w-full mt-2")

        # 4. Sparse algorithms
        with ui.row().classes("w-full items-center gap-4 mt-2"):
            ui.label(t("label.algorithm")).classes("text-sm font-semibold")
            bm25_check = ui.checkbox(t("algorithm.bm25"))
            tfidf_check = ui.checkbox(t("algorithm.tfidf"))

        # 5. Metric  +  6. Top-K
        with ui.row().classes("w-full items-end gap-4 mt-2"):
            metric_select = ui.select(
                label=t("label.metric"),
                options=_metric_options(),
                value="cosine",
            ).props("dense").classes("w-48")

            top_k_num = ui.number(
                label=t("label.top_k"),
                value=10,
                min=1,
            ).props("dense").classes("w-32")

        # 7. Start button
        start_btn = ui.button(t("btn.start")).classes("mt-4")

    # ---- Results area ----
    results_area = ui.column().classes("w-full gap-4")

    # ---- History ----
    with ui.card().classes("w-full mt-4"):
        ui.label(t("label.history")).classes("text-lg font-bold")
        history_container = ui.column().classes("w-full")
        _render_history_into(history_container)

    # Wire up the start button
    async def _on_start():
        await _run_eval(
            state, query_input, model_select, bm25_check, tfidf_check,
            metric_select, top_k_num, start_btn, results_area, history_container,
        )

    start_btn.on_click(_on_start)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _on_case_change(e, state: dict, chunk_status) -> None:
    """Handle case selection: load chunks from DB."""
    try:
        val = e.args.get("value") if hasattr(e, "args") else None
    except Exception:
        val = None
    if not val:
        return
    case_id = int(val)
    db = _db()
    chunk_rows = db.get_chunks(case_id)
    chunks = [cr[3] for cr in chunk_rows]  # content column
    state["chunks"] = chunks
    state["case_id"] = case_id
    chunk_status.text = f"{len(chunks)} chunks loaded"


async def _run_eval(
    state, query_input, model_select, bm25_check, tfidf_check,
    metric_select, top_k_num, start_btn, results_area, history_container,
) -> None:
    """Run evaluation asynchronously, updating UI components."""
    query = query_input.value.strip()
    if not query:
        ui.notify(t("msg.no_query"), type="warning")
        return

    # Resolve chunks
    chunks = list(state["chunks"])
    if not chunks and state.get("case_id"):
        chunk_rows = _db().get_chunks(state["case_id"])
        chunks = [cr[3] for cr in chunk_rows]
        state["chunks"] = chunks

    if not chunks:
        ui.notify(t("msg.no_chunks"), type="warning")
        return

    selected_model_ids = list(model_select.value or [])
    algorithms: list[str] = []
    if bm25_check.value:
        algorithms.append("bm25")
    if tfidf_check.value:
        algorithms.append("tfidf")

    if not selected_model_ids and not algorithms:
        ui.notify(t("msg.no_model"), type="warning")
        return

    metric = metric_select.value
    top_k = int(top_k_num.value)
    case_id = state.get("case_id")

    # Ensure we have a case_id for DB storage
    if case_id is None:
        db = _db()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_id = db.add_case(f"eval_{ts}", "Auto-created during evaluation")
        db.add_chunks(case_id, chunks)
        state["case_id"] = case_id

    # Loading state
    start_btn.props("loading")
    ui.notify(t("msg.evaluating"), type="info")

    try:
        all_results: list[dict] = []
        first_embeddings: np.ndarray | None = None
        first_model_name: str | None = None

        # --- Dense scoring with selected models ---
        if selected_model_ids:
            models_list = _db().list_models()
            providers_list = _db().list_providers()
            prov_map = {p[0]: p for p in providers_list}

            for mid_str in selected_model_ids:
                model_info = None
                for m in models_list:
                    if str(m[0]) == mid_str:
                        model_info = m
                        break
                if model_info is None:
                    continue

                pid, mname = model_info[1], model_info[2]
                p = prov_map.get(pid)
                if p is None:
                    ui.notify(f"Provider not found for model {mname}", type="negative")
                    continue

                _, pname, api_key, base_url, _ = p
                emb = Embedder()
                emb.configure(pname, api_key, mname, base_url)

                db = _db()
                run_id = db.add_run(case_id, name=f"eval_{mname}", model=mname, metric=metric)
                try:
                    results = await asyncio.to_thread(
                        dense_score, query, chunks, emb, metric, top_k,
                    )
                    scores = [
                        (r["index"], r["score"], rank + 1)
                        for rank, r in enumerate(results)
                    ]
                    db.add_scores(run_id, scores)
                    db.update_run_status(run_id, "completed")
                    all_results.append({"model": mname, "scores": results})

                    # Keep first model's embeddings for heatmap
                    if first_embeddings is None:
                        first_embeddings = await asyncio.to_thread(emb.embed_batch, chunks)
                        first_model_name = mname

                except Exception as exc:
                    db.update_run_status(run_id, "failed")
                    ui.notify(f"{mname}: {exc}", type="negative")

        # --- Sparse scoring ---
        for algo in algorithms:
            db = _db()
            run_id = db.add_run(
                case_id, name=f"eval_{algo}", model=algo,
                metric="sparse", algorithm=algo,
            )
            try:
                results = await asyncio.to_thread(
                    sparse_score, query, chunks, algo, top_k,
                )
                scores = [
                    (r["index"], r["score"], rank + 1)
                    for rank, r in enumerate(results)
                ]
                db.add_scores(run_id, scores)
                db.update_run_status(run_id, "completed")
                all_results.append({"model": algo.upper(), "scores": results})
            except Exception as exc:
                db.update_run_status(run_id, "failed")
                ui.notify(f"{algo}: {exc}", type="negative")

        # --- Render results ---
        results_area.clear()
        with results_area:
            if all_results:
                model_names = [r["model"] for r in all_results]
                render_leaderboard(all_results, model_names, top_k)

                # Heatmap: chunk-to-chunk similarity using first dense model
                if first_embeddings is not None:
                    metric_fn = get_metric(metric)
                    n = len(chunks)
                    heatmap_n = min(n, 30)  # cap for performance
                    matrix = np.zeros((heatmap_n, heatmap_n))
                    for i in range(heatmap_n):
                        for j in range(heatmap_n):
                            matrix[i][j] = metric_fn(
                                first_embeddings[i], first_embeddings[j],
                            )
                    labels = [c[:30] for c in chunks[:heatmap_n]]
                    render_heatmap(
                        matrix.tolist(),
                        labels,
                        title=f"Chunk Similarity ({first_model_name})",
                    )
            else:
                ui.label(t("msg.no_chunks")).classes("text-gray-500")

        # Refresh history
        _render_history_into(history_container)
        ui.notify(t("msg.complete"), type="positive")

    except Exception as exc:
        ui.notify(f"Evaluation error: {exc}", type="negative")
    finally:
        start_btn.props(remove="loading")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def _render_history_into(container) -> None:
    """Render (or re-render) evaluation history into *container*."""
    container.clear()
    with container:
        db = _db()
        runs = db.list_runs()
        if not runs:
            ui.label(t("msg.no_runs")).classes("text-gray-500")
            return

        rows = []
        for r in runs:
            rid, _case_id, name, model, metric, algorithm, status, created_at = r
            status_label = t(f"status.{status}") if status else ""
            rows.append({
                "id": rid,
                "name": name,
                "model": model,
                "metric": metric or "",
                "algorithm": algorithm or "",
                "status": status_label,
                "created_at": created_at or "",
            })

        columns = [
            {"name": "id", "label": "ID", "field": "id",
             "align": "center", "style": "width: 40px"},
            {"name": "name", "label": t("label.name"), "field": "name",
             "align": "left"},
            {"name": "model", "label": t("label.model"), "field": "model",
             "align": "left"},
            {"name": "metric", "label": t("label.metric"), "field": "metric",
             "align": "center"},
            {"name": "algorithm", "label": t("label.algorithm"),
             "field": "algorithm", "align": "center"},
            {"name": "status", "label": t("label.status"), "field": "status",
             "align": "center"},
            {"name": "created_at", "label": t("label.run_at"),
             "field": "created_at", "align": "center"},
        ]

        ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
