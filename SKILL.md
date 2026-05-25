---
name: book2mindmap
description: 书籍 → 飞书云文档 + 思维导图画板 + IM 推送。输入书名，自动获取全文（公版书库/本地文件）或搜索摘要，生成逐章详细笔记和 7 层 Mermaid 思维导图，发布到飞书并推送链接给用户本人。触发词：book2mindmap、读书笔记、思维导图、给我读、帮我读。
---

# book2mindmap

把一本书变成飞书云文档（逐章笔记）+ 飞书画板（7层思维导图）+ IM 推送。

## 前置条件

1. **安装 Python 依赖**（首次使用）：
   ```bash
   pip install ebooklib pymupdf beautifulsoup4 lxml
   ```

2. **lark-cli 已配置**：`lark-cli auth login` 完成，user 和 bot 身份均可用。

3. **项目目录**：把 book2mindmap 项目放到任意目录，记住路径（下称 `<PROJECT_DIR>`）。

## 触发方式

用户说以下任意一种：
- "帮我读《XXX》"
- "给我做《XXX》的思维导图"
- "book2mindmap XXX"
- "读书笔记 XXX"

## 执行流程

### Step 1：询问全文来源

用 AskUserQuestion 问用户：

```
来源选择：
A. 本地文件（epub/pdf/txt/mobi/azw）— 把文件放到 <PROJECT_DIR>/books/ 后告诉我文件名
B. 网络自动搜索（公版书库：Gutenberg / Internet Archive / Wikisource）
```

根据回答拼接命令：
- 本地：`python book2mindmap.py "<书名>" --source local --source-file books/<文件名>`
- 网络：`python book2mindmap.py "<书名>" --source web`

### Step 2：运行 fetch（Stage 1）

```bash
cd <PROJECT_DIR>
python book2mindmap.py "<书名>" --stage fetch --source <local|web> [--source-file <路径>]
```

**结果处理**：
- `[ok]`：全文获取成功，继续 Step 3
- `[request_written]`（fallback）：公版没找到，需要执行搜索。读取 `cache/<slug>/_search_request.md`，用 bing-search + tavily 双引擎搜索，把结果写入 `cache/<slug>/search.json`，再继续 Step 3
- `[error]`：报告错误，停止

### Step 3：生成章节目录（Stage 2 — outline）

```bash
python book2mindmap.py "<书名>" --stage outline
```

读取生成的 `cache/<slug>/_outline_request.md`，按其中的 prompt 生成 `cache/<slug>/outline.json`，写入后继续。

**outline.json 格式**：
```json
{
  "book_title": "...",
  "author": "...",
  "language": "zh|en",
  "confidence": "high|medium|low",
  "source_mode": "fulltext|fallback_summary",
  "chapters": [
    {"index": 1, "title": "章名", "summary": "一句话概要"}
  ]
}
```

### Step 4：生成逐章笔记（Stage 3 — notes）

```bash
python book2mindmap.py "<书名>" --stage notes
```

读取 `cache/<slug>/_notes_request.md`，按 prompt 生成 `cache/<slug>/notes.md`。

**fulltext 模式**：用 Read 工具逐章读取 `cache/<slug>/fulltext/chapters/NN.txt`，基于原文生成笔记。每章结构：
- 核心观点（3-5条，基于原文）
- 关键论据/案例
- 可操作启示
- 反思/局限

**fallback 模式**：基于搜索摘要生成，在笔记头部标注「仅依据网络二手资料」。

### Step 5：生成思维导图（Stage 4 — mindmap）

```bash
python book2mindmap.py "<书名>" --stage mindmap
```

读取 `cache/<slug>/_mindmap_request.md`，按 prompt 生成 `cache/<slug>/mindmap.mmd`。

**Mermaid mindmap 规范（7层）**：
```
mindmap
  root((书名))
    全书核心
      核心论点1
        支撑论据
          具体细节
            延伸说明
              最深锚点
    第1章 章名
      核心观点1
        关键论据或方法
          具体案例
            引用或数据
              操作建议
```

约束：
- 深度 6-7 层
- 每章 3-5 个观点，每观点 2-3 个子点，逐层展开
- 节点文字 ≤ 20 字
- 不含 `:` `()` `[]` `{}` 等 Mermaid 特殊字符

### Step 6：发布到飞书（Stage 5 — publish）

```bash
python book2mindmap.py "<书名>" --stage publish
```

自动完成：
1. `docs +create`（含 `<whiteboard type="blank"/>` 占位）→ 拿到 doc_token + board_token
2. `docs +update --command str_replace` 追加 notes.md 正文
3. `whiteboard +update --input_format mermaid --overwrite` 写思维导图
4. `drive +create-folder`（首次）+ `drive +move` 归档到「书籍读书笔记」文件夹

### Step 7：推送 IM（Stage 6 — notify）

```bash
python book2mindmap.py "<书名>" --stage notify
```

用 `--as user` 给用户本人发飞书消息，包含可点击的文档链接。

## 幂等性与断点续跑

每个 Stage 产物落到 `cache/<slug>/`，已完成的 Stage 自动跳过。

失败重跑某一步：
```bash
python book2mindmap.py "<书名>" --stage <stage名> --force
```

## 目录结构

```
<PROJECT_DIR>/
├── book2mindmap.py          # 主入口
├── pipeline/
│   ├── fetch/               # Stage 1：全文获取
│   │   ├── local.py         # 本地文件解析（txt/epub/pdf/mobi/azw）
│   │   ├── web.py           # 公版书库（Gutenberg/Archive/Wikisource）
│   │   ├── validate.py      # 完整性校验 + 章节切分（5种策略）
│   │   └── fallback.py      # 退到搜索摘要
│   ├── llm_stages.py        # Stage 2/3/4：生成请求文件
│   ├── publish.py           # Stage 5：飞书发布
│   └── notify.py            # Stage 6：IM 推送
├── prompts/                 # LLM prompt 模板
│   ├── outline.txt / outline_fulltext.txt
│   ├── chapter_notes.txt / chapter_notes_fulltext.txt
│   └── mindmap.txt
├── books/                   # 放本地电子书
└── cache/<slug>/            # 每本书的工作产物
    ├── source.json          # 来源元数据
    ├── fulltext/raw.txt     # 全文原始
    ├── fulltext/chapters/   # 切好的章节
    ├── outline.json
    ├── notes.md
    ├── mindmap.mmd
    └── publish.json         # 飞书资源 token（断点续跑用）
```

## 注意事项

- **发消息给用户本人必须 `--as user`**（飞书规则）
- **飞书文档用 v2 API + DocxXML**，不要用 v1
- **画板更新必须带 `--overwrite`**，否则叠加在旧内容上
- **`--force` 重跑 publish 时**会清掉 `mindmap_written` 和 `notes_appended` 标志，重新写入画板和正文
- 现代版权书（如《深度工作》）网络模式必走 fallback，笔记质量依赖搜索摘要
