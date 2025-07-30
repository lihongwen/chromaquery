@echo off
REM ChromaDB Web Manager 部署脚本 (Windows)

setlocal enabledelayedexpansion

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo ChromaDB Web Manager 部署脚本
echo 平台: Windows
echo.

REM 检查必要工具
echo [1/2] 检查必要工具...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] Python: %%i

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 未安装或不在 PATH 中
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [OK] Node.js: %%i

npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm 未安装或不在 PATH 中
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do echo [OK] npm: %%i

REM 检查 uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] uv 未安装，将使用 pip
) else (
    for /f "tokens=*" %%i in ('uv --version') do echo [OK] uv: %%i
)

echo.

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

REM 运行 Python 部署脚本
echo [2/2] 运行部署脚本...
python deploy.py

echo.
echo 部署完成！
echo.
echo 下一步:
echo 运行 scripts\start.bat 或 python start.py 启动应用

pause
