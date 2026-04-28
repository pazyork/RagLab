"""Settings page: provider management, model management, default params, language toggle."""

from nicegui import ui, app

from raglab.storage.db import Database
from raglab.i18n import t, set_lang, get_lang


_DEFAULTS = {
    "chunk_size": 512,
    "overlap": 50,
    "top_k": 10,
    "metric": "cosine",
}


def _db() -> Database:
    """Return a Database instance (re-entrant; each call opens its own connection)."""
    return Database()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _provider_rows() -> list[dict]:
    """Return provider rows suitable for ui.table."""
    rows = []
    for p in _db().list_providers():
        pid, name, api_key, base_url, _ = p
        masked = api_key[:4] + "****" if api_key and len(api_key) > 4 else "****"
        rows.append({"id": pid, "name": name, "api_key": masked, "base_url": base_url or ""})
    return rows


def _provider_columns() -> list[dict]:
    return [
        {"name": "id", "label": "ID", "field": "id", "align": "center", "style": "width:50px"},
        {"name": "name", "label": t("label.name"), "field": "name", "align": "left"},
        {"name": "api_key", "label": t("label.api_key"), "field": "api_key", "align": "left"},
        {"name": "base_url", "label": t("label.base_url"), "field": "base_url", "align": "left"},
    ]


def _model_rows() -> list[dict]:
    rows = []
    for m in _db().list_models():
        mid, provider_id, model_name, model_type, _ = m
        rows.append({"id": mid, "provider_id": provider_id, "model_name": model_name, "model_type": model_type})
    return rows


def _model_columns() -> list[dict]:
    return [
        {"name": "id", "label": "ID", "field": "id", "align": "center", "style": "width:50px"},
        {"name": "provider_id", "label": t("label.provider") + " ID", "field": "provider_id", "align": "center"},
        {"name": "model_name", "label": t("label.model"), "field": "model_name", "align": "left"},
        {"name": "model_type", "label": "Type", "field": "model_type", "align": "center"},
    ]


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_settings() -> None:
    """Render the Settings page into the current NiceGUI page."""

    # ---- Section: Language Toggle ----
    with ui.card().classes("w-full"):
        ui.label(t("label.language")).classes("text-lg font-bold")
        lang_toggle = ui.toggle({"zh": "中文", "en": "English"},
                                value=get_lang(),
                                on_change=lambda e: _on_lang_change(e, refresh_area))

    # Placeholder that we can refresh when language changes
    refresh_area = ui.column().classes("w-full gap-4")

    with refresh_area:
        _render_providers_section()
        _render_models_section()
        _render_test_section()
        _render_defaults_section()


def _on_lang_change(e, refresh_area) -> None:
    """Handle language toggle: update i18n, then re-render the whole settings area."""
    set_lang(e.value)
    # Store in app.storage.user so other pages can pick it up
    app.storage.user["lang"] = e.value
    refresh_area.clear()
    with refresh_area:
        _render_providers_section()
        _render_models_section()
        _render_test_section()
        _render_defaults_section()


# ---------------------------------------------------------------------------
# Provider section
# ---------------------------------------------------------------------------

def _render_providers_section() -> None:
    with ui.card().classes("w-full"):
        ui.label(t("label.provider")).classes("text-lg font-bold")

        provider_table = ui.table(
            columns=_provider_columns(),
            rows=_provider_rows(),
            row_key="id",
        ).classes("w-full")

        # --- Add provider form ---
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            name_input = ui.input(label=t("label.name")).props("dense").classes("flex-1")
            key_input = ui.input(label=t("label.api_key"), password=True).props("dense").classes("flex-1")
            url_input = ui.input(label=t("label.base_url")).props("dense").classes("flex-1")

            async def _add_provider():
                name = name_input.value.strip()
                key = key_input.value.strip()
                url = url_input.value.strip() or None
                if not name or not key:
                    ui.notify("Name and API Key are required", type="warning")
                    return
                try:
                    _db().add_provider(name, key, url)
                    name_input.value = ""
                    key_input.value = ""
                    url_input.value = ""
                    provider_table.rows = _provider_rows()
                    provider_table.update()
                    ui.notify(t("msg.saved"), type="positive")
                except Exception as exc:
                    ui.notify(str(exc), type="negative")

            ui.button(t("btn.add"), on_click=_add_provider).props("dense")

        # --- Delete provider ---
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            del_name = ui.input(label=t("label.name")).props("dense").classes("flex-1")

            dialog = ui.dialog()
            with dialog:
                ui.label(t("msg.confirm_delete")).classes("text-body1")
                with ui.row():
                    ui.button(t("btn.delete"), on_click=lambda: _confirm_delete(del_name, dialog, provider_table))
                    ui.button("Cancel", on_click=dialog.close)

            async def _ask_delete():
                if not del_name.value.strip():
                    ui.notify("Enter a provider name", type="warning")
                    return
                dialog.open()

            ui.button(t("btn.delete"), on_click=_ask_delete).props("dense color=negative")


