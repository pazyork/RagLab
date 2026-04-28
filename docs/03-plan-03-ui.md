# RagLab 实施计划 (3/4)：i18n + Web UI

> **前置：** 计划 1/4 + 2/4 全部通过

**目标：** 实现 i18n 翻译系统 + NiceGUI Web 界面（三页面 + 两组件）

---

## 文件结构

```
src/raglab/
├── i18n/
│   ├── __init__.py         # t(key) 翻译函数 + 语言切换
│   ├── zh.json
│   └── en.json
└── ui/
    ├── app.py                 # NiceGUI 入口，路由 + 布局
    ├── pages/
    │   ├── evaluate.py        # 评测页面（核心）
    │   ├── chunk_lab.py       # Chunk 实验室
    │   └── settings.py        # 设置页面
    └── components/
        ├── heatmap.py         # 相似度热力图组件
        └── leaderboard.py     # 评分排行榜组件
```

---

### Task 8: i18n — 翻译模块 + 中英文 JSON

**文件：** `i18n/__init__.py`, `zh.json`, `en.json`

**`i18n/__init__.py` 接口：**
- `_current_lang: str = "zh"` — 模块级语言状态
- `_translations: dict[str, dict]` — 缓存已加载的翻译
- `t(key: str) -> str` — 返回当前语言的翻译，找不到则返回 key 本身
- `set_lang(lang: str) -> None` — 切换语言
- `get_lang() -> str` — 获取当前语言
- `_load_translations(lang: str) -> dict` — 读取对应 JSON 文件

**JSON 格式：**
```json
{
  "app.title": "RagLab",
  "nav.evaluate": "评测",
  "nav.chunk_lab": "Chunk 实验室",
  "nav.settings": "设置",
  "btn.start": "开始评测",
  ...
}
```

**测试要点：**
- `t("app.title")` 返回正确翻译
- `t("nonexistent.key")` 返回 key 本身
- `set_lang("en")` 后 `t()` 返回英文
- 两个 JSON 文件 key 集合一致

---

### Task 9: ui/components/heatmap.py — 相似度热力图

**职责：** 输入相似度矩阵 + chunk 标签，渲染交互式热力图

**接口：**
```
render_heatmap(matrix: list[list[float]], labels: list[str]) -> nicegui element
```

**实现：**
- 使用 NiceGUI 的 `ui.pyplot` 或 `ui.plotly` 渲染
- 备选：matplotlib 生成 PNG → ui.image 嵌入
- 颜色梯度 YlOrRd，数值范围 [0, 1]
- 支持 hover 显示具体数值

**依赖：** matplotlib, nicegui

---

### Task 10: ui/components/leaderboard.py — 评分排行榜

**职责：** 输入多条评分结果，渲染可排序的对比排行榜表格

**接口：**
```
render_leaderboard(results: list[dict], models: list[str]) -> nicegui element
```
其中 results 结构为 `[{model: str, scores: [{index, score, text}]}]`

**实现：**
- NiceGUI `ui.table` 或 `ui.aggrid`
- 列：Rank, Chunk 片段(截断), Score, Model
- 多模型时并排列出各自 Top-K
- 模型间用颜色区分

**依赖：** nicegui

---

### Task 11: ui/pages/settings.py — 设置页面

**职责：** 供应商管理 + 模型管理 + 默认参数配置

**布局：** 三栏或 Tab 切换

**功能区域：**

| 区域 | 操作 | UI 组件 |
|------|------|---------|
| 供应商列表 | 查看已配置列表 | ui.table |
| 添加供应商 | name, api_key, base_url 表单 | ui.input + ui.button |
| 删除供应商 | 确认后删除 | ui.button + 确认对话框 |
| 模型列表 | 按供应商查看模型 | ui.table |
| 快速测试 | 选模型 + 输入文本 → 测试 embedding | ui.select + ui.input + 结果显示 |
| 默认参数 | chunk_size, overlap, top_k, metric 等 | ui.number / ui.select |
| 语言切换 | 中文/English | ui.toggle |

**数据处理：** 通过 DB 读写（provider、model、config）

---

### Task 12: ui/pages/chunk_lab.py — Chunk 实验室

**职责：** 上传文本 → 实时切块预览 → 导出

**交互流程：**
1. 上传文本文件（或粘贴）
2. 选择策略（recursive / fixed / lines）+ 调整 chunk_size / overlap
3. 实时预览：原文中高亮切块边界，显示每个 chunk 的编号和字符数
4. 导出：保存切块结果或发送到评测页

**关键 UI：**
- `ui.upload` 文件上传
- `ui.textarea` 文字粘贴
- `ui.select` 策略选择
- `ui.slider` chunk_size / overlap 调节
- 预览区：每行一个 chunk，编号 + 淡色背景区分边界
- `ui.button` "导出" 和 "发送到评测"

**数据处理：** 调 core.splitter

---

### Task 13: ui/pages/evaluate.py — 评测页面（核心）

**职责：** 整个 tool 的主页面，完成完整的评测流程

**交互流程：**
1. Query 输入（手动输入或用已存 case）
2. Chunk 库选择（上传文件 / 从 case 库选取）
3. 模型选择（多选 checkbox，reload 来自 settings 配置）
4. 稀疏算法选择（可选，BM25/TF-IDF）
5. 相似度度量选择（cosine/euclidean/dot/manhattan）
6. Top-K 设置
7. 点击「开始评测」
8. 结果区：排行榜（leaderboard）+ 热力图（heatmap）
9. 可切换参数重新评测、对比历史 run

**关键 UI 组件：**
- `ui.input` Query 输入
- `ui.upload` + `ui.select` Chunk 库
- `ui.select(multiple=True)` 模型多选
- `ui.checkbox` 稀疏算法勾选
- `ui.select` 度量选择
- `ui.number` Top-K
- `ui.button` 开始评测（带 loading 状态）
- 结果区动态渲染 leaderboard + heatmap
- 历史 run 列表（从 DB 读取）

**数据处理：** 调 core.scorer + storage.db

---

### Task 14: ui/app.py — 应用入口 + 全局布局

**职责：** 组装三个页面，提供导航和全局状态

**架构：**
```
create_app() -> nicegui.Client
  ├── 顶部导航 (Tab 切换: 评测 / Chunk 实验室 / 设置)
  ├── 语言切换按钮
  └── 内容区 (根据 Tab 渲染对应 page)
```

**全局状态（NiceGUI app.storage 或 session）：**
- 当前语言
- 当前选中的 model/provider 引用
- 当前评测结果（跨组件共享）

**路由实现：** NiceGUI 用 `ui.tabs` + 条件渲染切换内容

**依赖：** nicegui

---

## 完成标准

```bash
raglab serve --port 8080    # 启动无报错
# 浏览器访问 http://localhost:8080
# 三个 Tab 可切换，设置页可添加 provider，评测页流程跑通
```
