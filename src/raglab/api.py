"""FastAPI backend for RagLab - REST API serving Vue frontend."""

import asyncio
import base64
import io
import json
import time
import urllib.request
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# Configure CJK font support — try common macOS/Linux CJK fonts in order
import matplotlib.font_manager as _fm
_CJK_FONTS = ["STHeiti", "PingFang SC", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
for _font in _CJK_FONTS:
    if any(f.name == _font for f in _fm.fontManager.ttflist):
        plt.rcParams["font.family"] = _font
        break
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from raglab.storage.db import Database
from raglab.core.embedder import Embedder
from raglab.core.scorer import dense_score, sparse_score, hybrid_score
from raglab.core.metrics import get_metric
from raglab.core.splitter import split_by_recursive, split_by_char, split_lines, split_by_markdown

app = FastAPI(title="RagLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> Database:
    return Database()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProviderCreate(BaseModel):
    name: str
    api_key: str
    base_url: Optional[str] = None


class ModelCreate(BaseModel):
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    model_name: str
    model_type: str = "embedding"


class DatasetCreate(BaseModel):
    name: str


class ChunkTextInput(BaseModel):
    text: str
    strategy: str = "recursive"
    chunk_size: int = 512
    overlap: int = 50
    source_name: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    chunks: list[str] = []
    dataset_id: Optional[int] = None
    strategy: str = "dense"
    model_id: Optional[int] = None
    top_k: int = 10
    threshold: float = 0.0
    metric: str = "cosine"
    hybrid_weight: float = 0.5  # weight for dense vs bm25 (0=all bm25, 1=all dense)
    projection: str = "tsne"   # "tsne" or "umap"
    n_clusters: int = 0        # 0 = auto, else fixed cluster count


class ChunkVsChunkRequest(BaseModel):
    chunks: list[str] = []
    dataset_id: Optional[int] = None
    strategy: str = "dense"
    model_id: Optional[int] = None
    max_n: int = 30
    metric: str = "cosine"
    hybrid_weight: float = 0.5
    projection: str = "tsne"
    n_clusters: int = 0


class ConfigSave(BaseModel):
    chunk_size: int = 512
    overlap: int = 50
    top_k: int = 10
    metric: str = "cosine"


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@app.get("/api/providers")
def list_providers():
    rows = _db().list_providers()
    return [
        {
            "id": r[0], "name": r[1],
            "api_key_masked": (r[2][:4] + "****") if r[2] and len(r[2]) > 4 else "****",
            "base_url": r[3], "created_at": r[4]
        }
        for r in rows
    ]


@app.post("/api/providers", status_code=201)
def create_provider(body: ProviderCreate):
    try:
        pid = _db().add_provider(body.name, body.api_key, body.base_url)
        return {"id": pid, "name": body.name}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/providers/{name}")
def delete_provider(name: str):
    _db().remove_provider(name)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@app.get("/api/models")
def list_models():
    db = _db()
    rows = db.list_models()
    providers = {p[0]: p[1] for p in db.list_providers()}
    return [
        {
            "id": r[0], "provider_id": r[1],
            "provider_name": providers.get(r[1], "?"),
            "model_name": r[2], "model_type": r[3] or "embedding",
            "created_at": r[4]
        }
        for r in rows
    ]


@app.post("/api/models", status_code=201)
def create_model(body: ModelCreate):
    db = _db()
    # Resolve provider_id from provider_name if needed
    provider_id = body.provider_id
    if provider_id is None and body.provider_name:
        provider = db.get_provider(body.provider_name)
        if not provider:
            raise HTTPException(400, f"Provider '{body.provider_name}' not found")
        provider_id = provider[0]
    if provider_id is None:
        raise HTTPException(400, "Either provider_id or provider_name is required")
    try:
        mid = db.add_model(provider_id, body.model_name, body.model_type)
        return {"id": mid, "model_name": body.model_name}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/models/{model_id}")
def delete_model(model_id: int):
    db = _db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
    db.conn.commit()
    return {"ok": True}


@app.post("/api/models/{model_id}/test")
def test_model(model_id: int):
    db = _db()
    models = db.list_models()
    providers = {p[0]: p for p in db.list_providers()}
    for mid, pid, mname, _, _ in models:
        if mid == model_id:
            p = providers.get(pid)
            if not p:
                raise HTTPException(404, "Provider not found")
            _, pname, api_key, base_url, _ = p
            try:
                emb = Embedder()
                emb.configure(pname, api_key, mname, base_url)
                vec = emb.embed("test embedding")
                return {
                    "ok": True,
                    "dim": len(vec),
                    "preview": [round(float(v), 4) for v in vec[:5]]
                }
            except Exception as e:
                raise HTTPException(500, str(e))
    raise HTTPException(404, "Model not found")


@app.get("/api/openrouter/models")
def list_openrouter_models():
    """Fetch embedding models from OpenRouter API."""
    try:
        url = "https://openrouter.ai/api/v1/models?output_modalities=embeddings"
        req = urllib.request.Request(url, headers={"User-Agent": "RagLab/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        models = data.get("data", [])
        # Sort by created timestamp descending (newest first)
        models.sort(key=lambda m: m.get("created", 0), reverse=True)
        return [
            {
                "id": m["id"],
                "name": m.get("name", m["id"]),
                "context_length": m.get("context_length"),
                "pricing": m.get("pricing", {}).get("prompt", "0"),
                "created": m.get("created"),
            }
            for m in models
        ]
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch models: {str(e)}")


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@app.get("/api/datasets")
def list_datasets():
    db = _db()
    cases = db.list_cases()
    result = []
    for cid, name, desc, created_at in cases:
        chunks = db.get_chunks(cid)
        result.append({
            "id": cid, "name": name, "description": desc,
            "chunk_count": len(chunks), "created_at": created_at
        })
    return result


@app.post("/api/datasets", status_code=201)
def create_dataset(body: DatasetCreate):
    try:
        cid = _db().add_case(body.name, "")
        return {"id": cid, "name": body.name}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: int):
    _db().delete_case(dataset_id)
    return {"ok": True}


@app.delete("/api/datasets/{dataset_id}/chunks")
def clear_chunks(dataset_id: int):
    """Delete all chunks for a dataset (clear source content)."""
    db = _db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM case_chunks WHERE case_id = ?", (dataset_id,))
    db.conn.commit()
    return {"ok": True}


@app.delete("/api/datasets/{dataset_id}/chunks/{chunk_id}")
def delete_chunk(dataset_id: int, chunk_id: int):
    """Delete a single chunk."""
    db = _db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM case_chunks WHERE id = ? AND case_id = ?", (chunk_id, dataset_id))
    db.conn.commit()
    return {"ok": True}


@app.get("/api/datasets/{dataset_id}/chunks")
def get_chunks(dataset_id: int, page: int = 0, page_size: int = 0):
    """Return chunks for a dataset.

    If page_size > 0, return paginated results with metadata.
    If page_size == 0, return all chunks (backward compatible).
    """
    db = _db()
    rows = db.get_chunks(dataset_id)
    total = len(rows)

    if page_size <= 0:
        # No pagination — return all
        return [{"id": r[0], "index": r[2], "content": r[3], "source_name": r[4]} for r in rows]

    # Paginated response
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    items = [{"id": r[0], "index": r[2], "content": r[3], "source_name": r[4]} for r in rows[start:end]]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@app.get("/api/datasets/{dataset_id}/sources")
def get_sources(dataset_id: int):
    """Return list of unique source names and chunk counts for a dataset."""
    db = _db()
    rows = db.get_sources(dataset_id)
    return [{"name": r[0], "chunk_count": r[1]} for r in rows]


@app.delete("/api/datasets/{dataset_id}/sources/{source_name}")
def delete_source(dataset_id: int, source_name: str):
    """Delete all chunks from a specific source for a dataset."""
    db = _db()
    deleted = db.delete_source_chunks(dataset_id, source_name)
    return {"ok": True, "deleted": deleted}


def _split_text(text: str, strategy: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text using the given strategy and deduplicate by normalized content."""
    if strategy == "lines":
        raw = split_lines(text)
    elif strategy == "fixed":
        raw = split_by_char(text, chunk_size=chunk_size, overlap=overlap)
    elif strategy == "markdown":
        chunks = split_by_markdown(
            text,
            chunk_size=chunk_size if chunk_size > 0 else None,
            chunk_overlap=overlap,
        )
        raw = [c["content"] for c in chunks]
    else:
        raw = split_by_recursive(text, chunk_size=chunk_size, chunk_overlap=overlap)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in raw:
        key = c.strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


@app.post("/api/preview-chunks")
def preview_chunks(body: ChunkTextInput):
    """Chunk text without saving — truncates to first 100 lines for speed."""
    lines = body.text.split("\n")[:100]
    text = "\n".join(lines)
    chunks = _split_text(text, body.strategy, body.chunk_size, body.overlap)
    return {"chunk_count": len(chunks), "chunks": chunks[:20]}


@app.post("/api/datasets/{dataset_id}/chunks")
def set_chunks(dataset_id: int, body: ChunkTextInput):
    db = _db()
    source = body.source_name or 'pasted text'
    chunks = _split_text(body.text, body.strategy, body.chunk_size, body.overlap)
    db.add_chunks(dataset_id, chunks, source_name=source)
    return {"chunk_count": len(chunks), "chunks": chunks[:5], "source_name": source}


@app.post("/api/datasets/{dataset_id}/upload")
async def upload_file(dataset_id: int, file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8")
    db = _db()
    chunks = split_by_recursive(content, chunk_size=512, chunk_overlap=50)
    db.add_chunks(dataset_id, chunks, source_name=file.filename)
    return {"chunk_count": len(chunks), "filename": file.filename}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@app.get("/api/config")
def get_config():
    db = _db()
    return {
        "chunk_size": db.get_config("chunk_size") or 512,
        "overlap": db.get_config("overlap") or 50,
        "top_k": db.get_config("top_k") or 10,
        "metric": db.get_config("metric") or "cosine",
    }


@app.post("/api/config")
def save_config(body: ConfigSave):
    db = _db()
    db.set_config("chunk_size", body.chunk_size)
    db.set_config("overlap", body.overlap)
    db.set_config("top_k", body.top_k)
    db.set_config("metric", body.metric)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Embedding cache management
# ---------------------------------------------------------------------------

@app.get("/api/cache/stats")
def cache_stats():
    return _db().get_cache_stats()


@app.delete("/api/cache")
def clear_cache():
    count = _db().clear_cache()
    return {"ok": True, "deleted": count}


# ---------------------------------------------------------------------------
# Embedding cache helper
# ---------------------------------------------------------------------------

def _make_model_key(provider_name: str, model_name: str) -> str:
    """Build a stable key for cache lookup: provider/model."""
    return f"{provider_name}/{model_name}"


def _embed_with_cache(
    emb: Embedder,
    texts: list[str],
    provider_name: str,
    model_name: str,
) -> np.ndarray:
    """Embed texts, using cache for hits and only calling API for misses.

    Returns np.ndarray of shape (len(texts), dim).
    Must be called from a sync context (e.g. inside asyncio.to_thread).
    """
    db = Database()  # fresh connection for thread safety
    model_key = _make_model_key(provider_name, model_name)
    cached = db.get_cached_embeddings(texts, model_key)

    # Split into hits and misses
    miss_texts: list[str] = []
    for t in texts:
        if cached[t] is None:
            miss_texts.append(t)

    # Fetch misses from API
    if miss_texts:
        new_embs = emb.embed_batch(miss_texts)
        db.put_cached_embeddings(miss_texts, new_embs, model_key)
        # Update cached dict so reassembly can use it
        for t in miss_texts:
            cached[t] = None  # will be filled from new_embs below
    else:
        new_embs = np.empty((0, 0), dtype=np.float32)

    # Reassemble in original order
    result = []
    miss_counter = 0
    for t in texts:
        if cached[t] is not None:
            result.append(cached[t])
        else:
            result.append(new_embs[miss_counter])
            miss_counter += 1

    return np.stack(result)


# ---------------------------------------------------------------------------
# Playground - Query vs Chunks
# ---------------------------------------------------------------------------

@app.post("/api/playground/query")
async def playground_query(body: QueryRequest):
    t0 = time.time()
    chunks = body.chunks

    # Load chunks from dataset if dataset_id provided
    if not chunks and body.dataset_id is not None:
        rows = _db().get_chunks(body.dataset_id)
        chunks = [r[3] for r in rows]  # r[3] = content column

    if not chunks:
        raise HTTPException(400, "No chunks provided")

    if body.strategy in ("dense", "hybrid"):
        if not body.model_id:
            raise HTTPException(400, "model_id required for dense/hybrid strategy")
        db = _db()
        models = db.list_models()
        providers = {p[0]: p for p in db.list_providers()}
        model_info = next((m for m in models if m[0] == body.model_id), None)
        if not model_info:
            raise HTTPException(404, "Model not found")
        pid, mname = model_info[1], model_info[2]
        p = providers.get(pid)
        if not p:
            raise HTTPException(404, "Provider not found")
        _, pname, api_key, base_url, _ = p
        emb = Embedder()
        emb.configure(pname, api_key, mname, base_url)

        if body.strategy == "hybrid":
            results = await asyncio.to_thread(
                hybrid_score, body.query, chunks, emb, body.metric, body.top_k, body.hybrid_weight
            )
        else:
            results = await asyncio.to_thread(dense_score, body.query, chunks, emb, body.metric, body.top_k)
        results = [r for r in results if r["score"] >= body.threshold]

        # Embeddings for visualization — uses cache
        all_embeddings = await asyncio.to_thread(
            _embed_with_cache, emb, chunks, pname, mname
        )
        # Query embedding — also cache (single text)
        query_emb_arr = await asyncio.to_thread(
            _embed_with_cache, emb, [body.query], pname, mname
        )
        query_emb = query_emb_arr[0]

        scores = [r["score"] for r in results]
        proj_points = None
        if len(all_embeddings) >= 3:
            proj_points = await asyncio.to_thread(
                _compute_projection_points,
                np.array(all_embeddings),
                chunks,
                body.projection,
                body.n_clusters,
                query_emb=np.array(query_emb),
            )
    else:
        results = await asyncio.to_thread(sparse_score, body.query, chunks, "bm25", body.top_k)
        results = [r for r in results if r["score"] >= body.threshold]
        scores = [r["score"] for r in results]
        proj_points = None

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "results": results,
        "elapsed_ms": elapsed_ms,
        "total": len(results),
        "scores": scores,
        "tsne_points": proj_points,
    }


# ---------------------------------------------------------------------------
# Playground - Chunk vs Chunk
# ---------------------------------------------------------------------------

@app.post("/api/playground/chunk-vs-chunk")
async def chunk_vs_chunk(body: ChunkVsChunkRequest):
    chunks = body.chunks

    # Load chunks from dataset if dataset_id provided
    if not chunks and body.dataset_id is not None:
        rows = _db().get_chunks(body.dataset_id)
        chunks = [r[3] for r in rows]

    chunks = chunks[:body.max_n]
    if len(chunks) < 2:
        raise HTTPException(400, "Need at least 2 chunks")

    if body.strategy in ("dense", "hybrid"):
        if not body.model_id:
            raise HTTPException(400, "model_id required for dense/hybrid strategy")
        db = _db()
        models = db.list_models()
        providers = {p[0]: p for p in db.list_providers()}
        model_info = next((m for m in models if m[0] == body.model_id), None)
        if not model_info:
            raise HTTPException(404, "Model not found")
        pid, mname = model_info[1], model_info[2]
        p = providers.get(pid)
        _, pname, api_key, base_url, _ = p
        emb = Embedder()
        emb.configure(pname, api_key, mname, base_url)
        # Use cache-aware embedding
        embeddings = await asyncio.to_thread(
            _embed_with_cache, emb, chunks, pname, mname
        )
        metric_fn = get_metric(body.metric)
        n = len(chunks)
        matrix = [
            [float(metric_fn(embeddings[i], embeddings[j])) for j in range(n)]
            for i in range(n)
        ]
        # For hybrid mode, blend with BM25
        if body.strategy == "hybrid":
            from raglab.core.scorer import bm25_score, _normalize_scores
            # Normalize dense matrix to [0,1]
            dense_flat = []
            for i in range(n):
                for j in range(n):
                    if i != j:
                        dense_flat.append(matrix[i][j])
            d_min = min(dense_flat) if dense_flat else 0
            d_max = max(dense_flat) if dense_flat else 1
            d_span = d_max - d_min if d_max != d_min else 1

            # Build BM25 matrix
            bm25_matrix = [[0.0] * n for _ in range(n)]
            for i in range(n):
                bm25_results = await asyncio.to_thread(bm25_score, chunks[i], chunks, n)
                for r in bm25_results:
                    bm25_matrix[i][r["index"]] = float(r["score"])
            # Normalize BM25 matrix
            b_flat = []
            for i in range(n):
                for j in range(n):
                    if i != j:
                        b_flat.append(bm25_matrix[i][j])
            b_min = min(b_flat) if b_flat else 0
            b_max = max(b_flat) if b_flat else 1
            b_span = b_max - b_min if b_max != b_min else 1

            w = body.hybrid_weight
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    d_norm = (matrix[i][j] - d_min) / d_span
                    b_norm = (bm25_matrix[i][j] - b_min) / b_span
                    matrix[i][j] = w * d_norm + (1 - w) * b_norm
    else:
        from raglab.core.scorer import bm25_score
        embeddings = []  # no embeddings for BM25
        n = len(chunks)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            results = await asyncio.to_thread(bm25_score, chunks[i], chunks, n)
            for r in results:
                matrix[i][r["index"]] = float(r["score"])

    labels = [c[:30] + "…" if len(c) > 30 else c for c in chunks]
    n = len(chunks)
    off_diag = [matrix[i][j] for i in range(n) for j in range(n) if i != j]
    avg_sim = float(sum(off_diag) / len(off_diag)) if off_diag else 0.0
    cohesion = float(sum(1 for s in off_diag if s >= 0.5) / len(off_diag) * 100) if off_diag else 0.0
    proj_points = None
    if body.strategy in ("dense", "hybrid") and len(chunks) >= 3:
        proj_points = await asyncio.to_thread(
            _compute_projection_points,
            np.array(embeddings), chunks, body.projection, body.n_clusters
        )
    return {
        "matrix": matrix, "labels": labels, "chunks": chunks,
        "off_diag_scores": off_diag,
        "avg_sim": round(avg_sim, 4), "cohesion": round(cohesion, 1),
        "tsne_points": proj_points,
    }


# ---------------------------------------------------------------------------
# Chart helpers (return base64 PNG)
# ---------------------------------------------------------------------------

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def _make_distribution_chart(scores: list) -> Optional[str]:
    if not scores:
        return None
    fig, ax = plt.subplots(figsize=(4, 2.5))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#050505")
    ax.hist(scores, bins=min(10, len(scores)), color="#38bdf8", alpha=0.85, edgecolor="#2D2D2D")
    ax.tick_params(colors="#bdc8d1", labelsize=8)
    ax.spines[:].set_color("#2D2D2D")
    ax.set_xlabel("Score", color="#bdc8d1", fontsize=8)
    ax.set_ylabel("Count", color="#bdc8d1", fontsize=8)
    plt.tight_layout(pad=0.5)
    return _fig_to_b64(fig)


def _cluster_points(coords: np.ndarray, n_clusters: int = 0) -> list[int]:
    """Run K-Means on 2D coords. n_clusters=0 means auto (min(6, max(2, n//3)))."""
    from sklearn.cluster import KMeans
    n = len(coords)
    if n_clusters <= 0:
        n_clusters = min(6, max(2, n // 3))
    if n < n_clusters:
        n_clusters = max(2, n)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)
    return [int(l) for l in labels]


def _compute_projection_points(
    embeddings: np.ndarray,
    chunks: list,
    projection: str,
    n_clusters: int = 0,
    query_emb: np.ndarray | None = None,
) -> Optional[list]:
    """Project embeddings to 2D (t-SNE or UMAP), cluster, and return JSON points."""
    try:
        n = len(embeddings)
        has_query = query_emb is not None
        vecs = np.vstack([embeddings, query_emb.reshape(1, -1)]) if has_query else embeddings

        if projection == "umap":
            from umap import UMAP
            n_neighbors = min(15, max(2, n - 1))
            reducer = UMAP(n_components=2, n_neighbors=n_neighbors, min_dist=0.1, random_state=42, metric="cosine")
            coords = reducer.fit_transform(vecs)
        else:
            from sklearn.manifold import TSNE
            perplexity = min(30, max(2, n - 1))
            tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=300)
            coords = tsne.fit_transform(vecs)

        # Cluster only chunk coordinates (exclude query if present)
        chunk_coords = coords[:-1] if has_query else coords
        labels = _cluster_points(chunk_coords, n_clusters)

        points = []
        for i, (x, y) in enumerate(coords):
            if has_query and i == len(coords) - 1:
                points.append({"x": float(x), "y": float(y), "index": -1, "text": "Query", "type": "query", "cluster": -1})
            else:
                points.append({
                    "x": float(x), "y": float(y),
                    "index": i,
                    "text": chunks[i] if i < len(chunks) else f"Chunk {i}",
                    "type": "chunk",
                    "cluster": labels[i],
                })
        return points
    except Exception:
        return None


def _make_heatmap(matrix: list, labels: list) -> str:
    n = len(labels)
    # Truncate labels for display
    display_labels = [f"#{i+1} {lb[:12]}{'…' if len(lb) > 12 else ''}" for i, lb in enumerate(labels)]
    fig, ax = plt.subplots(figsize=(max(5, n * 0.55), max(4, n * 0.5)))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#050505")
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax).ax.tick_params(colors="#bdc8d1", labelsize=7)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(display_labels, rotation=30, ha="right", fontsize=7, color="#bdc8d1")
    ax.set_yticklabels(display_labels, fontsize=7, color="#bdc8d1")
    ax.spines[:].set_color("#2D2D2D")
    if n <= 15:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{matrix[i][j]:.2f}", ha="center", va="center",
                        fontsize=6, color="white" if matrix[i][j] > 0.6 else "black")
    plt.tight_layout(pad=0.5)
    return _fig_to_b64(fig)


# ---------------------------------------------------------------------------
# Serve Vue frontend (production build)
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="static")
