# Ollama嵌入模型集成指南

本指南介绍如何在ChromaDB Web Manager中使用Ollama嵌入模型功能。

## 功能概述

ChromaDB Web Manager现在支持两种嵌入模型：
1. **阿里云百炼嵌入模型** - 云端API服务
2. **Ollama本地嵌入模型** - 本地运行的开源模型

## Ollama嵌入模型优势

- ✅ **本地运行** - 数据不离开本地环境，保护隐私
- ✅ **免费使用** - 无需API密钥，无使用限制
- ✅ **多模型支持** - 支持多种开源嵌入模型
- ✅ **离线工作** - 无需网络连接即可使用
- ✅ **自定义配置** - 可自定义服务器地址和端口

## 支持的嵌入模型

| 模型名称 | 参数量 | 向量维度 | 推荐程度 | 描述 |
|---------|--------|----------|----------|------|
| mxbai-embed-large | 334M | 1024 | ⭐⭐⭐ | 高质量嵌入模型，推荐使用 |
| nomic-embed-text | 137M | 768 | ⭐⭐⭐ | 轻量级嵌入模型，性能良好 |
| all-minilm | 23M | 384 | ⭐⭐ | 超轻量级模型，适合资源受限环境 |

## 安装和配置

### 1. 安装Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 从 https://ollama.com/download 下载安装包
```

### 2. 启动Ollama服务

```bash
ollama serve
```

默认服务地址：`http://localhost:11434`

### 3. 拉取嵌入模型

```bash
# 推荐：高质量嵌入模型
ollama pull mxbai-embed-large

# 或者：轻量级嵌入模型
ollama pull nomic-embed-text

# 或者：超轻量级嵌入模型
ollama pull all-minilm
```

### 4. 验证安装

```bash
# 查看已安装的模型
ollama list

# 测试嵌入功能
ollama embed mxbai-embed-large "测试文本"
```

## 使用方法

### 1. 创建使用Ollama嵌入模型的集合

通过API创建集合时，指定使用Ollama嵌入模型：

```json
{
  "name": "我的文档集合",
  "embedding_model": "ollama",
  "ollama_model": "mxbai-embed-large",
  "ollama_base_url": "http://localhost:11434",
  "metadata": {
    "description": "使用Ollama嵌入模型的集合"
  }
}
```

### 2. 参数说明

- `embedding_model`: 设置为 `"ollama"` 使用Ollama嵌入模型
- `ollama_model`: 指定Ollama模型名称（如 `"mxbai-embed-large"`）
- `ollama_base_url`: Ollama服务器地址（默认：`"http://localhost:11434"`）

### 3. 支持的操作

使用Ollama嵌入模型的集合支持所有标准操作：
- ✅ 添加文档
- ✅ 文件上传和RAG分块
- ✅ 向量搜索
- ✅ 集合重命名
- ✅ 文档管理

## API端点

### 获取支持的嵌入模型

```http
GET /api/embedding-models
```

返回所有支持的嵌入模型信息，包括可用状态。

## 测试功能

运行测试脚本验证Ollama嵌入功能：

```bash
cd backend
python test_ollama_embedding.py
```

测试内容包括：
- Ollama服务连接测试
- 支持的模型列表
- 嵌入向量生成测试
- 批量处理测试
- 模型信息获取测试

## 故障排除

### 1. Ollama服务连接失败

**问题**: `无法连接到Ollama服务`

**解决方案**:
```bash
# 检查Ollama服务状态
ps aux | grep ollama

# 启动Ollama服务
ollama serve

# 检查端口是否被占用
lsof -i :11434
```

### 2. 模型未找到

**问题**: `模型 'xxx' 未找到`

**解决方案**:
```bash
# 查看已安装的模型
ollama list

# 拉取所需模型
ollama pull mxbai-embed-large
```

### 3. 嵌入向量生成失败

**问题**: `生成嵌入向量时发生错误`

**解决方案**:
1. 检查Ollama服务是否正常运行
2. 确认模型已正确安装
3. 检查网络连接和防火墙设置
4. 查看Ollama服务日志

### 4. 性能优化

**建议**:
- 使用SSD存储提高模型加载速度
- 增加系统内存以支持更大的模型
- 根据需求选择合适的模型大小
- 考虑使用GPU加速（如果支持）

## 配置示例

### 开发环境配置

```json
{
  "embedding_model": "ollama",
  "ollama_model": "all-minilm",
  "ollama_base_url": "http://localhost:11434"
}
```

### 生产环境配置

```json
{
  "embedding_model": "ollama",
  "ollama_model": "mxbai-embed-large",
  "ollama_base_url": "http://ollama-server:11434"
}
```

## 性能对比

| 模型 | 向量维度 | 内存占用 | 处理速度 | 质量 |
|------|----------|----------|----------|------|
| mxbai-embed-large | 1024 | ~1GB | 中等 | 高 |
| nomic-embed-text | 768 | ~500MB | 快 | 中高 |
| all-minilm | 384 | ~100MB | 很快 | 中等 |

## 注意事项

1. **首次使用**: 首次使用某个模型时，系统会自动尝试拉取模型
2. **资源需求**: 确保系统有足够的内存和存储空间
3. **网络要求**: 拉取模型时需要网络连接，使用时可离线
4. **兼容性**: 与现有的阿里云嵌入模型完全兼容，可混合使用
5. **数据迁移**: 不同嵌入模型生成的向量不兼容，需要重新生成

## 更多信息

- [Ollama官方文档](https://ollama.com/docs)
- [Ollama GitHub仓库](https://github.com/ollama/ollama)
- [支持的嵌入模型列表](https://ollama.com/library?q=embed)
