# ChromaDB Web Manager API 文档

## 概述

ChromaDB Web Manager 提供了一套完整的 RESTful API 来管理 ChromaDB 集合，支持中文集合名称、文档管理、RAG 检索、LLM 对话、角色管理和系统配置。

## 基础信息

- **基础URL**: `http://localhost:8000/api`
- **内容类型**: `application/json`
- **字符编码**: UTF-8
- **WebSocket 端点**: `ws://localhost:8000/api/ws`

## 中文支持说明

本系统通过以下方式解决 ChromaDB 不支持中文集合名称的问题：

1. **编码方案**: 使用 MD5 哈希将中文名称转换为符合 ChromaDB 命名规范的英文名称
2. **元数据存储**: 在集合的元数据中存储原始中文名称
3. **透明处理**: 前端和 API 层面完全支持中文，用户无需关心底层编码

## API 接口

### 1. 基础接口

#### 1.1 首页
```http
GET /
```

#### 1.2 健康检查
检查服务状态和 ChromaDB 连接。

```http
GET /api/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "chromadb_heartbeat": 1752314882174615000,
  "message": "服务运行正常"
}
```

#### 1.3 WebSocket 连接
实时通信端点，用于文件上传进度、重命名状态等实时更新。

```http
WebSocket /api/ws
```

### 2. 集合管理

#### 2.1 获取集合列表
获取所有集合的列表信息。

```http
GET /api/collections
```

**响应示例**:
```json
[
  {
    "name": "col_9320cfba70a8f3e641b8c39f7603b2e2",
    "display_name": "测试集合",
    "count": 156,
    "metadata": {
      "description": "这是一个测试集合",
      "original_name": "测试集合"
    },
    "files_count": 12,
    "chunk_statistics": {
      "total_chunks": 156,
      "avg_chunk_size": 512
    },
    "dimension": 1024,
    "embedding_model": "alibaba",
    "embedding_provider": "通义千问",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-20T14:25:30"
  }
]
```

#### 2.2 获取集合详情
获取特定集合的详细信息。

```http
GET /api/collections/{collection_name}/detail
```

**路径参数**:
- `collection_name`: 集合名称（支持中文显示名称或内部编码名称）

**响应示例**:
```json
{
  "name": "col_9320cfba70a8f3e641b8c39f7603b2e2",
  "display_name": "测试集合",
  "count": 156,
  "metadata": {
    "description": "这是一个测试集合",
    "original_name": "测试集合"
  },
  "documents": [
    {
      "id": "doc_001",
      "metadata": {
        "filename": "document1.pdf",
        "upload_time": "2024-01-15T10:30:00"
      },
      "content": "文档内容摘要..."
    }
  ]
}
```

#### 2.3 创建集合
创建新的集合，支持中文名称和自定义嵌入模型。

```http
POST /api/collections
```

**请求体**:
```json
{
  "name": "新集合名称",
  "metadata": {
    "description": "集合描述",
    "type": "数据类型"
  },
  "embedding_model": "alibaba",
  "ollama_model": "snowflake-arctic-embed:335m",
  "ollama_base_url": "http://localhost:11434"
}
```

**参数说明**:
- `name` (必需): 集合名称，支持中文
- `metadata` (可选): 集合元数据，键值对形式
- `embedding_model` (可选): 嵌入模型提供商 ("alibaba" 或 "ollama")
- `ollama_model` (可选): Ollama 模型名称
- `ollama_base_url` (可选): Ollama 服务器地址

#### 2.4 删除集合
删除指定的集合。

```http
DELETE /api/collections/{collection_name}
```

#### 2.5 重命名集合
重命名现有集合（支持异步操作）。

```http
PUT /api/collections/rename
```

**请求体**:
```json
{
  "old_name": "旧集合名称",
  "new_name": "新集合名称"
}
```

**响应示例**:
```json
{
  "message": "重命名操作已开始",
  "task_id": "task_123456789",
  "immediate_response": false
}
```

#### 2.6 获取重命名状态
查询重命名任务的进度和状态。

```http
GET /api/collections/rename/status/{task_id}
```

#### 2.7 获取所有重命名任务
获取所有重命名任务的状态列表。

```http
GET /api/collections/rename/tasks
```

#### 2.8 集合分析
分析集合的数据分布和统计信息。

```http
GET /api/collections/{collection_name}/analysis
```

#### 2.9 集合调试信息
获取集合的调试和诊断信息。

```http
GET /api/collections/{collection_name}/debug
```

### 3. 文档管理

#### 3.1 添加文档
向集合中添加文本文档。

```http
POST /api/collections/{collection_name}/documents
```

**请求体**:
```json
{
  "collection_name": "目标集合",
  "documents": ["文档内容1", "文档内容2"],
  "metadatas": [
    {"source": "用户输入", "type": "text"},
    {"source": "API", "type": "text"}
  ],
  "ids": ["doc_001", "doc_002"]
}
```

#### 3.2 上传文件
上传文档文件并自动解析。

```http
POST /api/collections/{collection_name}/upload
```

