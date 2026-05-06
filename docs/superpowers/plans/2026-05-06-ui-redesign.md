# RagLab UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按照 Obsidian Sky 设计稿完全重构 RagLab UI，实现 Playground / Datasets / Settings 三页 IDE 风格布局。

**Architecture:** 全屏 sidebar + header 布局替换原有 tab 布局；新增 datasets.py 和 playground.py 页面；删除 chunk_lab.py 和 evaluate.py；Settings 合并 Provider+Model 管理。运行环境：`conda run -n mcp`。

**Tech Stack:** NiceGUI 3.11.1, matplotlib, scikit-learn (t-SNE), SQLite, Python 3.13

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| 完全重写 | `src/raglab/ui/app.py` |
| 新建 | `src/raglab/ui/pages/playground.py` |
| 新建 | `src/raglab/ui/pages/datasets.py` |
| 完全重写 | `src/raglab/ui/pages/settings.py` |
| 删除 | `src/raglab/ui/pages/evaluate.py` |
| 删除 | `src/raglab/ui/pages/chunk_lab.py` |
| 修改 | `src/raglab/ui/components/heatmap.py` |
| 删除 | `src/raglab/ui/components/leaderboard.py` |
| 修改 | `src/raglab/storage/db.py` (新增 delete_case 级联删除) |
| 修改 | `pyproject.toml` (新增 scikit-learn 依赖) |

---

## Task 1: 更新依赖 + DB 新增 delete_case

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/raglab/storage/db.py`
- Test: `tests/test_db_delete.py`

- [ ] **Step 1: 在 pyproject.toml 中添加 scikit-learn 依赖**

编辑 `pyproject.toml`，在 dependencies 列表末尾添加：
```toml
  "scikit-learn>=1.3",
```

- [ ] **Step 2: 在 db.py 中添加 delete_case 方法**

在 `src/raglab/storage/db.py` 的 `remove_case` 方法后面添加：

```python
def delete_case(self, case_id: int):
    """Delete a test case and cascade-delete its chunks and eval runs/scores."""
    cursor = self.conn.cursor()
    # eval_scores cascade from eval_runs via FK ON DELETE CASCADE
    cursor.execute("DELETE FROM eval_runs WHERE case_id = ?", (case_id,))
    # case_chunks cascade from test_cases via FK ON DELETE CASCADE
    cursor.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
    self.conn.commit()
```

- [ ] **Step 3: 写失败测试**

新建 `tests/test_db_delete.py`：

```python
import pytest
from raglab.storage.db import Database

def test_delete_case_cascades():
    db = Database(":memory:")
    pid = db.add_provider("p", "key")
    cid = db.add_case("c1", "desc")
    db.add_chunks(cid, ["chunk a", "chunk b"])
    rid = db.add_run(cid, "run1", "model1")
    db.add_scores(rid, [(0, 0.9, 1), (1, 0.8, 2)])

    db.delete_case(cid)

    assert db.get_case(cid) is None
    assert db.get_chunks(cid) == []
    assert db.list_runs(cid) == []
```

- [ ] **Step 4: 运行测试确认失败**

```bash
conda run -n mcp python3 -m pytest tests/test_db_delete.py -v
```
Expected: FAIL（delete_case 方法不存在）

- [ ] **Step 5: 运行测试确认通过**

```bash
conda run -n mcp python3 -m pytest tests/test_db_delete.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/raglab/storage/db.py tests/test_db_delete.py
git commit -m "feat(db): add delete_case with cascade, add scikit-learn dep"
```

---

## Task 2: app.py — 全局 IDE 布局（Sidebar + Header）

**Files:**
- Rewrite: `src/raglab/ui/app.py`

- [ ] **Step 1: 完全重写 app.py**

用以下内容替换 `src/raglab/ui/app.py` 全部内容：

```python
"""RagLab NiceGUI application: IDE-style layout with sidebar navigation."""

