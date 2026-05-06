"""Settings page: Provider management, Model management, Default parameters."""

from nicegui import ui
from raglab.storage.db import Database


def _db() -> Database:
    return Database()


def render_settings() -> None:
    """Render Settings page into current NiceGUI context."""
    with ui.element("div").style("height:100%;overflow-y:auto;padding:32px;width:100%;"):
        with ui.element("div").style(
            "max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:32px;"
        ):
            _render_providers_section()
            _render_models_section()
            _render_defaults_section()


# ---------------------------------------------------------------------------
# Provider Management
# ---------------------------------------------------------------------------

def _render_providers_section() -> None:
    section = ui.element("div").style(
        "background:#1E1E1E;border:1px solid #2D2D2D;border-radius:8px;overflow:hidden;"
    )
    with section:
        with ui.element("div").style(
            "padding:16px 24px;border-bottom:1px solid #2D2D2D;background:#121212;"
            "display:flex;align-items:center;justify-content:space-between;"
        ):
            ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Provider Management</span>')
            add_btn = ui.element("button").classes("rl-btn-secondary").style("width:auto;")
            with add_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:16px;">add</span> Add Provider')

        table_area = ui.element("div").style("padding:24px;")
        add_form_area = ui.element("div").style("padding:0 24px 24px;display:none;")
        add_form_area.props('data-provider-form=""')

        def _refresh_table():
            table_area.clear()
            with table_area:
                _build_provider_table()

        def _toggle_add_form():
            ui.run_javascript(
                'var el = document.querySelector("[data-provider-form]");'
                'el.style.display = el.style.display === "none" ? "block" : "none";'
            )

        add_btn.on("click", _toggle_add_form)

        with add_form_area:
            _build_add_provider_form(lambda: _refresh_table())

        _refresh_table()


def _build_provider_table() -> None:
    providers = _db().list_providers()
    if not providers:
        ui.html('<p style="color:var(--on-surface-variant);font-size:13px;">No providers configured.</p>')
        return

    with ui.element("table").style("width:100%;border-collapse:collapse;"):
        with ui.element("thead"):
            with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                for col in ["Name", "Base URL", "API Key", "Actions"]:
                    with ui.element("th").style(
                        "padding:8px;text-align:left;font-size:11px;font-weight:700;"
                        "text-transform:uppercase;letter-spacing:0.05em;color:var(--on-surface-variant);"
                    ):
                        ui.html(col)
        with ui.element("tbody"):
            for pid, name, api_key, base_url, _ in providers:
                masked = (api_key[:4] + "****") if api_key and len(api_key) > 4 else "****"
                with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                    for val in [name, base_url or "—", masked]:
                        with ui.element("td").style(
                            "padding:12px 8px;font-family:'JetBrains Mono',monospace;"
                            "font-size:13px;color:var(--on-surface);"
                        ):
                            ui.html(val)
                    with ui.element("td").style("padding:12px 8px;text-align:right;"):
                        del_btn = ui.element("button").style(
                            "background:none;border:none;cursor:pointer;color:var(--on-surface-variant);"
                        )
                        with del_btn:
                            ui.html('<span class="material-symbols-outlined" style="font-size:18px;">delete</span>')
                        del_btn.on("click", lambda n=name: _delete_provider(n))


def _build_add_provider_form(on_save) -> None:
    with ui.element("div").style(
        "background:#121212;border:1px solid #2D2D2D;border-radius:8px;padding:16px;"
        "display:flex;flex-direction:column;gap:12px;"
    ):
        ui.html('<span style="font-size:13px;font-weight:700;color:var(--on-surface-variant);">ADD PROVIDER</span>')
        name_in = ui.input(label="Name").props("outlined dense").classes("w-full")
        key_in = ui.input(label="API Key", password=True).props("outlined dense").classes("w-full")
        url_in = ui.input(label="Base URL (optional)").props("outlined dense").classes("w-full")

        def _save():
            name = name_in.value.strip()
            key = key_in.value.strip()
            url = url_in.value.strip() or None
            if not name or not key:
                ui.notify("Name and API Key required", type="warning")
                return
            try:
                _db().add_provider(name, key, url)
                name_in.value = ""
                key_in.value = ""
                url_in.value = ""
                ui.notify("Provider saved", type="positive")
                on_save()
            except Exception as e:
                ui.notify(str(e), type="negative")

        ui.button("Save", on_click=_save).props("dense").style(
            "background:var(--primary);color:var(--on-primary);border-radius:8px;"
        )


