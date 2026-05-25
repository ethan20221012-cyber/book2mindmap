# book2mindmap 安装包

你收到了这个 zip 文件。请按以下步骤自动完成安装：

## 自动安装指令

1. 解压这个 zip 到用户 HOME 目录下的 `book2mindmap/` 文件夹
2. 安装 Python 依赖：`pip install ebooklib pymupdf beautifulsoup4 lxml`
3. 把 `SKILL.md` 复制到 `~/.claude/skills/book2mindmap/SKILL.md`
4. 检测 lark-cli 是否已安装（`lark-cli --version`）：
   - 已安装 → 提示用户运行 `lark-cli auth login`
   - 未安装 → 运行 `npm install -g @larksuiteoapi/lark-cli`，再提示登录
5. 安装完成后告诉用户：
   - 项目目录在哪里
   - 本地电子书放到 `books/` 子目录
   - 在 Claude Code 里说「帮我读《书名》」即可使用
