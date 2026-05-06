"""Datasets page: three-column layout for dataset/source/chunking management."""

from nicegui import ui
from raglab.storage.db import Database
from raglab.core.splitter import split_lines, split_by_char, split_by_recursive


def _db() -> Database:
    return Database()


def render_datasets() -> None:
    """Render Datasets page into current NiceGUI context."""
    state = {
        "active_case_id": None,
        "active_source_idx": None,
    }

    with ui.element("div").style("display:flex;height:100%;overflow:hidden;width:100%;"):
        left = ui.element("section").style(
            "width:220px;min-width:200px;max-width:250px;"
            "border-right:1px solid var(--outline-variant);"
            "display:flex;flex-direction:column;background:#000;flex-shrink:0;"
        )
        mid = ui.element("section").style(
            "width:280px;min-width:250px;max-width:300px;"
            "border-right:1px solid var(--outline-variant);"
            "display:flex;flex-direction:column;background:#0a0a0a;flex-shrink:0;"
        )
        right = ui.element("section").style(
            "flex:1;overflow-y:auto;background:#000;padding:24px;"
        )

        with left:
            _build_dataset_list(state, mid, right)
        with mid:
            _build_source_list(state, right)
        with right:
            _build_right_placeholder()


def _build_dataset_list(state: dict, mid, right) -> None:
    with ui.element("div").style(
        "padding:12px 16px;border-bottom:1px solid var(--outline-variant);"
        "display:flex;align-items:center;justify-content:space-between;"
    ):
        ui.html('<span class="rl-label">Datasets</span>')
        add_btn = ui.element("button").style(
            "background:none;border:none;cursor:pointer;color:var(--on-surface-variant);"
        )
        with add_btn:
            ui.html('<span class="material-symbols-outlined" style="font-size:18px;">add</span>')

    list_area = ui.element("div").style(
        "flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px;"
    )
    new_form = ui.element("div").style("padding:8px;display:none;")
    new_form.props('data-new-dataset=""')

    def _refresh_list():
        list_area.clear()
        with list_area:
            cases = _db().list_cases()
            for cid, name, desc, created_at in cases:
                chunks = _db().get_chunks(cid)
                active = state["active_case_id"] == cid
                border = "border-left:2px solid var(--primary);" if active else "border-left:2px solid transparent;"
                bg = "background:var(--surface-highest);" if active else "background:transparent;"
                item = ui.element("div").style(
                    f"padding:8px;border-radius:4px;cursor:pointer;{border}{bg}"
                    "display:flex;flex-direction:column;gap:4px;position:relative;"
                )
                with item:
                    with ui.element("div").style("display:flex;align-items:center;gap:8px;"):
                        icon_color = "var(--primary)" if active else "var(--on-surface-variant)"
                        ui.html(f'<span class="material-symbols-outlined" style="font-size:16px;color:{icon_color};">folder</span>')
                        ui.html(f'<span style="font-size:14px;font-weight:600;color:var(--on-surface);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</span>')
                    ui.html(f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(chunks)} chunks</span>')

                def _select(c=cid):
                    state["active_case_id"] = c
                    state["active_source_idx"] = None
                    _refresh_list()
                    mid.clear()
                    with mid:
                        _build_source_list(state, right)
                    right.clear()
                    with right:
                        _build_right_placeholder()

                item.on("click", _select)

                del_btn = ui.element("button").style(
                    "position:absolute;right:4px;top:4px;background:none;border:none;"
                    "cursor:pointer;color:var(--on-surface-variant);opacity:0.6;"
                )
                with del_btn:
                    ui.html('<span class="material-symbols-outlined" style="font-size:16px;">delete</span>')

                def _delete(c=cid):
                    with ui.dialog() as dlg, ui.card():
                        ui.label("Delete this dataset and all its chunks?")
                        with ui.row():
                            ui.button(
                                "Delete",
                                on_click=lambda d=dlg, cc=c: _confirm_delete(
                                    cc, d, state, _refresh_list, mid, right
                                )
                            ).props("color=negative")
                            ui.button("Cancel", on_click=dlg.close)
                    dlg.open()

                del_btn.on("click", _delete)

    def _toggle_new_form():
        ui.run_javascript(
            'var el = document.querySelector("[data-new-dataset]");'
            'el.style.display = el.style.display === "none" ? "block" : "none";'
        )

    add_btn.on("click", _toggle_new_form)

    with new_form:
        name_in = ui.input(label="Dataset name").props("outlined dense").classes("w-full")

        def _create():
            name = name_in.value.strip()
            if not name:
                return
            _db().add_case(name, "")
            name_in.value = ""
            _refresh_list()
            ui.run_javascript(
                'var el = document.querySelector("[data-new-dataset]");'
                'el.style.display = "none";'
            )

        ui.button("Create", on_click=_create).props("dense").style(
            "background:var(--primary);color:var(--on-primary);border-radius:8px;margin-top:4px;"
        )

    _refresh_list()


