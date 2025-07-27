@echo off
REM ChromaDB Web Manager Windows故障排除脚本

setlocal enabledelayedexpansion

echo ChromaDB Web Manager - Windows故障排除
echo ====================================
echo.

REM 获取脚本目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM 切换到项目根目录
cd /d "%PROJECT_ROOT%"

echo [INFO] 系统信息检查...
echo 操作系统: %OS%
echo 处理器架构: %PROCESSOR_ARCHITECTURE%
echo 用户名: %USERNAME%
echo 当前目录: %CD%
echo.

echo [INFO] Python环境检查...
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python未安装或不在PATH中
    echo [SOLUTION] 请安装Python 3.8+并添加到PATH
    goto :end
) else (
    for /f "tokens=*" %%i in ('python --version') do echo Python版本: %%i
)

echo [INFO] Node.js环境检查...
node --version 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js未安装或不在PATH中
    echo [SOLUTION] 请安装Node.js 16+并添加到PATH
) else (
    for /f "tokens=*" %%i in ('node --version') do echo Node.js版本: %%i
)

npm --version 2>nul
if errorlevel 1 (
    echo [ERROR] npm未安装或不在PATH中
) else (
    for /f "tokens=*" %%i in ('npm --version') do echo npm版本: %%i
)

echo.
echo [INFO] 项目文件检查...

if not exist ".venv" (
    echo [ERROR] 虚拟环境不存在
    echo [SOLUTION] 运行: python deploy.py
) else (
    echo [OK] 虚拟环境存在
)

if not exist "config.json" (
    echo [ERROR] 配置文件不存在
    echo [SOLUTION] 运行: python deploy.py
) else (
    echo [OK] 配置文件存在
)

if not exist "frontend\node_modules" (
    echo [ERROR] 前端依赖未安装
    echo [SOLUTION] 运行: cd frontend && npm install
) else (
    echo [OK] 前端依赖已安装
)

echo.
echo [INFO] 端口占用检查...
netstat -an | findstr ":8000" >nul
if not errorlevel 1 (
    echo [WARNING] 端口8000被占用
    echo [SOLUTION] 停止占用端口的程序或修改配置
)

netstat -an | findstr ":5173" >nul
if not errorlevel 1 (
    echo [WARNING] 端口5173被占用
    echo [SOLUTION] 停止占用端口的程序或修改配置
)

echo.
echo [INFO] 权限检查...
echo test > test_write.tmp 2>nul
if errorlevel 1 (
    echo [ERROR] 当前目录没有写权限
    echo [SOLUTION] 以管理员身份运行或更改目录权限
) else (
    echo [OK] 目录写权限正常
    del test_write.tmp >nul 2>&1
)

echo.
echo [INFO] 防火墙检查...
echo [INFO] 请确保Windows防火墙允许以下端口:
echo - 8000 (后端API)
echo - 5173 (前端开发服务器)
echo - 11434 (Ollama服务，如果使用)

echo.
echo [INFO] 常见问题解决方案:
echo.
echo 1. 如果启动失败:
echo    - 检查Python和Node.js是否正确安装
echo    - 运行 python deploy.py 重新部署
echo    - 检查防火墙和杀毒软件设置
echo.
echo 2. 如果端口被占用:
echo    - 使用 netstat -ano ^| findstr :8000 查看占用进程
echo    - 使用任务管理器结束占用进程
echo.
echo 3. 如果权限错误:
echo    - 以管理员身份运行命令提示符
echo    - 检查文件夹权限设置
echo.
echo 4. 如果中文显示乱码:
echo    - 设置环境变量 PYTHONIOENCODING=utf-8
echo    - 在命令提示符中运行 chcp 65001
echo.

:end
echo 故障排除完成！
pause