from nicegui import ui
from raglab.i18n import t, set_lang, get_lang

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
.rl-input { width: 100%; background: var(--surface-input); border: 1px solid var(--border); border-radius: 4px; padding: 8px 12px; color: var(--on-surface); font-family: 'JetBrains Mono', monospace; font-size: 13px; outline: none; transition: border-color 0.15s; }
.rl-input:focus { border-color: var(--primary); }
.rl-select { width: 100%; background: var(--surface-input); border: 1px solid var(--border); border-radius: 4px; padding: 8px 12px; color: var(--on-surface); font-size: 13px; outline: none; appearance: none; }
.rl-select:focus { border-color: var(--primary); }
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

        # Shared reactive state
        page_state = {"page": "playground", "view": "query_vs_chunks"}

        shell = ui.element("div").props('id="rl-shell"')
        with shell:
            # ---- Header ----
            header = ui.element("div").props('id="rl-header"')
            with header:
                ui.html('<span style="font-size:20px;font-weight:900;color:var(--on-surface);letter-spacing:-0.02em;">RAGLab</span>')
                view_toggle_area = ui.element("div").style("flex:1;display:flex;justify-content:center;")
                lang_area = ui.element("div").style("margin-left:auto;")

            # ---- Body ----
            body = ui.element("div").props('id="rl-body"')
            with body:
                # Sidebar
                sidebar = ui.element("nav").props('id="rl-sidebar"')
                # Main
                main_area = ui.element("div").props('id="rl-main"')

        def _navigate(page: str):
            page_state["page"] = page
            # Rebuild sidebar active states
            sidebar.clear()
            with sidebar:
                _build_sidebar(page_state, _navigate)
            # Rebuild view toggle visibility
            view_toggle_area.clear()
            if page == "playground":
                with view_toggle_area:
                    _build_view_toggle(page_state, main_area)
            # Rebuild main content
            main_area.clear()
            with main_area:
                if page == "playground":
                    render_playground(page_state)
                elif page == "datasets":
                    render_datasets()
                elif page == "settings":
                    render_settings()

        # Initial render
        with sidebar:
            _build_sidebar(page_state, _navigate)
        with view_toggle_area:
            _build_view_toggle(page_state, main_area)
        with lang_area:
            from raglab.i18n import get_lang, set_lang
            lang_btn = ui.button(
                "EN" if get_lang() == "zh" else "中文",
            ).props("flat dense").style("color:var(--on-surface-variant);font-size:13px;")
            lang_btn.on_click(lambda: set_lang("en" if get_lang() == "zh" else "zh"))
        with main_area:
            render_playground(page_state)


def _build_sidebar(page_state: dict, navigate_fn):
    """Build sidebar nav buttons."""
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
    """Build Query vs Chunks / Chunk vs Chunk toggle."""
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
```

- [ ] **Step 2: 启动服务验证页面不报错**

```bash
pkill -f "raglab serve" 2>/dev/null; sleep 1
conda run -n mcp python3 -m raglab serve --port 8098 &
sleep 3
curl -s http://localhost:8098 | grep -c "RAGLab"
```
Expected: 输出 `1`

- [ ] **Step 3: Commit**

```bash
git add src/raglab/ui/app.py
git commit -m "feat(ui): rewrite app.py with IDE sidebar+header layout"
```

---

## Task 3: settings.py — Provider + Model 管理

**Files:**
- Rewrite: `src/raglab/ui/pages/settings.py`

- [ ] **Step 1: 完全重写 settings.py**

```python
"""Settings page: Provider management, Model management, Default parameters."""

from nicegui import ui
from raglab.storage.db import Database
from raglab.i18n import t


def _db() -> Database:
    return Database()


def render_settings() -> None:
    """Render Settings page into current NiceGUI context."""
    with ui.element("div").style(
        "height:100%;overflow-y:auto;padding:32px;"
    ):
        with ui.element("div").style("max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:32px;"):
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
        # Header
        with ui.element("div").style(
            "padding:16px 24px;border-bottom:1px solid #2D2D2D;background:#121212;"
            "display:flex;align-items:center;justify-content:space-between;"
        ):
            ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Provider Management</span>')
            add_btn = ui.element("button").classes("rl-btn-secondary").style("width:auto;")
            with add_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:16px;">add</span> Add Provider')

        # Table
        table_area = ui.element("div").style("padding:24px;")
        add_form_area = ui.element("div").style("padding:0 24px 24px;display:none;")

        def _refresh_table():
            table_area.clear()
            with table_area:
                _build_provider_table(add_form_area)

        def _toggle_add_form():
            # Toggle display via JS
            ui.run_javascript(
                'var el = document.querySelector("[data-provider-form]");'
                'el.style.display = el.style.display === "none" ? "block" : "none";'
            )

        add_btn.on("click", _toggle_add_form)
        add_form_area.props('data-provider-form=""')

        with add_form_area:
            _build_add_provider_form(lambda: _refresh_table())

        _refresh_table()


