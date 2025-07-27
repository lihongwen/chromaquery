@echo off
REM ChromaDB Web Manager Windows依赖安装脚本
REM 专门处理Windows平台的特殊依赖

setlocal enabledelayedexpansion

echo ChromaDB Web Manager - Windows依赖安装
echo =====================================
echo.

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

REM 检查虚拟环境
if not exist ".venv" (
    echo [ERROR] 虚拟环境不存在，请先运行: python deploy.py
    pause
    exit /b 1
)

echo [INFO] 激活虚拟环境...
call .venv\Scripts\activate.bat

REM 安装Windows特定的依赖
echo [INFO] 安装Windows特定依赖...

REM 安装pywin32（用于Windows快捷方式创建等功能）
echo [INFO] 安装pywin32...
pip install pywin32 -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [WARNING] pywin32安装失败，某些Windows特性可能不可用
)

REM 安装Windows下的编译工具（如果需要）
echo [INFO] 检查Microsoft Visual C++ Build Tools...
python -c "import distutils.msvccompiler; print('MSVC编译器可用')" 2>nul
if errorlevel 1 (
    echo [WARNING] Microsoft Visual C++ Build Tools未安装
    echo [INFO] 某些包可能需要编译工具，建议安装Visual Studio Build Tools
    echo [INFO] 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
)

REM 设置Windows特定的环境变量
echo [INFO] 设置Windows环境变量...
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 创建Windows启动快捷方式（可选）
echo [INFO] 是否创建桌面快捷方式？ (y/n)
set /p CREATE_SHORTCUT=
if /i "%CREATE_SHORTCUT%"=="y" (
    echo [INFO] 创建桌面快捷方式...
    python -c "
import os
from pathlib import Path
try:
    import win32com.client
    desktop = Path.home() / 'Desktop'
    shortcut_path = desktop / 'ChromaDB Web Manager.lnk'
    target_path = Path.cwd() / 'scripts' / 'start.bat'
    
    shell = win32com.client.Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(target_path)
    shortcut.WorkingDirectory = str(Path.cwd())
    shortcut.IconLocation = str(target_path)
    shortcut.save()
    print('桌面快捷方式创建成功')
except ImportError:
    print('需要pywin32才能创建快捷方式')
except Exception as e:
    print(f'创建快捷方式失败: {e}')
"
)

echo.
echo [SUCCESS] Windows依赖安装完成！
echo.
echo 下一步:
echo 1. 运行 scripts\start.bat 启动应用
echo 2. 或者运行 python start.py
echo.

pause
