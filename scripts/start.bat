@echo off
REM ChromaDB Web Manager 启动脚本 (Windows)

setlocal enabledelayedexpansion

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo ChromaDB Web Manager 启动器
echo 平台: Windows
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或不在 PATH 中
    pause
    exit /b 1
)

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

REM 检查虚拟环境
if not exist ".venv" (
    echo [ERROR] 虚拟环境不存在，请先运行: python deploy.py
    pause
    exit /b 1
)

REM 检查配置文件
if not exist "config.json" (
    echo [ERROR] 配置文件不存在，请先运行: python deploy.py
    pause
    exit /b 1
)

REM 启动服务
echo [INFO] 启动 ChromaDB Web Manager...
python start.py

pause
