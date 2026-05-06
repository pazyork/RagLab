"""RagLab NiceGUI application: IDE-style layout with sidebar navigation."""

from nicegui import ui
from raglab.i18n import set_lang, get_lang

_OBSIDIAN_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

:root {
    --bg: #000000;
    --surface-low: #1c1b1b;
    --surface: #201f1f;
    --surface-high: #2a2a2a;
    --surface-card: #121212;
    --surface-input: #050505;
    --primary: #8ed5ff;
    --primary-container: #38bdf8;
    --on-primary: #00354a;
    --secondary: #4edea3;
    --tertiary: #ffc176;
    --tertiary-container: #f1a02b;
    --error: #ffb4ab;
    --on-surface: #e5e2e1;
    --on-surface-variant: #bdc8d1;
    --outline: #87929a;
    --outline-variant: #3e484f;
    --border: #2D2D2D;
}

* { box-sizing: border-box; }
body {
    background: var(--bg) !important;
    color: var(--on-surface) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px; line-height: 1.43; margin: 0; overflow: hidden;
}
.material-symbols-outlined {
    font-family: 'Material Symbols Outlined' !important;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    font-size: 20px; line-height: 1; display: inline-block;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #050505; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--outline-variant); }

.q-card { background: var(--surface-card) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; box-shadow: none !important; }
.q-field__label { color: var(--on-surface-variant) !important; font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
.q-field__native, .q-field__input { color: var(--on-surface) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
.q-field--outlined .q-field__control { background: var(--surface-input) !important; border-color: var(--border) !important; border-radius: 4px !important; }
.q-field--outlined.q-field--focused .q-field__control { border-color: var(--primary) !important; }
.q-btn { text-transform: none !important; font-weight: 600 !important; }
.q-table { background: transparent !important; }
.q-table th { font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; color: var(--on-surface-variant) !important; border-bottom: 1px solid var(--border) !important; background: transparent !important; }
.q-table td { border-color: var(--border) !important; color: var(--on-surface) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }
.q-table tbody tr:hover { background: var(--surface-high) !important; }
.q-separator { background: var(--border) !important; }
.q-notification { border-radius: 4px !important; font-size: 13px !important; }
.q-menu { background: var(--surface-card) !important; border: 1px solid var(--border) !important; }
.q-item { color: var(--on-surface) !important; }
.q-item:hover { background: var(--surface-high) !important; }
.q-slider__inner { background: var(--primary) !important; }
.q-toggle__inner { background: var(--border) !important; }
.q-toggle__inner--active { background: var(--primary) !important; }

#rl-shell { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
#rl-header { height: 48px; background: var(--surface-low); border-bottom: 1px solid var(--outline-variant); display: flex; align-items: center; padding: 0 16px; flex-shrink: 0; gap: 16px; }
#rl-body { display: flex; flex: 1; overflow: hidden; }
#rl-sidebar { width: 64px; background: var(--surface-low); border-right: 1px solid var(--outline-variant); display: flex; flex-direction: column; align-items: center; padding: 16px 0; flex-shrink: 0; }
#rl-main { flex: 1; overflow: hidden; background: var(--bg); }

.rl-nav-btn { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 8px; cursor: pointer; color: var(--on-surface-variant); transition: all 0.15s; border: none; background: transparent; }
.rl-nav-btn:hover { background: var(--surface); color: var(--on-surface); }
.rl-nav-btn.active { background: var(--primary-container); color: #000; }
.rl-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--on-surface-variant); }
.rl-panel { background: var(--surface-low); border: 1px solid var(--outline-variant); border-radius: 12px; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.rl-card { background: var(--surface-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.rl-btn-primary { background: var(--primary); color: var(--on-primary); border: none; border-radius: 12px; padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; justify-content: center; transition: filter 0.15s; width: 100%; }
.rl-btn-primary:hover { filter: brightness(1.1); }
.rl-btn-secondary { background: var(--surface-card); color: var(--on-surface); border: 1px solid var(--border); border-radius: 4px; padding: 6px 12px; font-size: 13px; cursor: pointer; transition: border-color 0.15s; }
.rl-btn-secondary:hover { border-color: var(--primary); }
.rl-chunk-item { background: var(--surface-input); border: 1px solid var(--border); border-radius: 4px; padding: 8px; display: flex; flex-direction: column; gap: 4px; cursor: pointer; transition: border-color 0.15s; }
.rl-chunk-item:hover { border-color: var(--outline-variant); }
.rl-chunk-item.top { border-left: 2px solid var(--primary); background: #1E1E1E; }
.rl-score-badge { font-family: 'JetBrains Mono', monospace; font-size: 10px; padding: 2px 6px; border-radius: 4px; border: 1px solid; }
.rl-score-high { color: var(--secondary); border-color: #00a572; background: rgba(78,222,163,0.1); }
.rl-score-mid { color: var(--tertiary); border-color: var(--tertiary-container); background: rgba(255,193,118,0.1); }
.rl-view-toggle { display: flex; background: var(--surface-high); border-radius: 999px; padding: 4px; border: 1px solid var(--outline-variant); gap: 2px; }
.rl-view-btn { padding: 4px 16px; border-radius: 999px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; background: transparent; color: var(--on-surface-variant); display: flex; align-items: center; gap: 8px; transition: all 0.15s; }
.rl-view-btn.active { background: var(--primary-container); color: var(--on-primary); }
.rl-adhoc-tab { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 12px; }
.rl-adhoc-tab-btn { padding: 6px 16px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; background: transparent; color: var(--on-surface-variant); border-bottom: 2px solid transparent; transition: all 0.15s; }
.rl-adhoc-tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }
"""


def create_app():
    """Create and return the NiceGUI application."""

    @ui.page("/")
    def index():
        ui.dark_mode(True)
        ui.add_head_html(f"<style>{_OBSIDIAN_CSS}</style>")

        from raglab.ui.pages.playground import render_playground
        from raglab.ui.pages.datasets import render_datasets
        from raglab.ui.pages.settings import render_settings

        page_state = {"page": "playground", "view": "query_vs_chunks"}

        shell = ui.element("div").props('id="rl-shell"')
        with shell:
            header = ui.element("div").props('id="rl-header"')
            with header:
                ui.html('<span style="font-size:20px;font-weight:900;color:var(--on-surface);letter-spacing:-0.02em;">RAGLab</span>')
                view_toggle_area = ui.element("div").style("flex:1;display:flex;justify-content:center;")
                lang_area = ui.element("div").style("margin-left:auto;")

            body = ui.element("div").props('id="rl-body"')
            with body:
                sidebar = ui.element("nav").props('id="rl-sidebar"')
                main_area = ui.element("div").props('id="rl-main"')

        def _navigate(page: str):
            page_state["page"] = page
            sidebar.clear()
            with sidebar:
                _build_sidebar(page_state, _navigate)
            view_toggle_area.clear()
            if page == "playground":
                with view_toggle_area:
                    _build_view_toggle(page_state, main_area)
            main_area.clear()
            with main_area:
                if page == "playground":
                    render_playground(page_state)
                elif page == "datasets":
                    render_datasets()
                elif page == "settings":
                    render_settings()

        with sidebar:
            _build_sidebar(page_state, _navigate)
        with view_toggle_area:
            _build_view_toggle(page_state, main_area)
        with lang_area:
            lang_btn = ui.button(
                "EN" if get_lang() == "zh" else "中文",
            ).props("flat dense").style("color:var(--on-surface-variant);font-size:13px;")
            lang_btn.on_click(lambda: set_lang("en" if get_lang() == "zh" else "zh"))
        with main_area:
            render_playground(page_state)


def _build_sidebar(page_state: dict, navigate_fn):
    top = ui.element("div").style(
        "display:flex;flex-direction:column;gap:8px;width:100%;align-items:center;"
    )
    with top:
        for pid, icon in [("playground", "science"), ("datasets", "database")]:
            active = " active" if page_state["page"] == pid else ""
            btn = ui.element("button").classes(f"rl-nav-btn{active}").props(f'title="{pid.capitalize()}"')
            with btn:
                ui.html(f'<span class="material-symbols-outlined">{icon}</span>')
            btn.on("click", lambda p=pid: navigate_fn(p))

    bottom = ui.element("div").style(
        "margin-top:auto;width:100%;display:flex;justify-content:center;"
        "border-top:1px solid var(--outline-variant);padding-top:12px;"
    )
    with bottom:
        active = " active" if page_state["page"] == "settings" else ""
        btn = ui.element("button").classes(f"rl-nav-btn{active}").props('title="Settings"')
        with btn:
            ui.html('<span class="material-symbols-outlined">settings</span>')
        btn.on("click", lambda: navigate_fn("settings"))


def _build_view_toggle(page_state: dict, main_area):
    with ui.element("div").classes("rl-view-toggle"):
        for vid, icon, label in [
            ("query_vs_chunks", "compare_arrows", "Query vs Chunks"),
            ("chunk_vs_chunk", "grid_view", "Chunk vs Chunk"),
        ]:
            active = " active" if page_state["view"] == vid else ""
            btn = ui.element("button").classes(f"rl-view-btn{active}")
            with btn:
                ui.html(f'<span class="material-symbols-outlined" style="font-size:16px;">{icon}</span> {label}')

            def _switch(v=vid):
                page_state["view"] = v
                from raglab.ui.pages.playground import render_playground
                main_area.clear()
                with main_area:
                    render_playground(page_state)

            btn.on("click", _switch)


def run_app(host: str = "0.0.0.0", port: int = 8080):
    """Create the app and start the NiceGUI server."""
    create_app()
    ui.run(host=host, port=port, title="RagLab", reload=False, storage_secret="raglab-secret")