def _confirm_delete(del_name, dialog, provider_table) -> None:
    name = del_name.value.strip()
    _db().remove_provider(name)
    del_name.value = ""
    dialog.close()
    provider_table.rows = _provider_rows()
    provider_table.update()
    ui.notify(t("msg.saved"), type="positive")


# ---------------------------------------------------------------------------
# Model section
# ---------------------------------------------------------------------------

def _render_models_section() -> None:
    with ui.card().classes("w-full"):
        ui.label(t("label.model")).classes("text-lg font-bold")

        model_table = ui.table(
            columns=_model_columns(),
            rows=_model_rows(),
            row_key="id",
        ).classes("w-full")

        # Add model form
        with ui.row().classes("w-full items-end gap-2 mt-2"):
            providers = _db().list_providers()
            provider_opts = {str(p[0]): p[1] for p in providers}  # id -> name

            prov_select = ui.select(
                label=t("label.provider"),
                options=provider_opts,
                with_input=True,
            ).props("dense").classes("flex-1")

            model_input = ui.input(label=t("label.model")).props("dense").classes("flex-1")

            async def _add_model():
                pid_str = prov_select.value
                model_name = model_input.value.strip()
                if not pid_str or not model_name:
                    ui.notify("Provider and model name are required", type="warning")
                    return
                try:
                    _db().add_model(int(pid_str), model_name)
                    model_input.value = ""
                    model_table.rows = _model_rows()
                    model_table.update()
                    ui.notify(t("msg.saved"), type="positive")
                except Exception as exc:
                    ui.notify(str(exc), type="negative")

            ui.button(t("btn.add"), on_click=_add_model).props("dense")


# ---------------------------------------------------------------------------
# Quick Test section
# ---------------------------------------------------------------------------

def _render_test_section() -> None:
    with ui.card().classes("w-full"):
        ui.label(t("btn.test") + " " + t("label.model")).classes("text-lg font-bold")

        with ui.row().classes("w-full items-end gap-2"):
            # Build model options from DB
            models = _db().list_models()
            providers = {p[0]: p[1] for p in _db().list_providers()}
            model_opts = {}
            for m in models:
                mid, pid, mname, mtype, _ = m
                prov_name = providers.get(pid, str(pid))
                model_opts[str(mid)] = f"{prov_name}/{mname}"

            model_select = ui.select(
                label=t("label.model"),
                options=model_opts,
                with_input=True,
            ).props("dense").classes("flex-1")

            test_input = ui.input(label=t("label.query")).props("dense").classes("flex-1")

        result_label = ui.label("").classes("mt-2 text-sm")

        async def _run_test():
            mid_str = model_select.value
            text = test_input.value.strip()
            if not mid_str or not text:
                ui.notify(t("msg.no_model"), type="warning")
                return
            try:
                from raglab.core.embedder import Embedder
                emb = Embedder()
                # Look up provider info for this model
                models_list = _db().list_models()
                providers_list = _db().list_providers()
                prov_map = {p[0]: p for p in providers_list}
                for m in models_list:
                    if str(m[0]) == mid_str:
                        pid = m[1]
                        mname = m[2]
                        p = prov_map.get(pid)
                        if p:
                            _, pname, api_key, base_url, _ = p
                            emb.configure(pname, api_key, mname, base_url)
                        break
                vec = emb.embed(text)
                dim = len(vec)
                preview = ", ".join(f"{v:.4f}" for v in vec[:5])
                result_label.text = f"dim={dim}  [{preview}, ...]"
                ui.notify(t("msg.complete"), type="positive")
            except Exception as exc:
                result_label.text = f"{t('msg.error_api')}: {exc}"
                ui.notify(t("msg.error_api"), type="negative")

        ui.button(t("btn.test"), on_click=_run_test).props("dense").classes("mt-2")


# ---------------------------------------------------------------------------
# Default Params section
# ---------------------------------------------------------------------------

def _render_defaults_section() -> None:
    with ui.card().classes("w-full"):
        ui.label(t("label.default_parameters")).classes("text-lg font-bold")

        db = _db()

        with ui.row().classes("w-full items-end gap-4"):
            chunk_size = ui.number(
                label=t("label.chunk_size"),
                value=db.get_config("chunk_size") or _DEFAULTS["chunk_size"],
                min=1,
            ).props("dense")

            overlap = ui.number(
                label=t("label.overlap"),
                value=db.get_config("overlap") or _DEFAULTS["overlap"],
                min=0,
            ).props("dense")

            top_k = ui.number(
                label=t("label.top_k"),
                value=db.get_config("top_k") or _DEFAULTS["top_k"],
                min=1,
            ).props("dense")

            metric = ui.select(
                label=t("label.metric"),
                options=["cosine", "euclidean", "dot", "manhattan"],
                value=db.get_config("metric") or _DEFAULTS["metric"],
            ).props("dense")

        async def _save_defaults():
            d = _db()
            d.set_config("chunk_size", int(chunk_size.value))
            d.set_config("overlap", int(overlap.value))
            d.set_config("top_k", int(top_k.value))
            d.set_config("metric", metric.value)
            ui.notify(t("msg.saved"), type="positive")

        ui.button(t("btn.save"), on_click=_save_defaults).props("dense").classes("mt-2")
