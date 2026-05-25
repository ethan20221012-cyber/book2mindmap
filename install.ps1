# book2mindmap 一键安装（Windows PowerShell）
# 用法：irm https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO = "https://github.com/ethan20221012-cyber/book2mindmap"
$ZIP_URL = "$REPO/archive/refs/heads/master.zip"
$INSTALL_DIR = "$HOME\book2mindmap"
$SKILL_DIR = "$HOME\.claude\skills\book2mindmap"

Write-Host "=== book2mindmap 安装 ===" -ForegroundColor Cyan

# 1. 检测 Python
try { $v = python --version 2>&1; Write-Host "OK $v" -ForegroundColor Green }
catch {
    Write-Host "X 未检测到 Python，请先安装：https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  安装时勾选 'Add Python to PATH'"
    exit 1
}

# 2. 下载并解压
Write-Host "下载项目..."
$tmp = "$env:TEMP\b2m_install.zip"
Invoke-WebRequest -Uri $ZIP_URL -OutFile $tmp
if (Test-Path $INSTALL_DIR) { Remove-Item $INSTALL_DIR -Recurse -Force }
Expand-Archive -Path $tmp -DestinationPath $HOME -Force
Rename-Item "$HOME\book2mindmap-master" "book2mindmap" -ErrorAction SilentlyContinue
Remove-Item $tmp
Write-Host "OK 项目已安装到 $INSTALL_DIR" -ForegroundColor Green

# 3. Python 依赖
Write-Host "安装 Python 依赖..."
python -m pip install ebooklib pymupdf beautifulsoup4 lxml -q
Write-Host "OK 依赖安装完成" -ForegroundColor Green

# 4. Claude Code skill
New-Item -ItemType Directory -Force $SKILL_DIR | Out-Null
Copy-Item "$INSTALL_DIR\SKILL.md" "$SKILL_DIR\SKILL.md" -Force
Write-Host "OK Skill 已安装" -ForegroundColor Green

# 5. lark-cli
if (Get-Command lark-cli -ErrorAction SilentlyContinue) {
    Write-Host "OK lark-cli 已安装" -ForegroundColor Green
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "安装 lark-cli..."
    npm install -g @larksuiteoapi/lark-cli -q
    Write-Host "OK lark-cli 安装完成" -ForegroundColor Green
} else {
    Write-Host "! 请安装 Node.js 后运行：npm install -g @larksuiteoapi/lark-cli" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Cyan
Write-Host "项目目录：$INSTALL_DIR"
Write-Host "本地电子书放到：$INSTALL_DIR\books\"
Write-Host ""
Write-Host "首次使用：lark-cli auth login"
Write-Host "然后在 Claude Code 里说：「帮我读《书名》」"
