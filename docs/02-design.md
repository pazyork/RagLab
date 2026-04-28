# RagLab 设计文档

## 1. 架构设计

### 1.1 整体架构

```
raglab/
├── pyproject.toml               # 项目元信息 + 依赖
├── src/raglab/
│   ├── __init__.py
│   ├── __main__.py              # python -m raglab 入口
│   ├── cli.py                   # CLI 路由（typer）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── embedder.py          # litellm embedding 统一封装
│   │   ├── splitter.py          # 文本切块引擎
│   │   ├── scorer.py            # 稠密 + 稀疏评分
│   │   └── metrics.py           # 相似度度量函数
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py               # NiceGUI 应用入口
│   │   ├── pages/
│   │   │   ├── __init__.py
│   │   │   ├── evaluate.py      # 评测页面
│   │   │   ├── chunk_lab.py     # Chunk 实验室
│   │   │   └── settings.py      # 设置页面
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── heatmap.py       # 相似度热力图
│   │       └── leaderboard.py   # 评分排行榜
│   ├── storage/
│   │   ├── __init__.py
│   │   └── db.py                # SQLite 持久化
│   └── i18n/
│       ├── __init__.py         # t(key) 翻译函数
│       ├── zh.json
│       └── en.json
├── tests/
│   ├── test_embedder.py
│   ├── test_splitter.py
│   ├── test_scorer.py
│   └── test_metrics.py
└── README.md
```

### 1.2 模块职责

| 模块 | 职责 | 关键依赖 |
|------|------|----------|
| `core/embedder.py` | 封装 litellm.embedding，统一供应商和模型调用 | litellm |
| `core/splitter.py` | 按字符/递归/按行切块，不依赖外部库 | 无 |
| `core/scorer.py` | 调用 embedder 或本地稀疏算法，输出评分 | core.embedder, core.metrics |
| `core/metrics.py` | 余弦/欧氏/点积/曼哈顿等相似度函数 | numpy |
| `storage/db.py` | SQLite CRUD，所有持久化操作 | sqlite3（内置）|
| `ui/` | NiceGUI 页面 + 可视化组件 | nicegui |
| `i18n/` | JSON 翻译文件 + t(key) 加载函数 | 无 |

## 2. CLI 设计（typer）

所有命令的顶层入口，完全覆盖原子操作。

```bash
# 供应商管理
raglab provider add <name> --api-key <key> [--base-url <url>]
raglab provider list
raglab provider remove <name>

# 模型管理
raglab model list [--provider <name>]
raglab model test <model> --text <text>

# 配置管理
raglab config set <key> <value>     # chunk_size, overlap, top_k, metric
raglab config show
raglab config reset

# 文本切块
raglab split <file> [--strategy recursive|fixed|lines]
                     [--chunk-size 512]
                     [--overlap 50]
                     [--output /path]

# 打分
raglab score <query> <file> --model <name> [--metric cosine] [--top-k 10]
raglab score <query> <file> --algorithm bm25|tfidf

# 多模型对比
raglab compare <query> <file> --models m1,m2,m3 [--algorithm bm25] [--metric cosine]

# 相似度矩阵
raglab matrix <file> --model <name> [--metric cosine] [--output heatmap.png]

# 测试用例
raglab case add <name> <file>
raglab case list
raglab case run <name> --models m1,m2
raglab case remove <name>

# 启动 Web
raglab serve [--port 8080]
```

## 3. 数据库模型（SQLite）

