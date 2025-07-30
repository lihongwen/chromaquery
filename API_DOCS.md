# ChromaDB Web Manager API 文档

## 概述

ChromaDB Web Manager 提供了一套完整的 RESTful API 来管理 ChromaDB 集合，支持中文集合名称。

## 基础信息

- **基础URL**: `http://localhost:8000/api`
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 中文支持说明

本系统通过以下方式解决 ChromaDB 不支持中文集合名称的问题：

1. **编码方案**: 使用 MD5 哈希将中文名称转换为符合 ChromaDB 命名规范的英文名称
2. **元数据存储**: 在集合的元数据中存储原始中文名称
3. **透明处理**: 前端和 API 层面完全支持中文，用户无需关心底层编码

## API 接口

### 1. 健康检查

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

### 2. 获取集合列表

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
    "count": 0,
    "metadata": {
      "description": "这是一个测试集合",
      "original_name": "测试集合"
    }
  },
  {
    "name": "col_0da9b12963e0091ce77d558d72a98ede",
    "display_name": "用户数据",
    "count": 0,
    "metadata": {
      "type": "user_data",
      "created_by": "admin",
      "original_name": "用户数据"
    }
  }
]
```

**字段说明**:
- `name`: 内部编码后的集合名称
- `display_name`: 显示名称（原始中文名称）
- `count`: 集合中的文档数量
- `metadata`: 集合元数据

### 3. 创建集合

创建新的集合，支持中文名称。

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
  }
}
```

**参数说明**:
- `name` (必需): 集合名称，支持中文
- `metadata` (可选): 集合元数据，键值对形式

**响应示例**:
```json
{
  "message": "集合 '新集合名称' 创建成功",
  "name": "col_abc123...",
  "display_name": "新集合名称"
}
```

**错误响应**:
```json
{
  "detail": "集合 '新集合名称' 已存在"
}
```

### 4. 删除集合

删除指定的集合。

```http
DELETE /api/collections/{collection_name}
```

**路径参数**:
- `collection_name`: 集合名称（支持中文显示名称或内部编码名称）

**响应示例**:
```json
{
  "message": "集合 '测试集合' 删除成功"
}
```

**错误响应**:
```json
{
  "detail": "集合 '不存在的集合' 不存在"
}
```

### 5. 重命名集合

重命名现有集合。

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

**参数说明**:
- `old_name` (必需): 原集合名称
- `new_name` (必需): 新集合名称

**响应示例**:
```json
{
  "message": "集合从 '旧集合名称' 重命名为 '新集合名称' 成功",
  "old_name": "旧集合名称",
  "new_name": "新集合名称"
}
```

**注意事项**:
- 重命名操作会复制所有数据到新集合，然后删除旧集合
- 如果集合包含大量数据，操作可能需要较长时间

## 错误处理

### HTTP 状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误
- `503`: 服务不可用

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

## 使用示例

### 使用 curl 创建中文集合

```bash
curl -X POST http://localhost:8000/api/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "客户反馈数据",
    "metadata": {
      "department": "客服部",
      "created_date": "2024-01-15"
    }
  }'
```

### 使用 JavaScript 获取集合列表

```javascript
async function getCollections() {
  try {
    const response = await fetch('http://localhost:8000/api/collections');
    const collections = await response.json();
    console.log('集合列表:', collections);
  } catch (error) {
    console.error('获取集合列表失败:', error);
  }
}
```

## 技术实现细节

### 中文名称编码

1. **哈希生成**: 使用 MD5 算法对中文名称进行哈希
2. **前缀添加**: 添加 "col_" 前缀确保符合 ChromaDB 命名规范
3. **元数据存储**: 在 `metadata.original_name` 中存储原始中文名称

### 集合查找策略

系统支持通过以下方式查找集合：
1. 原始中文名称（通过元数据匹配）
2. 内部编码名称（直接匹配）

这种设计确保了 API 的灵活性和向后兼容性。

## 限制和注意事项

1. **集合名称长度**: 建议中文集合名称不超过 50 个字符
2. **特殊字符**: 支持所有 Unicode 字符，包括中文、日文、韩文等
3. **性能考虑**: 重命名操作需要复制数据，大集合操作时间较长
4. **并发安全**: 当前版本不支持并发操作同一集合

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持中文集合名称
- 实现基础 CRUD 操作
- 提供完整的 Web 管理界面
