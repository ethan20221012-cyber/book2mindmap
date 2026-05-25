@echo off
:: book2mindmap 一键安装（Windows）
:: 用法：在 PowerShell 里运行：
::   irm https://raw.githubusercontent.com/ethan20221012-cyber/book2mindmap/master/install.bat | iex
:: 或下载后双击运行

setlocal
set REPO=https://github.com/ethan20221012-cyber/book2mindmap
set ZIP_URL=%REPO%/archive/refs/heads/master.zip
set INSTALL_DIR=%USERPROFILE%\book2mindmap
set SKILL_DIR=%USERPROFILE%\.claude\skills\book2mindmap
set TMP_ZIP=%TEMP%\book2mindmap.zip
set TMP_DIR=%TEMP%\book2mindmap_install

echo === book2mindmap 安装 ===

:: 1. 检测 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo X 未检测到 Python，请先安装 Python 3.8+：
    echo   https://www.python.org/downloads/
    echo   安装时勾选 "Add Python to PATH"
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo OK %%i

:: 2. 下载并解压
echo 下载项目...
powershell -Command "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%TMP_ZIP%'"
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"
powershell -Command "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%TMP_DIR%' -Force"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
move "%TMP_DIR%\book2mindmap-master" "%INSTALL_DIR%" >nul
rmdir /s /q "%TMP_DIR%"
del "%TMP_ZIP%"
echo OK 项目已安装到 %INSTALL_DIR%

:: 3. 安装 Python 依赖
echo 安装 Python 依赖...
python -m pip install ebooklib pymupdf beautifulsoup4 lxml -q
echo OK 依赖安装完成

:: 4. 安装 Claude Code skill
if not exist "%SKILL_DIR%" mkdir "%SKILL_DIR%"
copy /y "%INSTALL_DIR%\SKILL.md" "%SKILL_DIR%\SKILL.md" >nul
echo OK Skill 已安装到 %SKILL_DIR%

:: 5. 检测 lark-cli
lark-cli --version >nul 2>&1
if errorlevel 1 (
    echo ! 未检测到 lark-cli
    npm --version >nul 2>&1
    if errorlevel 1 (
        echo   请先安装 Node.js：https://nodejs.org
        echo   安装后运行：npm install -g @larksuiteoapi/lark-cli
    ) else (
        echo   正在安装 lark-cli...
        npm install -g @larksuiteoapi/lark-cli
        echo OK lark-cli 安装完成
    )
) else (
    echo OK lark-cli 已安装
)

echo.
echo === 安装完成 ===
echo 项目目录：%INSTALL_DIR%
echo 本地电子书放到：%INSTALL_DIR%\books\
echo.
echo 首次使用前请运行：lark-cli auth login
echo 然后在 Claude Code 里说：帮我读《书名》
echo.
pause
