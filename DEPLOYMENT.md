# ChromaDB Web Manager 部署指南

本指南提供了在不同操作系统上部署和运行 ChromaDB Web Manager 的详细说明。

## 🎯 快速开始

### 一键部署和启动

**Linux/macOS:**
```bash
# 部署
./scripts/deploy.sh
# 或
python3 deploy.py

# 启动
./scripts/start.sh
# 或
python3 start.py
```

**Windows:**
```cmd
REM 部署
scripts\deploy.bat
REM 或
python deploy.py

REM 启动
scripts\start.bat
REM 或
python start.py
```

## 📋 环境要求

### 必需软件
- **Python 3.8+** - 后端运行环境
- **Node.js 16+** - 前端构建和运行环境
- **npm** - Node.js 包管理器

### 推荐软件
- **uv** - 更快的 Python 包管理器（可选，会自动回退到 pip）

### 安装必需软件

**Linux (Ubuntu/Debian):**
```bash
# 安装 Python 3
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 安装 Node.js 和 npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 uv (可选)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS:**
```bash
# 使用 Homebrew
brew install python@3.11 node npm

# 安装 uv (可选)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
1. 从 [python.org](https://www.python.org/downloads/) 下载并安装 Python 3.8+
2. 从 [nodejs.org](https://nodejs.org/) 下载并安装 Node.js (包含 npm)
3. 可选：从 [GitHub](https://github.com/astral-sh/uv) 安装 uv

## 🚀 详细部署步骤

### 1. 克隆项目
```bash
git clone <repository-url>
cd chromadb-web-manager
```

### 2. 运行部署脚本

部署脚本会自动完成以下操作：
- ✅ 检查环境依赖
- ✅ 创建 Python 虚拟环境
- ✅ 安装后端依赖
- ✅ 安装前端依赖
- ✅ 初始化配置文件
- ✅ 创建数据目录
- ✅ 设置环境变量文件

**自动部署:**
```bash
# Linux/macOS
./scripts/deploy.sh

# Windows
scripts\deploy.bat

# 或使用 Python 脚本 (跨平台)
python3 deploy.py  # Linux/macOS
python deploy.py   # Windows
```

### 3. 启动服务

**一键启动:**
```bash
# Linux/macOS
./scripts/start.sh

# Windows
scripts\start.bat

# 或使用 Python 脚本 (跨平台)
python3 start.py  # Linux/macOS
python start.py   # Windows
```

**手动启动:**
```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 启动后端 (终端1)
python backend/main.py

# 启动前端 (终端2)
cd frontend
npm run dev
```

### 4. 访问应用

启动成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## ⚙️ 配置说明

### 配置文件

部署完成后，会在项目根目录生成 `config.json` 配置文件：

```json
{
  "chroma_db_path": "/path/to/chroma_data",
  "path_history": ["/path/to/chroma_data"],
  "last_updated": "",
  "max_history_count": 10,
  "embedding_config": {
    "default_provider": "ollama",
    "alibaba": {
      "model": "text-embedding-v4",
      "dimension": 1024,
      "api_key": "",
      "verified": false,
      "last_verified": null
    },
    "ollama": {
      "model": "snowflake-arctic-embed:335m",
      "base_url": "http://localhost:11434",
      "timeout": 60,
      "verified": false,
      "last_verified": null
    }
  }
}
```

### 环境变量

**后端环境变量** (`backend/.env`):
```env
# 阿里云DashScope API密钥
DASHSCOPE_API_KEY=your_api_key_here

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8000

# FastAPI配置
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# 日志级别
LOG_LEVEL=INFO
```

**前端环境变量** (`frontend/.env`):
```env
# API基础URL
VITE_API_BASE_URL=http://localhost:8000/api

# 应用标题
VITE_APP_TITLE=ChromaDB Web Manager

# 调试模式
VITE_DEBUG=true
```

## 🔧 故障排除

### 常见问题

**1. Python 虚拟环境创建失败**
```bash
# 手动创建虚拟环境
python3 -m venv .venv  # Linux/macOS
python -m venv .venv   # Windows
```

**2. 依赖安装失败**
```bash
# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt
```

**3. 端口被占用**
- 后端默认端口：8000
- 前端默认端口：5173

检查端口占用：
```bash
# Linux/macOS
lsof -i :8000
lsof -i :5173

# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

**4. 权限问题 (Linux/macOS)**
```bash
# 设置脚本执行权限
chmod +x scripts/*.sh
```

### 日志查看

启动脚本会显示实时日志。如需查看详细日志：

```bash
# 后端日志
tail -f backend/logs/app.log

# 前端日志
cd frontend && npm run dev
```

## 🐳 Docker 部署 (可选)

如果你更喜欢使用 Docker：

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📝 开发模式

如果你需要进行开发：

```bash
# 安装开发依赖
pip install -r backend/requirements-dev.txt

# 启用热重载
cd frontend && npm run dev
cd backend && python main.py --reload
```

## 🔄 更新和维护

### 更新代码
```bash
git pull origin main
python3 deploy.py  # 重新部署依赖
```

### 备份数据
```bash
# 备份配置和数据
cp -r chroma_data/ backup/
cp -r data/ backup/
cp config.json backup/
```

### 清理环境
```bash
# 清理虚拟环境
rm -rf .venv

# 清理前端依赖
rm -rf frontend/node_modules

# 重新部署
python3 deploy.py
```
