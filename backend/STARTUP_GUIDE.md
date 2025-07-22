# ChromaDB Web Manager 启动指南

## 启动文件说明

本项目提供两个启动文件，用于不同的使用场景：

### 1. main.py - 生产版本（主要启动文件）
- **用途**: 生产环境的完整功能版本
- **特性**: 
  - 完整的RAG分块功能
  - 高级LLM集成
  - 完整的文档管理
  - 流式响应支持
  - 复杂的查询功能
- **启动命令**: `python main.py`
- **注意**: 目前存在依赖版本冲突问题，需要解决后使用

### 2. dev_main.py - 开发/测试版本
- **用途**: 开发和测试环境的简化版本
- **特性**:
  - 基础的RAG分块功能
  - 简化的LLM集成
  - 基础的文档管理
  - 较少的依赖项
  - 启动更快
- **启动命令**: `python dev_main.py`
- **推荐**: 当前推荐用于开发和测试

## 快速启动

### 开发环境（推荐）
```bash
# 激活虚拟环境
source ../.venv/bin/activate

# 启动开发版本
python dev_main.py
```

### 生产环境（需要修复依赖问题）
```bash
# 激活虚拟环境
source ../.venv/bin/activate

# 启动生产版本
python main.py
```

## 端口配置
- 后端服务: http://localhost:8000
- 前端服务: http://localhost:3000

## 依赖问题解决

如果 main.py 启动失败，可能是由于以下依赖版本冲突：
- langchain 相关包版本不兼容
- pydantic v1/v2 版本冲突

建议使用 dev_main.py 进行开发，待依赖问题解决后再使用 main.py。
