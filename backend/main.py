"""
ChromaDB Web Manager - 后端主应用
支持中文集合名称的ChromaDB Web管理界面
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import chromadb
from chromadb.config import Settings
import uvicorn
import logging
from typing import List, Optional
import base64
import hashlib
from pydantic import BaseModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="ChromaDB Web Manager",
    description="ChromaDB集合管理Web界面，支持中文集合名称",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # 前端开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB客户端
chroma_client = None

def init_chroma_client():
    """初始化ChromaDB客户端"""
    global chroma_client
    try:
        # 使用持久化客户端
        chroma_client = chromadb.PersistentClient(path="./chroma_data")
        logger.info("ChromaDB客户端初始化成功")
    except Exception as e:
        logger.error(f"ChromaDB客户端初始化失败: {e}")
        # 如果持久化失败，使用内存客户端
        chroma_client = chromadb.Client()
        logger.info("使用内存ChromaDB客户端")

def encode_collection_name(chinese_name: str) -> str:
    """
    将中文集合名称编码为ChromaDB兼容的名称
    使用MD5哈希 + 字母数字字符确保兼容性
    """
    # 使用MD5哈希生成固定长度的字符串
    hash_object = hashlib.md5(chinese_name.encode('utf-8'))
    hash_hex = hash_object.hexdigest()

    # 确保以字母开头，符合ChromaDB命名规范
    return f"col_{hash_hex}"

def decode_collection_name(encoded_name: str) -> str:
    """
    将编码后的集合名称解码为中文名称
    由于使用哈希，需要维护一个映射表
    """
    # 由于MD5是单向的，我们需要在元数据中存储原始名称
    # 这里先返回编码名称，实际解码在获取集合时通过元数据实现
    return encoded_name

# Pydantic模型
class CollectionInfo(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict = {}

class CreateCollectionRequest(BaseModel):
    name: str
    metadata: Optional[dict] = {}

class RenameCollectionRequest(BaseModel):
    old_name: str
    new_name: str

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化ChromaDB客户端"""
    init_chroma_client()

@app.get("/")
async def root():
    """根路径"""
    return {"message": "ChromaDB Web Manager API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        # 检查ChromaDB连接
        heartbeat = chroma_client.heartbeat()
        return {
            "status": "healthy",
            "chromadb_heartbeat": heartbeat,
            "message": "服务运行正常"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不可用")

@app.get("/api/collections", response_model=List[CollectionInfo])
async def get_collections():
    """获取所有集合列表"""
    try:
        collections = chroma_client.list_collections()
        result = []

        for collection in collections:
            # 从元数据中获取原始中文名称
            metadata = collection.metadata or {}
            display_name = metadata.get('original_name', collection.name)

            # 获取集合中的文档数量
            try:
                count = collection.count()
            except:
                count = 0

            result.append(CollectionInfo(
                name=collection.name,  # 原始编码名称
                display_name=display_name,  # 显示名称（中文）
                count=count,
                metadata=metadata
            ))

        return result
    except Exception as e:
        logger.error(f"获取集合列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")

@app.post("/api/collections")
async def create_collection(request: CreateCollectionRequest):
    """创建新集合"""
    try:
        # 编码集合名称
        encoded_name = encode_collection_name(request.name)

        # 检查集合是否已存在（通过检查是否有相同原始名称的集合）
        existing_collections = chroma_client.list_collections()
        for existing in existing_collections:
            existing_metadata = existing.metadata or {}
            if existing_metadata.get('original_name') == request.name:
                raise HTTPException(status_code=400, detail=f"集合 '{request.name}' 已存在")

        # 准备元数据，包含原始中文名称
        metadata = request.metadata or {}
        metadata['original_name'] = request.name

        # 创建集合
        collection = chroma_client.create_collection(
            name=encoded_name,
            metadata=metadata
        )

        return {
            "message": f"集合 '{request.name}' 创建成功",
            "name": collection.name,
            "display_name": request.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建集合失败: {str(e)}")

@app.delete("/api/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """删除集合"""
    try:
        # 查找要删除的集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            # 支持通过原始名称或编码名称删除
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 获取显示名称用于返回消息
        display_name = target_collection.metadata.get('original_name', target_collection.name)

        # 删除集合
        chroma_client.delete_collection(target_collection.name)

        return {"message": f"集合 '{display_name}' 删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除集合失败: {str(e)}")

@app.put("/api/collections/rename")
async def rename_collection(request: RenameCollectionRequest):
    """重命名集合"""
    try:
        # 查找要重命名的集合
        collections = chroma_client.list_collections()
        old_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            if metadata.get('original_name') == request.old_name:
                old_collection = collection
                break

        if not old_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{request.old_name}' 不存在")

        # 检查新名称是否已存在
        for collection in collections:
            metadata = collection.metadata or {}
            if metadata.get('original_name') == request.new_name:
                raise HTTPException(status_code=400, detail=f"集合 '{request.new_name}' 已存在")

        # 编码新名称
        new_encoded = encode_collection_name(request.new_name)

        # 准备新的元数据
        new_metadata = old_collection.metadata.copy() if old_collection.metadata else {}
        new_metadata['original_name'] = request.new_name

        # ChromaDB不支持直接重命名，需要创建新集合并复制数据
        # 创建新集合
        new_collection = chroma_client.create_collection(
            name=new_encoded,
            metadata=new_metadata
        )

        # 复制数据（如果有的话）
        try:
            # 获取所有数据
            results = old_collection.get()
            if results['ids']:
                # 添加到新集合
                new_collection.add(
                    ids=results['ids'],
                    embeddings=results.get('embeddings'),
                    metadatas=results.get('metadatas'),
                    documents=results.get('documents')
                )
        except Exception as e:
            logger.warning(f"复制集合数据时出现警告: {e}")

        # 删除旧集合
        chroma_client.delete_collection(old_collection.name)

        return {
            "message": f"集合从 '{request.old_name}' 重命名为 '{request.new_name}' 成功",
            "old_name": request.old_name,
            "new_name": request.new_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重命名集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"重命名集合失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