def _delete_provider(name: str) -> None:
    _db().remove_provider(name)
    ui.notify(f"Provider '{name}' deleted", type="positive")
    ui.navigate.reload()


# ---------------------------------------------------------------------------
# Model Management
# ---------------------------------------------------------------------------

def _render_models_section() -> None:
    section = ui.element("div").style(
        "background:#1E1E1E;border:1px solid #2D2D2D;border-radius:8px;overflow:hidden;"
    )
    with section:
        with ui.element("div").style(
            "padding:16px 24px;border-bottom:1px solid #2D2D2D;background:#121212;"
            "display:flex;align-items:center;justify-content:space-between;"
        ):
            ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Model Management</span>')
            add_btn = ui.element("button").classes("rl-btn-secondary").style("width:auto;")
            with add_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:16px;">add</span> Add Model')

        table_area = ui.element("div").style("padding:24px;")
        add_form_area = ui.element("div").style("padding:0 24px 24px;display:none;")
        add_form_area.props('data-model-form=""')

        def _refresh():
            table_area.clear()
            with table_area:
                _build_model_table()

        def _toggle():
            ui.run_javascript(
                'var el = document.querySelector("[data-model-form]");'
                'el.style.display = el.style.display === "none" ? "block" : "none";'
            )

        add_btn.on("click", _toggle)

        with add_form_area:
            _build_add_model_form(lambda: _refresh())

        _refresh()


def _build_model_table() -> None:
    models = _db().list_models()
    providers = {p[0]: p[1] for p in _db().list_providers()}
    if not models:
        ui.html('<p style="color:var(--on-surface-variant);font-size:13px;">No models configured.</p>')
        return

    with ui.element("table").style("width:100%;border-collapse:collapse;"):
        with ui.element("thead"):
            with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                for col in ["Model Name", "Provider", "Type", "Actions"]:
                    with ui.element("th").style(
                        "padding:8px;text-align:left;font-size:11px;font-weight:700;"
                        "text-transform:uppercase;letter-spacing:0.05em;color:var(--on-surface-variant);"
                    ):
                        ui.html(col)
        with ui.element("tbody"):
            for mid, pid, mname, mtype, _ in models:
                pname = providers.get(pid, str(pid))
                with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                    for val in [mname, pname, mtype or "embedding"]:
                        with ui.element("td").style(
                            "padding:12px 8px;font-family:'JetBrains Mono',monospace;"
                            "font-size:13px;color:var(--on-surface);"
                        ):
                            ui.html(val)
                    with ui.element("td").style(
                        "padding:12px 8px;display:flex;gap:8px;justify-content:flex-end;"
                    ):
                        test_btn = ui.element("button").style(
                            "background:none;border:none;cursor:pointer;color:var(--on-surface-variant);"
                        )
                        with test_btn:
                            ui.html('<span class="material-symbols-outlined" style="font-size:18px;">play_arrow</span>')
                        test_btn.on("click", lambda m=mid: _test_model(m))

                        del_btn = ui.element("button").style(
                            "background:none;border:none;cursor:pointer;color:var(--on-surface-variant);"
                        )
                        with del_btn:
                            ui.html('<span class="material-symbols-outlined" style="font-size:18px;">delete</span>')
                        del_btn.on("click", lambda m=mid: _delete_model(m))


