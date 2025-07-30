# ChromaDB Web Manager

一个功能完整的智能文档管理和检索平台，基于 ChromaDB 构建，支持中文集合名称、RAG 检索、LLM 对话和多种文档格式解析。

## 🌿 分支说明

- **main**: 主线分支，包含稳定的生产版本代码
- **ollama**: Ollama集成分支，专注于Ollama嵌入模型的优化和功能增强

> 当前分支: `ollama` 🚀

## 功能特性

- 📋 **集合管理**：查看、创建、重命名、删除 ChromaDB 集合，完全支持中文名称
- 🤖 **智能对话**：集成 LLM 模型，支持基于文档内容的智能问答
- 🔍 **RAG 检索**：先进的检索增强生成，支持语义搜索和混合检索
- 📄 **文档解析**：支持 PDF、Word、Excel、PPT、Markdown 等多种格式
- 🧠 **多模型支持**：支持阿里云通义千问、Ollama 本地模型等多种嵌入模型
- 🎨 **现代化界面**：基于 React 19 + Ant Design 的响应式界面
- ⚡ **高性能**：FastAPI 后端，异步处理，快速响应
- 🔧 **易于配置**：可视化配置管理，支持多种部署方式

## 技术栈

### 前端
- React 19.1.0
- Vite 7.0.4
- Ant Design 5.26.4
- TypeScript 5.8.3
- React Router Dom 7.7.1
- React Markdown + Syntax Highlighter

### 后端
- Python 3.8+
- FastAPI 0.104.1
- ChromaDB 0.4.18
- Uvicorn 0.24.0
- LangChain (文本分割和处理)
- 多种 LLM 和嵌入模型支持

### 支持的模型
- **嵌入模型**：阿里云通义千问、Ollama 本地模型
- **LLM 模型**：通过统一接口支持多种大语言模型
- **文档处理**：PDF、Word、Excel、PPT、Markdown 等

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- uv (Python包管理器)

### 🚀 一键部署和启动

**方式一：使用跨平台脚本（推荐）**
```bash
# 1. 克隆项目
git clone <repository-url>
cd chromadb-web-manager

# 2. 一键部署
python3 deploy.py    # Linux/macOS
python deploy.py     # Windows

# 3. 一键启动
python3 start.py     # Linux/macOS
python start.py      # Windows
```

**方式二：使用平台特定脚本**
```bash
# Linux/macOS
./scripts/deploy.sh  # 部署
./scripts/start.sh   # 启动

# Windows
scripts\deploy.bat   # 部署
scripts\start.bat    # 启动
```

### 📋 详细安装步骤

如果你需要手动安装，请参考以下步骤：

1. **环境要求**
   - Python 3.8+
   - Node.js 16+
   - npm
   - uv（可选，推荐）

2. **克隆项目**
```bash
git clone <repository-url>
cd chromadb-web-manager
```

3. **后端设置**
```bash
# 创建虚拟环境
uv venv .venv                    # 使用 uv（推荐）
# 或 python3 -m venv .venv      # 使用标准 venv

# 激活虚拟环境
source .venv/bin/activate        # Linux/macOS
# 或 .venv\Scripts\activate     # Windows

# 安装依赖
uv pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt
```

4. **前端设置**
```bash
cd frontend
npm install
```

5. **启动服务**
```bash
# 后端（终端1）
source .venv/bin/activate
python backend/main.py

# 前端（终端2）
cd frontend
npm run dev
```

6. **访问应用**
- 前端界面：http://localhost:5173
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

## 配置说明

### 嵌入模型配置

系统支持多种嵌入模型，可通过 Web 界面或配置文件进行设置：

1. **阿里云通义千问**
   - 需要阿里云 API Key
   - 支持 text-embedding-v4 模型
   - 1024 维向量

2. **Ollama 本地模型**
   - 需要本地运行 Ollama 服务
   - 支持多种开源嵌入模型
   - 推荐模型：snowflake-arctic-embed:335m

详细配置指南：[backend/OLLAMA_EMBEDDING_GUIDE.md](backend/OLLAMA_EMBEDDING_GUIDE.md)

### 启动说明

详细的启动和配置说明请参考：[backend/STARTUP_GUIDE.md](backend/STARTUP_GUIDE.md)

## 项目结构

