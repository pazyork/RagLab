# RagLab 实施计划 (2/4)：存储层 + CLI

> **前置：** 计划 1/4 全部通过

**目标：** 实现 SQLite 持久化 + typer CLI 所有原子命令

---

## 模块依赖图

```
cli.py ──→ storage/db.py ──→ sqlite3 (内置)
  │
  ├──→ core/scorer.py
  ├──→ core/splitter.py
  └──→ core/embedder.py
```

---

### Task 6: storage/db.py — SQLite 持久化

**职责：** 所有持久化操作的唯一入口，封装 SQLite

**类：`Database(path: str | None)`**
- path=None 时默认 `~/.raglab.db`
- 构造时自动建表（CREATE IF NOT EXISTS）

**五张表：**

| 表 | 核心列 | 说明 |
|----|--------|------|
| `providers` | id, name(UNIQUE), api_key, base_url | 供应商 |
| `models` | id, provider_id(FK), model_name, model_type | 模型快照 |
| `test_cases` | id, name(UNIQUE), description | 测试用例 |
| `case_chunks` | id, case_id(FK CASCADE), chunk_index, content | 用例的 chunk |
| `eval_runs` | id, case_id(FK), name, model, metric, algorithm, status | 评测任务 |
| `eval_scores` | id, run_id(FK CASCADE), chunk_index, score, rank | 评分结果 |
| `config` | key(PRIMARY), value | 键值配置 |

**方法接口（按实体分组）：**

**Providers:**
- `add_provider(name, api_key, base_url?) -> int` — 返回 id
- `list_providers() -> list[tuple]`
- `get_provider(name) -> tuple | None`
- `remove_provider(name) -> None`

**Models:**
- `add_model(provider_id, model_name, model_type?) -> int`
- `list_models(provider_name?) -> list[tuple]`

**Test Cases:**
- `add_case(name, description?) -> int`
- `list_cases() -> list[tuple]`
- `get_case(case_id) -> tuple | None`
- `remove_case(case_id) -> None`

**Chunks:**
- `add_chunks(case_id, chunks: list[str]) -> None`
- `get_chunks(case_id) -> list[tuple]`

**Eval Runs:**
- `add_run(case_id, name, model, metric, algorithm?) -> int`
- `update_run_status(run_id, status) -> None`
- `list_runs(case_id?) -> list[tuple]`
- `add_scores(run_id, scores: list[(chunk_index, score, rank)]) -> None`
- `get_scores(run_id) -> list[tuple]`

**Config:**
- `set_config(key, value) -> None` — INSERT OR REPLACE
- `get_config(key) -> int|float|str|None` — 自动类型推断
- `get_all_config() -> dict`

**close()** — 关闭连接

**测试要点：**
- 每个 CRUD 操作验证写后读一致
- ON DELETE CASCADE：删 case → chunks 连带删除
- config 类型推断 (int: "512" → 512, float: "0.5" → 0.5)
- 每次测试用临时文件，测试后清理

**依赖：** 仅 sqlite3（Python 内置）

---

### Task 7: cli.py — CLI 原子命令

**职责：** typer 命令树，每个命令做一件事

**技术选型：** typer（内置 help、颜色、prompt）

**架构：**
```
app (typer.Typer)
├── provider_app: add / list / remove
├── model_app: list / test
├── config_app: set / show / reset
├── split (顶层命令)
├── score (顶层命令)
├── compare (顶层命令)
├── matrix (顶层命令)
├── case_app: add / list / run / remove
└── serve (顶层命令)
```

**状态管理：** 两个懒加载全局单例（模块级变量）：
- `get_db() -> Database` — 延迟初始化 ~/.raglab.db
- `get_embedder() -> Embedder` — 从 DB 读取 provider 配置填充

**各命令功能定义：**

| 命令 | 参数 | 功能 |
|------|------|------|
| `provider add <name>` | `--api-key`(必), `--base-url`(选) | 写 DB |
| `provider list` | 无 | 读 DB 表格式输出 |
| `provider remove <name>` | `--force` | 确认后删 |
| `model list` | `--provider`(选) | 按 provider 过滤 |
| `model test` | `--model`(必), `--text`(选) | 调 embedder 验证可用性 |
| `config set <key> <value>` | 无 | 写 DB config 表 |
| `config show` | 无 | 读 DB 全量输出 |
| `config reset` | `--force` | 清空 config 表 |
| `split <file>` | `--strategy`, `--chunk-size`, `--overlap`, `--output` | 读文件→切块→输出 |
| `score <query> <file>` | `--model`/`--algorithm`, `--metric`, `--top-k`, `--format` | 单模型/算法评分 |
| `compare <query> <file>` | `--models`(逗号分隔), `--algorithm`(选), `--metric`, `--top-k` | 多模型逐个评分输出 |
| `matrix <file>` | `--model`(必), `--metric`, `--output`(选) | embed→两两相似度→PNG 或 JSON |
| `case add <name> <file>` | `--description` | 读文件→写 case + chunks |
| `case list` | 无 | 列表 + chunk 数量 |
| `case run <name>` | `--models`, `--metric`, `--top-k` | 按名找 case→逐模型评分→存 DB |
| `case remove <name>` | `--force` | 确认后删 |
| `serve` | `--port`(默认 8080) | 启动 NiceGUI Web |

**输出格式：** score/compare/case-run 支持 `--format table|json|csv`
- table：对齐的终端表格
- json：标准 JSON 数组
- csv：带 header 的逗号分隔

**测试要点：**
- 使用 `typer.testing.CliRunner`，不实际调用 API
- provider add/list/remove 基本流程
- config set/show 往返一致
- split 用 tmp_path 创建临时文件
- score 不存在的 model → 非零退出码
- serve --help 正常输出

**依赖：** typer, core.*, storage.db

---

## 完成标准

```bash
raglab --help              # 帮助信息完整
raglab config set top_k 5  # 写入成功
raglab config show         # 读回 top_k=5
pytest tests/ -v           # 全部 green（新增约 7 个 CLI + 7 个 DB 测试）
```
