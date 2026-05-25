# book2mindmap

书名 → 飞书云文档（逐章笔记）+ 飞书画板（7层思维导图）+ IM 推送

## 安装（一行命令）

**Mac / Linux：**
```bash
curl -fsSL https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.sh | bash
```

**Windows（PowerShell）：**
```powershell
irm https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.ps1 | iex
```

安装完成后运行一次：
```bash
lark-cli auth login
```

然后在 Claude Code 里说：**「帮我读《书名》」**

---

## 前提

- Python 3.8+（[下载](https://www.python.org/downloads/)，Windows 安装时勾选 "Add Python to PATH"）
- Claude Code 已安装

---

## 使用

| 来源 | 说法 |
|------|------|
| 公版书（Gutenberg 等） | 「帮我读《Walden》」 |
| 本地电子书 | 把 epub/pdf/txt 放到 `~/book2mindmap/books/`，说「帮我读《书名》」 |
| 现代版权书 | 自动退到双引擎搜索摘要 |

## 产出

- 飞书云文档：逐章详细笔记
- 飞书画板：7 层 Mermaid 思维导图
- 飞书 IM：文档链接推送给本人
