# ChromaQuery 项目概览

## 项目目的
ChromaQuery是一个功能完整的智能文档管理和检索平台，基于ChromaDB构建，支持中文集合名称、RAG检索、LLM对话和多种文档格式解析。

## 技术栈
### 前端
- React 19.1.0
- TypeScript 5.8.3  
- Vite 7.0.4
- Ant Design 5.26.4
- React Router Dom 7.7.1

### 后端
- Python 3.8+
- FastAPI 0.104.1
- ChromaDB 1.0.15
- Uvicorn 0.35.0
- LangChain (文本分割和处理)

### 核心功能
- 智能文档管理和向量检索
- 中文集合名称支持
- RAG (检索增强生成)
- 多种嵌入模型支持(阿里云通义千问、Ollama)
- 文档格式解析(PDF、Word、Excel、PPT、Markdown等)
- 异步重命名和数据清理

## 项目结构
- backend/ - FastAPI后端服务
- frontend/ - React前端应用  
- chromadbdata/ - ChromaDB数据存储
- deploy.py, start.py - 跨平台部署和启动脚本