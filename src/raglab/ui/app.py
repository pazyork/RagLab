"""RagLab NiceGUI application: global layout with tab navigation."""

from nicegui import ui

from raglab.i18n import t
from raglab.ui.pages.evaluate import render_evaluate
from raglab.ui.pages.chunk_lab import render_chunk_lab
from raglab.ui.pages.settings import render_settings

# Material Design 3 inspired dark theme for RagLab
_CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400&display=swap');

:root {
    /* Material Design 3 Color Tokens */
    --md-sys-color-primary: #8ed5ff;
    --md-sys-color-primary-container: #38bdf8;
    --md-sys-color-on-primary: #00354a;
    --md-sys-color-on-primary-container: #004965;
    --md-sys-color-secondary: #4edea3;
    --md-sys-color-secondary-container: #00a572;
    --md-sys-color-on-secondary: #003824;
    --md-sys-color-on-secondary-container: #00311f;
    --md-sys-color-tertiary: #ffc176;
    --md-sys-color-tertiary-container: #f1a02b;
    --md-sys-color-error: #ffb4ab;
    --md-sys-color-error-container: #93000a;
    --md-sys-color-background: #131313;
    --md-sys-color-on-background: #e5e2e1;
    --md-sys-color-surface: #131313;
    --md-sys-color-on-surface: #e5e2e1;
    --md-sys-color-on-surface-variant: #bdc8d1;
    --md-sys-color-surface-container-lowest: #0e0e0e;
    --md-sys-color-surface-container-low: #1c1b1b;
    --md-sys-color-surface-container: #201f1f;
    --md-sys-color-surface-container-high: #2a2a2a;
    --md-sys-color-surface-container-highest: #353534;
    --md-sys-color-surface-bright: #393939;
    --md-sys-color-surface-dim: #131313;
    --md-sys-color-surface-tint: #7bd0ff;
    --md-sys-color-outline: #87929a;
    --md-sys-color-outline-variant: #3e484f;
    --md-sys-color-inverse-surface: #e5e2e1;
    --md-sys-color-inverse-on-surface: #313030;
    --md-sys-color-inverse-primary: #00668a;

    /* Legacy vars (mapped to new system) */
    --primary: #8ed5ff;
    --primary-dark: #7bd0ff;
    --background: #131313;
    --surface: #201f1f;
    --surface-hover: #2a2a2a;
    --text-primary: #e5e2e1;
    --text-secondary: #bdc8d1;
    --border: #2D2D2D;
    --success: #4edea3;
    --warning: #ffc176;
    --error: #ffb4ab;
}

body {
    background-color: var(--background) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.43;
}

/* Material 3 Custom Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #050505;
}
::-webkit-scrollbar-thumb {
    background: #2D2D2D;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #3e484f;
}

/* Cards */
.q-card {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

/* Inputs */
.q-input, .q-select, .q-number {
    background-color: #050505 !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 4px !important;
}

.q-input:focus, .q-select:focus, .q-number:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 1px rgba(142, 213, 255, 0.2) !important;
}

.q-field__label {
    color: var(--text-secondary) !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* Buttons */
.q-button {
    background-color: var(--primary) !important;
    color: #000000 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: none !important;
    transition: all 0.2s ease !important;
    padding: 8px 16px !important;
}

.q-button:hover {
    filter: brightness(1.1);
    box-shadow: 0 4px 12px rgba(142, 213, 255, 0.2) !important;
}

/* Tabs */
.q-tab {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    text-transform: none !important;
    font-size: 14px !important;
}

.q-tab.q-tab--active {
    color: var(--primary) !important;
}

.q-tab__indicator {
    background-color: var(--primary) !important;
}

/* Tables */
.q-table {
    background-color: transparent !important;
    border: none !important;
}

.q-table th {
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: var(--text-secondary) !important;
    border-bottom: 1px solid var(--border) !important;
    background-color: transparent !important;
}

.q-table td {
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

.q-table tbody tr:hover {
    background-color: var(--surface-hover) !important;
}

/* Upload */
.q-upload {
    background-color: #050505 !important;
    border: 1px dashed var(--border) !important;
    border-radius: 4px !important;
    transition: all 0.2s ease !important;
}

.q-upload:hover {
    border-color: var(--primary) !important;
    background-color: var(--surface) !important;
}

/* Textarea */
.q-textarea {
    background-color: #050505 !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.q-textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 1px rgba(142, 213, 255, 0.2) !important;
}

/* Toggle & Checkbox */
.q-toggle__inner {
    background-color: #2D2D2D !important;
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

/* Notifications */
.q-notification {
    border-radius: 4px !important;
    font-size: 13px !important;
}

/* Chips / Badges */
.q-chip {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
}

/* Mono text */
.font-mono, code {
    font-family: 'JetBrains Mono', Menlo, monospace !important;
    font-size: 13px !important;
}

/* Utility */
.text-gray-500 {
    color: var(--text-secondary) !important;
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
