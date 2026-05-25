#!/usr/bin/env python3
"""
book2mindmap 一键安装脚本

用法：
    python install.py

完成后说：「帮我读《书名》」即可使用。
"""
import os, sys, subprocess, shutil, urllib.request
from pathlib import Path

REPO = "https://github.com/ethan20221012-cyber/book2mindmap"
SKILL_DIR = Path.home() / ".claude" / "skills" / "book2mindmap"
SKILL_MD_URL = f"{REPO}/raw/master/SKILL.md"

def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, check=True, **kw)

def pip_install(pkg):
    run(f"{sys.executable} -m pip install {pkg} -q")

print("=== book2mindmap 安装 ===\n")

# 1. 安装 Python 依赖
print("1. 安装 Python 依赖...")
for pkg in ["ebooklib", "pymupdf", "beautifulsoup4", "lxml"]:
    pip_install(pkg)
print("   ✓ 依赖安装完成")

# 2. 克隆项目代码
install_dir = Path.home() / "book2mindmap"
if install_dir.exists():
    print(f"2. 项目目录已存在：{install_dir}，跳过克隆")
else:
    print(f"2. 克隆项目到 {install_dir}...")
    run(f"git clone {REPO} {install_dir}")
    print("   ✓ 克隆完成")

# 3. 安装 Claude Code skill
print("3. 安装 Claude Code skill...")
SKILL_DIR.mkdir(parents=True, exist_ok=True)
skill_md = SKILL_DIR / "SKILL.md"
urllib.request.urlretrieve(SKILL_MD_URL, skill_md)
print(f"   ✓ Skill 已安装到 {SKILL_DIR}")

# 4. 检查 lark-cli
if shutil.which("lark-cli"):
    print("4. ✓ lark-cli 已安装")
else:
    print("4. ⚠ 未检测到 lark-cli，请先安装：npm install -g @larksuiteoapi/lark-cli")

print(f"""
=== 安装完成 ===

项目目录：{install_dir}
放本地电子书：{install_dir}/books/

在 Claude Code 里说：
  「帮我读《深度工作》」
  「book2mindmap Walden」

注意：首次使用需确保 lark-cli 已登录（lark-cli auth login）
""")