```
表 providers:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  name        TEXT NOT NULL UNIQUE
  api_key     TEXT
  base_url    TEXT
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP

表 models:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  provider_id INTEGER REFERENCES providers(id)
  model_name  TEXT NOT NULL
  model_type  TEXT DEFAULT 'embedding'  -- embedding（预留扩展）
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  UNIQUE(provider_id, model_name)

表 test_cases:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  name        TEXT NOT NULL UNIQUE
  description TEXT
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP

表 case_chunks:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  case_id     INTEGER REFERENCES test_cases(id) ON DELETE CASCADE
  chunk_index INTEGER NOT NULL
  content     TEXT NOT NULL

表 eval_runs:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  case_id     INTEGER REFERENCES test_cases(id)
  name        TEXT
  model       TEXT NOT NULL
  metric      TEXT DEFAULT 'cosine'
  algorithm   TEXT               -- NULL 表示稠密检索
  status      TEXT DEFAULT 'pending'  -- pending | running | done | failed
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP

表 eval_scores:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  run_id      INTEGER REFERENCES eval_runs(id) ON DELETE CASCADE
  chunk_index INTEGER NOT NULL
  score       REAL NOT NULL
  rank        INTEGER

表 config:
  key         TEXT PRIMARY KEY
  value       TEXT NOT NULL
```

## 4. 交互流程

### 4.1 Web 评测流（主要路径）

```
用户操作                        系统处理
──────                        ─────
1. 选 Query 输入
2. 选 Chunk 库文件               → 读文件，生成 case + chunks
3. 选 Embedding 模型（多选）      → 从已配置供应商加载
4. 选稀疏检索算法（可选）         → BM25/TF-IDF
5. 选相似度度量                  → cosine/dot/euclidean/manhattan
6. 点击「开始评测」              → 创建 eval_run，逐模型打分
7. 查看结果                     → 排行榜 + 热力图
8. 切换参数或模型重新对比         → 新增 run，并排对比
```

### 4.2 Chunk 实验室流

```
1. 上传文本文件
2. 选择切块策略 + 调整参数
3. 实时预览切块结果（高亮分段边界）
4. 导出切块结果或直接发送到评测
```

## 5. 支持的评分维度

### 5.1 稠密检索（Embedding）

- 任意 litellm 支持的 embedding provider（OpenAI、百炼、Cohere、Voyage 等）
- 相似度度量：余弦相似度、欧氏距离（归一化后）、点积、曼哈顿距离

### 5.2 稀疏检索

- BM25、TF-IDF
- 纯本地计算，不需要 API

### 5.3 组合对比

- 同时显示多个模型在同一 query 和 metric 下的 top-K 排名
- 同屏对比柱状图

## 6. 可视化

### 6.1 排行榜
- 表格形式展示 Top-K 结果，包含 rank、chunk 片段、score
- 多个模型并列对比

### 6.2 相似度热力图（Heatmap）
- Chunk 之间两两相似度
- 使用 matplotlib/seaborn 或 NiceGUI 的交互式组件
- 颜色梯度直观展示

### 6.3 切块可视化
- 文本原文高亮分段边界
- 显示每段 token 数量

## 7. i18n 多语言

- 基础语言：中文 + 英文
- 使用 JSON 文件存储 key-value 翻译
- `i18n/__init__.py` 提供 `t(key)` 函数，根据当前语言返回翻译文本
- 切换语言即时生效

## 8. 最小依赖原则

```toml
# pyproject.toml (MVP)
dependencies = [
    "typer>=0.12",          # CLI
    "nicegui>=2.0",         # Web UI
    "litellm>=1.0",         # 统一 embedding 接口
    "numpy>=1.24",          # 向量计算
    "matplotlib",           # 热力图
]
```

所有依赖均可在 macOS 和 Windows 上一行安装。

## 9. 奥卡姆剃刀原则

- 不做用户管理、权限、远程部署
- 不引入 docker
- 不依赖外部数据库（只用内置 SQLite）
- 不做前端构建步骤（NiceGUI 原地渲染）
- 不做插件系统（供应商由 litellm 覆盖）
- 不做语义切块（需要 embedding 依赖，MVP 仅支持 recursive/fixed/lines）
- 不做 BM25+（BM25 + TF-IDF 两个 baseline 足够）
- 不做 rerank（MVP 聚焦 embedding 选型）
- 不做 embedding 向量缓存（MVP 先跑通，后续按需加）
- API Key 明文存储于本地 SQLite，用户自行确保文件权限
