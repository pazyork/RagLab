# RAGLab — Agent Reference

RAGLab is a local embedding model evaluation tool. It exposes a REST API and a CLI. Use this document to integrate, automate, or reason about it programmatically.

**Human docs**: [English](README_en.md) · [中文](README.md)

---

## System architecture

```
raglab serve          → FastAPI server (default: localhost:8099)
~/.raglab.db          → SQLite, all persistent state
litellm               → unified embedding API adapter (100+ providers)
```

Screenshots: [Settings](docs/screenshots/settings.png) · [Datasets](docs/screenshots/datasets.png) · [Playground+t-SNE](docs/screenshots/playground_tsne.png) · [Heatmap](docs/screenshots/heatmap.png)

The server is stateless between requests. All state lives in SQLite. No auth layer — designed for local single-user use only.

---

## Startup

Requires Python 3.10+.

```bash
pip install raglab
raglab serve [--port 8099] [--log-level INFO]
```

API base: `http://localhost:8099`  
OpenAPI spec: `GET /openapi.json`

---

## Data model

```
Provider
  id, name, api_key (plaintext), base_url, created_at

Model
  id, provider_id → Provider, model_name, model_type ("embedding"), created_at

Dataset
  id, name, created_at
  → has many Chunks, has many Sources (logical grouping by source_name)

Chunk
  id, dataset_id → Dataset, content (text), source_name, chunk_index, created_at

EmbeddingCache
  content_hash, model_key, embedding (JSON blob), created_at
  UNIQUE(content_hash, model_key)

Config
  key, value (string)
  keys: chunk_size (int), overlap (int), top_k (int), metric (string)
```

---

## REST API

All mutating endpoints return `{"ok": true}` on success unless a richer response is noted.

### Providers

```
GET  /api/providers
     → [{id, name, api_key_masked, base_url, created_at}]

POST /api/providers
     body: {name: str, api_key: str, base_url?: str}
     → {id, name, api_key_masked, base_url, created_at}

DELETE /api/providers/{name}
     → {ok: true}
```

### Models

```
GET  /api/models
     → [{id, provider_id, provider_name, model_name, model_type, created_at}]

POST /api/models
     body: {provider_id?: int, provider_name?: str, model_name: str, model_type?: str}
     → {id, provider_id, provider_name, model_name, model_type, created_at}

DELETE /api/models/{model_id}
     → {ok: true}

POST /api/models/{model_id}/test
     body: {}
     → {ok: bool, dim: int, preview: [float, ...]}   # dim = embedding dimension

GET  /api/openrouter/models
     → [{id, name, ...}]   # fetched live from OpenRouter
```

### Datasets

```
GET  /api/datasets
     → [{id, name, chunk_count, created_at}]

POST /api/datasets
     body: {name: str}
     → {id, name, created_at}

DELETE /api/datasets/{dataset_id}
     → {ok: true}

GET  /api/datasets/{dataset_id}/chunks?page=0&page_size=0
     page_size=0  → returns full list as [{id, index, content, source_name}]
     page_size>0  → returns {items: [...], total, page, page_size, total_pages}

POST /api/datasets/{dataset_id}/chunks
     body: {text: str, strategy: str, chunk_size: int, overlap: int, source_name?: str}
     → {chunk_count: int, chunks: [...first 5], source_name: str}

DELETE /api/datasets/{dataset_id}/chunks
     → {ok: true}

DELETE /api/datasets/{dataset_id}/chunks/{chunk_id}
     → {ok: true}

GET  /api/datasets/{dataset_id}/sources
     → [{name: str, chunk_count: int}]

DELETE /api/datasets/{dataset_id}/sources/{source_name}
     → {ok: true, deleted: int}

POST /api/datasets/{dataset_id}/upload
     multipart: file (text/*)
     → {chunk_count: int, filename: str}

POST /api/preview-chunks
     body: {text: str, strategy: str, chunk_size: int, overlap: int}
     → {chunks: [str], count: int}
```

### Config

```
GET  /api/config
     → {chunk_size: int, overlap: int, top_k: int, metric: str}

POST /api/config
     body: {chunk_size?: int, overlap?: int, top_k?: int, metric?: str}
     → {ok: true}
```

### Cache

```
GET    /api/cache/stats
       → {entry_count: int, total_size_mb: float}

DELETE /api/cache
       → {ok: true, deleted: int}
```

### Playground

