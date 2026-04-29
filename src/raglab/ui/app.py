"""RagLab NiceGUI application: global layout with tab navigation."""

from nicegui import ui

from raglab.i18n import t
from raglab.ui.pages.evaluate import render_evaluate
from raglab.ui.pages.chunk_lab import render_chunk_lab
from raglab.ui.pages.settings import render_settings

# Custom CSS for dark elegant developer style
_CUSTOM_CSS = """
:root {
    --primary: #6366F1;
    --primary-dark: #4F46E5;
    --background: #1E1E2E;
    --surface: #2D2D3F;
    --surface-hover: #383850;
    --text-primary: #E0E0E0;
    --text-secondary: #A0A0B0;
    --border: #3D3D5F;
    --success: #10B981;
    --warning: #F59E0B;
    --error: #EF4444;
}

body {
    background-color: var(--background) !important;
    color: var(--text-primary) !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.q-card {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2) !important;
}

.q-input, .q-select, .q-toggle, .q-checkbox, .q-button, .q-table {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
}

.q-input:focus, .q-select:focus {
    border-color: var(--primary) !important;
}

.q-button {
    background-color: var(--primary) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    text-transform: none !important;
    transition: all 0.2s ease !important;
}

.q-button:hover {
    background-color: var(--primary-dark) !important;
    transform: translateY(-1px);
    box-shadow: 0 8px 16px -4px rgba(99, 102, 241, 0.4) !important;
}

.q-tab {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    text-transform: none !important;
}

.q-tab.q-tab--active {
    color: var(--primary) !important;
}

.q-tab__indicator {
    background-color: var(--primary) !important;
}

.q-table {
    background-color: var(--surface) !important;
    border: none !important;
}

.q-table th, .q-table td {
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
}

.q-upload {
    background-color: var(--surface) !important;
    border: 2px dashed var(--border) !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

.q-upload:hover {
    border-color: var(--primary) !important;
    background-color: var(--surface-hover) !important;
}

.text-gray-500 {
    color: var(--text-secondary) !important;
}

.q-notification {
    border-radius: 8px !important;
}

.q-toggle__inner {
    background-color: var(--border) !important;
}

.q-toggle__inner--active {
    background-color: var(--primary) !important;
}

.q-checkbox__inner {
    border-color: var(--border) !important;
}

.q-checkbox__inner--checked {
    background-color: var(--primary) !important;
    border-color: var(--primary) !important;
}

.q-textarea {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
}

.q-textarea:focus {
    border-color: var(--primary) !important;
}
"""


def create_app():
    """Create and return the NiceGUI application with all pages registered."""

    @ui.page("/")
    def index():
        # Enable dark mode
        ui.dark_mode(True)
        # Add custom CSS
        ui.add_head_html(f"<style>{_CUSTOM_CSS}</style>")
        # Top title bar
        ui.label("RagLab").classes("text-3xl font-bold mb-6 text-[var(--primary)]")

        # Tab navigation
        with ui.tabs() as tabs:
            ui.tab("evaluate", label=t("nav.evaluate"))
            ui.tab("chunk_lab", label=t("nav.chunk_lab"))
            ui.tab("settings", label=t("nav.settings"))

        with ui.tab_panels(tabs, value="evaluate").classes("w-full gap-6 mt-2"):
            with ui.tab_panel("evaluate"):
                render_evaluate()
            with ui.tab_panel("chunk_lab"):
                render_chunk_lab()
            with ui.tab_panel("settings"):
                render_settings()


def run_app(host: str = "0.0.0.0", port: int = 8080):
    """Create the app and start the NiceGUI server."""
    create_app()
    ui.run(host=host, port=port, title="RagLab", reload=False)