def _build_provider_table(add_form_area) -> None:
    providers = _db().list_providers()
    if not providers:
        ui.html('<p style="color:var(--on-surface-variant);font-size:13px;">No providers configured.</p>')
        return

    with ui.element("table").style("width:100%;border-collapse:collapse;"):
        with ui.element("thead"):
            with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                for col in ["Name", "Base URL", "API Key", "Actions"]:
                    ui.element("th").style(
                        "padding:8px;text-align:left;font-size:11px;font-weight:700;"
                        "text-transform:uppercase;letter-spacing:0.05em;color:var(--on-surface-variant);"
                    ).text = col
        with ui.element("tbody"):
            for pid, name, api_key, base_url, _ in providers:
                masked = (api_key[:4] + "****") if api_key and len(api_key) > 4 else "****"
                with ui.element("tr").style(
                    "border-bottom:1px solid #2D2D2D;transition:background 0.15s;"
                ):
                    for val in [name, base_url or "—", masked]:
                        ui.element("td").style(
                            "padding:12px 8px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--on-surface);"
                        ).text = val
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
                    ui.element("th").style(
                        "padding:8px;text-align:left;font-size:11px;font-weight:700;"
                        "text-transform:uppercase;letter-spacing:0.05em;color:var(--on-surface-variant);"
                    ).text = col
        with ui.element("tbody"):
            for mid, pid, mname, mtype, _ in models:
                pname = providers.get(pid, str(pid))
                with ui.element("tr").style("border-bottom:1px solid #2D2D2D;"):
                    for val in [mname, pname, mtype or "embedding"]:
                        ui.element("td").style(
                            "padding:12px 8px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--on-surface);"
                        ).text = val
                    with ui.element("td").style("padding:12px 8px;text-align:right;display:flex;gap:8px;justify-content:flex-end;"):
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
        prov_sel = ui.select(label="Provider", options=provider_opts, with_input=True).props("outlined dense").classes("w-full")
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
                ui.notify(f"OK — dim={len(vec)}, first=[{vec[0]:.4f}, {vec[1]:.4f}, ...]", type="positive")
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

        with ui.element("div").style("padding:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px;"):
            db = _db()
            chunk_size = ui.number(
                label="Chunk Size", value=db.get_config("chunk_size") or 512, min=1
            ).props("outlined dense")
            overlap = ui.number(
                label="Overlap", value=db.get_config("overlap") or 50, min=0
            ).props("outlined dense")
            top_k = ui.number(
                label="Top-K", value=db.get_config("top_k") or 10, min=1
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
                "padding:8px 32px;font-weight:600;"
            )
```

- [ ] **Step 2: 删除旧文件，验证导入**

```bash
conda run -n mcp python3 -c "from raglab.ui.pages.settings import render_settings; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/raglab/ui/pages/settings.py
git commit -m "feat(ui): rewrite settings page with provider+model management"
```

---

## Task 4: datasets.py — 数据集管理（三栏布局）

**Files:**
- Create: `src/raglab/ui/pages/datasets.py`

- [ ] **Step 1: 新建 datasets.py**

```python
"""Datasets page: three-column layout for dataset/source/chunking management."""

import json
from datetime import datetime
from nicegui import ui
from raglab.storage.db import Database
from raglab.core.splitter import split_lines, split_by_char, split_by_recursive


def _db() -> Database:
    return Database()


