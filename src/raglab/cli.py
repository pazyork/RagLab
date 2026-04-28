"""RagLab CLI — typer command tree connecting core modules and storage layer."""

import csv
import io
import json
from pathlib import Path
from typing import Dict, List, Optional

import typer

from raglab.core.embedder import Embedder
from raglab.core.metrics import get_metric
from raglab.core.scorer import dense_score, sparse_score
from raglab.core.splitter import split_by_char, split_by_recursive
from raglab.storage.db import Database

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------

_db: Optional[Database] = None
_embedder: Optional[Embedder] = None


def get_db() -> Database:
    """Return a lazily-initialised Database singleton (``~/.raglab.db``)."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def get_embedder() -> Embedder:
    """Return a lazily-initialised Embedder singleton populated from DB."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
        db = get_db()
        providers = db.list_providers()
        for prov in providers:
            # prov tuple: (id, name, api_key, base_url, created_at)
            _embedder.providers[prov[1]] = {
                "api_key": prov[2],
                "base_url": prov[3],
            }
    return _embedder


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _output_results(results: List[Dict], fmt: str = "table") -> str:
    """Format *results* (list of dicts) as table / json / csv."""
    if not results:
        return "(no results)"

    if fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        return buf.getvalue().rstrip()

    # table — aligned columns
    keys = list(results[0].keys())
    widths = {k: max(len(str(k)), *(len(str(r.get(k, ""))) for r in results)) for k in keys}
    header = "  ".join(str(k).ljust(widths[k]) for k in keys)
    sep = "  ".join("-" * widths[k] for k in keys)
    rows = []
    for r in results:
        rows.append("  ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))
    return "\n".join([header, sep, *rows])


# ---------------------------------------------------------------------------
# Main app & sub-apps
# ---------------------------------------------------------------------------

app = typer.Typer(name="raglab", help="Embedding model evaluation and selection tool.")

provider_app = typer.Typer(help="Manage embedding providers.")
model_app = typer.Typer(help="List and test models.")
config_app = typer.Typer(help="Manage configuration.")
case_app = typer.Typer(help="Manage test cases.")

app.add_typer(provider_app, name="provider")
app.add_typer(model_app, name="model")
app.add_typer(config_app, name="config")
app.add_typer(case_app, name="case")

# ---------------------------------------------------------------------------
# Provider commands
# ---------------------------------------------------------------------------


@provider_app.command("add")
def provider_add(
    name: str = typer.Argument(..., help="Provider name"),
    api_key: str = typer.Option(..., "--api-key", help="API key (required)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL (optional)"),
) -> None:
    """Add a new provider."""
    db = get_db()
    db.add_provider(name, api_key, base_url)
    typer.echo(f"Provider '{name}' added.")


@provider_app.command("list")
def provider_list() -> None:
    """List all providers."""
    db = get_db()
    providers = db.list_providers()
    if not providers:
        typer.echo("No providers found.")
        return
    rows = []
    for p in providers:
        rows.append({"id": p[0], "name": p[1], "api_key": p[2][:8] + "..." if p[2] else "", "base_url": p[3] or "", "created_at": p[4] or ""})
    typer.echo(_output_results(rows))


@provider_app.command("remove")
def provider_remove(
    name: str = typer.Argument(..., help="Provider name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
) -> None:
    """Remove a provider."""
    db = get_db()
    provider = db.get_provider(name)
    if provider is None:
        typer.echo(f"Provider '{name}' not found.")
        raise typer.Exit(code=1)
    if not force:
        confirmed = typer.confirm(f"Remove provider '{name}'?")
        if not confirmed:
            raise typer.Abort()
    db.remove_provider(name)
    typer.echo(f"Provider '{name}' removed.")


# ---------------------------------------------------------------------------
# Model commands
# ---------------------------------------------------------------------------


@model_app.command("list")
def model_list(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider name"),
) -> None:
    """List models, optionally filtered by provider."""
    db = get_db()
    models = db.list_models(provider)
    if not models:
        typer.echo("No models found.")
        return
    rows = []
    for m in models:
        rows.append({"id": m[0], "provider_id": m[1], "model_name": m[2], "model_type": m[3], "created_at": m[4] or ""})
    typer.echo(_output_results(rows))


@model_app.command("test")
def model_test(
    model: str = typer.Option(..., "--model", help="Model name to test"),
    text: str = typer.Option("hello world", "--text", help="Text to embed"),
) -> None:
    """Test an embedding model for availability."""
    embedder = get_embedder()
    # Pick the first configured provider if none selected
    if not embedder.providers:
        typer.echo("No providers configured. Add one with `raglab provider add` first.")
        raise typer.Exit(code=1)
    provider_name = next(iter(embedder.providers))
    prov_cfg = embedder.providers[provider_name]
    embedder.configure(provider_name, prov_cfg["api_key"], model, prov_cfg.get("base_url"))
    try:
        vec = embedder.embed(text)
        typer.echo(f"OK — model '{model}' returned embedding of dimension {len(vec)}")
    except Exception as exc:
        typer.echo(f"FAILED — {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value"),
) -> None:
    """Set a configuration value."""
    db = get_db()
    db.set_config(key, value)
    typer.echo(f"Config '{key}' set to '{value}'.")


@config_app.command("show")
def config_show() -> None:
    """Show all configuration values."""
    db = get_db()
    all_config = db.get_all_config()
    if not all_config:
        typer.echo("No configuration set.")
        return
    rows = [{"key": k, "value": v} for k, v in sorted(all_config.items())]
    typer.echo(_output_results(rows))


@config_app.command("reset")
def config_reset(
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
) -> None:
    """Reset all configuration values."""
    if not force:
        confirmed = typer.confirm("Reset all configuration?")
        if not confirmed:
            raise typer.Abort()
    db = get_db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM config")
    db.conn.commit()
    typer.echo("Configuration reset.")


# ---------------------------------------------------------------------------
# Split command (top-level)
# ---------------------------------------------------------------------------


@app.command("split")
def split_cmd(
    file: Path = typer.Argument(..., help="Input text file", exists=True),
    strategy: str = typer.Option("recursive", "--strategy", help="Split strategy: recursive | char"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Chunk size in characters"),
    overlap: int = typer.Option(50, "--overlap", help="Overlap in characters"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Read a file, split it into chunks, and output the results."""
    text = file.read_text(encoding="utf-8")
    if strategy == "recursive":
        chunks = split_by_recursive(text, chunk_size=chunk_size, chunk_overlap=overlap)
    elif strategy == "char":
        chunks = split_by_char(text, chunk_size=chunk_size, overlap=overlap)
    else:
        typer.echo(f"Unknown strategy '{strategy}'. Use 'recursive' or 'char'.")
        raise typer.Exit(code=1)

    results = [{"index": i, "length": len(c), "text": c} for i, c in enumerate(chunks)]
    formatted = _output_results(results, fmt="table")

    if output:
        output.write_text(formatted, encoding="utf-8")
        typer.echo(f"Wrote {len(chunks)} chunks to {output}")
    else:
        typer.echo(formatted)


# ---------------------------------------------------------------------------
# Score command (top-level)
# ---------------------------------------------------------------------------


@app.command("score")
def score_cmd(
    query: str = typer.Argument(..., help="Query string"),
    file: Path = typer.Argument(..., help="Input text file", exists=True),
    model: Optional[str] = typer.Option(None, "--model", help="Embedding model name (for dense scoring)"),
    algorithm: Optional[str] = typer.Option(None, "--algorithm", help="Sparse algorithm: bm25 | tfidf"),
    metric: str = typer.Option("cosine", "--metric", help="Similarity metric"),
    top_k: int = typer.Option(10, "--top-k", help="Number of top results"),
    format: str = typer.Option("table", "--format", help="Output format: table | json | csv"),
) -> None:
    """Score chunks against a query using a dense model or sparse algorithm."""
    text = file.read_text(encoding="utf-8")
    chunks = split_by_recursive(text)

    if model and not algorithm:
        embedder = get_embedder()
        if not embedder.providers:
            typer.echo("No providers configured. Add one with `raglab provider add` first.")
            raise typer.Exit(code=1)
        provider_name = next(iter(embedder.providers))
        prov_cfg = embedder.providers[provider_name]
        embedder.configure(provider_name, prov_cfg["api_key"], model, prov_cfg.get("base_url"))
        results = dense_score(query, chunks, embedder, metric, top_k)
    elif algorithm and not model:
        results = sparse_score(query, chunks, algorithm, top_k)
    else:
        typer.echo("Provide exactly one of --model (dense) or --algorithm (sparse).")
        raise typer.Exit(code=1)

    typer.echo(_output_results(results, fmt=format))


# ---------------------------------------------------------------------------
# Compare command (top-level)
# ---------------------------------------------------------------------------


@app.command("compare")
def compare_cmd(
    query: str = typer.Argument(..., help="Query string"),
    file: Path = typer.Argument(..., help="Input text file", exists=True),
    models: str = typer.Option(..., "--models", help="Comma-separated model names"),
    algorithm: Optional[str] = typer.Option(None, "--algorithm", help="Sparse algorithm for fallback"),
    metric: str = typer.Option("cosine", "--metric", help="Similarity metric"),
    top_k: int = typer.Option(10, "--top-k", help="Number of top results"),
) -> None:
    """Compare multiple models by scoring the same query and file."""
    text = file.read_text(encoding="utf-8")
    chunks = split_by_recursive(text)

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    embedder = get_embedder()

    for model_name in model_list:
        typer.echo(f"\n=== Model: {model_name} ===")
        if embedder.providers:
            provider_name = next(iter(embedder.providers))
            prov_cfg = embedder.providers[provider_name]
            embedder.configure(provider_name, prov_cfg["api_key"], model_name, prov_cfg.get("base_url"))
            results = dense_score(query, chunks, embedder, metric, top_k)
        elif algorithm:
            results = sparse_score(query, chunks, algorithm, top_k)
        else:
            typer.echo("No providers configured and no --algorithm specified.")
            raise typer.Exit(code=1)
        typer.echo(_output_results(results))


# ---------------------------------------------------------------------------
# Matrix command (top-level)
# ---------------------------------------------------------------------------


@app.command("matrix")
def matrix_cmd(
    file: Path = typer.Argument(..., help="Input text file", exists=True),
    model: str = typer.Option(..., "--model", help="Embedding model name"),
    metric: str = typer.Option("cosine", "--metric", help="Similarity metric"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output path (.png or .json)"),
) -> None:
    """Embed file chunks and compute pairwise similarity matrix."""
    text = file.read_text(encoding="utf-8")
    chunks = split_by_recursive(text)

    embedder = get_embedder()
    if not embedder.providers:
        typer.echo("No providers configured. Add one with `raglab provider add` first.")
        raise typer.Exit(code=1)
    provider_name = next(iter(embedder.providers))
    prov_cfg = embedder.providers[provider_name]
    embedder.configure(provider_name, prov_cfg["api_key"], model, prov_cfg.get("base_url"))

    import numpy as np
    embeddings = embedder.embed_batch(chunks)
    metric_fn = get_metric(metric)

    n = len(chunks)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            matrix[i][j] = metric_fn(embeddings[i], embeddings[j])

    if output and str(output).endswith(".png"):
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(max(6, n * 0.5), max(6, n * 0.5)))
            im = ax.imshow(matrix, cmap="viridis")
            ax.set_xticks(range(n))
            ax.set_yticks(range(n))
            ax.set_xticklabels([f"Chunk {i}" for i in range(n)], rotation=45, ha="right", fontsize=8)
            ax.set_yticklabels([f"Chunk {i}" for i in range(n)], fontsize=8)
            fig.colorbar(im, ax=ax)
            ax.set_title(f"Pairwise {metric} similarity")
            fig.tight_layout()
            fig.savefig(str(output), dpi=150)
            plt.close(fig)
            typer.echo(f"Matrix heatmap saved to {output}")
        except ImportError:
            typer.echo("matplotlib not available; falling back to JSON output.")
            out_path = output.with_suffix(".json")
            out_path.write_text(json.dumps(matrix.tolist(), indent=2))
            typer.echo(f"Matrix saved to {out_path}")
    else:
        result = {"chunks": n, "metric": metric, "matrix": matrix.tolist()}
        if output:
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            typer.echo(f"Matrix saved to {output}")
        else:
            typer.echo(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Case commands
# ---------------------------------------------------------------------------


@case_app.command("add")
def case_add(
    name: str = typer.Argument(..., help="Case name"),
    file: Path = typer.Argument(..., help="Input text file", exists=True),
    description: Optional[str] = typer.Option(None, "--description", help="Case description"),
) -> None:
    """Read a file, split it, and store as a test case with chunks."""
    db = get_db()
    text = file.read_text(encoding="utf-8")
    chunks = split_by_recursive(text)
    case_id = db.add_case(name, description)
    db.add_chunks(case_id, chunks)
    typer.echo(f"Case '{name}' added with {len(chunks)} chunks (id={case_id}).")


@case_app.command("list")
def case_list() -> None:
    """List all test cases with chunk counts."""
    db = get_db()
    cases = db.list_cases()
    if not cases:
        typer.echo("No test cases found.")
        return
    rows = []
    for c in cases:
        chunks = db.get_chunks(c[0])
        rows.append({"id": c[0], "name": c[1], "description": c[2] or "", "chunks": len(chunks), "created_at": c[3] or ""})
    typer.echo(_output_results(rows))


@case_app.command("run")
def case_run(
    name: str = typer.Argument(..., help="Case name"),
    models: Optional[str] = typer.Option(None, "--models", help="Comma-separated model names"),
    metric: str = typer.Option("cosine", "--metric", help="Similarity metric"),
    top_k: int = typer.Option(10, "--top-k", help="Number of top results"),
) -> None:
    """Run evaluation on a stored test case for each model."""
    db = get_db()
    # Find case by name
    cases = db.list_cases()
    case_row = None
    for c in cases:
        if c[1] == name:
            case_row = c
            break
    if case_row is None:
        typer.echo(f"Case '{name}' not found.")
        raise typer.Exit(code=1)

    case_id = case_row[0]
    chunk_rows = db.get_chunks(case_id)
    chunks = [cr[3] for cr in chunk_rows]  # content column

    if models:
        model_list = [m.strip() for m in models.split(",") if m.strip()]
    else:
        model_list = []

    embedder = get_embedder()

    for model_name in model_list:
        typer.echo(f"\n=== Model: {model_name} ===")
        if not embedder.providers:
            typer.echo("No providers configured. Add one with `raglab provider add` first.")
            raise typer.Exit(code=1)
        provider_name = next(iter(embedder.providers))
        prov_cfg = embedder.providers[provider_name]
        embedder.configure(provider_name, prov_cfg["api_key"], model_name, prov_cfg.get("base_url"))

        run_id = db.add_run(case_id, name=f"{name}_{model_name}", model=model_name, metric=metric)
        try:
            results = dense_score(chunks[0] if len(chunks) == 1 else "query", chunks, embedder, metric, top_k)
            scores = [(r["index"], r["score"], rank + 1) for rank, r in enumerate(results)]
            db.add_scores(run_id, scores)
            db.update_run_status(run_id, "completed")
            typer.echo(_output_results(results))
        except Exception as exc:
            db.update_run_status(run_id, "failed")
            typer.echo(f"Run failed: {exc}")


@case_app.command("remove")
def case_remove(
    name: str = typer.Argument(..., help="Case name"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
) -> None:
    """Remove a test case."""
    db = get_db()
    cases = db.list_cases()
    case_row = None
    for c in cases:
        if c[1] == name:
            case_row = c
            break
    if case_row is None:
        typer.echo(f"Case '{name}' not found.")
        raise typer.Exit(code=1)

    if not force:
        confirmed = typer.confirm(f"Remove case '{name}'?")
        if not confirmed:
            raise typer.Abort()

    db.remove_case(case_row[0])
    typer.echo(f"Case '{name}' removed.")


# ---------------------------------------------------------------------------
# Serve command (top-level, placeholder)
# ---------------------------------------------------------------------------


@app.command("serve")
def serve_cmd(
    port: int = typer.Option(8080, "--port", help="Port to listen on"),
) -> None:
    """Start the NiceGUI web interface."""
    from raglab.ui.app import run_app
    run_app(host="0.0.0.0", port=port)
