#!/usr/bin/env python3
"""
ChromaDB Web Manager - 后端主应用
支持中文集合名称的ChromaDB Web管理界面
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as ef
import uvicorn
import logging
from typing import List, Optional, AsyncGenerator
import base64
import hashlib
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from alibaba_embedding import create_alibaba_embedding_function
from config_manager import config_manager
from vector_optimization import (
    get_optimized_collection_metadata,
    DEFAULT_OPTIMIZATION_CONFIG,
    HIGH_PRECISION_CONFIG,
    DistanceMetric,
    calculate_optimized_similarity
)
from fastapi import UploadFile, File, Form
import tempfile
import time
import json
import asyncio
from file_parsers import file_parser_manager, FileFormat

# 延迟导入有问题的模块，避免启动时冲突
def get_rag_chunker():
    """延迟导入RAG分块器"""
    try:
        from rag_chunking import RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config
        return RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config
    except ImportError as e:
        logger.warning(f"RAG分块功能不可用: {e}")
        return None, None, None, None

def get_llm_client_module():
    """延迟导入LLM客户端"""
    try:
        from llm_client import get_llm_client, init_llm_client
        return get_llm_client, init_llm_client
    except ImportError as e:
        logger.warning(f"LLM客户端功能不可用: {e}")
        return None, None

# 加载环境变量
load_dotenv()

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:5173", "http://127.0.0.1:5173"],
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
        # 使用配置管理器获取绝对路径
        chroma_path = config_manager.get_chroma_db_path()
        logger.info(f"使用ChromaDB数据路径: {chroma_path}")

        # 验证路径有效性
        if not config_manager.validate_path(chroma_path):
            raise Exception(f"ChromaDB数据路径无效: {chroma_path}")

        # 使用持久化客户端
        chroma_client = chromadb.PersistentClient(path=chroma_path)
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
    files_count: Optional[int] = None
    chunk_statistics: Optional[dict] = None
    dimension: Optional[int] = None  # 向量维数

class DocumentInfo(BaseModel):
    id: str
    document: Optional[str] = None
    metadata: Optional[dict] = {}
    embedding: Optional[List[float]] = None

class CollectionDetail(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict = {}
    created_time: Optional[str] = None
    documents: List[DocumentInfo] = []
    sample_documents: List[DocumentInfo] = []
    uploaded_files: List[str] = []
    chunk_statistics: dict = {}

class CreateCollectionRequest(BaseModel):
    name: str
    metadata: Optional[dict] = {}

class RenameCollectionRequest(BaseModel):
    old_name: str
    new_name: str

class AddDocumentRequest(BaseModel):
    collection_name: str
    documents: List[str]
    metadatas: Optional[List[dict]] = None
    ids: Optional[List[str]] = None

class ChunkTextRequest(BaseModel):
    text: str
    chunking_config: dict  # 使用dict类型避免导入问题

class FileUploadResponse(BaseModel):
    message: str
    file_name: str
    chunks_created: int
    total_size: int
    processing_time: float
    collection_name: str

class QueryRequest(BaseModel):
    query: str
    collections: List[str]
    limit: Optional[int] = 5

class QueryResult(BaseModel):
    id: str
    document: str
    metadata: dict
    distance: float
    collection_name: str

class QueryResponse(BaseModel):
    query: str
    results: List[QueryResult]
    total_results: int
    processing_time: float

# LLM查询相关数据模型
class LLMQueryRequest(BaseModel):
    query: str
    collections: List[str]
    limit: Optional[int] = 5
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    similarity_threshold: Optional[float] = 1.5

class LLMStreamChunk(BaseModel):
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None

class LLMQueryResponse(BaseModel):
    query: str
    answer: str
    context_results: List[QueryResult]
    processing_time: float
    model_info: dict

class DeleteDocumentResponse(BaseModel):
    message: str
    file_name: str
    deleted_chunks: int
    collection_name: str

# 存储配置相关数据模型
class StorageConfigRequest(BaseModel):
    path: str

class StorageConfigResponse(BaseModel):
    current_path: str
    path_history: List[str]
    last_updated: str

class PathInfoResponse(BaseModel):
    path: str
    exists: bool
    is_directory: bool
    readable: bool
    writable: bool
    collections_count: int
    size_mb: float
    error: Optional[str] = None

class PathValidationResponse(BaseModel):
    valid: bool
    message: str
    path_info: Optional[PathInfoResponse] = None

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化ChromaDB客户端和LLM客户端"""
    init_chroma_client()

    # 尝试初始化LLM客户端
    get_llm_client_func, init_llm_client_func = get_llm_client_module()
    if init_llm_client_func:
        try:
            init_llm_client_func()
            logger.info("LLM客户端初始化成功")
        except Exception as e:
            logger.warning(f"LLM客户端初始化失败: {e}")
    else:
        logger.warning("LLM客户端模块不可用")

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