def _confirm_delete(case_id: int, dialog, state: dict, refresh_fn, mid, right) -> None:
    dialog.close()
    _db().delete_case(case_id)
    if state["active_case_id"] == case_id:
        state["active_case_id"] = None
        state["active_source_idx"] = None
        mid.clear()
        with mid:
            _build_source_list(state, right)
        right.clear()
        with right:
            _build_right_placeholder()
    refresh_fn()
    ui.notify("Dataset deleted", type="positive")


def _build_source_list(state: dict, right) -> None:
    with ui.element("div").style(
        "padding:12px 16px;border-bottom:1px solid var(--outline-variant);"
        "display:flex;align-items:center;justify-content:space-between;"
    ):
        ui.html('<span class="rl-label">Sources</span>')

    if state["active_case_id"] is None:
        with ui.element("div").style("padding:16px;"):
            ui.html('<span style="color:var(--on-surface-variant);font-size:13px;">Select a dataset first.</span>')
        return

    with ui.element("div").style(
        "padding:8px;border-bottom:1px solid var(--outline-variant);display:flex;gap:8px;"
    ):
        file_btn = ui.element("button").classes("rl-btn-secondary").style("flex:1;")
        with file_btn:
            ui.html('<span class="material-symbols-outlined" style="font-size:16px;">upload_file</span> File')
        text_btn = ui.element("button").classes("rl-btn-secondary").style("flex:1;")
        with text_btn:
            ui.html('<span class="material-symbols-outlined" style="font-size:16px;">edit_note</span> Text')

    upload_area = ui.element("div").style("padding:8px;display:none;")
    upload_area.props('data-upload-area=""')
    text_area_div = ui.element("div").style("padding:8px;display:none;")
    text_area_div.props('data-text-area=""')

    source_list = ui.element("div").style(
        "flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px;"
    )

    def _refresh_sources():
        source_list.clear()
        with source_list:
            case_id = state["active_case_id"]
            chunks = _db().get_chunks(case_id)
            case = _db().get_case(case_id)
            if case:
                _, name, desc, _ = case
                active = state["active_source_idx"] == 0
                border = "border-left:2px solid var(--primary);" if active else ""
                bg = "background:var(--surface);" if active else "background:transparent;"
                item = ui.element("div").style(
                    f"padding:8px;border-radius:4px;cursor:pointer;{border}{bg}"
                    "display:flex;flex-direction:column;gap:4px;"
                )
                with item:
                    with ui.element("div").style("display:flex;align-items:center;gap:8px;"):
                        ui.html('<span class="material-symbols-outlined" style="font-size:16px;color:var(--primary);">description</span>')
                        ui.html(f'<span style="font-size:14px;font-weight:600;color:var(--on-surface);">{name}</span>')
                    ui.html(f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(chunks)} chunks</span>')

                def _select_source():
                    state["active_source_idx"] = 0
                    _refresh_sources()
                    right.clear()
                    with right:
                        _build_chunking_config(state, _refresh_sources)

                item.on("click", _select_source)

    def _toggle_upload():
        ui.run_javascript(
            'var el = document.querySelector("[data-upload-area]");'
            'el.style.display = el.style.display === "none" ? "block" : "none";'
            'document.querySelector("[data-text-area]").style.display = "none";'
        )

    def _toggle_text():
        ui.run_javascript(
            'var el = document.querySelector("[data-text-area]");'
            'el.style.display = el.style.display === "none" ? "block" : "none";'
            'document.querySelector("[data-upload-area]").style.display = "none";'
        )

    file_btn.on("click", _toggle_upload)
    text_btn.on("click", _toggle_text)

    with upload_area:
        async def _on_upload(e):
            content = e.content.read().decode("utf-8")
            case_id = state["active_case_id"]
            db = _db()
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM case_chunks WHERE case_id = ?", (case_id,))
            db.conn.commit()
            chunks = split_by_recursive(content, chunk_size=512, chunk_overlap=50)
            db.add_chunks(case_id, chunks)
            ui.notify(f"{len(chunks)} chunks loaded from file", type="positive")
            _refresh_sources()
            ui.run_javascript(
                'document.querySelector("[data-upload-area]").style.display = "none";'
            )

        ui.upload(
            label=".txt / .md", auto_upload=True, on_upload=_on_upload
        ).props('accept=".txt,.md"').classes("w-full")

    with text_area_div:
        text_in = ui.textarea(label="Paste text").props("outlined rows=6").classes("w-full")

        def _load_text():
            content = text_in.value.strip()
            if not content:
                return
            case_id = state["active_case_id"]
            db = _db()
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM case_chunks WHERE case_id = ?", (case_id,))
            db.conn.commit()
            chunks = split_by_recursive(content, chunk_size=512, chunk_overlap=50)
            db.add_chunks(case_id, chunks)
            text_in.value = ""
            ui.notify(f"{len(chunks)} chunks loaded", type="positive")
            _refresh_sources()
            ui.run_javascript(
                'document.querySelector("[data-text-area]").style.display = "none";'
            )

        ui.button("Load", on_click=_load_text).props("dense").style(
            "background:var(--primary);color:var(--on-primary);border-radius:8px;margin-top:4px;"
        )

    _refresh_sources()