**请求体**: `multipart/form-data`
- `file`: 上传的文件
- `chunk_size` (可选): 分块大小，默认 512
- `chunk_overlap` (可选): 分块重叠，默认 50

**响应示例**:
```json
{
  "message": "文件上传成功",
  "filename": "document.pdf",
  "chunks_count": 25,
  "total_size": 15680,
  "processing_time": 2.5
}
```

#### 3.3 流式文件上传
支持大文件的流式上传，提供实时进度更新。

```http
POST /api/collections/{collection_name}/upload-stream
```

#### 3.4 获取支持的文件格式
获取系统支持的文档格式列表。

```http
GET /api/supported-formats
```

**响应示例**:
```json
{
  "formats": {
    ".pdf": "PDF文档 - 支持文本提取和OCR",
    ".docx": "Word文档 - 支持完整格式解析",
    ".xlsx": "Excel表格 - 支持多工作表解析",
    ".pptx": "PowerPoint演示文稿",
    ".md": "Markdown文档",
    ".txt": "纯文本文件",
    ".html": "HTML网页文件",
    ".rtf": "富文本格式"
  }
}
```

#### 3.5 删除文档
根据文件名删除集合中的文档。

```http
DELETE /api/collections/{collection_name}/documents/{file_name}
```

**响应示例**:
```json
{
  "message": "文档删除成功",
  "deleted_count": 12,
  "filename": "document.pdf"
}
```

### 4. 文本分块

#### 4.1 文本分块处理
对文本进行智能分块处理。

```http
POST /api/collections/{collection_name}/chunk
```

**请求体**:
```json
{
  "text": "要分块的长文本内容...",
  "chunk_size": 512,
  "chunk_overlap": 50,
  "method": "recursive"
}
```

#### 4.2 获取分块配置
获取指定分块方法的默认配置。

```http
GET /api/chunking/config/{method}
```

**路径参数**:
- `method`: 分块方法 (recursive, semantic, fixed, hierarchical)

### 5. 检索和查询

#### 5.1 向量检索
在指定集合中进行语义搜索。

```http
POST /api/query
```

**请求体**:
```json
{
  "query": "搜索查询文本",
  "collections": ["集合1", "集合2"],
  "limit": 10
}
```

**响应示例**:
```json
{
  "results": [
    {
      "collection": "集合1",
      "documents": ["相关文档内容..."],
      "distances": [0.85, 0.78],
      "metadatas": [
        {"filename": "doc1.pdf", "page": 1}
      ],
      "ids": ["doc_001_chunk_1"]
    }
  ],
  "total_results": 8,
  "query_time": 0.15
}
```

#### 5.2 LLM 智能问答
结合检索结果进行 LLM 问答。

```http
POST /api/llm-query
```

**请求体**:
```json
{
  "query": "基于文档回答的问题",
  "collections": ["知识库集合"],
  "limit": 5,
  "temperature": 0.7,
  "max_tokens": 2000,
  "similarity_threshold": 1.5,
  "role_id": "assistant_role_001"
}
```

**响应**: 支持流式响应，逐步返回生成的答案。

### 6. 数据管理

#### 6.1 扫描孤立数据
扫描并分析系统中的孤立数据。

```http
GET /api/data/cleanup/scan
```

**响应示例**:
```json
{
  "analysis": {
    "chromadb_collections": ["col_123", "col_456"],
    "filesystem_dirs": ["col_123", "col_456", "col_orphan"],
    "orphaned_dirs": ["col_orphan"],
    "total_orphaned_size_mb": 15.6,
    "summary": {
      "cleanup_needed": true,
      "orphaned_count": 1
    }
  }
}
```

#### 6.2 执行数据清理
清理检测到的孤立数据。

```http
POST /api/data/cleanup/execute
```

**请求体**:
```json
{
  "dry_run": false,
  "confirm": true
}
```

#### 6.3 获取清理报告
获取数据清理的详细报告。

```http
GET /api/data/cleanup/report
```

### 7. 系统分析

#### 7.1 获取分析数据
获取系统使用情况和统计信息。

```http
GET /api/analytics
```

**响应示例**:
```json
{
  "collections_count": 5,
  "total_documents": 1250,
  "total_size_mb": 156.8,
  "recent_queries": [
    {
      "query": "最近的搜索",
      "timestamp": "2024-01-20T14:30:00",
      "collections": ["集合1"],
      "response_time": 0.25
    }
  ],
  "popular_collections": [
    {"name": "常用集合", "query_count": 45}
  ]
}
```

### 8. 嵌入模型配置

#### 8.1 获取可用嵌入模型
获取系统支持的嵌入模型列表。

```http
GET /api/embedding-models
```

#### 8.2 获取所有嵌入模型
获取完整的嵌入模型信息。

```http
GET /api/embedding-models/all
```

#### 8.3 获取嵌入配置
获取当前的嵌入模型配置。

```http
GET /api/embedding-config
```

#### 8.4 设置嵌入配置
配置默认的嵌入模型和参数。

```http
POST /api/embedding-config
```

