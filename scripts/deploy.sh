#!/bin/bash
# ChromaDB Web Manager 部署脚本 (Linux/macOS)

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

echo -e "${BOLD}${BLUE}ChromaDB Web Manager 部署脚本${NC}"
echo -e "${BLUE}平台: $(uname -s) $(uname -r)${NC}"
echo

# 检查必要工具
echo -e "${CYAN}[1/3]${NC} 检查必要工具..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python3 未安装"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python3: $(python3 --version)"

if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Node.js 未安装"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js: $(node --version)"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} npm 未安装"
    exit 1
fi
echo -e "${GREEN}✓${NC} npm: $(npm --version)"

# 检查 uv
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} uv: $(uv --version)"
    USE_UV=true
else
    echo -e "${YELLOW}⚠${NC} uv 未安装，将使用 pip"
    USE_UV=false
fi

echo

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 运行 Python 部署脚本
echo -e "${CYAN}[2/3]${NC} 运行部署脚本..."
python3 deploy.py

echo

# 设置脚本权限
echo -e "${CYAN}[3/3]${NC} 设置脚本权限..."
chmod +x scripts/start.sh
chmod +x scripts/deploy.sh
echo -e "${GREEN}✓${NC} 脚本权限设置完成"

echo
echo -e "${GREEN}部署完成！${NC}"
echo
echo -e "${BOLD}下一步:${NC}"
echo -e "运行 ${GREEN}./scripts/start.sh${NC} 或 ${GREEN}python3 start.py${NC} 启动应用"
