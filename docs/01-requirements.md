# RagLab 需求文档

## 1. 项目概述

RagLab 是一个轻量级的 Embedding 模型选型评测工具，支持用户在本地快速对比不同 Embedding 模型、稀疏检索算法和相似度度量方式的效果。

### 核心价值

- 帮助开发者在 RAG 场景中选择最合适的 Embedding 模型
- 可视化对比不同模型/算法/参数组合的评分表现
- 零基础设施依赖，一行命令安装使用

## 2. 目标用户

- 单用户，个人开发者和 RAG 应用构建者
- 需要快速验证 Embedding 模型在自有数据上的表现
- 需要在不同模型供应商之间做出选型决策

## 3. 安装与部署

- `pip install raglab` 一行命令安装
- `raglab` 启动 Web UI，`raglab <subcommand>` 执行 CLI 操作
- 支持 macOS & Windows
- 本地运行，数据持久化到 SQLite

## 4. 功能需求

### 4.1 供应商管理 (Provider)

- 管理多家 Embedding 供应商配置（API Key、Base URL）
- 优先支持：OpenRouter、百炼、OpenAI
- 通过 litellm 统一接口，理论上覆盖 100+ 供应商

### 4.2 模型管理 (Model)

- 从已配置的供应商中可用模型列表
- 添加自定义模型
- 快速测试模型是否可用（输入一段文本测试 embedding 输出）

### 4.3 文本切块 (Chunk/Split) 评测

- 用户上传文本文件，可视化和对比不同切块策略的效果
- 支持策略：按字符切（fixed）、递归分隔符切（recursive）、按行切（lines）
- 可配置参数：chunk_size、overlap
- 可视化展示切块边界和内容

### 4.4 Embedding 模型评分对比 (核心功能)

- 输入 Query + Chunk 库（简单格式，每行一个 Chunk）
- 选择多个 Embedding 模型进行评分
- 支持不同相似度度量：余弦相似度、欧氏距离、点积、曼哈顿距离
- 以排行榜形式展示不同模型在各个度量下的评分

### 4.5 稀疏检索对比

- 支持 BM25、TF-IDF 作为稠密检索的 baseline 参考
- 同一评分界面展示稀疏 vs 稠密的对比

### 4.6 相似度矩阵

- 对 Chunk 库内所有片段两两计算相似度
- 生成热力图（Heatmap）可视化展示
- 支持导出为图片/HTML

### 4.7 RAG 参数配置面板

- 可调节常见 RAG 参数：chunk_size、overlap、top_k、metric 等
- 参数变更后用户手动重新运行评测

### 4.8 测试用例管理

- 用户可以创建和保存测试用例（名称 + 测试文本文件）
- 关联多个模型配置批量运行
- 保存历史评测结果，支持对比

### 4.9 多语言

- 支持中文和英文界面
- 通过 i18n JSON 文件维护翻译，提供 `t(key)` 翻译函数

## 5. 交互方式

### 5.1 Web UI（优先）

- NiceGUI 构建的本地 Web 应用
- 提供完整的可视化操作界面
- 交互流程：评测流 > 对比流

### 5.2 CLI（原子能力）

CLI 覆盖所有原子操作，支持管道和脚本组合：

| 分类 | 命令 | 用途 |
|------|------|------|
| 供应商管理 | `raglab provider add/list/remove` | 管理供应商配置 |
| 模型管理 | `raglab model list/test` | 查看和测试模型 |
| 配置管理 | `raglab config set/show/reset` | 管理 RAG 参数 |
| 文本切块 | `raglab split` | 文本切块并输出 |
| 打分 | `raglab score` | 单模型或稀疏算法评分 |
| 对比 | `raglab compare` | 多模型对比评分 |
| 相似度矩阵 | `raglab matrix` | 生成相似度矩阵 |
| 测试用例 | `raglab case add/list/run/remove` | 管理测试用例 |
| 启动 Web | `raglab serve` | 启动 Web UI |

## 6. 非功能需求

- 轻量级，最小外部依赖
- 本地优先，数据不出用户设备
- 响应式界面，美观现代
- 可在纯离线环境运行部分功能（稀疏检索、本地切块）