```
POST /api/playground/query
     body: {
       query: str,
       chunks?: [str],          # ad-hoc (mutually exclusive with dataset_id)
       dataset_id?: int,
       strategy: "dense"|"bm25"|"hybrid",
       model_id?: int,          # required if strategy includes dense
       top_k?: int,
       threshold?: float,       # default: 0.0
       metric?: "cosine"|"dot"|"euclidean"|"manhattan",
       hybrid_weight?: float,   # 0.0–1.0, dense weight; default 0.5
       projection?: "tsne"|"umap",
       n_clusters?: int         # 0 = auto
     }
     → {
       results: [{chunk: str, score: float, rank: int, source_name?: str}],
       elapsed_ms: int,
       total: int,
       scores: [float],
       tsne_points: [[x, y, label, color]] | null
     }

POST /api/playground/chunk-vs-chunk
     body: {
       chunks?: [str],
       dataset_id?: int,
       strategy: "dense"|"bm25"|"hybrid",
       model_id?: int,
       max_n?: int,
       metric?: str,
       hybrid_weight?: float,
       projection?: "tsne"|"umap",
       n_clusters?: int
     }
     → {
       matrix: [[float]],        # n×n similarity matrix
       labels: [str],            # chunk preview strings
       chunks: [str],            # full chunk texts
       off_diag_scores: [float],
       avg_sim: float,
       cohesion: float,          # % of off-diagonal pairs with sim >= 0.5
       tsne_points: [[x, y, label, color]] | null
     }
```

---

## CLI reference

```bash
# Provider management
raglab provider add <name> --api-key <key> [--base-url <url>]
raglab provider list
raglab provider remove <name>

# Model management
raglab model list
raglab model test --model <model_name> [--text "hello world"]

# Config (one key at a time)
raglab config set <key> <value>   # keys: chunk_size, overlap, top_k, metric
raglab config show
raglab config reset

# Chunking (stdout)
raglab split <file> [--strategy recursive|char] [--chunk-size 512] [--overlap 50]
# Note: lines and markdown strategies are Web API only, not available in CLI

# Scoring
raglab score <query> <chunks_file> --model <model_name> [--metric cosine] [--top-k 10]
raglab compare <query> <chunks_file> --models <m1,m2,...> [--metric cosine]

# Similarity matrix
raglab matrix <chunks_file> --model <model_name> [--metric cosine] [--output matrix.png]

# Test cases
raglab case add <name> <file>
raglab case list
raglab case run <name> [--model <model_name>]
raglab case remove <name>

# Server
raglab serve [--port 8099] [--log-level INFO]
```

---

## Chunking strategies

| Strategy | Availability | Behavior |
|----------|-------------|----------|
| `recursive` | CLI + API | Split on `\n\n`, `\n`, `. `, ` ` until chunks fit size |
| `char` | CLI + API | Hard split by character count |
| `lines` | API only | One chunk per non-empty line |
| `markdown` | API only | Split on `##` headings, then by size |

Default: `recursive`, chunk_size=512, overlap=50.

---

## Embedding providers

RAGLab uses [litellm](https://github.com/BerriAI/litellm) as the adapter. Any provider litellm supports works. Common setups:

| Provider | base_url | model name format |
|----------|----------|-------------------|
| OpenAI | (none) | `text-embedding-3-small` |
| OpenRouter | `https://openrouter.ai/api/v1` | `baai/bge-m3` |
| Alibaba Bailian | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `text-embedding-v3` |
| Local (Ollama) | `http://localhost:11434/v1` | `nomic-embed-text` |

Optional: install `umap-learn` for UMAP projection support (`pip install umap-learn`).

---

## Automation example

```python
import requests

BASE = "http://localhost:8099"

# Setup
requests.post(f"{BASE}/api/providers", json={
    "name": "openrouter",
    "api_key": "sk-xxx",
    "base_url": "https://openrouter.ai/api/v1"
})
model_id = requests.post(f"{BASE}/api/models", json={
    "provider_name": "openrouter",
    "model_name": "baai/bge-m3"
}).json()["id"]

# Create dataset
ds = requests.post(f"{BASE}/api/datasets", json={"name": "test"}).json()
requests.post(f"{BASE}/api/datasets/{ds['id']}/chunks", json={
    "text": open("corpus.txt").read(),
    "strategy": "recursive",
    "chunk_size": 512,
    "overlap": 50
})

# Query
result = requests.post(f"{BASE}/api/playground/query", json={
    "query": "what is retrieval augmented generation",
    "dataset_id": ds["id"],
    "strategy": "dense",
    "model_id": model_id,
    "top_k": 5,
    "metric": "cosine"
}).json()

for r in result["results"]:
    print(f"[{r['score']:.3f}] {r['chunk'][:80]}")
```

---

## Key behaviors to know

- Embeddings are cached by `(sha256(content), model_key)`. Same query + same model = instant after first call.
- `dataset_id` and `chunks` are mutually exclusive in playground endpoints.
- `strategy: "bm25"` runs fully offline — no embedding API call.
- `hybrid_weight`: `1.0` = pure dense, `0.0` = pure BM25.
- `/api/providers` and `/api/models` return full lists (no pagination).
- `/api/datasets/{id}/chunks` with `page_size=0` (default) returns all chunks as a flat list. Set `page_size>0` for paginated response.
- UMAP projection requires `umap-learn` installed. Falls back to `null` if not available.
