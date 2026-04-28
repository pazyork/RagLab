"""RagLab NiceGUI application: global layout with tab navigation."""

from nicegui import ui, app

from raglab.i18n import t
from raglab.ui.pages.evaluate import render_evaluate
from raglab.ui.pages.chunk_lab import render_chunk_lab
from raglab.ui.pages.settings import render_settings


def create_app():
    """Create and return the NiceGUI application with all pages registered."""

    @ui.page("/")
    def index():
        # Top title bar
        ui.label("RagLab").classes("text-h4 font-bold")

        # Tab navigation
        with ui.tabs() as tabs:
            ui.tab("evaluate", label=t("nav.evaluate"))
            ui.tab("chunk_lab", label=t("nav.chunk_lab"))
            ui.tab("settings", label=t("nav.settings"))

        with ui.tab_panels(tabs, value="evaluate").classes("w-full"):
            with ui.tab_panel("evaluate"):
                render_evaluate()
            with ui.tab_panel("chunk_lab"):
                render_chunk_lab()
            with ui.tab_panel("settings"):
                render_settings()

    return app
