# ChromaDB Web Manager

一个用于管理ChromaDB集合的Web界面，支持中文集合名称。

## 功能特性

- 📋 集合管理：查看、创建、重命名、删除ChromaDB集合
- 🌏 中文支持：完全支持中文集合名称的创建和显示
- 🎨 现代化界面：基于React + Ant Design的响应式界面
- ⚡ 高性能：FastAPI后端，快速响应
- 🔧 易于部署：使用uv管理Python依赖，简化环境配置

## 技术栈

### 前端
- React 18
- Vite
- Ant Design
- TypeScript

### 后端
- Python 3.8+
- FastAPI
- ChromaDB
- uvicorn

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- uv (Python包管理器)

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd chromadb-web-manager
```

2. 后端设置
```bash
# 在项目根目录创建虚拟环境
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装Python依赖（使用中国镜像源）
uv pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt
```

3. 前端设置
```bash
cd frontend
npm install
```

4. 启动服务

后端：
```bash
# 激活虚拟环境（在项目根目录）
source .venv/bin/activate
# 启动后端服务
python backend/main.py
```

前端：
```bash
cd frontend
npm run dev
```

5. 访问应用
- 前端界面：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

## 项目结构

```
chromadb-web-manager/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI应用入口
│   ├── api/                # API路由
│   ├── models/             # 数据模型
│   ├── services/           # 业务逻辑
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── src/                # 源代码
│   ├── public/             # 静态资源
│   └── package.json        # Node.js依赖
└── README.md              # 项目说明
```

## API接口

### 集合管理
- `GET /api/collections` - 获取所有集合
- `POST /api/collections` - 创建新集合
- `PUT /api/collections/{name}` - 重命名集合
- `DELETE /api/collections/{name}` - 删除集合

## 中文支持说明

本项目解决了ChromaDB原生不支持中文集合名称的问题，通过以下方案实现：
- 集合名称编码转换
- 前端中文显示映射
- 后端透明处理

## 开发说明

### 添加新功能
1. 后端：在 `backend/api/` 中添加新的路由
2. 前端：在 `frontend/src/` 中添加新的组件

### 测试
```bash
# 后端测试
cd backend
python -m pytest

# 前端测试
cd frontend
npm test
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