def _build_add_model_form(on_save) -> None:
    providers = _db().list_providers()
    provider_opts = {str(p[0]): p[1] for p in providers}

    with ui.element("div").style(
        "background:#121212;border:1px solid #2D2D2D;border-radius:8px;padding:16px;"
        "display:flex;flex-direction:column;gap:12px;"
    ):
        ui.html('<span style="font-size:13px;font-weight:700;color:var(--on-surface-variant);">ADD MODEL</span>')
        prov_sel = ui.select(
            label="Provider", options=provider_opts, with_input=True
        ).props("outlined dense").classes("w-full")
        model_in = ui.input(label="Model Name").props("outlined dense").classes("w-full")

        def _save():
            pid_str = prov_sel.value
            mname = model_in.value.strip()
            if not pid_str or not mname:
                ui.notify("Provider and model name required", type="warning")
                return
            try:
                _db().add_model(int(pid_str), mname)
                model_in.value = ""
                ui.notify("Model saved", type="positive")
                on_save()
            except Exception as e:
                ui.notify(str(e), type="negative")

        ui.button("Save", on_click=_save).props("dense").style(
            "background:var(--primary);color:var(--on-primary);border-radius:8px;"
        )


def _test_model(model_id: int) -> None:
    models = _db().list_models()
    providers = {p[0]: p for p in _db().list_providers()}
    for mid, pid, mname, _, _ in models:
        if mid == model_id:
            p = providers.get(pid)
            if not p:
                ui.notify("Provider not found", type="negative")
                return
            _, pname, api_key, base_url, _ = p
            try:
                from raglab.core.embedder import Embedder
                emb = Embedder()
                emb.configure(pname, api_key, mname, base_url)
                vec = emb.embed("test embedding")
                ui.notify(
                    f"OK — dim={len(vec)}, first=[{vec[0]:.4f}, {vec[1]:.4f}, ...]",
                    type="positive"
                )
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")
            return


def _delete_model(model_id: int) -> None:
    db = _db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
    db.conn.commit()
    ui.notify("Model deleted", type="positive")
    ui.navigate.reload()


# ---------------------------------------------------------------------------
# Default Parameters
# ---------------------------------------------------------------------------

def _render_defaults_section() -> None:
    section = ui.element("div").style(
        "background:#1E1E1E;border:1px solid #2D2D2D;border-radius:8px;overflow:hidden;"
    )
    with section:
        with ui.element("div").style(
            "padding:16px 24px;border-bottom:1px solid #2D2D2D;background:#121212;"
        ):
            ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Default Parameters</span>')

        with ui.element("div").style(
            "padding:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px;"
        ):
            db = _db()
            chunk_size = ui.number(
                label="Chunk Size",
                value=db.get_config("chunk_size") or 512,
                min=1,
            ).props("outlined dense")
            overlap = ui.number(
                label="Overlap",
                value=db.get_config("overlap") or 50,
                min=0,
            ).props("outlined dense")
            top_k = ui.number(
                label="Top-K",
                value=db.get_config("top_k") or 10,
                min=1,
            ).props("outlined dense")
            metric = ui.select(
                label="Default Metric",
                options=["cosine", "euclidean", "dot", "manhattan"],
                value=db.get_config("metric") or "cosine",
            ).props("outlined dense")

        with ui.element("div").style("padding:0 24px 24px;display:flex;justify-content:flex-end;"):
            def _save():
                d = _db()
                d.set_config("chunk_size", int(chunk_size.value))
                d.set_config("overlap", int(overlap.value))
                d.set_config("top_k", int(top_k.value))
                d.set_config("metric", metric.value)
                ui.notify("Saved", type="positive")

            ui.button("Save Changes", on_click=_save).style(
                "background:var(--primary-container);color:#000;border-radius:8px;"
                "padding:8px 32px;font-weight:600;border:none;cursor:pointer;"
            )