**请求体**:
```json
{
  "default_provider": "alibaba",
  "alibaba_config": {
    "api_key": "your_api_key",
    "model_name": "text-embedding-v4"
  },
  "ollama_config": {
    "base_url": "http://localhost:11434",
    "model_name": "snowflake-arctic-embed:335m"
  }
}
```

#### 8.5 测试嵌入配置
测试嵌入模型配置是否正确。

```http
POST /api/embedding-config/test
```

#### 8.6 获取嵌入提供商状态
检查各嵌入模型提供商的服务状态。

```http
GET /api/embedding-providers/status
```

#### 8.7 验证嵌入提供商
验证特定提供商的配置和连接。

```http
POST /api/embedding-providers/{provider}/verify
```

### 9. LLM 配置

#### 9.1 获取 LLM 配置
获取当前的 LLM 模型配置。

```http
GET /api/llm-config
```

#### 9.2 设置 LLM 配置
配置 LLM 模型和参数。

```http
POST /api/llm-config
```

#### 9.3 测试 LLM 配置
测试 LLM 模型配置是否正确。

```http
POST /api/llm-config/test
```

#### 9.4 获取 LLM 模型列表
获取支持的 LLM 模型列表。

```http
GET /api/llm-models
```

#### 9.5 获取 LLM 提供商状态
检查 LLM 提供商的服务状态。

```http
GET /api/llm-providers/status
```

#### 9.6 验证 LLM 提供商
验证特定 LLM 提供商的配置。

```http
POST /api/llm-providers/{provider}/verify
```

### 10. 角色管理

#### 10.1 获取角色列表
获取系统中定义的所有角色。

```http
GET /api/roles
```

**响应示例**:
```json
[
  {
    "id": "role_001",
    "name": "智能助手",
    "prompt": "你是一个专业的智能助手，能够准确回答用户的问题...",
    "description": "通用智能助手角色",
    "is_active": true,
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-20T15:30:00"
  }
]
```

#### 10.2 获取角色详情
获取特定角色的详细信息。

```http
GET /api/roles/{role_id}
```

#### 10.3 创建角色
创建新的角色配置。

```http
POST /api/roles
```

**请求体**:
```json
{
  "name": "专业顾问",
  "prompt": "你是一个专业的技术顾问，具备丰富的经验...",
  "description": "技术咨询专家角色",
  "is_active": true
}
```

#### 10.4 更新角色
更新现有角色的配置。

```http
PUT /api/roles/{role_id}
```

#### 10.5 删除角色
删除指定的角色。

```http
DELETE /api/roles/{role_id}
```

## 错误处理

### HTTP 状态码

- `200`: 请求成功
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未授权
- `403`: 禁止访问
- `404`: 资源不存在
- `409`: 资源冲突
- `422`: 请求参数验证失败
- `500`: 服务器内部错误
- `503`: 服务不可用

### 错误响应格式

```json
{
  "detail": "错误描述信息",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-20T15:30:00"
}
```

## 使用示例

### 创建集合并上传文档

```bash
# 1. 创建集合
curl -X POST http://localhost:8000/api/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "知识库",
    "metadata": {
      "description": "公司知识库",
      "department": "技术部"
    },
    "embedding_model": "alibaba"
  }'

# 2. 上传文档
curl -X POST http://localhost:8000/api/collections/知识库/upload \
  -F "file=@document.pdf" \
  -F "chunk_size=512" \
  -F "chunk_overlap=50"
```

### 智能问答查询

```javascript
async function askQuestion() {
  const response = await fetch('http://localhost:8000/api/llm-query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: "如何提高工作效率？",
      collections: ["知识库"],
      limit: 5,
      temperature: 0.7,
      role_id: "assistant_001"
    })
  });
  
  const reader = response.body.getReader();
  let result = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    result += new TextDecoder().decode(value);
  }
  
  console.log('AI回答:', result);
}
```

## 技术实现细节

### 中文名称编码
1. **哈希生成**: 使用 MD5 算法对中文名称进行哈希
2. **前缀添加**: 添加 "col_" 前缀确保符合 ChromaDB 命名规范
3. **元数据存储**: 在 `metadata.original_name` 中存储原始中文名称

### 异步操作
- 重命名操作支持异步处理，返回任务ID
- 文件上传支持进度跟踪
- 支持 WebSocket 实时状态更新

### 嵌入模型支持
- 阿里云通义千问嵌入模型
- Ollama 本地嵌入模型
- 可配置的模型参数和服务地址

## 限制和注意事项

1. **集合名称长度**: 建议中文集合名称不超过 50 个字符
2. **文件大小**: 单个文件上传建议不超过 100MB
3. **并发操作**: 重命名等敏感操作不支持并发
4. **嵌入模型**: 需要正确配置嵌入模型才能使用向量功能
5. **WebSocket**: 连接会在空闲时自动断开

## 更新日志

### v2.0.0 (2024-01-20)
- 新增角色管理功能
- 支持流式 LLM 问答
- 增强文档上传和解析能力
- 完善数据清理和分析功能
- 添加嵌入模型配置管理
- 支持异步重命名操作

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持中文集合名称
- 实现基础 CRUD 操作
- 提供完整的 Web 管理界面