def render_datasets() -> None:
    """Render Datasets page into current NiceGUI context."""
    state = {
        "active_case_id": None,
        "active_source_idx": None,  # index into sources list for active case
    }

    with ui.element("div").style("display:flex;height:100%;overflow:hidden;"):
        # Left: dataset list
        left = ui.element("section").style(
            "width:220px;min-width:200px;max-width:250px;border-right:1px solid var(--outline-variant);"
            "display:flex;flex-direction:column;background:#000;flex-shrink:0;"
        )
        # Middle: sources list
        mid = ui.element("section").style(
            "width:280px;min-width:250px;max-width:300px;border-right:1px solid var(--outline-variant);"
            "display:flex;flex-direction:column;background:#0a0a0a;flex-shrink:0;"
        )
        # Right: chunking config + preview
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

    list_area = ui.element("div").style("flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px;")
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
                item = ui.element("div").style(
                    f"padding:8px;border-radius:4px;cursor:pointer;{border}"
                    f"background:{'var(--surface-highest)' if active else 'transparent'};"
                    "display:flex;flex-direction:column;gap:4px;position:relative;"
                )
                with item:
                    with ui.element("div").style("display:flex;align-items:center;gap:8px;"):
                        ui.html(f'<span class="material-symbols-outlined" style="font-size:16px;color:{"var(--primary)" if active else "var(--on-surface-variant)"};">folder</span>')
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

                # Delete button (shown on hover via JS would be complex; show always)
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
                            ui.button("Delete", on_click=lambda d=dlg, cc=c: _confirm_delete(cc, d, state, _refresh_list, mid, right)).props("color=negative")
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

    with list_area:
        pass
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

    # Add source buttons
    with ui.element("div").style(
        "padding:8px;border-bottom:1px solid var(--outline-variant);"
        "display:flex;gap:8px;"
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
            # Group by source (description prefix)
            sources = {}
            for _, cid, idx, content in chunks:
                sources.setdefault("default", []).append(content)

            # Show case info as single source entry
            case = _db().get_case(case_id)
            if case:
                _, name, desc, _ = case
                active = state["active_source_idx"] == 0
                border = "border-left:2px solid var(--primary);" if active else ""
                item = ui.element("div").style(
                    f"padding:8px;border-radius:4px;cursor:pointer;{border}"
                    f"background:{'var(--surface)' if active else 'transparent'};"
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
            # Clear existing chunks and re-add
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM case_chunks WHERE case_id = ?", (case_id,))
            db.conn.commit()
            chunks = split_by_recursive(content, chunk_size=512, chunk_overlap=50)
            db.add_chunks(case_id, chunks)
            ui.notify(f"{len(chunks)} chunks loaded from file", type="positive")
            _refresh_sources()
            ui.run_javascript('document.querySelector("[data-upload-area]").style.display = "none";')

        ui.upload(label=".txt / .md", auto_upload=True, on_upload=_on_upload).props('accept=".txt,.md"').classes("w-full")

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
            ui.run_javascript('document.querySelector("[data-text-area]").style.display = "none";')

        ui.button("Load", on_click=_load_text).props("dense").style(
            "background:var(--primary);color:var(--on-primary);border-radius:8px;margin-top:4px;"
        )

    _refresh_sources()


def _build_right_placeholder() -> None:
    with ui.element("div").style(
        "height:100%;display:flex;align-items:center;justify-content:center;"
    ):
        ui.html('<span style="color:var(--on-surface-variant);font-size:14px;">Select a source to configure chunking.</span>')


def _build_chunking_config(state: dict, refresh_sources_fn) -> None:
    case_id = state["active_case_id"]
    case = _db().get_case(case_id)
    if not case:
        return
    _, name, _, _ = case
    chunks = _db().get_chunks(case_id)

    with ui.element("div").style("display:flex;flex-direction:column;gap:24px;max-width:800px;"):
        # Title
        with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;"):
            ui.html(f'<span style="font-size:32px;font-weight:700;color:var(--on-surface);">{name}</span>')
            ui.html(f'<span style="font-size:13px;color:var(--on-surface-variant);">Configure chunking strategy</span>')

        # Strategy card
        strategy_card = ui.element("div").classes("rl-card")
        with strategy_card:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:16px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--on-surface-variant);">cut</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Chunking Strategy</span>')

            strategy_sel = ui.select(
                label="Strategy Type",
                options={"recursive": "Recursive", "fixed": "Fixed Length", "lines": "By Lines"},
                value="recursive",
            ).props("outlined dense").classes("w-full")

            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px;"):
                chunk_size_in = ui.number(label="Chunk Size", value=512, min=1).props("outlined dense")
                overlap_in = ui.number(label="Overlap", value=50, min=0).props("outlined dense")

        # Preview card
        preview_card = ui.element("div").classes("rl-card")
        preview_area = ui.element("div")

        def _apply():
            content_rows = _db().get_chunks(case_id)
            if not content_rows:
                ui.notify("No content loaded", type="warning")
                return
            # Re-chunk from joined content
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
                "display:flex;align-items:center;gap:8px;border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:16px;"
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
                ui.html(f'<p style="font-size:13px;color:var(--on-surface);margin:4px 0 0;white-space:pre-wrap;word-break:break-word;">{chunk[:300]}{"..." if len(chunk) > 300 else ""}</p>')
        if len(chunks) > 20:
            ui.html(f'<span style="font-size:12px;color:var(--on-surface-variant);">... and {len(chunks)-20} more chunks</span>')
```

- [ ] **Step 2: 验证导入**

```bash
conda run -n mcp python3 -c "from raglab.ui.pages.datasets import render_datasets; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/raglab/ui/pages/datasets.py
git commit -m "feat(ui): add datasets page with three-column layout"
```

---

## Task 5: playground.py — Query vs Chunks 视图

**Files:**
- Create: `src/raglab/ui/pages/playground.py`

- [ ] **Step 1: 新建 playground.py（Query vs Chunks 部分）**

```python
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
    """Render Playground page. page_state['view'] controls which view is shown."""
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
        "adhoc_mode": True,  # True = ad-hoc textarea, False = dataset
    }

    with ui.element("div").style(
        "display:grid;grid-template-columns:3fr 6fr 3fr;gap:16px;"
        "padding:16px;height:100%;overflow:hidden;"
    ):
        # ---- Left: Retrieval Configuration ----
        left = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with left:
            with ui.element("div").style(
                "display:flex;align-items:center;gap:8px;border-bottom:1px solid #2D2D2D;padding-bottom:12px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--primary);">Retrieval Configuration</span>')

            # Embedding Model
            models = _db().list_models()
            providers = {p[0]: p[1] for p in _db().list_providers()}
            model_opts = {str(m[0]): f"{providers.get(m[1], '?')}/{m[2]}" for m in models}
            model_sel = ui.select(label="Embedding Model", options=model_opts, with_input=True).props("outlined dense").classes("w-full")

            # Retrieval Strategy toggle
            with ui.element("div").style("display:flex;flex-direction:column;gap:4px;"):
                ui.html('<span class="rl-label">Retrieval Strategy</span>')
                strategy_state = {"value": "dense"}
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;border:1px solid #2D2D2D;border-radius:4px;overflow:hidden;"
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

            # Top-K slider
            topk_val = ui.label("5").style("color:var(--primary);font-family:monospace;font-size:13px;")
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"):
                ui.html('<span class="rl-label">Top-K Results</span>')
                topk_val
            topk_slider = ui.slider(min=1, max=20, value=5).props("color=primary").classes("w-full")
            topk_slider.on("update:model-value", lambda e: topk_val.set_text(str(int(e.args))))

            # Similarity Threshold slider
            thresh_val = ui.label("0.00").style("color:var(--primary);font-family:monospace;font-size:13px;")
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"):
                ui.html('<span class="rl-label">Similarity Threshold</span>')
                thresh_val
            thresh_slider = ui.slider(min=0, max=1, step=0.01, value=0.0).props("color=primary").classes("w-full")
            thresh_slider.on("update:model-value", lambda e: thresh_val.set_text(f"{float(e.args):.2f}"))

            # Re-run button (bottom)
            run_btn = ui.element("button").classes("rl-btn-primary").style("margin-top:auto;")
            with run_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:20px;">refresh</span> Re-run Query')

        # ---- Center: Query + Chunks ----
        center = ui.element("section").style(
            "display:flex;flex-direction:column;gap:16px;height:calc(100vh - 80px);overflow:hidden;"
        )
        with center:
            # Query input card
            query_card = ui.element("div").classes("rl-card").style("flex-shrink:0;")
            with query_card:
                with ui.element("div").style("display:flex;align-items:center;gap:8px;margin-bottom:8px;"):
                    ui.html('<span class="material-symbols-outlined" style="font-size:16px;color:var(--on-surface-variant);">search</span>')
                    ui.html('<span class="rl-label">Test Query</span>')
                with ui.element("div").style("position:relative;"):
                    query_input = ui.textarea(placeholder="Enter query to test retrieval...").props("outlined rows=3").classes("w-full")
                    send_btn = ui.element("button").style(
                        "position:absolute;bottom:8px;right:8px;background:var(--primary);"
                        "color:#000;border:none;border-radius:4px;padding:4px;cursor:pointer;"
                    )
                    with send_btn:
                        ui.html('<span class="material-symbols-outlined">send</span>')

            # Chunks area
            chunks_card = ui.element("div").classes("rl-card").style("flex:1;overflow:hidden;display:flex;flex-direction:column;")
            with chunks_card:
                # Header with Ad-hoc / Dataset tab
                with ui.element("div").style(
                    "display:flex;justify-content:space-between;align-items:center;"
                    "border-bottom:1px solid #2D2D2D;padding-bottom:12px;margin-bottom:12px;flex-shrink:0;"
                ):
                    with ui.element("div").style("display:flex;align-items:center;gap:8px;"):
                        ui.html('<span class="material-symbols-outlined">format_list_bulleted</span>')
                        ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Top-Retrieved Chunks</span>')
                    results_badge = ui.element("span").style(
                        "background:rgba(142,213,255,0.1);border:1px solid var(--primary);"
                        "color:var(--primary);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;"
                    )
                    results_badge.text = "0 Results"

                # Ad-hoc / Dataset tab
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
                    chunks_detected = ui.html('<span style="font-size:12px;color:var(--on-surface-variant);">0 Chunks Detected</span>')

                    def _on_adhoc_change(e):
                        text = adhoc_input.value or ""
                        raw = [c.strip() for c in text.split("\n\n") if c.strip()]
                        state["chunks"] = raw
                        state["case_id"] = None
                        chunks_detected.content = f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(raw)} Chunks Detected</span>'

                    adhoc_input.on("update:model-value", _on_adhoc_change)

                with dataset_area:
                    cases = _db().list_cases()
                    case_opts = {str(c[0]): c[1] for c in cases}
                    case_sel = ui.select(label="Select Dataset", options=case_opts, with_input=True).props("outlined dense").classes("w-full")

                    def _on_case_select(e):
                        val = case_sel.value
                        if not val:
                            return
                        cid = int(val)
                        rows = _db().get_chunks(cid)
                        state["chunks"] = [r[3] for r in rows]
                        state["case_id"] = cid
                        chunks_detected.content = f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(state["chunks"])} Chunks Loaded</span>'

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

                # Results list
                results_list = ui.element("div").style("flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:12px;margin-top:12px;")

        # ---- Right: Analytics ----
        right = ui.element("aside").classes("rl-panel").style("height:calc(100vh - 80px);")
        with right:
            # Quick stats
            stats_grid = ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:16px;flex-shrink:0;")
            with stats_grid:
                time_card = ui.element("div").classes("rl-card")
                with time_card:
                    ui.html('<span class="rl-label">Retrieval Time</span>')
                    time_val = ui.html('<div style="display:flex;align-items:flex-end;gap:4px;margin-top:4px;"><span style="font-size:32px;font-weight:700;color:var(--primary);">—</span><span style="font-size:13px;color:var(--on-surface-variant);margin-bottom:4px;">ms</span></div>')

                tokens_card = ui.element("div").classes("rl-card")
                with tokens_card:
                    ui.html('<span class="rl-label">Chunks</span>')
                    chunks_val = ui.html('<span style="font-size:32px;font-weight:700;color:var(--on-surface);">0</span>')

            # Similarity distribution chart
            dist_card = ui.element("div").classes("rl-card").style("flex-shrink:0;")
            with dist_card:
                ui.html('<span class="rl-label">Similarity Distribution</span>')
                dist_plot_area = ui.element("div").style("margin-top:8px;")

            # t-SNE projection
            tsne_card = ui.element("div").classes("rl-card").style("flex:1;display:flex;flex-direction:column;min-height:200px;")
            with tsne_card:
                ui.html('<span class="rl-label">t-SNE Projection</span>')
                tsne_plot_area = ui.element("div").style("flex:1;margin-top:8px;")

        # ---- Wire up run button ----
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
                    # Filter by threshold
                    results = [r for r in results if r["score"] >= threshold]
                    # Get embeddings for visualization
                    all_embeddings = await asyncio.to_thread(emb.embed_batch, chunks)
                    query_emb = await asyncio.to_thread(emb.embed, query)
                else:
                    results = await asyncio.to_thread(sparse_score, query, chunks, "bm25", top_k)
                    results = [r for r in results if r["score"] >= threshold]
                    all_embeddings = None
                    query_emb = None

                elapsed_ms = int((time.time() - t0) * 1000)

                # Update stats
                time_val.content = f'<div style="display:flex;align-items:flex-end;gap:4px;margin-top:4px;"><span style="font-size:32px;font-weight:700;color:var(--primary);">{elapsed_ms}</span><span style="font-size:13px;color:var(--on-surface-variant);margin-bottom:4px;">ms</span></div>'
                chunks_val.content = f'<span style="font-size:32px;font-weight:700;color:var(--on-surface);">{len(results)}</span>'
                results_badge.text = f"{len(results)} Results"

                # Render results list
                results_list.clear()
                with results_list:
                    for i, r in enumerate(results):
                        score = r["score"]
                        is_top = i == 0
                        badge_cls = "rl-score-high" if score >= 0.8 else "rl-score-mid"
                        item = ui.element("div").classes(f"rl-chunk-item{'  top' if is_top else ''}")
                        with item:
                            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"):
                                ui.html(f'<span style="font-family:monospace;font-size:11px;color:var(--on-surface-variant);">chunk_{r["index"]:04d}</span>')
                                ui.html(f'<span class="rl-score-badge {badge_cls}">{score:.3f}</span>')
                            ui.html(f'<p style="font-size:13px;color:var(--on-surface);margin:4px 0 0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;">{r["text"][:300]}</p>')

                # Render similarity distribution
                if results:
                    scores = [r["score"] for r in results]
                    dist_plot_area.clear()
                    with dist_plot_area:
                        _render_distribution_chart(scores)

                # Render t-SNE
                if all_embeddings is not None and len(all_embeddings) >= 3:
                    tsne_plot_area.clear()
                    with tsne_plot_area:
                        await asyncio.to_thread(_render_tsne_chart, tsne_plot_area, all_embeddings, query_emb)

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


