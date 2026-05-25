#!/bin/bash
# book2mindmap 一键安装（Mac/Linux）
# 用法：curl -fsSL https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.sh | bash

set -e
REPO="https://github.com/ethan20221012-cyber/book2mindmap"
ZIP_URL="$REPO/archive/refs/heads/master.zip"
INSTALL_DIR="$HOME/book2mindmap"
SKILL_DIR="$HOME/.claude/skills/book2mindmap"

echo "=== book2mindmap 安装 ==="

# 1. 检测 Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ 未检测到 Python。请先安装 Python 3.8+："
    echo "   https://www.python.org/downloads/"
    exit 1
fi
echo "✓ Python: $($PYTHON --version)"

# 2. 下载并解压（不需要 git）
echo "下载项目..."
TMP=$(mktemp -d)
curl -fsSL "$ZIP_URL" -o "$TMP/book2mindmap.zip"
unzip -q "$TMP/book2mindmap.zip" -d "$TMP"
rm -rf "$INSTALL_DIR"
mv "$TMP/book2mindmap-master" "$INSTALL_DIR"
rm -rf "$TMP"
echo "✓ 项目已安装到 $INSTALL_DIR"

# 3. 安装 Python 依赖
echo "安装 Python 依赖..."
$PYTHON -m pip install ebooklib pymupdf beautifulsoup4 lxml -q
echo "✓ 依赖安装完成"

# 4. 安装 Claude Code skill
mkdir -p "$SKILL_DIR"
cp "$INSTALL_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "✓ Skill 已安装到 $SKILL_DIR"

# 5. 检测 lark-cli
if command -v lark-cli &>/dev/null; then
    echo "✓ lark-cli 已安装"
else
    echo "⚠ 未检测到 lark-cli"
    if command -v npm &>/dev/null; then
        echo "  正在安装 lark-cli..."
        npm install -g @larksuiteoapi/lark-cli -q
        echo "✓ lark-cli 安装完成"
    else
        echo "  请手动安装 Node.js 后运行：npm install -g @larksuiteoapi/lark-cli"
        echo "  Node.js 下载：https://nodejs.org"
    fi
fi

echo ""
echo "=== 安装完成 ==="
echo "项目目录：$INSTALL_DIR"
echo "本地电子书放到：$INSTALL_DIR/books/"
echo ""
echo "首次使用前请运行：lark-cli auth login"
echo "然后在 Claude Code 里说：「帮我读《书名》」"