```
chromadb-web-manager/
├── backend/                    # 后端代码
│   ├── main.py                # 主启动文件
│   ├── config_manager.py      # 配置管理
│   ├── alibaba_embedding.py   # 阿里云嵌入模型
│   ├── ollama_embedding.py    # Ollama 嵌入模型
│   ├── llm_client.py          # LLM 客户端
│   ├── rag_chunking.py        # RAG 分块功能
│   ├── file_parsers.py        # 文件解析器
│   ├── vector_optimization.py # 向量优化
│   ├── hierarchical_rag.py    # 分层 RAG
│   ├── hybrid_retrieval.py    # 混合检索
│   ├── requirements.txt       # Python 依赖
│   ├── STARTUP_GUIDE.md       # 启动指南
│   └── OLLAMA_EMBEDDING_GUIDE.md # Ollama 配置指南
├── frontend/                  # 前端代码
│   ├── src/                   # 源代码
│   ├── public/                # 静态资源
│   └── package.json           # Node.js 依赖
├── docs/                      # 文档目录
│   └── llm-api-specification.md # LLM API 规范
├── config.json               # 配置文件
├── API_DOCS.md              # API 详细文档
├── COLLECTION_TIME_FIX.md   # 集合时间修复说明
└── README.md                # 项目说明
```

## API 接口

系统提供完整的 RESTful API，支持集合管理、文档处理、RAG 检索等功能。

### 主要接口
- **集合管理**：创建、删除、重命名、查询集合
- **文档管理**：上传、解析、分块、向量化文档
- **检索功能**：语义搜索、混合检索、RAG 问答
- **配置管理**：嵌入模型配置、系统设置
- **对话功能**：基于文档的智能问答

详细的 API 文档请参考：[API_DOCS.md](API_DOCS.md)

## 核心功能详解

### 中文支持
本项目完美解决了 ChromaDB 原生不支持中文集合名称的问题：
- **智能编码**：使用 MD5 哈希将中文名称转换为符合规范的英文名称
- **透明映射**：前端完全支持中文显示，用户无感知
- **元数据存储**：在集合元数据中保存原始中文名称

### RAG 检索增强
- **智能分块**：支持多种分块策略（固定长度、语义分块、分层分块）
- **混合检索**：结合语义搜索和关键词匹配
- **上下文优化**：智能选择最相关的文档片段
- **多模型支持**：可配置不同的嵌入模型

### 文档处理
支持多种文档格式的智能解析：
- **PDF**：文本提取和结构化处理
- **Office 文档**：Word、Excel、PowerPoint
- **文本文件**：Markdown、TXT、RTF
- **网页内容**：HTML 解析和清理

## 使用指南

### 基本使用流程

1. **配置嵌入模型**
   - 首次启动时，系统会引导你配置嵌入模型
   - 可选择阿里云通义千问或 Ollama 本地模型

2. **创建集合**
   - 支持中文集合名称
   - 可设置集合描述和元数据

3. **上传文档**
   - 支持多种格式文档批量上传
   - 自动解析和分块处理

4. **智能检索**
   - 使用语义搜索查找相关内容
   - 支持自然语言问答

### 开发说明

#### 添加新功能
1. **后端**：在 `backend/` 中添加新的模块和 API 路由
2. **前端**：在 `frontend/src/` 中添加新的组件和页面

#### 测试
```bash
# 后端测试
cd backend
source ../.venv/bin/activate
python -m pytest

# 前端测试
cd frontend
npm test
```

#### 代码规范
- 后端遵循 PEP 8 规范
- 前端使用 ESLint 和 TypeScript 严格模式
- 提交前请运行 lint 检查

## 常见问题

### Q: 如何配置嵌入模型？
A: 首次启动时系统会自动引导配置，也可以通过 Web 界面的设置页面进行配置。

### Q: 支持哪些文档格式？
A: 支持 PDF、Word、Excel、PowerPoint、Markdown、TXT、RTF、HTML 等格式。

### Q: 如何提高检索准确性？
A: 可以尝试不同的分块策略、调整检索参数，或使用更适合的嵌入模型。

### Q: 可以部署到生产环境吗？
A: 可以，建议使用 Docker 部署，并配置适当的安全措施。

## 📚 相关文档

- [部署指南](DEPLOYMENT.md) - 详细的跨平台部署说明
- [API 详细文档](API_DOCS.md) - 完整的 API 接口文档
- [启动指南](backend/STARTUP_GUIDE.md) - 服务启动说明
- [Ollama 配置指南](backend/OLLAMA_EMBEDDING_GUIDE.md) - 本地模型配置
- [LLM API 规范](docs/llm-api-specification.md) - LLM 接口规范

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 支持

如果这个项目对你有帮助，请给它一个 ⭐️！

如有问题或建议，请通过 Issue 联系我们。