def _render_tsne_chart(container, embeddings: np.ndarray, query_emb: np.ndarray) -> None:
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
```

- [ ] **Step 2: 验证导入**

```bash
conda run -n mcp python3 -c "from raglab.ui.pages.playground import render_playground; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/raglab/ui/pages/playground.py
git commit -m "feat(ui): add playground page - query vs chunks view"
```

---

## Task 6: playground.py — Chunk vs Chunk 视图（追加到 playground.py）

**Files:**
- Modify: `src/raglab/ui/pages/playground.py`

- [ ] **Step 1: 在 playground.py 末尾追加 _render_chunk_vs_chunk 函数**

在文件末尾（`_render_tsne_chart` 函数之后）追加：

```python

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
                "display:flex;align-items:center;gap:8px;border-bottom:1px solid #2D2D2D;padding-bottom:12px;"
            ):
                ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                ui.html('<span style="font-size:18px;font-weight:600;color:var(--primary);">Model Configuration</span>')

            models = _db().list_models()
            providers = {p[0]: p[1] for p in _db().list_providers()}
            model_opts = {str(m[0]): f"{providers.get(m[1], '?')}/{m[2]}" for m in models}
            model_sel = ui.select(label="Embedding Model", options=model_opts, with_input=True).props("outlined dense").classes("w-full")

            # Strategy toggle
            with ui.element("div").style("display:flex;flex-direction:column;gap:4px;"):
                ui.html('<span class="rl-label">Retrieval Strategy</span>')
                strategy_state = {"value": "dense"}
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;border:1px solid #2D2D2D;border-radius:4px;overflow:hidden;"
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

            # Matrix size
            matrix_size = ui.number(label="Max Matrix Size", value=30, min=2, max=100).props("outlined dense").classes("w-full")

            # Run button
            run_btn = ui.element("button").classes("rl-btn-primary").style("margin-top:auto;")
            with run_btn:
                ui.html('<span class="material-symbols-outlined" style="font-size:20px;">play_arrow</span> Run Analysis')

        # ---- Center: Chunks input ----
        center = ui.element("section").style(
            "display:flex;flex-direction:column;gap:16px;height:calc(100vh - 80px);overflow:hidden;"
        )
        with center:
            center_card = ui.element("div").classes("rl-card").style("flex:1;overflow:hidden;display:flex;flex-direction:column;")
            with center_card:
                with ui.element("div").style(
                    "display:flex;align-items:center;gap:8px;border-bottom:1px solid #2D2D2D;"
                    "padding-bottom:12px;margin-bottom:12px;flex-shrink:0;"
                ):
                    ui.html('<span class="material-symbols-outlined" style="color:var(--primary);">tune</span>')
                    ui.html('<span style="font-size:18px;font-weight:600;color:var(--on-surface);">Model Configuration</span>')

                # Ad-hoc / Dataset tab
                with ui.element("div").classes("rl-adhoc-tab"):
                    adhoc_tab = ui.element("button").classes("rl-adhoc-tab-btn active")
                    with adhoc_tab:
                        ui.html("Ad-hoc")
                    dataset_tab = ui.element("button").classes("rl-adhoc-tab-btn")
                    with dataset_tab:
                        ui.html("Dataset")

                adhoc_area = ui.element("div").style("flex:1;display:flex;flex-direction:column;gap:8px;")
                dataset_area = ui.element("div").style("display:none;")

                with adhoc_area:
                    adhoc_input = ui.textarea(
                        placeholder="Paste multiple text chunks here, separated by double newlines..."
                    ).props("outlined rows=12").classes("w-full")
                    chunks_detected = ui.html('<span style="font-size:12px;color:var(--on-surface-variant);">0 Chunks Detected</span>')

                    def _on_adhoc_change(e):
                        text = adhoc_input.value or ""
                        raw = [c.strip() for c in text.split("\n\n") if c.strip()]
                        state["chunks"] = raw
                        chunks_detected.content = f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(raw)} Chunks Detected</span>'

                    adhoc_input.on("update:model-value", _on_adhoc_change)

                with dataset_area:
                    cases = _db().list_cases()
                    case_opts = {str(c[0]): c[1] for c in cases}
                    case_sel = ui.select(label="Select Dataset", options=case_opts, with_input=True).props("outlined dense").classes("w-full")

                    def _on_case_select(e):
                        val = case_sel.value
                        if not val:
                            return
                        rows = _db().get_chunks(int(val))
                        state["chunks"] = [r[3] for r in rows]
                        chunks_detected.content = f'<span style="font-size:12px;color:var(--on-surface-variant);">{len(state["chunks"])} Chunks Loaded</span>'

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
                    _, pname, api_key, base_url, _ = p
                    emb = Embedder()
                    emb.configure(pname, api_key, mname, base_url)
                    embeddings = await asyncio.to_thread(emb.embed_batch, chunks_n)
                    metric_fn = get_metric("cosine")
                    n = len(chunks_n)
                    matrix = [[metric_fn(embeddings[i], embeddings[j]) for j in range(n)] for i in range(n)]
                else:
                    # BM25: use scores as proxy for similarity
                    from raglab.core.scorer import bm25_score
                    n = len(chunks_n)
                    matrix = [[0.0] * n for _ in range(n)]
                    for i in range(n):
                        results = await asyncio.to_thread(bm25_score, chunks_n[i], chunks_n, top_k=n)
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
                ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center",
                        fontsize=6, color="white" if matrix[i][j] > 0.6 else "black")
    plt.tight_layout(pad=0.5)
    ui.pyplot(fig)
    plt.close(fig)
