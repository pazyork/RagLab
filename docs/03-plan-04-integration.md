# RagLab 实施计划 (4/4)：集成收尾

> **前置：** 计划 1/4 + 2/4 + 3/4 全部实现

**目标：** 端到端调通、README、发布准备

---

### Task 15: CLI 端到端调通

**验证场景：**

1. **完整评测流程：**
```bash
echo -e "RAG是检索增强生成技术\nEmbedding将文本映射到向量空间\nBM25是一种稀疏检索算法\n深度学习改变了NLP领域\nTransformer架构是基础" > /tmp/chunks.txt

raglab provider add openai --api-key $OPENAI_API_KEY
raglab config set top_k 3
raglab score "什么是Embedding" /tmp/chunks.txt --model text-embedding-3-small --metric cosine
raglab score "什么是Embedding" /tmp/chunks.txt --algorithm bm25
raglab compare "什么是Embedding" /tmp/chunks.txt --models text-embedding-3-small --algorithm bm25
raglab matrix /tmp/chunks.txt --model text-embedding-3-small --output /tmp/heatmap.png
```

2. **测试用例生命周期：**
```bash
raglab case add demo /tmp/chunks.txt --description "demo chunks"
raglab case list
raglab case run demo --models text-embedding-3-small
raglab case remove demo --force
```

3. **split 命令：**
```bash
raglab split /tmp/chunks.txt --strategy recursive --chunk-size 200 --overlap 20
```

**修复：** 集成过程中发现的签名不匹配、import 缺失、typer option 默认值问题

---

### Task 16: Web UI 端到端调通

**验证操作：**
1. `raglab serve --port 8080`
2. 浏览器打开 http://localhost:8080
3. 设置页面：添加 provider + 快速测试模型连接
4. Chunk 实验室：上传文本 → 调整参数 → 预览切块
5. 评测页面：输入 query → 选 chunks → 选模型 → 开始评测 → 查看结果

**修复：** UI 交互 bug、数据流转问题、响应式布局

---

### Task 17: README.md

**内容要点：**
- 一句话介绍
- 安装：`pip install raglab`
- 快速开始：3 条命令跑通典型流程
- CLI 命令速查表
- Web UI 截图（描述）
- 支持的模型供应商（OpenRouter、OpenAI、百炼等）
- 支持的相似度度量
- 支持的切块策略
- 项目结构简介
- 中英文

---

### Task 18: 最终检查

- [ ] `pip install -e .` 在 macOS 和 Windows 分别测试
- [ ] `raglab --help` 正常
- [ ] `raglab serve` 可启动
- [ ] `pytest tests/ -v` 全绿
- [ ] git tag v0.1.0

---

## 整体完成标准

| 维度 | 标准 |
|------|------|
| 安装 | `pip install -e .` 一次成功 |
| CLI | 所有原子命令可独立执行，管道组合不阻塞 |
| Web | 三个页面可用，评测流程端到端走通 |
| 持久化 | 重启后 provider/config/case 数据不丢 |
| 测试 | `pytest tests/ -v` 全部通过 |
| 跨平台 | macOS 确认，Windows 路径分隔符兼容 |
