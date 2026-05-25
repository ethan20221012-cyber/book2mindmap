# book2mindmap

> 输入一个书名 → 飞书云文档（逐章笔记）+ 飞书画板（思维导图）+ IM 推送

## 快速开始

```bash
cd f:/claude_lark_workspace/book2mindmap

# 端到端（半自动，Stage 2/3/4 由 Claude Code 完成 LLM 工作）
python book2mindmap.py "深度工作"
```

## 工作原理

6 个 Stage，每个 Stage 把产物落到 `cache/<book-slug>/`，可断点续跑：

```
search → outline → notes → mindmap → publish → notify
```

- **search / publish / notify**：纯 Python + lark-cli，自动跑
- **outline / notes / mindmap**：脚本生成 prompt 后暂停，由 Claude Code 在 IDE 里读取 prompt + 原料、生成产物、写回缓存目录，再 `python book2mindmap.py "<书名>" --stage <下一阶段>` 继续

## 技术细节

### 飞书 API

- 文档：`docs +create --api-version v2 --content '<title>...</title><whiteboard type="blank"/>...'`
  - 一次创建 docx + 嵌入空画板
  - 响应里取 `data.board_tokens[0]` 即画板 token
- 画板：`whiteboard +update --input_format mermaid` 写 mindmap
- 消息：`im +messages-send --as user --user-id <self>`（发给本人必须 `--as user`）

### 搜索校验

- bing-search MCP（无墙）+ tavily MCP（深度研究）双源
- AI 分别从两份原料提目录 → 章数差 > 2 时仲裁
- 笔记阶段把两份原料一起喂给 AI，要求标注观点来源

### 思维导图

Mermaid `mindmap` 语法，根节点是书名，第二层是章名，第三层是核心观点（每章 3-5 个）。

## 目录结构

```
book2mindmap/
├── book2mindmap.py        # 主入口
├── pipeline/              # 各 Stage 模块
├── prompts/               # LLM prompt 模板
└── cache/<slug>/          # 每本书的工作产物（幂等）
```

## 常见问题

### 重跑某一步
```bash
python book2mindmap.py "深度工作" --stage notes --force
```

### 完全重跑
```bash
rm -rf cache/<slug>/
python book2mindmap.py "深度工作"
```

### 文档去哪了
飞书云空间 → 「书籍读书笔记」文件夹（首次跑时自动创建）。