def _build_right_placeholder() -> None:
    with ui.element("div").style(
        "height:100%;display:flex;align-items:center;justify-content:center;"
    ):
        ui.html(
            '<span style="color:var(--on-surface-variant);font-size:14px;">'
            'Select a source to configure chunking.</span>'
        )


def _build_chunking_config(state: dict, refresh_sources_fn) -> None:
    case_id = state["active_case_id"]
    case = _db().get_case(case_id)
    if not case:
        return
    _, name, _, _ = case
    chunks = _db().get_chunks(case_id)

    with ui.element("div").style(
        "display:flex;flex-direction:column;gap:24px;max-width:800px;"
    ):
        with ui.element("div").style(
            "display:flex;align-items:center;justify-content:space-between;"
        ):
            ui.html(f'<span style="font-size:32px;font-weight:700;color:var(--on-surface);">{name}</span>')
            ui.html('<span style="font-size:13px;color:var(--on-surface-variant);">Configure chunking strategy</span>')

        strategy_card = ui.element("div").classes("rl-card")
        with strategy_card:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;"
                "border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:16px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--on-surface-variant);">cut</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Chunking Strategy</span>')

            strategy_sel = ui.select(
                label="Strategy Type",
                options={"recursive": "Recursive", "fixed": "Fixed Length", "lines": "By Lines"},
                value="recursive",
            ).props("outlined dense").classes("w-full")

            with ui.element("div").style(
                "display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px;"
            ):
                chunk_size_in = ui.number(label="Chunk Size", value=512, min=1).props("outlined dense")
                overlap_in = ui.number(label="Overlap", value=50, min=0).props("outlined dense")

        preview_card = ui.element("div").classes("rl-card")
        preview_area = ui.element("div")

        def _apply():
            content_rows = _db().get_chunks(case_id)
            if not content_rows:
                ui.notify("No content loaded", type="warning")
                return
            full_text = "\n\n".join(r[3] for r in content_rows)
            strategy = strategy_sel.value
            cs = int(chunk_size_in.value)
            ov = int(overlap_in.value)
            if strategy == "lines":
                new_chunks = split_lines(full_text)
            elif strategy == "fixed":
                new_chunks = split_by_char(full_text, chunk_size=cs, overlap=ov)
            else:
                new_chunks = split_by_recursive(full_text, chunk_size=cs, chunk_overlap=ov)

            db = _db()
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM case_chunks WHERE case_id = ?", (case_id,))
            db.conn.commit()
            db.add_chunks(case_id, new_chunks)
            ui.notify(f"{len(new_chunks)} chunks created", type="positive")
            refresh_sources_fn()
            _render_preview(preview_area, new_chunks)

        with strategy_card:
            ui.button("Apply", on_click=_apply).props("dense").style(
                "background:var(--primary);color:var(--on-primary);border-radius:8px;margin-top:12px;"
            )

        with preview_card:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;"
                "border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:16px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--on-surface-variant);">visibility</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Chunking Preview</span>')
            with preview_area:
                _render_preview(preview_area, [r[3] for r in chunks])


def _render_preview(container, chunks: list) -> None:
    container.clear()
    with container:
        if not chunks:
            ui.html('<span style="color:var(--on-surface-variant);font-size:13px;">No chunks yet.</span>')
            return
        ui.html(f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(chunks)} chunks total</span>')
        for i, chunk in enumerate(chunks[:20]):
            with ui.element("div").style(
                "background:var(--surface-input);border:1px solid #2D2D2D;border-radius:4px;"
                "padding:8px;margin-top:8px;"
            ):
                ui.html(f'<span style="font-size:11px;color:var(--on-surface-variant);font-family:monospace;">#{i+1}</span>')
                preview = chunk[:300] + ("..." if len(chunk) > 300 else "")
                ui.html(
                    f'<p style="font-size:13px;color:var(--on-surface);margin:4px 0 0;'
                    f'white-space:pre-wrap;word-break:break-word;">{preview}</p>'
                )
        if len(chunks) > 20:
            ui.html(
                f'<span style="font-size:12px;color:var(--on-surface-variant);">'
                f'... and {len(chunks)-20} more chunks</span>'
            )