# 存储配置API
@app.get("/api/settings/storage", response_model=StorageConfigResponse)
async def get_storage_config():
    """获取当前存储配置"""
    try:
        return StorageConfigResponse(
            current_path=config_manager.get_chroma_db_path(),
            path_history=config_manager.get_path_history(),
            last_updated=config_manager._config.get("last_updated", "")
        )
    except Exception as e:
        logger.error(f"获取存储配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储配置失败: {str(e)}")

@app.post("/api/settings/storage")
async def set_storage_config(request: StorageConfigRequest):
    """设置存储路径"""
    try:
        # 验证路径
        if not config_manager.validate_path(request.path):
            raise HTTPException(status_code=400, detail="路径无效或无法访问")

        # 设置新路径
        if not config_manager.set_chroma_db_path(request.path):
            raise HTTPException(status_code=500, detail="设置存储路径失败")

        # 重新初始化ChromaDB客户端
        init_chroma_client()

        return {
            "success": True,
            "message": "存储路径设置成功",
            "new_path": config_manager.get_chroma_db_path()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置存储路径失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置存储路径失败: {str(e)}")

@app.post("/api/settings/storage/validate", response_model=PathValidationResponse)
async def validate_storage_path(request: StorageConfigRequest):
    """验证存储路径"""
    try:
        is_valid = config_manager.validate_path(request.path)
        path_info = config_manager.get_path_info(request.path)

        message = "路径有效" if is_valid else "路径无效"
        if "error" in path_info:
            message = path_info["error"]

        return PathValidationResponse(
            valid=is_valid,
            message=message,
            path_info=PathInfoResponse(**path_info)
        )
    except Exception as e:
        logger.error(f"验证存储路径失败: {e}")
        return PathValidationResponse(
            valid=False,
            message=f"验证失败: {str(e)}"
        )

@app.get("/api/settings/storage/history")
async def get_storage_history():
    """获取存储路径历史记录"""
    try:
        history = config_manager.get_path_history()
        history_with_info = []

        for path in history:
            path_info = config_manager.get_path_info(path)
            history_with_info.append({
                "path": path,
                "info": path_info
            })

        return {
            "history": history_with_info
        }
    except Exception as e:
        logger.error(f"获取存储历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储历史失败: {str(e)}")

@app.delete("/api/settings/storage/history")
async def remove_from_storage_history(request: StorageConfigRequest):
    """从历史记录中移除路径"""
    try:
        if config_manager.remove_from_history(request.path):
            return {"success": True, "message": "已从历史记录中移除"}
        else:
            raise HTTPException(status_code=500, detail="移除失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"移除历史记录失败: {str(e)}")

@app.post("/api/settings/storage/reset")
async def reset_storage_config():
    """重置存储配置为默认值"""
    try:
        if not config_manager.reset_to_default():
            raise HTTPException(status_code=500, detail="重置配置失败")

        # 重新初始化ChromaDB客户端
        init_chroma_client()

        return {
            "success": True,
            "message": "已重置为默认配置",
            "default_path": config_manager.get_chroma_db_path()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置存储配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置存储配置失败: {str(e)}")

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

            # 获取文件统计信息
            files_count = 0  # 默认为0而不是None
            chunk_statistics = None
            try:
                if count > 0:
                    # 获取所有文档的元数据来计算文件统计
                    docs_result = collection.get(limit=count, include=['metadatas'])
                    if docs_result and docs_result['metadatas']:
                        # 统计唯一文件数
                        unique_files = set()
                        methods_used = set()

                        for doc_metadata in docs_result['metadatas']:
                            if doc_metadata:
                                file_name = doc_metadata.get('file_name') or doc_metadata.get('source_file')
                                if file_name:
                                    unique_files.add(file_name)

                                chunk_method = doc_metadata.get('chunk_method')
                                if chunk_method:
                                    methods_used.add(chunk_method)

                        files_count = len(unique_files)
                        chunk_statistics = {
                            'total_chunks': count,
                            'files_count': files_count,
                            'methods_used': list(methods_used)
                        }
                else:
                    # 对于空集合，设置基本的统计信息
                    chunk_statistics = {
                        'total_chunks': 0,
                        'files_count': 0,
                        'methods_used': []
                    }
            except Exception as e:
                logger.warning(f"获取集合 {collection.name} 的文件统计信息失败: {e}")
                # 即使出错也要确保有基本的统计信息
                files_count = 0
                chunk_statistics = {
                    'total_chunks': count,
                    'files_count': 0,
                    'methods_used': []
                }

            # 从元数据中提取向量维数，如果没有则尝试从实际向量中获取
            dimension = metadata.get('vector_dimension')

            # 如果元数据中没有维度信息，尝试从实际向量中获取
            if not dimension and count > 0:
                try:
                    sample_result = collection.get(limit=1, include=["embeddings"])
                    if sample_result and sample_result.get('embeddings') and sample_result['embeddings'][0]:
                        dimension = len(sample_result['embeddings'][0])
                        # 更新元数据中的维度信息
                        metadata['vector_dimension'] = dimension
                        logger.info(f"从实际向量中检测到集合 '{display_name}' 的维度: {dimension}")
                except Exception as e:
                    logger.warning(f"无法获取集合 '{display_name}' 的向量维度: {e}")
                    dimension = None

            result.append(CollectionInfo(
                name=collection.name,  # 原始编码名称
                display_name=display_name,  # 显示名称（中文）
                count=count,
                metadata=metadata,
                files_count=files_count,
                chunk_statistics=chunk_statistics,
                dimension=dimension  # 向量维数
            ))

        return result
    except Exception as e:
        logger.error(f"获取集合列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")

@app.get("/api/collections/{collection_name}/detail", response_model=CollectionDetail)
async def get_collection_detail(collection_name: str, limit: Optional[int] = 10):
    """获取集合详细信息"""
    try:
        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            # 支持通过原始名称或编码名称查找
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 获取集合基本信息
        metadata = target_collection.metadata or {}
        display_name = metadata.get('original_name', target_collection.name)
        count = target_collection.count()

        # 获取文档数据
        documents = []
        sample_documents = []

        if count > 0:
            try:
                # 获取所有文档（如果数量不多）或者样本文档
                if count <= 100:
                    # 获取所有文档
                    results = target_collection.get(
                        include=["documents", "metadatas", "embeddings"]
                    )
                else:
                    # 获取样本文档
                    results = target_collection.get(
                        limit=limit,
                        include=["documents", "metadatas", "embeddings"]
                    )

                # 处理文档数据
                if results and results.get('ids'):
                    for i, doc_id in enumerate(results['ids']):
                        doc_info = DocumentInfo(
                            id=doc_id,
                            document=results.get('documents', [None])[i] if results.get('documents') else None,
                            metadata=results.get('metadatas', [{}])[i] if results.get('metadatas') else {},
                            embedding=results.get('embeddings', [None])[i] if results.get('embeddings') else None
                        )

                        if count <= 100:
                            documents.append(doc_info)
                        else:
                            sample_documents.append(doc_info)

            except Exception as e:
                logger.warning(f"获取集合文档时出现警告: {e}")

        # 获取创建时间（如果在元数据中）
        created_time = metadata.get('created_time') or metadata.get('created_date')

        # 计算文件统计信息
        uploaded_files = set()
        chunk_methods = set()
        total_chunks = 0

        # 从所有文档中提取文件信息
        all_docs = documents if documents else sample_documents
        for doc in all_docs:
            doc_metadata = doc.metadata or {}
            file_name = doc_metadata.get('file_name')
            if file_name:
                uploaded_files.add(file_name)

            chunk_method = doc_metadata.get('chunk_method')
            if chunk_method:
                chunk_methods.add(chunk_method)

            if doc_metadata.get('chunk_index') is not None:
                total_chunks += 1

        # 如果没有从样本中获取到完整信息，尝试获取更多数据
        if count > 100 and len(uploaded_files) == 0:
            try:
                # 获取更多文档来统计文件信息
                more_results = target_collection.get(
                    limit=min(count, 1000),  # 最多获取1000个文档用于统计
                    include=["metadatas"]
                )

                if more_results and more_results.get('metadatas'):
                    for metadata_item in more_results['metadatas']:
                        if metadata_item:
                            file_name = metadata_item.get('file_name')
                            if file_name:
                                uploaded_files.add(file_name)

                            chunk_method = metadata_item.get('chunk_method')
                            if chunk_method:
                                chunk_methods.add(chunk_method)

                            if metadata_item.get('chunk_index') is not None:
                                total_chunks += 1

            except Exception as e:
                logger.warning(f"获取文件统计信息时出现警告: {e}")

        chunk_statistics = {
            "total_chunks": total_chunks if total_chunks > 0 else count,
            "files_count": len(uploaded_files),
            "methods_used": list(chunk_methods)
        }

        return CollectionDetail(
            name=target_collection.name,
            display_name=display_name,
            count=count,
            metadata=metadata,
            created_time=created_time,
            documents=documents,
            sample_documents=sample_documents,
            uploaded_files=list(uploaded_files),
            chunk_statistics=chunk_statistics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取集合详细信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取集合详细信息失败: {str(e)}")

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

        # 使用优化配置
        optimization_config = HIGH_PRECISION_CONFIG

        # 准备元数据，包含原始中文名称和优化配置
        base_metadata = request.metadata or {}
        base_metadata['original_name'] = request.name
        base_metadata['embedding_model'] = 'alibaba-text-embedding-v4'

        # 应用向量优化配置
        metadata = get_optimized_collection_metadata(optimization_config, base_metadata)

        # 创建阿里云嵌入函数，使用优化的维度
        try:
            alibaba_embedding_func = create_alibaba_embedding_function(dimension=optimization_config.vector_dimension)
            logger.info(f"成功创建阿里云嵌入函数，维度: {optimization_config.vector_dimension}")
        except Exception as e:
            logger.error(f"创建阿里云嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")

        # 创建集合，使用阿里云嵌入函数和优化的元数据
        collection = chroma_client.create_collection(
            name=encoded_name,
            metadata=metadata,
            embedding_function=alibaba_embedding_func
        )

        logger.info(f"集合创建成功，使用优化配置: 距离度量={optimization_config.distance_metric}, 维度={optimization_config.vector_dimension}")

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
        # 检查原集合是否使用阿里云嵌入模型
        embedding_function = None
        if new_metadata.get('embedding_model') == 'alibaba-text-embedding-v4':
            try:
                embedding_function = create_alibaba_embedding_function(dimension=1024)
                logger.info(f"为重命名集合创建阿里云嵌入函数")
            except Exception as e:
                logger.warning(f"创建阿里云嵌入函数失败，使用默认函数: {e}")

        # 创建新集合
        if embedding_function:
            new_collection = chroma_client.create_collection(
                name=new_encoded,
                metadata=new_metadata,
                embedding_function=embedding_function
            )
        else:
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

@app.post("/api/collections/{collection_name}/documents")
async def add_documents(collection_name: str, request: AddDocumentRequest):
    """向集合添加文档"""
    try:
        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            # 支持通过原始名称或编码名称查找
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 检查集合是否使用阿里云嵌入模型
        collection_metadata = target_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')

        if embedding_model == 'alibaba-text-embedding-v4':
            # 重新创建阿里云嵌入函数
            try:
                alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
                logger.info(f"为集合 '{collection_name}' 重新创建阿里云嵌入函数")

                # 使用阿里云嵌入函数生成向量
                embeddings = alibaba_embedding_func(request.documents)
                logger.info(f"成功生成 {len(embeddings)} 个1024维向量")

            except Exception as e:
                logger.error(f"创建阿里云嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")
        else:
            # 使用默认嵌入函数
            embeddings = None
            logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        # 准备文档数据
        documents = request.documents
        metadatas = request.metadatas or [{}] * len(documents)
        ids = request.ids or [f"doc_{i}_{hash(doc)}" for i, doc in enumerate(documents)]

        # 确保数据长度一致
        if len(metadatas) != len(documents):
            metadatas = metadatas + [{}] * (len(documents) - len(metadatas))

        if len(ids) != len(documents):
            raise HTTPException(status_code=400, detail="文档ID数量与文档数量不匹配")

        # 添加文档到集合
        if embeddings:
            # 使用预生成的向量
            target_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            # 使用集合的默认嵌入函数
            target_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return {
            "message": f"成功向集合 '{collection_name}' 添加 {len(documents)} 个文档",
            "added_count": len(documents),
            "collection_name": collection_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加文档失败: {str(e)}")

@app.post("/api/collections/{collection_name}/upload", response_model=FileUploadResponse)
async def upload_document(
    collection_name: str,
    file: UploadFile = File(...),
    chunking_config: str = Form(...)
):
    """上传文档文件并进行RAG分块处理"""
    start_time = time.time()

    try:
        # 获取RAG分块器相关类
        RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config = get_rag_chunker()
        if not ChunkingConfig:
            raise HTTPException(status_code=500, detail="RAG分块功能不可用")

        # 验证文件名
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 验证文件格式
        if not file_parser_manager.can_parse(file.filename):
            supported_extensions = file_parser_manager.get_supported_extensions()
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式。支持的格式: {', '.join(supported_extensions)}"
            )

        # 读取文件内容
        content = await file.read()

        # 验证文件大小 (50MB限制，增加了限制以支持更多格式)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")

        # 使用文件解析器解析文件
        parse_result = file_parser_manager.parse_file(content, file.filename)

        if not parse_result.success:
            raise HTTPException(
                status_code=400,
                detail=f"文件解析失败: {parse_result.error_message}"
            )

        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            # 支持通过原始名称或编码名称查找
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 根据文件类型决定处理方式
        if parse_result.is_table and parse_result.table_data:
            # 表格文件：使用表格专用逻辑，不需要分块配置
            logger.info(f"检测到表格文件 '{file.filename}'，使用表格专用处理逻辑")
            chunking_result = None  # 表格文件不需要分块
        else:
            # 普通文件：解析分块配置并进行分块
            import json
            try:
                config_dict = json.loads(chunking_config)
                config = ChunkingConfig(**config_dict)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"分块配置格式错误: {e}")

            text_content = parse_result.content
            if not text_content.strip():
                raise HTTPException(status_code=400, detail="文件中未提取到有效文本内容")

            # 进行RAG分块
            chunker = RAGChunker()
            chunking_result = chunker.chunk_text(text_content, config)

        # 准备文档数据
        documents = []
        metadatas = []
        ids = []

        # 处理表格文件的特殊情况
        if parse_result.is_table and parse_result.table_data:
            # 表格文件：每行数据作为一个文档
            for row_idx, row_data in enumerate(parse_result.table_data):
                # 构建文档内容
                content_columns = [col for col, type_ in parse_result.column_analysis.items() if type_ == 'content']
                metadata_columns = [col for col, type_ in parse_result.column_analysis.items() if type_ == 'metadata']

                # 内容部分
                content_parts = []
                for col in content_columns:
                    if col in row_data and row_data[col] is not None and str(row_data[col]).strip():
                        content_parts.append(f"{col}: {str(row_data[col]).strip()}")

                if content_parts:
                    document_text = " | ".join(content_parts)
                else:
                    # 如果没有内容列，使用所有列
                    all_parts = []
                    for col, value in row_data.items():
                        if value is not None and str(value).strip():
                            all_parts.append(f"{col}: {str(value).strip()}")
                    document_text = " | ".join(all_parts)

                documents.append(document_text)

                # 创建元数据（包含表格的元数据列）
                metadata = {
                    "file_name": file.filename,
                    "file_format": parse_result.file_format.value if parse_result.file_format else "unknown",
                    "is_table": True,
                    "row_index": row_idx,
                    "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_rows": len(parse_result.table_data)
                }

                # 添加表格的元数据列
                for col in metadata_columns:
                    if col in row_data and row_data[col] is not None:
                        metadata[f"table_{col}"] = str(row_data[col])

                # 添加文件解析的元数据
                if parse_result.metadata:
                    for key, value in parse_result.metadata.items():
                        if key not in metadata:
                            metadata[f"file_{key}"] = value

                metadatas.append(metadata)

                # 生成文档ID
                import uuid
                doc_id = f"{file.filename}_row_{row_idx}_{str(uuid.uuid4())[:8]}"
                ids.append(doc_id)
        else:
            # 普通文件：使用分块处理
            if chunking_result is None:
                raise HTTPException(status_code=500, detail="分块处理失败：未生成分块结果")

            for chunk in chunking_result.chunks:
                documents.append(chunk.text)

                # 创建元数据
                metadata = {
                    "file_name": file.filename,
                    "file_format": parse_result.file_format.value if parse_result.file_format else "unknown",
                    "is_table": False,
                    "chunk_method": config.method.value,
                    "chunk_index": chunk.index,
                    "chunk_size": len(chunk.text),
                    "start_position": chunk.start_pos,
                    "end_position": chunk.end_pos,
                    "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_chunks": chunking_result.total_chunks
                }

                # 添加文件解析的元数据
                if parse_result.metadata:
                    for key, value in parse_result.metadata.items():
                        if key not in metadata:
                            metadata[f"file_{key}"] = value

                metadatas.append(metadata)

                # 生成文档ID
                import uuid
                chunk_id = f"{file.filename}_{chunk.index}_{str(uuid.uuid4())[:8]}"
                ids.append(chunk_id)

        # 检查集合是否使用阿里云嵌入模型
        collection_metadata = target_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')

        if embedding_model == 'alibaba-text-embedding-v4':
            # 重新创建阿里云嵌入函数
            try:
                alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
                logger.info(f"为集合 '{collection_name}' 重新创建阿里云嵌入函数")

                # 使用阿里云嵌入函数生成向量，支持批量处理
                embeddings = []
                batch_size = 10  # 阿里云API限制

                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    logger.info(f"处理文档批次 {i//batch_size + 1}: {len(batch)} 个文档")

                    try:
                        batch_embeddings = alibaba_embedding_func(batch)
                        embeddings.extend(batch_embeddings)
                        logger.info(f"成功生成批次 {i//batch_size + 1} 的嵌入向量")
                    except Exception as e:
                        logger.error(f"批次 {i//batch_size + 1} 嵌入向量生成失败: {e}")
                        raise e

                logger.info(f"成功生成 {len(embeddings)} 个1024维向量")

            except Exception as e:
                logger.error(f"创建阿里云嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")
        else:
            # 使用默认嵌入函数
            embeddings = None
            logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        # 添加到ChromaDB
        if embeddings:
            # 使用预生成的向量
            target_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            # 使用集合的默认嵌入函数
            target_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        processing_time = time.time() - start_time

        # 构建响应消息
        if parse_result.is_table:
            message = f"表格文件 '{file.filename}' 上传成功，创建了 {len(documents)} 行数据"
        else:
            message = f"文档 '{file.filename}' 上传成功，创建了 {len(documents)} 个文档块"

        return FileUploadResponse(
            message=message,
            file_name=file.filename,
            chunks_created=len(documents),
            total_size=len(content),
            processing_time=processing_time,
            collection_name=collection_name
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"文档上传失败: {e}")
        logger.error(f"详细错误信息: {error_details}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@app.get("/api/supported-formats")
async def get_supported_formats():
    """获取支持的文件格式"""
    try:
        supported_formats = file_parser_manager.get_supported_formats()
        supported_extensions = file_parser_manager.get_supported_extensions()

        format_info = {}
        for format_ in supported_formats:
            format_info[format_.value] = {
                "extension": f".{format_.value}",
                "description": _get_format_description(format_)
            }

        return {
            "supported_formats": format_info,
            "supported_extensions": supported_extensions,
            "total_count": len(supported_formats)
        }
    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取支持格式失败: {str(e)}")

def _get_format_description(format_: FileFormat) -> str:
    """获取文件格式描述"""
    descriptions = {
        FileFormat.TXT: "纯文本文件",
        FileFormat.PDF: "PDF文档",
        FileFormat.DOCX: "Word文档 (新格式)",
        FileFormat.DOC: "Word文档 (旧格式)",
        FileFormat.PPTX: "PowerPoint演示文稿 (新格式)",
        FileFormat.PPT: "PowerPoint演示文稿 (旧格式)",
        FileFormat.MARKDOWN: "Markdown文档",
        FileFormat.RTF: "富文本格式文档",
        FileFormat.XLSX: "Excel工作簿 (新格式)",
        FileFormat.XLS: "Excel工作簿 (旧格式)",
        FileFormat.CSV: "逗号分隔值文件"
    }
    return descriptions.get(format_, "未知格式")

@app.delete("/api/collections/{collection_name}/documents/{file_name}", response_model=DeleteDocumentResponse)
async def delete_document_by_filename(collection_name: str, file_name: str):
    """删除指定文件名的所有文档块"""
    try:
        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            # 支持通过原始名称或编码名称查找
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 获取该文件的所有文档块
        try:
            # 获取所有文档
            results = target_collection.get(include=['metadatas'])
            
            if not results or not results.get('ids'):
                raise HTTPException(status_code=404, detail=f"集合中没有找到文档")

            # 找到属于指定文件的所有文档块
            target_ids = []
            for i, doc_id in enumerate(results['ids']):
                doc_metadata = results['metadatas'][i] if results.get('metadatas') else {}
                if doc_metadata:
                    doc_file_name = doc_metadata.get('file_name') or doc_metadata.get('source_file')
                    if doc_file_name == file_name:
                        target_ids.append(doc_id)

            if not target_ids:
                raise HTTPException(status_code=404, detail=f"未找到文件 '{file_name}' 的文档")

            # 删除这些文档块
            target_collection.delete(ids=target_ids)
            
            logger.info(f"成功删除文件 '{file_name}' 的 {len(target_ids)} 个文档块")

            return DeleteDocumentResponse(
                message=f"成功删除文件 '{file_name}' 的所有文档块",
                file_name=file_name,
                deleted_chunks=len(target_ids),
                collection_name=collection_name
            )

        except Exception as e:
            logger.error(f"删除文档块时出错: {e}")
            raise HTTPException(status_code=500, detail=f"删除文档块时出错: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@app.post("/api/collections/{collection_name}/chunk")
async def chunk_text(collection_name: str, request: ChunkTextRequest):
    """对文本进行RAG分块处理（预览功能）"""
    try:
        # 获取RAG分块器相关类
        RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config = get_rag_chunker()
        if not RAGChunker:
            raise HTTPException(status_code=500, detail="RAG分块功能不可用")

        # 验证集合是否存在
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            if (metadata.get('original_name') == collection_name or
                collection.name == collection_name):
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 进行RAG分块
        chunker = RAGChunker()
        chunking_result = chunker.chunk_text(request.text, request.chunking_config)

        # 转换为API响应格式
        chunks = []
        for chunk in chunking_result.chunks:
            chunks.append({
                "text": chunk.text,
                "index": chunk.index,
                "start_pos": chunk.start_pos,
                "end_pos": chunk.end_pos,
                "metadata": chunk.metadata
            })

        return {
            "chunks": chunks,
            "total_chunks": chunking_result.total_chunks,
            "method_used": chunking_result.method_used.value,
            "processing_time": chunking_result.processing_time,
            "original_length": chunking_result.original_length
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本分块失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本分块失败: {str(e)}")

@app.get("/api/chunking/config/{method}")
async def get_default_chunking_config_api(method: str):
    """获取指定分块方式的默认配置"""
    try:
        # 获取RAG分块器相关类
        RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config = get_rag_chunker()
        if not ChunkingMethod:
            raise HTTPException(status_code=500, detail="RAG分块功能不可用")

        chunking_method = ChunkingMethod(method)
        config = get_default_chunking_config(chunking_method)
        return config.model_dump()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的分块方式: {method}")
    except Exception as e:
        logger.error(f"获取默认配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取默认配置失败: {str(e)}")

@app.post("/api/query", response_model=QueryResponse)
async def query_collections(request: QueryRequest):
    """在指定集合中进行向量查询"""
    start_time = time.time()

    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")

        if not request.collections:
            raise HTTPException(status_code=400, detail="请选择至少一个集合")

        # 验证集合是否存在
        existing_collections = chroma_client.list_collections()
        collection_map = {}

        for collection in existing_collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('original_name', collection.name)
            collection_map[display_name] = collection

        # 检查请求的集合是否都存在
        missing_collections = []
        target_collections = []

        for collection_name in request.collections:
            if collection_name in collection_map:
                target_collections.append((collection_name, collection_map[collection_name]))
            else:
                missing_collections.append(collection_name)

        if missing_collections:
            raise HTTPException(
                status_code=404,
                detail=f"以下集合不存在: {', '.join(missing_collections)}"
            )

        # 生成查询向量
        # 使用第一个集合的嵌入模型来生成查询向量
        first_collection = target_collections[0][1]
        collection_metadata = first_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')

        query_embedding = None
        if embedding_model == 'alibaba-text-embedding-v4':
            try:
                alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
                query_embeddings = alibaba_embedding_func([request.query])
                query_embedding = query_embeddings[0]
                logger.info(f"使用阿里云嵌入模型生成查询向量，维度: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"生成查询向量失败: {e}")
                raise HTTPException(status_code=500, detail=f"生成查询向量失败: {str(e)}")

        # 在每个集合中进行查询
        all_results = []

        for collection_name, collection in target_collections:
            try:
                # 执行向量查询
                if query_embedding:
                    # 使用预生成的向量查询
                    search_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=request.limit,
                        include=['documents', 'metadatas', 'distances']
                    )
                else:
                    # 使用文本查询（让ChromaDB自动生成向量）
                    search_results = collection.query(
                        query_texts=[request.query],
                        n_results=request.limit,
                        include=['documents', 'metadatas', 'distances']
                    )

                # 处理查询结果
                if search_results and search_results.get('ids') and search_results['ids'][0]:
                    # 获取集合的距离度量类型
                    collection_metadata = collection.metadata or {}
                    distance_metric_str = collection_metadata.get('hnsw:space', 'l2')
                    if distance_metric_str == 'cosine':
                        distance_metric = DistanceMetric.COSINE
                    elif distance_metric_str == 'ip':
                        distance_metric = DistanceMetric.IP
                    else:
                        distance_metric = DistanceMetric.L2

                    for i, doc_id in enumerate(search_results['ids'][0]):
                        distance = search_results['distances'][0][i] if search_results.get('distances') else 0.0

                        # 使用优化的相似度计算
                        similarity_percent = calculate_optimized_similarity(distance, distance_metric)

                        # 相似度阈值过滤：将百分比阈值转换为0-1范围
                        similarity_threshold_decimal = request.similarity_threshold
                        similarity_decimal = similarity_percent / 100.0

                        if similarity_decimal >= similarity_threshold_decimal:
                            result = QueryResult(
                                id=doc_id,
                                document=search_results['documents'][0][i] if search_results.get('documents') else "",
                                metadata=search_results['metadatas'][0][i] if search_results.get('metadatas') else {},
                                distance=distance,
                                collection_name=collection_name
                            )
                            all_results.append(result)

            except Exception as e:
                logger.warning(f"在集合 '{collection_name}' 中查询失败: {e}")
                # 继续查询其他集合，不中断整个查询过程
                continue

        # 按相似度排序（距离越小越相似）
        all_results.sort(key=lambda x: x.distance)

        # 限制返回结果数量
        final_results = all_results[:request.limit]

        processing_time = time.time() - start_time

        return QueryResponse(
            query=request.query,
            results=final_results,
            total_results=len(final_results),
            processing_time=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.post("/api/llm-query")
async def llm_query(request: LLMQueryRequest):
    """
    LLM智能查询接口
    结合ChromaDB向量查询和LLM生成回答
    """
    start_time = time.time()

    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")

        if not request.collections:
            raise HTTPException(status_code=400, detail="请选择至少一个集合")

        # 1. 执行ChromaDB向量查询
        logger.info(f"开始向量查询: {request.query}")

        # 验证集合是否存在
        existing_collections = chroma_client.list_collections()
        collection_map = {}

        for collection in existing_collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('original_name', collection.name)
            collection_map[display_name] = collection

        # 检查请求的集合是否都存在
        missing_collections = []
        target_collections = []

        for collection_name in request.collections:
            if collection_name in collection_map:
                target_collections.append((collection_name, collection_map[collection_name]))
            else:
                missing_collections.append(collection_name)

        if missing_collections:
            raise HTTPException(
                status_code=404,
                detail=f"以下集合不存在: {', '.join(missing_collections)}"
            )

        # 生成查询向量
        query_embedding = None
        try:
            embedding_function = create_alibaba_embedding_function()
            query_embedding = embedding_function([request.query])[0]
            logger.info(f"查询向量生成成功，维度: {len(query_embedding)}")
        except Exception as e:
            logger.warning(f"查询向量生成失败，将使用文本查询: {e}")

        # 在每个集合中进行查询
        all_results = []

        for collection_name, collection in target_collections:
            try:
                # 执行向量查询
                if query_embedding:
                    search_results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=request.limit,
                        include=['documents', 'metadatas', 'distances']
                    )
                else:
                    search_results = collection.query(
                        query_texts=[request.query],
                        n_results=request.limit,
                        include=['documents', 'metadatas', 'distances']
                    )

                # 处理查询结果
                if search_results['documents'] and search_results['documents'][0]:
                    logger.info(f"集合 {collection_name} 返回了 {len(search_results['documents'][0])} 个结果")

                    # 获取集合的距离度量类型
                    collection_metadata = collection.metadata or {}
                    distance_metric_str = collection_metadata.get('hnsw:space', 'l2')
                    if distance_metric_str == 'cosine':
                        distance_metric = DistanceMetric.COSINE
                    elif distance_metric_str == 'ip':
                        distance_metric = DistanceMetric.IP
                    else:
                        distance_metric = DistanceMetric.L2

                    for i in range(len(search_results['documents'][0])):
                        distance = search_results['distances'][0][i]

                        # 使用优化的相似度计算
                        similarity_percent = calculate_optimized_similarity(distance, distance_metric)

                        # 相似度阈值过滤：将百分比阈值转换为0-1范围
                        similarity_threshold_decimal = request.similarity_threshold
                        similarity_decimal = similarity_percent / 100.0

                        logger.info(f"文档 {i}: distance={distance:.4f}, similarity={similarity_percent:.1f}%, threshold={similarity_threshold_decimal:.2f}")
                        if similarity_decimal >= similarity_threshold_decimal:
                            result_data = {
                                'id': f"{collection_name}_{i}_{int(time.time() * 1000)}",
                                'document': search_results['documents'][0][i],
                                'metadata': search_results['metadatas'][0][i] or {},
                                'distance': distance,
                                'collection_name': collection_name
                            }
                            all_results.append(result_data)

            except Exception as e:
                logger.error(f"在集合 {collection_name} 中查询失败: {e}")
                continue

        # 按相似度排序并限制结果数量
        all_results.sort(key=lambda x: x['distance'])
        final_results = all_results[:request.limit]

        logger.info(f"向量查询完成，找到 {len(final_results)} 个结果")

        # 2. 调用LLM生成流式响应
        async def generate_stream():
            try:
                # 首先发送查询结果元数据
                metadata_chunk = {
                    'metadata': {
                        'documents_found': len(final_results),
                        'query_results': [
                            {
                                'id': result['id'],
                                'document': result['document'][:200] + '...' if len(result['document']) > 200 else result['document'],
                                'distance': result['distance'],
                                'collection_name': result['collection_name'],
                                'metadata': result['metadata']
                            }
                            for result in final_results
                        ]
                    }
                }
                data = json.dumps(metadata_chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"

                get_llm_client_func, init_llm_client_func = get_llm_client_module()
                if get_llm_client_func is None:
                    # 如果LLM客户端不可用，返回简单的搜索结果
                    simple_response = {
                        "type": "search_results",
                        "results": final_results,
                        "message": "找到相关文档，但AI回答功能暂时不可用"
                    }
                    data = json.dumps(simple_response, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    return

                llm_client = get_llm_client_func()

                async for chunk in llm_client.query_with_context(
                    query_results=final_results,
                    user_query=request.query,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # 格式化为Server-Sent Events格式
                    data = json.dumps(chunk, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                    # 如果完成或出错，结束流
                    if chunk.get('finish_reason'):
                        break

            except Exception as e:
                error_chunk = {
                    'content': '',
                    'finish_reason': 'error',
                    'error': f"LLM处理失败: {str(e)}"
                }
                data = json.dumps(error_chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"LLM查询失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
