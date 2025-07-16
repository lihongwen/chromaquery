"""
简单的测试后端服务，用于测试前端导航功能
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List
from pydantic import BaseModel
import json
import random

# 创建FastAPI应用
app = FastAPI(
    title="ChromaDB Web Manager Test",
    description="测试用的简化后端服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模拟数据
class CollectionInfo(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict

class CollectionDetail(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict
    created_time: str
    documents: List[dict]
    sample_documents: List[dict]

# 模拟集合数据
mock_collections = [
    {
        "name": "test_collection_1",
        "display_name": "测试集合1",
        "count": 5,
        "metadata": {"vector_dimension": 1024, "embedding_model": "alibaba-text-embedding-v4"}
    },
    {
        "name": "test_collection_2", 
        "display_name": "测试集合2",
        "count": 3,
        "metadata": {"vector_dimension": 1024, "embedding_model": "alibaba-text-embedding-v4"}
    }
]

# 模拟文档数据 - 使用字典以便于按集合和文件名管理
mock_documents = {
    "测试集合1": [
        {
            "id": "doc1",
            "document": "这是第一个测试文档的内容，用于验证集合详情页面的显示功能。",
            "metadata": {"file_name": "test1.txt", "chunk_method": "recursive", "total_chunks": 2},
            "embedding": [0.1] * 1024
        },
        {
            "id": "doc2",
            "document": "这是第二个测试文档的内容，包含更多的文字来测试文档预览功能的效果。",
            "metadata": {"file_name": "test2.txt", "chunk_method": "semantic", "total_chunks": 3},
            "embedding": [0.2] * 1024
        }
    ],
    "测试集合2": [
        {
            "id": "doc3",
            "document": "这是测试集合2中的文档内容。",
            "metadata": {"file_name": "test3.txt", "chunk_method": "fixed_size", "total_chunks": 1},
            "embedding": [0.3] * 1024
        }
    ]
}

@app.get("/api/collections")
async def get_collections():
    """获取集合列表"""
    return mock_collections

@app.get("/api/collections/{collection_name}/detail")
async def get_collection_detail(collection_name: str, limit: int = 20):
    """获取集合详细信息"""
    # 查找集合
    collection = None
    for col in mock_collections:
        if col["display_name"] == collection_name or col["name"] == collection_name:
            collection = col
            break

    if not collection:
        raise HTTPException(status_code=404, detail="集合不存在")

    # 获取该集合的文档
    collection_docs = mock_documents.get(collection["display_name"], [])

    # 返回集合详情
    detail = {
        "name": collection["name"],
        "display_name": collection["display_name"],
        "count": len(collection_docs),
        "metadata": collection["metadata"],
        "created_time": "2024-01-01 12:00:00",
        "documents": collection_docs,
        "sample_documents": collection_docs
    }

    return detail

@app.delete("/api/collections/{collection_name}/documents/{file_name}")
async def delete_document(collection_name: str, file_name: str):
    """删除指定集合中的指定文档"""
    # 查找集合
    collection = None
    for col in mock_collections:
        if col["display_name"] == collection_name or col["name"] == collection_name:
            collection = col
            break

    if not collection:
        raise HTTPException(status_code=404, detail="集合不存在")

    # 获取该集合的文档列表
    collection_docs = mock_documents.get(collection["display_name"], [])

    # 查找要删除的文档
    doc_to_remove = None
    for doc in collection_docs:
        if doc["metadata"].get("file_name") == file_name:
            doc_to_remove = doc
            break

    if not doc_to_remove:
        raise HTTPException(status_code=404, detail=f"文档 '{file_name}' 不存在")

    # 删除文档
    collection_docs.remove(doc_to_remove)

    # 更新集合的文档数量
    for col in mock_collections:
        if col["display_name"] == collection["display_name"]:
            col["count"] = len(collection_docs)
            break

    return {"message": f"文档 '{file_name}' 删除成功", "deleted_file": file_name}

@app.post("/api/collections/{collection_name}/upload")
async def upload_document(
    collection_name: str,
    file: UploadFile = File(...),
    chunking_config: str = Form(...)
):
    """上传文档到指定集合"""
    # 查找集合
    collection = None
    for col in mock_collections:
        if col["display_name"] == collection_name or col["name"] == collection_name:
            collection = col
            break

    if not collection:
        raise HTTPException(status_code=404, detail="集合不存在")

    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支持上传 .txt 格式的文件")

    try:
        # 解析分块配置
        config = json.loads(chunking_config)
        chunk_method = config.get("method", "recursive")
        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 200)

        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')

        # 模拟RAG分块处理
        # 根据chunk_size简单计算分块数量
        estimated_chunks = max(1, len(file_content) // chunk_size)
        # 添加一些随机性来模拟真实的分块结果
        chunks_created = max(1, estimated_chunks + random.randint(-1, 2))

        # 创建新文档记录
        new_document = {
            "id": f"doc_{len(mock_documents.get(collection['display_name'], [])) + 1}",
            "document": file_content[:200] + "..." if len(file_content) > 200 else file_content,  # 预览内容
            "metadata": {
                "file_name": file.filename,
                "chunk_method": chunk_method,
                "total_chunks": chunks_created,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "model": "alibaba-text-embedding-v4"
            },
            "embedding": [random.random() for _ in range(1024)]  # 模拟1024维向量
        }

        # 添加文档到集合
        if collection["display_name"] not in mock_documents:
            mock_documents[collection["display_name"]] = []

        mock_documents[collection["display_name"]].append(new_document)

        # 更新集合的文档数量
        for col in mock_collections:
            if col["display_name"] == collection["display_name"]:
                col["count"] = len(mock_documents[collection["display_name"]])
                break

        return {"chunks_created": chunks_created, "message": f"文档 '{file.filename}' 上传成功"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="分块配置格式错误")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请确保文件为UTF-8编码")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "ChromaDB Web Manager Test Backend"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
