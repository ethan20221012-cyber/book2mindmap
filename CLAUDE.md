# book2mindmap

## 项目目标

输入一个书名，自动产出：
1. **飞书云文档**：逐章详细笔记（带信息来源标注）
2. **飞书画板**：Mermaid mindmap 思维导图
3. **飞书 IM 消息**：把链接推送给用户本人

## 管道分 6 个 Stage

| Stage | 名称 | 执行者 | 产物 |
|-------|------|--------|------|
| 1 | search | Python + MCP（bing-search / tavily） | `cache/<slug>/search.json` |
| 2 | outline | Claude Code（读 search.json，产出目录） | `cache/<slug>/outline.json` |
| 3 | notes | Claude Code（逐章笔记） | `cache/<slug>/notes.md` |
| 4 | mindmap | Claude Code（笔记压成 mermaid） | `cache/<slug>/mindmap.mmd` |
| 5 | publish | Python + lark-cli | `cache/<slug>/publish.json` |
| 6 | notify | Python + lark-cli | （IM 已发） |

Stage 2/3/4 是 LLM 工作，Python 脚本输出 prompt 文件后退出，等待 Claude Code 完成并把产物写回缓存目录，再继续 Stage 5/6。

## 用法

```bash
# 完整流程（半自动）
python book2mindmap.py "深度工作"

# 指定阶段
python book2mindmap.py "深度工作" --stage publish
python book2mindmap.py "深度工作" --stage notify

# 强制重跑某阶段（无视缓存）
python book2mindmap.py "深度工作" --stage outline --force
```

## 重要约束

- 飞书 docs 用 **v2 API + DocxXML**（不要用 v1 markdown）
- 思维导图用 **Mermaid mindmap**，深度 ≤ 3 层，每章 3-5 节点
- 发消息给用户本人必须 `--as user`
- 内容必须双引擎搜索校验，单源结果不出笔记
- 失败重跑：删 `cache/<slug>/` 对应 stage 产物文件即可

## 父项目继承

继承 `f:/claude_lark_workspace/CLAUDE.md` 的飞书 CLI 工具与共享 skill 配置。

## 不做

- 不上传 PDF/EPUB（纯靠搜索+AI）
- 不做多语言翻译
- 不做画板复杂美化

## 改进方向

- 接 Anthropic SDK 全自动化
- 支持本地 PDF 输入
- 同步到 Lark Wiki
