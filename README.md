# RAGLab

在选 Embedding 模型之前，你需要在自己的数据上测一测。RAGLab 就是干这个的——本地运行，数据不出机器，装完一行命令启动。

**[English](README_en.md)** · **[Agent Reference](README_agent.md)**

---

## 长这样

**Settings** — 配置供应商和模型（支持 OpenAI、百炼、OpenRouter 等任何兼容 OpenAI 接口的服务）

![Settings](docs/screenshots/settings.png)

**Datasets** — 管理测试文本，上传文件或直接粘贴内容

![Datasets](docs/screenshots/datasets.png)

**Playground** — 跑 Query，检索结果按相似度排序，右侧实时显示分布直方图和 t-SNE/UMAP 语义分簇图

![Playground](docs/screenshots/playground_tsne.png)

**Chunk vs Chunk** — 全量 chunk 两两相似度热力图，快速发现冗余和语义结构

![Heatmap](docs/screenshots/heatmap.png)

---

## 装

需要 Python 3.10+。

```bash
pip install raglab
raglab serve
```

打开 http://localhost:8099 就行了。

数据存在 `~/.raglab.db`，SQLite，重启不丢。如需 UMAP 投影功能，额外安装：`pip install umap-learn`。

---

## 用

**第一步：配供应商**

进 Settings，填 API Key 和 Base URL。只要是 OpenAI 兼容接口都能用。比如 OpenRouter 的 Base URL 是 `https://openrouter.ai/api/v1`。

**第二步：加模型**

同一个供应商可以加多个模型，Settings 里点 Add Model。加完可以点 Test 验证一下能不能通。

**第三步：准备数据集**

去 Datasets，创建一个数据集，把你的文档粘进去或者上传文件。文档会按配置的 chunk size 自动切块。

**第四步：在 Playground 跑评测**

- **Query vs Chunks**：输入一个 query，选模型和检索策略（Dense / BM25 / Hybrid），看哪些 chunk 被检索出来、排名怎么样。右边有相似度分布图和 UMAP 投影。
- **Chunk vs Chunk**：选一个数据集，生成所有 chunk 的相似度矩阵热力图，看 chunk 之间的语义关系。

---

## CLI

不想开 Web UI 也行，直接命令行用：

```bash
# 配置供应商
raglab provider add openrouter --api-key sk-xxx --base-url https://openrouter.ai/api/v1
raglab provider list

# 看模型列表、测模型
raglab model list
raglab model test --model baai/bge-m3

# 切块
raglab split doc.txt --strategy recursive --chunk-size 512

# 打分（单模型）
raglab score "什么是 RAG" chunks.txt --model baai/bge-m3

# 多模型对比
raglab compare "什么是 RAG" chunks.txt --models baai/bge-m3,qwen/qwen3-embedding-8b

# 相似度矩阵
raglab matrix chunks.txt --model baai/bge-m3

# 管理测试用例
raglab case add mytest chunks.txt
raglab case run mytest
```

---

## 支持的检索策略

| 策略 | 说明 |
|------|------|
| Dense | 向量相似度，需要 Embedding 模型 |
| BM25 | 基于词频的稀疏检索，不需要模型 |
| Hybrid | 两者结合，加权融合 |

相似度度量支持：Cosine、Dot Product、Euclidean、Manhattan。

---

## 数据和隐私

所有数据（包括 API Key）存在本地 `~/.raglab.db`，不上传到任何地方。API Key 明文存储，注意文件权限。