```

- [ ] **Step 2: 验证导入**

```bash
conda run -n mcp python3 -c "from raglab.ui.pages.playground import render_playground, _render_chunk_vs_chunk; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/raglab/ui/pages/playground.py
git commit -m "feat(ui): add chunk vs chunk view to playground"
```

---

## Task 7: 删除旧文件 + 更新 __init__.py + 端到端验证

**Files:**
- Delete: `src/raglab/ui/pages/evaluate.py`
- Delete: `src/raglab/ui/pages/chunk_lab.py`
- Delete: `src/raglab/ui/components/leaderboard.py`
- Modify: `src/raglab/ui/pages/__init__.py`
- Modify: `src/raglab/ui/components/__init__.py`

- [ ] **Step 1: 删除旧文件**

```bash
rm src/raglab/ui/pages/evaluate.py
rm src/raglab/ui/pages/chunk_lab.py
rm src/raglab/ui/components/leaderboard.py
```

- [ ] **Step 2: 更新 pages/__init__.py**

将 `src/raglab/ui/pages/__init__.py` 内容替换为：

```python
from .playground import render_playground
from .datasets import render_datasets
from .settings import render_settings

__all__ = ["render_playground", "render_datasets", "render_settings"]
```

- [ ] **Step 3: 更新 components/__init__.py**

将 `src/raglab/ui/components/__init__.py` 内容替换为：

```python
from .heatmap import render_heatmap

__all__ = ["render_heatmap"]
```

- [ ] **Step 4: 验证整体导入无报错**

```bash
conda run -n mcp python3 -c "
from raglab.ui.pages import render_playground, render_datasets, render_settings
from raglab.ui.components import render_heatmap
print('all imports ok')
"
```
Expected: `all imports ok`

- [ ] **Step 5: 启动服务端到端验证**

```bash
pkill -f "raglab serve" 2>/dev/null; sleep 1
conda run -n mcp python3 -m raglab serve --port 8098 &
sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:8098
```
Expected: `200`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ui): complete IDE redesign - remove old pages, wire up all three pages"
```

---

## 自检清单

- [x] Task 1: DB delete_case 级联删除 ✓
- [x] Task 2: app.py sidebar+header 布局 ✓
- [x] Task 3: settings.py Provider+Model 管理 ✓
- [x] Task 4: datasets.py 三栏布局 ✓
- [x] Task 5: playground.py Query vs Chunks ✓
- [x] Task 6: playground.py Chunk vs Chunk ✓
- [x] Task 7: 删除旧文件，端到端验证 ✓

**运行环境：** `conda run -n mcp python3 -m raglab serve --port 8098`

