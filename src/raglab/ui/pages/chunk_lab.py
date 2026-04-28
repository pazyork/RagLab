"""Chunk Lab page: upload/paste text, live chunk preview, export results."""

import json

from nicegui import ui

from raglab.core.splitter import split_lines, split_by_char, split_by_recursive
from raglab.i18n import t


def _strategy_options() -> dict:
    """Return strategy key -> translated label."""
    return {
        "recursive": t("strategy.recursive"),
        "fixed": t("strategy.fixed"),
        "lines": t("strategy.lines"),
    }


def _do_split(text: str, strategy: str, chunk_size: int, overlap: int) -> list[str]:
    """Dispatch to the appropriate splitter function."""
    if strategy == "lines":
        return split_lines(text)
    elif strategy == "fixed":
        return split_by_char(text, chunk_size=chunk_size, overlap=overlap)
    elif strategy == "recursive":
        return split_by_recursive(text, chunk_size=chunk_size, chunk_overlap=overlap)
    else:
        return split_by_recursive(text, chunk_size=chunk_size, chunk_overlap=overlap)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_chunk_lab() -> None:
    """Render the Chunk Lab page into the current NiceGUI page."""

    # Reactive state stored on the page element scope
    state = {"text": "", "chunks": []}

    with ui.card().classes("w-full"):
        ui.label(t("nav.chunk_lab")).classes("text-xl font-bold")

        # ---- Upload area ----
        with ui.row().classes("w-full items-start gap-4"):
            # File upload
            upload_area = ui.column().classes("flex-1")
            with upload_area:
                ui.label("Upload text file").classes("text-sm font-semibold mb-1")

                async def _on_upload(e):
                    """Handle file upload: read content into textarea."""
                    content = e.content.read().decode("utf-8")
                    state["text"] = content
                    text_area.set_value(content)
                    _refresh_preview()

                ui.upload(
                    label=".txt",
                    auto_upload=True,
                    on_upload=_on_upload,
                ).props('accept=".txt"').classes("w-full")

            # Textarea for paste
            text_area = ui.textarea(
                label="Paste / edit text",
                value="",
            ).classes("flex-1 min-w-[300px]").props('rows=10').on(
                "update:model-value",
                lambda e: _on_text_change(e, state, text_area),
            )

    # ---- Controls: strategy + params ----
    with ui.card().classes("w-full"):
        ui.label(t("label.strategy")).classes("text-lg font-bold")

        with ui.row().classes("w-full items-end gap-4"):
            strategy_select = ui.select(
                label=t("label.strategy"),
                options=_strategy_options(),
                value="recursive",
            ).props("dense").classes("w-48")

            chunk_size_num = ui.number(
                label=t("label.chunk_size"),
                value=512,
                min=1,
            ).props("dense")

            overlap_num = ui.number(
                label=t("label.overlap"),
                value=50,
                min=0,
            ).props("dense")

            ui.button(t("btn.start"), on_click=lambda: _refresh_preview()).props("dense")

    # ---- Preview area ----
    with ui.card().classes("w-full"):
        ui.label("Preview").classes("text-lg font-bold")
        preview_container = ui.column().classes("w-full gap-1")

    # ---- Export button ----
    with ui.row().classes("w-full mt-2"):
        ui.button(t("btn.export"), on_click=lambda: _export(state)).props("dense")

    # ---- Internal helpers ----

    def _on_text_change(e, state, text_area):
        """Keep state in sync when the textarea value changes."""
        # NiceGUI 3.x passes the new value via e.args
        try:
            new_val = e.args.get("value", "") if hasattr(e, "args") else text_area.value
        except Exception:
            new_val = text_area.value
        state["text"] = new_val

    def _refresh_preview():
        """Run the splitter and render chunk previews."""
        text = state["text"] or text_area.value or ""
        strategy = strategy_select.value
        cs = int(chunk_size_num.value)
        ov = int(overlap_num.value)

        try:
            chunks = _do_split(text, strategy, cs, ov)
        except ValueError as exc:
            ui.notify(str(exc), type="warning")
            chunks = []

        state["chunks"] = chunks

        preview_container.clear()
        with preview_container:
            if not chunks:
                ui.label(t("msg.no_chunks")).classes("text-gray-500")
                return

            ui.label(f"{len(chunks)} chunks").classes("text-sm text-gray-400 mb-1")
            for i, chunk in enumerate(chunks):
                bg = "#f0f4ff" if i % 2 == 0 else "#fff8f0"
                with ui.card().classes(
                    f"w-full p-2"
                ).style(f"background-color: {bg}; border-radius: 4px;"):
                    ui.label(f"#{i + 1}").classes("text-xs text-gray-400 font-mono")
                    ui.label(chunk).classes("text-sm whitespace-pre-wrap break-words")

    def _export(state):
        """Export chunks as a JSON file download."""
        chunks = state.get("chunks", [])
        if not chunks:
            ui.notify(t("msg.no_chunks"), type="warning")
            return
        payload = {
            "count": len(chunks),
            "chunks": [{"index": i, "content": c} for i, c in enumerate(chunks)],
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        ui.download(data.encode("utf-8"), filename="chunks.json", media_type="application/json")
