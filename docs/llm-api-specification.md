# LLM查询API接口规范

## 概述

本文档定义了ChromaDB Web Manager中LLM智能查询功能的API接口规范。该API将ChromaDB向量查询与阿里云通义千问LLM模型集成，提供智能问答功能。

## API端点

### 1. LLM流式查询接口

**端点**: `POST /api/llm-query`

**描述**: 执行ChromaDB向量查询，并将结果作为上下文发送给LLM模型，返回流式响应。

#### 请求参数

```json
{
  "query": "string",           // 必需：用户查询文本
  "collections": ["string"],   // 必需：要查询的集合名称列表
  "limit": 5,                  // 可选：返回的向量查询结果数量，默认5
  "temperature": 0.7,          // 可选：LLM温度参数，默认0.7
  "max_tokens": 2000          // 可选：LLM最大输出token数，默认2000
}
```

#### 响应格式

**Content-Type**: `text/plain; charset=utf-8`

**流式响应格式** (Server-Sent Events):

```
data: {"content": "部分回答内容", "finish_reason": null}

data: {"content": "更多回答内容", "finish_reason": null}

data: {"content": "", "finish_reason": "stop", "usage": {"total_tokens": 150}}
```

#### 流式数据结构

每个数据块包含以下字段：

- `content` (string): 当前块的文本内容
- `finish_reason` (string|null): 完成原因，可能值：
  - `null`: 流式响应继续
  - `"stop"`: 正常完成
  - `"length"`: 达到最大长度限制
  - `"error"`: 发生错误
- `usage` (object|null): 仅在最后一个块中包含，包含token使用统计

#### 错误响应

**HTTP状态码**: 400, 500

```json
{
  "detail": "错误描述信息"
}
```

常见错误：
- `400`: 请求参数无效（查询内容为空、集合列表为空等）
- `404`: 指定的集合不存在
- `500`: 服务器内部错误（ChromaDB连接失败、LLM API调用失败等）

## 实现细节

### 1. 处理流程

1. **参数验证**: 验证请求参数的有效性
2. **向量查询**: 在指定集合中执行向量相似度查询
3. **上下文构建**: 将查询结果格式化为LLM上下文
4. **LLM调用**: 调用阿里云通义千问API，启用流式响应
5. **流式传输**: 实时传输LLM响应给客户端

### 2. 上下文格式化

查询结果将按以下格式组织为LLM上下文：

```
基于以下相关文档内容，请回答用户的问题：

文档1（相似度：95.2%，来源：collection_name）：
[文档内容]

文档2（相似度：89.7%，来源：collection_name）：
[文档内容]

...

用户问题：[用户查询]

请基于上述文档内容提供准确、有用的回答。如果文档中没有相关信息，请明确说明。
```

### 3. LLM配置

- **模型**: qwen-turbo
- **API端点**: 阿里云百炼平台
- **流式响应**: 启用
- **默认参数**:
  - temperature: 0.7
  - max_tokens: 2000
  - stream: true

### 4. 错误处理

- **网络错误**: 自动重试机制（最多3次）
- **API限流**: 实现指数退避重试
- **超时处理**: 设置合理的超时时间（30秒）
- **流式中断**: 优雅处理连接中断

### 5. 性能优化

- **并发查询**: 支持多集合并发查询
- **结果缓存**: 对相同查询实现短期缓存
- **连接池**: 复用HTTP连接
- **异步处理**: 全异步实现，提高并发性能

## 安全考虑

1. **输入验证**: 严格验证所有输入参数
2. **SQL注入防护**: 使用参数化查询
3. **API密钥保护**: 安全存储和使用API密钥
4. **请求限流**: 实现请求频率限制
5. **日志记录**: 记录关键操作和错误信息

## 监控和日志

### 关键指标

- 请求响应时间
- 向量查询耗时
- LLM API调用耗时
- 错误率
- 并发连接数

### 日志格式

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event": "llm_query",
  "query": "用户查询内容",
  "collections": ["collection1", "collection2"],
  "vector_query_time": 0.15,
  "llm_response_time": 2.34,
  "total_time": 2.49,
  "status": "success"
}
```

## 版本兼容性

- API版本: v1
- 向后兼容: 保证现有查询API继续可用
- 迁移路径: 提供平滑的功能迁移方案
