# RagLab 实施计划 (1/4)：项目搭建 + Core 模块

> **Agent worker:** 使用 superpowers:subagent-driven-development，逐 Task 执行。每步 checkbox。

**目标：** 搭建项目骨架，实现 core/ 下所有纯逻辑模块（无 UI、无持久化）

**顺序：** 自下而上，每层可独立测试。metrics → splitter → embedder → scorer

---

## 文件结构

```
raglab/
├── pyproject.toml
├── src/raglab/
│   ├── __init__.py
│   ├── __main__.py            # 入口（try import cli，失败则提示先完成后续安装）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── metrics.py         # 纯函数，无外部依赖
│   │   ├── splitter.py        # 纯文本处理，无外部依赖
│   │   ├── embedder.py        # litellm 封装
│   │   └── scorer.py          # 依赖 metrics + embedder
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── pages/__init__.py
│   │   └── components/__init__.py
│   └── storage/
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_metrics.py
    ├── test_splitter.py
    ├── test_embedder.py
    └── test_scorer.py
```

## 模块依赖图

```
scorer ──→ embedder ──→ litellm
  │
  └──→ metrics ──→ numpy

splitter (独立，no external deps)
```

---

### Task 1: 项目骨架

**创建文件：** `pyproject.toml`, 所有 `__init__.py`, `__main__.py`

**pyproject.toml 要点：**
- name: `raglab`, 入口脚本: `raglab = "raglab.cli:app"`
- 依赖: typer, nicegui, litellm, numpy, matplotlib
- Python >= 3.10, pip install -e . 可编辑安装

**验证：** `python -c "import raglab; print('ok')"` 输出 `ok`（cli.py 尚未创建，`__main__.py` 用 try/except 容错）

---

### Task 2: core/metrics.py — 相似度度量

**职责：** 提供纯函数的向量相似度/距离计算

**对外接口：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `cosine_similarity(a: np.ndarray, b: np.ndarray) -> float` | [0, 1] | 余弦相似度 |
| `euclidean_distance(a, b) -> float` | [0, +∞) | 欧氏距离 |
| `dot_product(a, b) -> float` | (-∞, +∞) | 点积 |
| `manhattan_distance(a, b) -> float` | [0, +∞) | 曼哈顿距离 |
| `get_metric(name: str) -> Callable` | 函数引用 | "cosine" / "euclidean" / "dot" / "manhattan" |

**测试要点：**
- 相同向量 → cosine=1, euclidean=0
- 正交向量 → cosine=0
- 已知值 → 手动验算
- 零向量 → 不抛异常
- get_metric 非法 name → ValueError

**依赖：** numpy

---

### Task 3: core/splitter.py — 文本切块

**职责：** 多种策略的文本切块，纯文本处理，不依赖外部模型

**对外接口：**

| 函数 | 入参 | 返回值 | 说明 |
|------|------|--------|------|
| `split_lines(text)` | str | `list[str]` | 按行切，过滤空行 |
| `split_by_char(text, chunk_size, overlap)` | str, int, int | `list[str]` | 固定字符数滑窗切 |
| `split_by_recursive(text, chunk_size, chunk_overlap)` | str, int, int | `list[str]` | 段落→句子→字符递归切 |

**实现要点：**
- `split_by_recursive` 按分隔符优先级 `["\n\n", "\n", "。", ".", "，", ",", " "]` 逐级尝试
- 每级切完后合并短片段，超长的进入下一级
- overlap 只对最终字符切生效

**测试要点：**
- 空文本 → 空列表
- 短于 chunk_size → 单个元素
- overlap 验证：前后 chunk 有重叠内容
- recursive 优先按段落切分

**依赖：** 无（纯标准库）

---

### Task 4: core/embedder.py — Embedding 统一接口

**职责：** 封装 litellm，支持多 provider 配置和切换

**类：`Embedder`**

**State：**
```
providers: dict[str, dict]   # {provider_name: {api_key, base_url}}
model: str | None
provider: str | None
```

**方法签名：**

| 方法 | 说明 |
|------|------|
| `configure(provider, api_key, model, base_url?) -> None` | 设置当前 provider 和 model |
| `load_config(providers: dict) -> None` | 批量加载 provider 配置 |
| `embed(text: str | list[str]) -> np.ndarray` | 单个或批量 embedding |
| `embed_batch(texts: list[str]) -> np.ndarray` | 批量 embedding 别名 |

**实现要点：**
- `embed()` 调用 `litellm.embedding(model=..., input=...)`，从 `resp.data[].embedding` 提取向量
- 单文本返回 1D array，多文本返回 2D array
- 未配置时抛 ValueError
- API 失败时包装为 RuntimeError

**测试要点：**
- 未配置状态 → 抛异常
- configure 后状态正确更新
- load_config 从 dict 加载
- 不测试真实 API 调用（用 mock 或仅测试状态管理）

**依赖：** litellm, numpy

---

### Task 5: core/scorer.py — 评分引擎

**职责：** 稠密检索（调用 embedder + metric）+ 稀疏检索（本地 BM25/TF-IDF 实现）

**对外接口：**

| 函数 | 入参 | 返回值 | 说明 |
|------|------|--------|------|
| `dense_score(query, chunks, embedder, metric, top_k)` | str, list[str], Embedder, str, int | `list[dict]` | 稠密评分 |
| `bm25_score(query, chunks, top_k, k1, b)` | str, list[str], int, float, float | `list[dict]` | BM25 评分 |
| `tfidf_score(query, chunks, top_k)` | str, list[str], int | `list[dict]` | TF-IDF 评分 |
| `sparse_score(query, chunks, algorithm, top_k)` | str, list[str], str, int | `list[dict]` | 稀疏路由分发 |

**返回结构：** `[{"index": int, "score": float, "text": str}, ...]` 按 score 降序

**实现要点：**
- `dense_score`: embed query → embed_batch chunks → 对每个用 metric_fn 计算 → 排序取 top_k
- `bm25_score`: 手动分词 → 计算 idf → 对每个 doc 计算 bm25 → 排序
- `tfidf_score`: 同上，公式更简单
- `sparse_score`: 根据 algorithm 分发到 bm25_score / tfidf_score
- BM25 默认参数 k1=1.5, b=0.75

**测试要点：**
- dense_score 用 FakeEmbedder（返回固定随机种子向量）
- 验证结果按 score 降序排列
- 验证 top_k 截断生效
- sparse_score 非法 algorithm → ValueError

**依赖：** core.metrics, core.embedder, numpy

---

## 完成标准

```bash
pytest tests/ -v     # 全部 green（预计 16+ 个测试）
```
