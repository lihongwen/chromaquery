# ChromaDB Web Manager 测试文档

这是一个用于测试Markdown文件解析的示例文档。

## 功能概述

ChromaDB Web Manager是一个现代化的向量数据库管理界面，具有以下特点：

### 核心功能

1. **多格式文档支持**
   - 文本文件 (.txt)
   - PDF文档 (.pdf)
   - Word文档 (.docx, .doc)
   - PowerPoint演示文稿 (.pptx, .ppt)
   - Markdown文档 (.md)
   - RTF文档 (.rtf)
   - Excel表格 (.xlsx, .xls)
   - CSV文件 (.csv)

2. **智能文档处理**
   - 自动文本提取
   - 智能分块算法
   - 表格结构分析
   - 向量化存储

3. **用户界面**
   - 响应式设计
   - 中文支持
   - 实时进度显示
   - 错误处理

## 技术架构

### 前端技术栈
- **框架**: React 18 + TypeScript
- **UI库**: Ant Design
- **构建工具**: Vite
- **状态管理**: React Hooks

### 后端技术栈
- **框架**: FastAPI
- **数据库**: ChromaDB
- **嵌入模型**: 阿里云 text-embedding-v4
- **文件解析**: 多种专业库

## 使用示例

```javascript
// 文件上传示例
const uploadFile = async (file, config) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('chunking_config', JSON.stringify(config));
  
  const response = await api.documents.upload(collectionName, formData);
  return response.data;
};
```

## 分块算法

### 递归分块 (Recursive)
按照指定的分隔符递归地分割文本，保持语义完整性。

### 固定大小分块 (Fixed-size)
按照固定的字符数量分割文本，简单高效。

### 语义分块 (Semantic)
基于语义相似度分割文本，保持语义连贯性。

## 表格处理

对于Excel和CSV文件，系统会：
1. 自动识别表格结构
2. 分析列的类型（元数据/内容）
3. 将每行转换为独立文档
4. 保留元数据信息

---

*这是一个测试文档，用于验证Markdown解析功能的完整性。*
