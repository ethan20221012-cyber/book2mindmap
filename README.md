# book2mindmap

书名 → 飞书云文档（逐章笔记）+ 飞书画板（7层思维导图）+ IM 推送

## 安装

### Mac / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.sh | bash
```

### Windows

下载 [install.bat](https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.bat) 后双击运行。

或在 PowerShell 里：
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.bat" -OutFile install.bat; .\install.bat
```

安装脚本自动完成：下载代码 → 安装 Python 依赖 → 安装 Claude Code skill → 检测 lark-cli。

**最低要求：Python 3.8+**（[下载](https://www.python.org/downloads/)）

---

## 首次使用

```bash
lark-cli auth login   # 登录飞书账号
```

然后在 Claude Code 里说：

> 「帮我读《深度工作》」

---

## 使用方式

| 来源 | 命令 |
|------|------|
| 本地电子书（epub/pdf/txt/mobi/azw） | 把文件放到 `~/book2mindmap/books/`，告诉 Claude |
| 网络公版书（Gutenberg 等） | 直接说书名，Claude 自动搜索 |
| 现代版权书 | 自动退到双引擎搜索摘要 |

---

## 产出

- **飞书云文档**：逐章详细笔记，含核心观点、论据、可操作启示
- **飞书画板**：7层 Mermaid 思维导图
- **飞书 IM**：文档链接推送给本人
