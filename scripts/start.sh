#!/bin/bash
# ChromaDB Web Manager 启动脚本 (Linux/macOS)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BOLD}${BLUE}ChromaDB Web Manager 启动器${NC}"
echo -e "${BLUE}平台: $(uname -s) $(uname -r)${NC}"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python3 未安装"
    exit 1
fi

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${RED}[ERROR]${NC} 虚拟环境不存在，请先运行: python3 deploy.py"
    exit 1
fi

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo -e "${RED}[ERROR]${NC} 配置文件不存在，请先运行: python3 deploy.py"
    exit 1
fi

# 启动服务
echo -e "${CYAN}[INFO]${NC} 启动 ChromaDB Web Manager..."
python3 start.py
