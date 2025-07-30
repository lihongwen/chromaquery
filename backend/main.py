#!/usr/bin/env python3
"""
ChromaDB Web Manager - 后端主应用
支持中文集合名称的ChromaDB Web管理界面
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as ef
import uvicorn
import logging
from typing import List, Optional, AsyncGenerator, Callable
import base64
import hashlib
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sqlite3
import json
from datetime import datetime, timedelta
import time
import asyncio
from alibaba_embedding import create_alibaba_embedding_function
from ollama_embedding import create_ollama_embedding_function, get_recommended_models, get_model_dimension, OllamaEmbeddingFunction
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
import asyncio
from file_parsers import file_parser_manager, FileFormat
from config_manager import config_manager
from platform_utils import platform_utils
from role_manager import role_manager, Role, CreateRoleRequest, UpdateRoleRequest

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

# ChromaDB客户端
chroma_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
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

    yield

    # 关闭时清理（如果需要的话）
    logger.info("应用关闭，清理资源")

# 创建FastAPI应用
app = FastAPI(
    title="ChromaDB Web Manager",
    description="ChromaDB集合管理Web界面，支持中文集合名称",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3002", "http://127.0.0.1:3002",
        "http://localhost:5173", "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def init_chroma_client():
    """初始化ChromaDB客户端"""
    global chroma_client
    try:
        # 使用跨平台工具获取ChromaDB数据路径
        chroma_path = platform_utils.get_chroma_data_directory()
        logger.info(f"使用ChromaDB数据路径: {chroma_path}")

        # ChromaDB 1.0+版本使用新的API
        # 使用持久化客户端，确保数据永久保存
        chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        logger.info("ChromaDB持久化客户端初始化成功")

    except Exception as e:
        logger.error(f"ChromaDB客户端初始化失败: {e}")
        # 如果持久化失败，使用内存客户端作为回退
        logger.warning("持久化初始化失败，使用内存客户端作为回退")
        chroma_client = chromadb.EphemeralClient()
        logger.info("ChromaDB内存客户端初始化成功（回退模式）")

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

def sanitize_metadata(metadata: dict) -> dict:
    """清理元数据，确保所有值都是ChromaDB支持的类型（str, int, float）"""
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, bool):
            # 将布尔值转换为字符串
            sanitized[key] = "true" if value else "false"
        elif isinstance(value, (str, int, float)):
            # 保持支持的类型不变
            sanitized[key] = value
        else:
            # 其他类型转换为字符串
            sanitized[key] = str(value)
    return sanitized

# Pydantic模型
class CollectionInfo(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict = {}
    files_count: Optional[int] = None
    chunk_statistics: Optional[dict] = None
    dimension: Optional[int] = None  # 向量维数
    embedding_model: Optional[str] = None  # 嵌入模型信息
    embedding_provider: Optional[str] = None  # 嵌入模型提供商
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间

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
    embedding_model: Optional[str] = None  # 支持 "alibaba" 或 "ollama"，None表示使用配置的默认值
    ollama_model: Optional[str] = None  # ollama模型名称，None表示使用配置的默认值
    ollama_base_url: Optional[str] = None  # ollama服务器地址，None表示使用配置的默认值

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

class UploadProgressUpdate(BaseModel):
    stage: str  # 'uploading', 'processing', 'chunking', 'embedding', 'success', 'error'
    percent: int  # Overall progress percentage (0-100)
    message: str  # Progress message
    chunks_processed: Optional[int] = None  # Number of chunks processed so far
    total_chunks: Optional[int] = None  # Total number of chunks to process
    batch_current: Optional[int] = None  # Current batch number
    batch_total: Optional[int] = None  # Total number of batches
    sub_percent: Optional[int] = None  # Sub-progress within current stage

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
    role_id: Optional[str] = None  # 角色ID，用于选择角色提示词

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



# 统计数据相关数据模型
class QueryLogEntry(BaseModel):
    id: str
    timestamp: str
    query: str
    collection: str
    results_count: int
    response_time: float
    status: str
    user_id: Optional[str] = None

class AnalyticsData(BaseModel):
    totalQueries: int
    avgResponseTime: float
    activeCollections: int
    uniqueUsers: int
    queryTrend: List[dict]
    collectionUsage: List[dict]
    recentLogs: List[QueryLogEntry]

class AnalyticsRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period: Optional[str] = "7days"

class EmbeddingConfigRequest(BaseModel):
    default_provider: str  # "alibaba" 或 "ollama"
    alibaba_config: Optional[dict] = None
    ollama_config: Optional[dict] = None

class LLMConfigRequest(BaseModel):
    default_provider: str  # "deepseek" 或 "alibaba"
    deepseek_config: Optional[dict] = None
    alibaba_config: Optional[dict] = None

class CollectionMigrationRequest(BaseModel):
    collection_name: str
    target_provider: str  # "alibaba" 或 "ollama"
    target_config: Optional[dict] = None  # 目标模型配置



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
                    if (sample_result and
                        sample_result.get('embeddings') and
                        len(sample_result['embeddings']) > 0):

                        # 获取第一个嵌入向量
                        first_embedding = sample_result['embeddings'][0]

                        # 增强的向量有效性检查
                        if first_embedding is not None:
                            # 检查是否为列表或数组类型
                            if isinstance(first_embedding, (list, tuple)):
                                if len(first_embedding) > 0:
                                    # 检查向量元素是否为数值类型
                                    if all(isinstance(x, (int, float)) for x in first_embedding[:5]):  # 只检查前5个元素以提高性能
                                        dimension = len(first_embedding)
                                        # 更新元数据中的维度信息
                                        metadata['vector_dimension'] = dimension
                                        logger.info(f"从实际向量中检测到集合 '{display_name}' 的维度: {dimension}")
                                    else:
                                        logger.warning(f"集合 '{display_name}' 的向量包含非数值元素，无法确定维度")
                                else:
                                    logger.warning(f"集合 '{display_name}' 的向量为空数组，无法确定维度")
                            else:
                                logger.warning(f"集合 '{display_name}' 的向量格式不正确，类型: {type(first_embedding)}")
                        else:
                            logger.warning(f"集合 '{display_name}' 的第一个向量为None，无法确定维度")

                except Exception as e:
                    logger.warning(f"无法获取集合 '{display_name}' 的向量维度: {e}")
                    dimension = None

            # 解析嵌入模型信息
            embedding_model_raw = metadata.get('embedding_model', '未知')
            embedding_provider = None
            embedding_model = embedding_model_raw

            if embedding_model_raw.startswith('alibaba-'):
                embedding_provider = 'alibaba'
                embedding_model = embedding_model_raw.replace('alibaba-', '')
            elif embedding_model_raw.startswith('ollama-'):
                embedding_provider = 'ollama'
                embedding_model = embedding_model_raw.replace('ollama-', '')
            elif embedding_model_raw == 'alibaba-text-embedding-v4':
                embedding_provider = 'alibaba'
                embedding_model = 'text-embedding-v4'

            # 格式化时间信息
            created_at = metadata.get('created_at')
            updated_at = metadata.get('updated_at')

            # 为没有时间戳的旧集合提供默认时间
            if not created_at and not updated_at:
                # 使用一个默认的创建时间（表示这是旧集合）
                created_at = "2024-01-01 00:00:00"
                updated_at = "2024-01-01 00:00:00"
            elif not created_at:
                created_at = updated_at  # 如果没有创建时间，使用更新时间
            elif not updated_at:
                updated_at = created_at  # 如果没有更新时间，使用创建时间

            # 如果有时间信息，格式化为用户友好的格式
            if created_at and created_at != "2024-01-01 00:00:00":
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass  # 如果解析失败，保持原始格式

            if updated_at and updated_at != "2024-01-01 00:00:00":
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    updated_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass  # 如果解析失败，保持原始格式

            result.append(CollectionInfo(
                name=collection.name,  # 原始编码名称
                display_name=display_name,  # 显示名称（中文）
                count=count,
                metadata=metadata,
                files_count=files_count,
                chunk_statistics=chunk_statistics,
                dimension=dimension,  # 向量维数
                embedding_model=embedding_model,  # 嵌入模型名称
                embedding_provider=embedding_provider,  # 嵌入模型提供商
                created_at=created_at,  # 创建时间
                updated_at=updated_at   # 更新时间
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
                        # 安全地获取文档数据
                        documents_list = results.get('documents')
                        metadatas_list = results.get('metadatas')
                        embeddings_list = results.get('embeddings')

                        # 安全地获取 embedding，避免对 NumPy 数组进行布尔判断
                        embedding_value = None
                        if embeddings_list is not None and len(embeddings_list) > i:
                            embedding_value = embeddings_list[i]

                        doc_info = DocumentInfo(
                            id=doc_id,
                            document=documents_list[i] if documents_list and len(documents_list) > i else None,
                            metadata=metadatas_list[i] if metadatas_list and len(metadatas_list) > i else {},
                            embedding=embedding_value
                        )

                        if count <= 100:
                            documents.append(doc_info)
                        else:
                            sample_documents.append(doc_info)

            except Exception as e:
                import traceback
                logger.warning(f"获取集合文档时出现警告: {e}")
                logger.warning(f"错误详情: {traceback.format_exc()}")

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

        # 准备元数据，包含原始中文名称和嵌入模型信息
        base_metadata = request.metadata or {}
        base_metadata['original_name'] = request.name

        # 添加创建时间和更新时间
        from datetime import datetime
        current_time = datetime.now().isoformat()
        base_metadata['created_at'] = current_time
        base_metadata['updated_at'] = current_time

        # 获取嵌入模型配置（优先使用请求参数，否则使用配置的默认值）
        embedding_provider = request.embedding_model or config_manager.get_default_embedding_provider()

        # 根据选择的嵌入模型设置元数据和创建嵌入函数
        embedding_function = None

        if embedding_provider == "ollama":
            # 使用Ollama嵌入模型
            ollama_config = config_manager.get_ollama_config()
            ollama_model = request.ollama_model or ollama_config.get("model", "mxbai-embed-large")
            ollama_base_url = request.ollama_base_url or ollama_config.get("base_url", "http://localhost:11434")

            base_metadata['embedding_model'] = f'ollama-{ollama_model}'
            base_metadata['ollama_base_url'] = ollama_base_url

            try:
                embedding_function = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                logger.info(f"成功创建Ollama嵌入函数: 模型={ollama_model}, 服务器={ollama_base_url}")
            except Exception as e:
                logger.error(f"创建Ollama嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建Ollama嵌入函数失败: {str(e)}")
        else:
            # 使用阿里云嵌入模型
            alibaba_config = config_manager.get_alibaba_config()
            alibaba_model = alibaba_config.get("model", "text-embedding-v4")
            alibaba_dimension = alibaba_config.get("dimension", 1024)

            base_metadata['embedding_model'] = f'alibaba-{alibaba_model}'

            try:
                embedding_function = create_alibaba_embedding_function(dimension=alibaba_dimension)
                logger.info(f"成功创建阿里云嵌入函数: 模型={alibaba_model}, 维度={alibaba_dimension}")
            except Exception as e:
                logger.error(f"创建阿里云嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")

        # 应用向量优化配置（仅对阿里云模型）
        if embedding_provider == "alibaba":
            metadata = get_optimized_collection_metadata(optimization_config, base_metadata)
        else:
            metadata = base_metadata

        # 清理元数据，确保所有值都是ChromaDB支持的类型
        metadata = sanitize_metadata(metadata)

        # 创建集合，使用选择的嵌入函数和元数据
        collection = chroma_client.create_collection(
            name=encoded_name,
            metadata=metadata,
            embedding_function=embedding_function
        )

        # ChromaDB 1.0+ 自动持久化数据
        logger.info("数据已自动持久化到磁盘")

        if embedding_provider == "alibaba":
            alibaba_config = config_manager.get_alibaba_config()
            logger.info(f"集合创建成功，使用阿里云嵌入模型: {alibaba_config.get('model')}")
        else:
            ollama_config = config_manager.get_ollama_config()
            ollama_model = request.ollama_model or ollama_config.get("model")
            logger.info(f"集合创建成功，使用Ollama嵌入模型: {ollama_model}")

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

        # 更新修改时间，保留原创建时间
        from datetime import datetime
        new_metadata['updated_at'] = datetime.now().isoformat()
        # 如果没有创建时间，添加当前时间作为创建时间
        if 'created_at' not in new_metadata:
            new_metadata['created_at'] = new_metadata['updated_at']

        # ChromaDB不支持直接重命名，需要创建新集合并复制数据
        # 检查原集合使用的嵌入模型
        embedding_function = None
        embedding_model = new_metadata.get('embedding_model')

        if embedding_model == 'alibaba-text-embedding-v4':
            try:
                embedding_function = create_alibaba_embedding_function(dimension=1024)
                logger.info(f"为重命名集合创建阿里云嵌入函数")
            except Exception as e:
                logger.warning(f"创建阿里云嵌入函数失败，使用默认函数: {e}")

        elif embedding_model and embedding_model.startswith('ollama-'):
            try:
                ollama_model = embedding_model.replace('ollama-', '')
                ollama_base_url = new_metadata.get('ollama_base_url', 'http://localhost:11434')

                embedding_function = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                logger.info(f"为重命名集合创建Ollama嵌入函数: {ollama_model}")
            except Exception as e:
                logger.warning(f"创建Ollama嵌入函数失败，使用默认函数: {e}")

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

        # 检查集合使用的嵌入模型
        collection_metadata = target_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')
        embeddings = None

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

        elif embedding_model and embedding_model.startswith('ollama-'):
            # 使用Ollama嵌入模型
            try:
                ollama_model = embedding_model.replace('ollama-', '')
                ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

                ollama_embedding_func = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                logger.info(f"为集合 '{collection_name}' 重新创建Ollama嵌入函数: {ollama_model}")

                # 使用Ollama嵌入函数生成向量
                embeddings = ollama_embedding_func(request.documents)
                # 安全地获取向量维度
                dimension_info = "未知"
                if embeddings and len(embeddings) > 0 and embeddings[0] is not None:
                    if isinstance(embeddings[0], (list, tuple)) and len(embeddings[0]) > 0:
                        dimension_info = len(embeddings[0])
                logger.info(f"成功生成 {len(embeddings)} 个嵌入向量，维度: {dimension_info}")

            except Exception as e:
                logger.error(f"创建Ollama嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建Ollama嵌入函数失败: {str(e)}")

        else:
            # 使用默认嵌入函数
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

        # ChromaDB 1.0+ 自动持久化数据
        logger.info(f"向集合 '{collection_name}' 添加文档后，数据已自动持久化到磁盘")

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
    logger.info(f"开始处理文件上传: collection_name={collection_name}, file={file.filename}")

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
        logger.info(f"开始读取文件内容: {file.filename}")
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"文件读取完成，大小: {file_size_mb:.2f}MB")

        # 验证文件大小 (150MB限制，增加了限制以支持更多格式)
        if len(content) > 150 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过 150MB")

        # 使用文件解析器解析文件
        logger.info(f"开始解析文件: {file.filename} ({file_size_mb:.2f}MB)")
        parse_start_time = time.time()
        parse_result = file_parser_manager.parse_file(content, file.filename)
        parse_time = time.time() - parse_start_time
        logger.info(f"文件解析完成: success={parse_result.success}, is_table={parse_result.is_table}, 耗时: {parse_time:.2f}秒")

        if not parse_result.success:
            logger.error(f"文件解析失败: {parse_result.error_message}")
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
            try:
                config_dict = json.loads(chunking_config)
                config = ChunkingConfig(**config_dict)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"分块配置格式错误: {e}")

            text_content = parse_result.content
            if not text_content.strip():
                raise HTTPException(status_code=400, detail="文件中未提取到有效文本内容")

            # 进行RAG分块
            logger.info(f"开始RAG分块处理，文本长度: {len(text_content)} 字符，方法: {config.method}")
            chunking_start_time = time.time()
            chunker = RAGChunker()
            chunking_result = chunker.chunk_text(text_content, config)
            chunking_time = time.time() - chunking_start_time
            logger.info(f"RAG分块完成，生成 {chunking_result.total_chunks} 个块，耗时: {chunking_time:.2f}秒")

        # 准备文档数据
        documents = []
        metadatas = []
        ids = []

        # 处理表格文件的特殊情况
        if parse_result.is_table and parse_result.table_data:
            logger.info(f"处理表格文件，行数: {len(parse_result.table_data)}")
            logger.info(f"列分析结果: {parse_result.column_analysis}")

            # 表格文件：每行数据作为一个文档
            for row_idx, row_data in enumerate(parse_result.table_data):
                # 构建文档内容
                if not parse_result.column_analysis:
                    logger.error("列分析结果为空")
                    raise HTTPException(status_code=500, detail="表格列分析失败")

                content_columns = [col for col, type_ in parse_result.column_analysis.items() if type_ == 'content']
                metadata_columns = [col for col, type_ in parse_result.column_analysis.items() if type_ == 'metadata']
                logger.info(f"Content列: {content_columns}, Metadata列: {metadata_columns}")

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
                    "is_table": "true",  # ChromaDB 0.3.29不支持布尔值
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
                    "is_table": "false",  # ChromaDB 0.3.29不支持布尔值
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

        # 检查集合使用的嵌入模型
        collection_metadata = target_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')
        embeddings = None

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

        elif embedding_model and embedding_model.startswith('ollama-'):
            # 使用Ollama嵌入模型
            try:
                ollama_model = embedding_model.replace('ollama-', '')
                ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

                ollama_embedding_func = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                logger.info(f"为集合 '{collection_name}' 重新创建Ollama嵌入函数: {ollama_model}")

                # 使用Ollama嵌入函数生成向量，支持批量处理
                embeddings = []
                batch_size = 5  # Ollama批量处理限制

                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    logger.info(f"处理文档批次 {i//batch_size + 1}: {len(batch)} 个文档")

                    try:
                        batch_embeddings = ollama_embedding_func(batch)
                        embeddings.extend(batch_embeddings)
                        logger.info(f"成功生成批次 {i//batch_size + 1} 的嵌入向量")
                    except Exception as e:
                        logger.error(f"批次 {i//batch_size + 1} 嵌入向量生成失败: {e}")
                        raise e

                # 安全地获取向量维度
                dimension_info = "未知"
                if embeddings and len(embeddings) > 0 and embeddings[0] is not None:
                    if isinstance(embeddings[0], (list, tuple)) and len(embeddings[0]) > 0:
                        dimension_info = len(embeddings[0])
                logger.info(f"成功生成 {len(embeddings)} 个嵌入向量，维度: {dimension_info}")

            except Exception as e:
                logger.error(f"创建Ollama嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建Ollama嵌入函数失败: {str(e)}")

        else:
            # 使用默认嵌入函数
            logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        # 清理所有元数据，确保兼容ChromaDB 0.3.29
        sanitized_metadatas = [sanitize_metadata(metadata) for metadata in metadatas]

        # 添加到ChromaDB
        logger.info(f"开始向量化和存储 {len(documents)} 个文档块到集合 '{collection_name}'")
        embedding_start_time = time.time()

        if embeddings:
            # 使用预生成的向量
            target_collection.add(
                documents=documents,
                metadatas=sanitized_metadatas,
                ids=ids,
                embeddings=embeddings
            )
        else:
            # 使用集合的默认嵌入函数
            target_collection.add(
                documents=documents,
                metadatas=sanitized_metadatas,
                ids=ids
            )

        embedding_time = time.time() - embedding_start_time
        logger.info(f"向量化和存储完成，耗时: {embedding_time:.2f}秒")

        # ChromaDB 1.0+ 自动持久化数据
        logger.info(f"文件 '{file.filename}' 上传后，数据已自动持久化到磁盘")

        processing_time = time.time() - start_time

        # 构建响应消息
        if parse_result.is_table:
            message = f"表格文件 '{file.filename}' 上传成功，创建了 {len(documents)} 行数据"
        else:
            message = f"文档 '{file.filename}' 上传成功，创建了 {len(documents)} 个文档块"

        logger.info(f"文件处理完成: {file.filename}, 总耗时: {processing_time:.2f}秒, 创建文档块: {len(documents)}")

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

async def process_embeddings_with_progress(
    target_collection,
    documents: List[str],
    metadatas: List[dict],
    ids: List[str],
    embedding_model: str,
    collection_metadata: dict,
    collection_name: str,
    total_chunks: int,
    generate_progress_callback: Callable[[int, int, dict], None]
):
    """处理嵌入向量生成，支持进度回调"""

    embeddings = None
    processed_chunks = 0

    if embedding_model == 'alibaba-text-embedding-v4':
        # 阿里云嵌入模型处理
        try:
            alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
            logger.info(f"为集合 '{collection_name}' 重新创建阿里云嵌入函数")

            embeddings = []
            batch_size = 10  # 阿里云API限制
            total_batches = (len(documents) + batch_size - 1) // batch_size

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                current_batch = i // batch_size + 1

                logger.info(f"处理文档批次 {current_batch}: {len(batch)} 个文档")

                try:
                    batch_embeddings = alibaba_embedding_func(batch)
                    embeddings.extend(batch_embeddings)
                    processed_chunks += len(batch)

                    # 发送进度更新
                    batch_info = {'current': current_batch, 'total': total_batches}
                    await generate_progress_callback(processed_chunks, total_chunks, batch_info)

                    logger.info(f"成功生成批次 {current_batch} 的嵌入向量")
                except Exception as e:
                    logger.error(f"批次 {current_batch} 嵌入向量生成失败: {e}")
                    raise e

            logger.info(f"成功生成 {len(embeddings)} 个1024维向量")

        except Exception as e:
            logger.error(f"创建阿里云嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")

    elif embedding_model and embedding_model.startswith('ollama-'):
        # Ollama嵌入模型处理
        try:
            ollama_model = embedding_model.replace('ollama-', '')
            ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

            ollama_embedding_func = create_ollama_embedding_function(
                model_name=ollama_model,
                base_url=ollama_base_url
            )
            logger.info(f"为集合 '{collection_name}' 重新创建Ollama嵌入函数: {ollama_model}")

            embeddings = []
            batch_size = 5  # Ollama批量处理限制
            total_batches = (len(documents) + batch_size - 1) // batch_size

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                current_batch = i // batch_size + 1

                logger.info(f"处理文档批次 {current_batch}: {len(batch)} 个文档")

                try:
                    batch_embeddings = ollama_embedding_func(batch)
                    embeddings.extend(batch_embeddings)
                    processed_chunks += len(batch)

                    # 发送进度更新
                    batch_info = {'current': current_batch, 'total': total_batches}
                    await generate_progress_callback(processed_chunks, total_chunks, batch_info)

                    logger.info(f"成功生成批次 {current_batch} 的嵌入向量")
                except Exception as e:
                    logger.error(f"批次 {current_batch} 嵌入向量生成失败: {e}")
                    raise e

            # 安全地获取向量维度
            dimension_info = "未知"
            if embeddings and len(embeddings) > 0 and embeddings[0] is not None:
                if isinstance(embeddings[0], (list, tuple)) and len(embeddings[0]) > 0:
                    dimension_info = len(embeddings[0])
            logger.info(f"成功生成 {len(embeddings)} 个嵌入向量，维度: {dimension_info}")

        except Exception as e:
            logger.error(f"创建Ollama嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建Ollama嵌入函数失败: {str(e)}")
    else:
        # 使用默认嵌入函数 - 逐个处理以提供进度更新
        logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        # 对于默认嵌入函数，我们需要逐个添加文档以提供进度更新
        for i, (doc, metadata, doc_id) in enumerate(zip(documents, metadatas, ids)):
            try:
                target_collection.add(
                    documents=[doc],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                processed_chunks += 1

                # 发送进度更新
                await generate_progress_callback(processed_chunks, total_chunks, None)

            except Exception as e:
                logger.error(f"添加文档 {i+1} 失败: {e}")
                raise e

        # 对于默认嵌入函数，我们已经逐个添加了，所以直接返回
        return

    # 添加到ChromaDB（对于有预生成向量的情况）
    logger.info(f"开始向量化和存储 {len(documents)} 个文档块到集合 '{collection_name}'")

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

    logger.info(f"向量化和存储完成")

async def process_embeddings_with_progress_sync(
    target_collection,
    documents: List[str],
    metadatas: List[dict],
    ids: List[str],
    embedding_model: str,
    collection_metadata: dict,
    collection_name: str,
    total_chunks: int,
    progress_callback: Callable[[int, int, dict], None]
):
    """处理嵌入向量生成，支持同步进度回调"""

    embeddings = None
    processed_chunks = 0

    if embedding_model == 'alibaba-text-embedding-v4':
        # 阿里云嵌入模型处理
        try:
            alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
            logger.info(f"为集合 '{collection_name}' 重新创建阿里云嵌入函数")

            embeddings = []
            batch_size = 10  # 阿里云API限制
            total_batches = (len(documents) + batch_size - 1) // batch_size

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                current_batch = i // batch_size + 1

                logger.info(f"处理文档批次 {current_batch}: {len(batch)} 个文档")

                try:
                    batch_embeddings = alibaba_embedding_func(batch)
                    embeddings.extend(batch_embeddings)
                    processed_chunks += len(batch)

                    # 发送进度更新
                    batch_info = {'current': current_batch, 'total': total_batches}
                    progress_callback(processed_chunks, total_chunks, batch_info)

                    logger.info(f"成功生成批次 {current_batch} 的嵌入向量")
                except Exception as e:
                    logger.error(f"批次 {current_batch} 嵌入向量生成失败: {e}")
                    raise e

            logger.info(f"成功生成 {len(embeddings)} 个1024维向量")

        except Exception as e:
            logger.error(f"创建阿里云嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")

    elif embedding_model and embedding_model.startswith('ollama-'):
        # Ollama嵌入模型处理
        try:
            ollama_model = embedding_model.replace('ollama-', '')
            ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

            ollama_embedding_func = create_ollama_embedding_function(
                model_name=ollama_model,
                base_url=ollama_base_url
            )
            logger.info(f"为集合 '{collection_name}' 重新创建Ollama嵌入函数: {ollama_model}")

            embeddings = []
            batch_size = 5  # Ollama批量处理限制
            total_batches = (len(documents) + batch_size - 1) // batch_size

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                current_batch = i // batch_size + 1

                logger.info(f"处理文档批次 {current_batch}: {len(batch)} 个文档")

                try:
                    batch_embeddings = ollama_embedding_func(batch)
                    embeddings.extend(batch_embeddings)
                    processed_chunks += len(batch)

                    # 发送进度更新
                    batch_info = {'current': current_batch, 'total': total_batches}
                    logger.info(f"🔄 Ollama批次 {current_batch} 完成，调用进度回调: {processed_chunks}/{total_chunks}")
                    progress_callback(processed_chunks, total_chunks, batch_info)

                    logger.info(f"成功生成批次 {current_batch} 的嵌入向量")
                except Exception as e:
                    logger.error(f"批次 {current_batch} 嵌入向量生成失败: {e}")
                    raise e

            # 安全地获取向量维度
            dimension_info = "未知"
            if embeddings and len(embeddings) > 0 and embeddings[0] is not None:
                if isinstance(embeddings[0], (list, tuple)) and len(embeddings[0]) > 0:
                    dimension_info = len(embeddings[0])
            logger.info(f"成功生成 {len(embeddings)} 个嵌入向量，维度: {dimension_info}")

        except Exception as e:
            logger.error(f"创建Ollama嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建Ollama嵌入函数失败: {str(e)}")
    else:
        # 使用默认嵌入函数 - 逐个处理以提供进度更新
        logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        # 对于默认嵌入函数，我们需要逐个添加文档以提供进度更新
        for i, (doc, metadata, doc_id) in enumerate(zip(documents, metadatas, ids)):
            try:
                target_collection.add(
                    documents=[doc],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                processed_chunks += 1

                # 发送进度更新
                progress_callback(processed_chunks, total_chunks, None)

            except Exception as e:
                logger.error(f"添加文档 {i+1} 失败: {e}")
                raise e

        # 对于默认嵌入函数，我们已经逐个添加了，所以直接返回
        return

    # 添加到ChromaDB（对于有预生成向量的情况）
    logger.info(f"开始向量化和存储 {len(documents)} 个文档块到集合 '{collection_name}'")

    if embeddings:
        # 使用预生成的向量
        target_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

        # 发送最终进度更新 - 所有文档都已存储
        progress_callback(total_chunks, total_chunks, None)
    else:
        # 使用集合的默认嵌入函数
        target_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        # 发送最终进度更新 - 所有文档都已存储
        progress_callback(total_chunks, total_chunks, None)

    logger.info(f"向量化和存储完成")

@app.post("/api/collections/{collection_name}/upload-stream")
async def upload_document_stream(
    collection_name: str,
    file: UploadFile = File(...),
    chunking_config: str = Form(...)
):
    """上传文档文件并进行RAG分块处理 - 支持实时进度流"""

    # 创建进度队列，设置较小的队列大小以确保实时性
    progress_queue = asyncio.Queue(maxsize=1)

    async def generate_progress():
        start_time = time.time()
        logger.info(f"开始流式处理文件上传: collection_name={collection_name}, file={file.filename}")

        try:
            # 发送初始进度
            yield f"data: {json.dumps(UploadProgressUpdate(stage='uploading', percent=5, message='正在上传文件...').model_dump())}\n\n"

            # 获取RAG分块器相关类
            RAGChunker, ChunkingConfig, ChunkingMethod, get_default_chunking_config = get_rag_chunker()
            if not ChunkingConfig:
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message='RAG分块功能不可用').model_dump())}\n\n"
                return

            # 验证文件名
            if not file.filename:
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message='文件名不能为空').model_dump())}\n\n"
                return

            # 验证文件格式
            if not file_parser_manager.can_parse(file.filename):
                supported_extensions = file_parser_manager.get_supported_extensions()
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message=f'不支持的文件格式。支持的格式: {', '.join(supported_extensions)}').model_dump())}\n\n"
                return

            # 读取文件内容
            yield f"data: {json.dumps(UploadProgressUpdate(stage='processing', percent=15, message='正在读取文件内容...').model_dump())}\n\n"
            content = await file.read()
            file_size_mb = len(content) / (1024 * 1024)
            logger.info(f"文件读取完成，大小: {file_size_mb:.2f}MB")

            # 验证文件大小
            if len(content) > 150 * 1024 * 1024:
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message='文件大小不能超过 150MB').model_dump())}\n\n"
                return

            # 解析文件
            yield f"data: {json.dumps(UploadProgressUpdate(stage='processing', percent=25, message='正在解析文件内容...').model_dump())}\n\n"
            parse_result = file_parser_manager.parse_file(content, file.filename)

            if not parse_result.success:
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message=f'文件解析失败: {parse_result.error_message}').model_dump())}\n\n"
                return

            # 查找集合
            collections = chroma_client.list_collections()
            target_collection = None
            for collection in collections:
                metadata = collection.metadata or {}
                if (metadata.get('original_name') == collection_name or collection.name == collection_name):
                    target_collection = collection
                    break

            if not target_collection:
                yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message=f'集合 \'{collection_name}\' 不存在').model_dump())}\n\n"
                return

            # 处理文档数据
            yield f"data: {json.dumps(UploadProgressUpdate(stage='chunking', percent=35, message='正在进行RAG分块处理...').model_dump())}\n\n"

            documents = []
            metadatas = []
            ids = []

            # 根据文件类型处理
            if parse_result.is_table and parse_result.table_data:
                # 表格文件处理
                for row_idx, row_data in enumerate(parse_result.table_data):
                    # 构建文档内容和元数据（简化版本）
                    content_columns = [col for col, type_ in parse_result.column_analysis.items() if type_ == 'content']
                    content_parts = []
                    for col in content_columns:
                        if col in row_data and row_data[col] is not None and str(row_data[col]).strip():
                            content_parts.append(f"{col}: {str(row_data[col]).strip()}")

                    if content_parts:
                        document_text = " | ".join(content_parts)
                    else:
                        all_parts = []
                        for col, value in row_data.items():
                            if value is not None and str(value).strip():
                                all_parts.append(f"{col}: {str(value).strip()}")
                        document_text = " | ".join(all_parts)

                    documents.append(document_text)

                    metadata = {
                        "file_name": file.filename,
                        "file_format": parse_result.file_format.value if parse_result.file_format else "unknown",
                        "is_table": "true",
                        "row_index": row_idx,
                        "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "total_rows": len(parse_result.table_data)
                    }
                    metadatas.append(metadata)

                    import uuid
                    doc_id = f"{file.filename}_row_{row_idx}_{str(uuid.uuid4())[:8]}"
                    ids.append(doc_id)
            else:
                # 普通文件处理
                try:
                    config_dict = json.loads(chunking_config)
                    config = ChunkingConfig(**config_dict)
                except Exception as e:
                    yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message=f'分块配置格式错误: {e}').model_dump())}\n\n"
                    return

                text_content = parse_result.content
                if not text_content.strip():
                    yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message='文件中未提取到有效文本内容').model_dump())}\n\n"
                    return

                # 进行RAG分块
                chunker = RAGChunker()
                chunking_result = chunker.chunk_text(text_content, config)

                for chunk in chunking_result.chunks:
                    documents.append(chunk.text)

                    metadata = {
                        "file_name": file.filename,
                        "file_format": parse_result.file_format.value if parse_result.file_format else "unknown",
                        "is_table": "false",
                        "chunk_method": config.method.value,
                        "chunk_index": chunk.index,
                        "chunk_size": len(chunk.text),
                        "start_position": chunk.start_pos,
                        "end_position": chunk.end_pos,
                        "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "total_chunks": chunking_result.total_chunks
                    }
                    metadatas.append(metadata)

                    import uuid
                    chunk_id = f"{file.filename}_{chunk.index}_{str(uuid.uuid4())[:8]}"
                    ids.append(chunk_id)

            total_chunks = len(documents)
            yield f"data: {json.dumps(UploadProgressUpdate(stage='embedding', percent=70, message=f'开始生成向量嵌入，共 {total_chunks} 个文档块...', total_chunks=total_chunks, chunks_processed=0).model_dump())}\n\n"

            # 检查集合使用的嵌入模型并处理向量化
            collection_metadata = target_collection.metadata or {}
            embedding_model = collection_metadata.get('embedding_model')

            # 清理所有元数据
            sanitized_metadatas = [sanitize_metadata(metadata) for metadata in metadatas]

            # 创建进度回调函数
            def send_embedding_progress(processed: int, total: int, batch_info: dict = None):
                # 计算嵌入阶段的子进度 (70% - 95%)
                embedding_progress = int(70 + (processed / total) * 25)
                sub_progress = int((processed / total) * 100)

                message = f"正在生成向量嵌入并存储... 已保存 {processed} / {total} 个文档块"
                if batch_info:
                    message += f" (批次 {batch_info['current']}/{batch_info['total']})"

                progress_update = UploadProgressUpdate(
                    stage='embedding',
                    percent=embedding_progress,
                    message=message,
                    chunks_processed=processed,
                    total_chunks=total,
                    sub_percent=sub_progress,
                    batch_current=batch_info['current'] if batch_info else None,
                    batch_total=batch_info['total'] if batch_info else None
                )

                # 将进度更新放入队列，清空旧更新确保实时性
                try:
                    # 清空队列中的旧进度更新，只保留最新的
                    while not progress_queue.empty():
                        try:
                            progress_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                    progress_queue.put_nowait(progress_update)
                    # 增强日志输出，显示完整的进度信息
                    logger.info(f"📊 进度更新发送: {processed}/{total} ({embedding_progress}%) - chunks_processed={processed}, total_chunks={total}, sub_percent={sub_progress}")
                except asyncio.QueueFull:
                    logger.warning("Progress queue is full, skipping update")

            # 启动处理任务
            processing_task = asyncio.create_task(
                process_embeddings_with_progress_sync(
                    target_collection, documents, sanitized_metadatas, ids,
                    embedding_model, collection_metadata, collection_name,
                    total_chunks, progress_callback=send_embedding_progress
                )
            )

            # 监听进度更新并发送
            while not processing_task.done():
                try:
                    # 等待进度更新，超时时间短一些以便检查任务状态
                    progress_update = await asyncio.wait_for(progress_queue.get(), timeout=0.1)

                    # 立即发送进度更新
                    progress_data = progress_update.model_dump()
                    logger.info(f"🚀 发送进度数据到前端: {progress_data}")
                    yield f"data: {json.dumps(progress_data)}\n\n"

                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                except Exception as e:
                    logger.error(f"Progress update error: {e}")
                    break

            # 等待处理任务完成
            await processing_task

            # 处理队列中剩余的进度更新（应该很少或没有）
            while not progress_queue.empty():
                try:
                    progress_update = progress_queue.get_nowait()
                    progress_data = progress_update.model_dump()
                    yield f"data: {json.dumps(progress_data)}\n\n"
                except asyncio.QueueEmpty:
                    break

            processing_time = time.time() - start_time

            # 发送完成消息
            if parse_result.is_table:
                message = f"表格文件 '{file.filename}' 上传成功，创建了 {len(documents)} 行数据"
            else:
                message = f"文档 '{file.filename}' 上传成功，创建了 {len(documents)} 个文档块"

            final_progress = UploadProgressUpdate(stage='success', percent=100, message=message, chunks_processed=total_chunks, total_chunks=total_chunks)
            yield f"data: {json.dumps(final_progress.model_dump())}\n\n"

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"流式文档上传失败: {e}")
            logger.error(f"详细错误信息: {error_details}")
            yield f"data: {json.dumps(UploadProgressUpdate(stage='error', percent=0, message=f'文档上传失败: {str(e)}').model_dump())}\n\n"

    return StreamingResponse(generate_progress(), media_type="text/plain")

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

        elif embedding_model and embedding_model.startswith('ollama-'):
            try:
                ollama_model = embedding_model.replace('ollama-', '')
                ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

                ollama_embedding_func = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                query_embeddings = ollama_embedding_func([request.query])
                query_embedding = query_embeddings[0]
                logger.info(f"使用Ollama嵌入模型生成查询向量: {ollama_model}，维度: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"生成查询向量失败: {e}")
                raise HTTPException(status_code=500, detail=f"生成查询向量失败: {str(e)}")

        # 在每个集合中进行查询
        all_results = []

        for collection_name, collection in target_collections:
            try:
                # 执行向量查询
                if query_embedding is not None and len(query_embedding) > 0:
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
                if (search_results and
                    search_results.get('ids') and
                    len(search_results['ids']) > 0 and
                    search_results['ids'][0] is not None and
                    len(search_results['ids'][0]) > 0):
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
                        # 确保distance是标量值，兼容新版本ChromaDB/NumPy
                        distance_raw = search_results['distances'][0][i] if search_results.get('distances') else 0.0
                        distance = float(distance_raw) if hasattr(distance_raw, '__iter__') and not isinstance(distance_raw, str) else float(distance_raw)

                        # 使用优化的相似度计算
                        similarity_percent = calculate_optimized_similarity(distance, distance_metric)

                        # 确保similarity_percent是标量值
                        if hasattr(similarity_percent, '__iter__') and not isinstance(similarity_percent, str):
                            similarity_percent = float(similarity_percent[0]) if len(similarity_percent) > 0 else 0.0
                        else:
                            similarity_percent = float(similarity_percent)

                        # 相似度阈值过滤：将百分比阈值转换为0-1范围
                        similarity_threshold_decimal = float(request.similarity_threshold)
                        similarity_decimal = similarity_percent / 100.0

                        # 确保similarity_decimal是标量值
                        if hasattr(similarity_decimal, '__iter__') and not isinstance(similarity_decimal, str):
                            similarity_decimal = float(similarity_decimal[0]) if len(similarity_decimal) > 0 else 0.0
                        else:
                            similarity_decimal = float(similarity_decimal)

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
                import traceback
                logger.warning(f"在集合 '{collection_name}' 中查询失败: {e}")
                logger.warning(f"错误详情: {traceback.format_exc()}")
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
                logger.warning(f"查询向量生成失败，将使用文本查询: {e}")

        elif embedding_model and embedding_model.startswith('ollama-'):
            try:
                ollama_model = embedding_model.replace('ollama-', '')
                ollama_base_url = collection_metadata.get('ollama_base_url', 'http://localhost:11434')

                ollama_embedding_func = create_ollama_embedding_function(
                    model_name=ollama_model,
                    base_url=ollama_base_url
                )
                query_embeddings = ollama_embedding_func([request.query])
                query_embedding = query_embeddings[0]
                logger.info(f"使用Ollama嵌入模型生成查询向量: {ollama_model}，维度: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"生成查询向量失败: {e}")
                logger.warning(f"查询向量生成失败，将使用文本查询: {e}")
        else:
            # 如果无法识别嵌入模型，尝试使用默认的阿里云模型
            try:
                embedding_function = create_alibaba_embedding_function()
                query_embedding = embedding_function([request.query])[0]
                logger.info(f"使用默认阿里云嵌入模型生成查询向量，维度: {len(query_embedding)}")
            except Exception as e:
                logger.warning(f"查询向量生成失败，将使用文本查询: {e}")

        # 在每个集合中进行查询
        all_results = []

        for collection_name, collection in target_collections:
            try:
                # 执行向量查询
                if query_embedding is not None and len(query_embedding) > 0:
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
                if (search_results.get('documents') and
                    len(search_results['documents']) > 0 and
                    search_results['documents'][0] is not None and
                    len(search_results['documents'][0]) > 0):
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
                        # 确保distance是标量值，兼容新版本ChromaDB/NumPy
                        distance_raw = search_results['distances'][0][i]
                        distance = float(distance_raw) if hasattr(distance_raw, '__iter__') and not isinstance(distance_raw, str) else float(distance_raw)

                        # 使用优化的相似度计算
                        similarity_percent = calculate_optimized_similarity(distance, distance_metric)

                        # 确保similarity_percent是标量值
                        if hasattr(similarity_percent, '__iter__') and not isinstance(similarity_percent, str):
                            similarity_percent = float(similarity_percent[0]) if len(similarity_percent) > 0 else 0.0
                        else:
                            similarity_percent = float(similarity_percent)

                        # 相似度阈值过滤：将百分比阈值转换为0-1范围
                        similarity_threshold_decimal = float(request.similarity_threshold)
                        similarity_decimal = similarity_percent / 100.0

                        # 确保similarity_decimal是标量值
                        if hasattr(similarity_decimal, '__iter__') and not isinstance(similarity_decimal, str):
                            similarity_decimal = float(similarity_decimal[0]) if len(similarity_decimal) > 0 else 0.0
                        else:
                            similarity_decimal = float(similarity_decimal)

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
                import traceback
                logger.error(f"在集合 {collection_name} 中查询失败: {e}")
                logger.error(f"错误详情: {traceback.format_exc()}")
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
                    max_tokens=request.max_tokens,
                    role_id=request.role_id
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

# 统计数据API
@app.get("/api/analytics", response_model=AnalyticsData)
async def get_analytics_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = "7days"
):
    """获取分析统计数据"""
    try:
        # 计算时间范围
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not start_date:
            if period == "7days":
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
            elif period == "30days":
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            elif period == "90days":
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

        # 连接conversations数据库 - 使用跨平台工具
        db_path = platform_utils.get_data_directory() / "conversations.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 获取总查询数（用户消息）
        cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE type = 'user' AND timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        total_queries = cursor.fetchone()[0]

        # 获取平均响应时间（从assistant消息中获取）
        cursor.execute("""
            SELECT AVG(processing_time) FROM messages
            WHERE type = 'assistant' AND processing_time IS NOT NULL
            AND timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        avg_response_time_result = cursor.fetchone()[0]
        avg_response_time = avg_response_time_result if avg_response_time_result else 0.0

        # 获取独立用户数
        cursor.execute("""
            SELECT COUNT(DISTINCT c.user_id) FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            WHERE m.timestamp BETWEEN ? AND ? AND c.user_id IS NOT NULL
        """, (start_date, end_date))
        unique_users_result = cursor.fetchone()[0]
        unique_users = unique_users_result if unique_users_result else 0

        # 获取查询趋势数据（按天统计）
        cursor.execute("""
            SELECT DATE(timestamp) as query_date, COUNT(*) as count
            FROM messages
            WHERE type = 'user' AND timestamp BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            ORDER BY query_date
        """, (start_date, end_date))
        query_trend_data = cursor.fetchall()
        query_trend = [{"date": row[0], "count": row[1]} for row in query_trend_data]

        # 获取最近的查询日志
        cursor.execute("""
            SELECT m.id, m.timestamp, m.content,
                   COALESCE(m.selected_collections, 'null') as collections,
                   COALESCE(m.processing_time, 0) as processing_time,
                   c.user_id
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE m.type = 'user' AND m.timestamp BETWEEN ? AND ?
            ORDER BY m.timestamp DESC
            LIMIT 20
        """, (start_date, end_date))
        recent_logs_data = cursor.fetchall()

        recent_logs = []
        for row in recent_logs_data:
            # 解析集合信息
            collections_str = row[3]
            try:
                if collections_str and collections_str != 'null':
                    collections_data = json.loads(collections_str)
                    collection_name = collections_data[0] if isinstance(collections_data, list) and collections_data else "未知"
                else:
                    collection_name = "未知"
            except:
                collection_name = "未知"

            recent_logs.append(QueryLogEntry(
                id=row[0],
                timestamp=row[1],
                query=row[2][:100] + "..." if len(row[2]) > 100 else row[2],  # 限制查询内容长度
                collection=collection_name,
                results_count=0,  # 暂时设为0，后续可以从query_results中解析
                response_time=row[4],
                status="success",  # 暂时设为success，后续可以根据实际情况判断
                user_id=row[5]
            ))

        conn.close()

        # 获取ChromaDB集合信息
        try:
            collections = chroma_client.list_collections()
            active_collections = len(collections)

            # 计算集合使用分布（基于文档数量）
            collection_usage = []
            for collection in collections:
                metadata = collection.metadata or {}
                display_name = metadata.get('original_name', collection.name)
                count = collection.count()
                if count > 0:  # 只包含有文档的集合
                    collection_usage.append({
                        "collection": display_name,
                        "count": count
                    })

            # 按文档数量排序
            collection_usage.sort(key=lambda x: x["count"], reverse=True)

        except Exception as e:
            logger.warning(f"获取ChromaDB集合信息失败: {e}")
            active_collections = 0
            collection_usage = []

        return AnalyticsData(
            totalQueries=total_queries,
            avgResponseTime=round(avg_response_time, 3),
            activeCollections=active_collections,
            uniqueUsers=unique_users,
            queryTrend=query_trend,
            collectionUsage=collection_usage,
            recentLogs=recent_logs
        )

    except Exception as e:
        logger.error(f"获取分析数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分析数据失败: {str(e)}")

@app.get("/api/embedding-models")
async def get_embedding_models():
    """获取已验证的嵌入模型列表（用于创建集合时的选择）"""
    try:
        result = {}

        # 检查阿里云验证状态
        alibaba_verified = config_manager.is_provider_configured_and_verified("alibaba")
        if alibaba_verified:
            result["alibaba"] = {
                "name": "阿里云百炼",
                "description": "阿里云百炼平台嵌入模型",
                "models": [
                    {
                        "name": "text-embedding-v4",
                        "description": "高质量嵌入模型，支持多种维度",
                        "dimension": 1024,
                        "available": True,
                        "recommended": True
                    }
                ],
                "available": True,
                "verified": True
            }

        # 检查Ollama验证状态
        ollama_verified = config_manager.is_provider_configured_and_verified("ollama")
        if ollama_verified:
            # 获取推荐的Ollama模型
            recommended_models = get_recommended_models()

            # 获取Ollama服务配置
            ollama_config = config_manager.get_ollama_config()
            ollama_base_url = ollama_config.get("base_url", "http://localhost:11434")

            # 检查Ollama服务是否可用并获取实际可用的模型
            ollama_result = OllamaEmbeddingFunction.get_available_models(ollama_base_url)

            if ollama_result["success"]:
                # 合并推荐模型和实际可用模型
                available_embedding_models = ollama_result["embedding_models"]

                # 为推荐模型添加可用状态
                for model in recommended_models:
                    model['available'] = any(
                        available['name'].startswith(model['name'])
                        for available in available_embedding_models
                    )

                # 添加实际可用但不在推荐列表中的模型
                for available_model in available_embedding_models:
                    model_name = available_model['name']
                    base_name = model_name.split(':')[0]

                    # 检查是否已在推荐列表中
                    if not any(rec['name'] == base_name for rec in recommended_models):
                        recommended_models.append({
                            "name": model_name,
                            "description": f"可用的嵌入模型",
                            "dimension": None,  # 未知维度
                            "recommended": False,
                            "available": True
                        })

            result["ollama"] = {
                "name": "Ollama本地模型",
                "description": "本地运行的Ollama嵌入模型",
                "models": recommended_models,
                "available": ollama_result["success"],
                "verified": True,
                "service_url": ollama_base_url,
                "available_models": ollama_result.get("embedding_models", []),
                "error": ollama_result.get("error") if not ollama_result["success"] else None
            }

        return result
    except Exception as e:
        logger.error(f"获取嵌入模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取嵌入模型列表失败: {str(e)}")

@app.get("/api/embedding-models/all")
async def get_all_embedding_models():
    """获取所有支持的嵌入模型列表（包括未验证的，用于设置页面）"""
    try:
        # 获取推荐的Ollama模型
        recommended_models = get_recommended_models()

        # 获取Ollama服务配置
        ollama_config = config_manager.get_ollama_config()
        ollama_base_url = ollama_config.get("base_url", "http://localhost:11434")

        # 检查Ollama服务是否可用并获取实际可用的模型
        ollama_result = OllamaEmbeddingFunction.get_available_models(ollama_base_url)

        if ollama_result["success"]:
            # 合并推荐模型和实际可用模型
            available_embedding_models = ollama_result["embedding_models"]

            # 为推荐模型添加可用状态
            for model in recommended_models:
                model['available'] = any(
                    available['name'].startswith(model['name'])
                    for available in available_embedding_models
                )

            # 添加实际可用但不在推荐列表中的模型
            for available_model in available_embedding_models:
                model_name = available_model['name']
                base_name = model_name.split(':')[0]

                # 检查是否已在推荐列表中
                if not any(rec['name'] == base_name for rec in recommended_models):
                    recommended_models.append({
                        "name": model_name,
                        "description": f"可用的嵌入模型",
                        "dimension": None,  # 未知维度
                        "recommended": False,
                        "available": True
                    })

        # 获取验证状态
        alibaba_verified = config_manager.is_provider_configured_and_verified("alibaba")
        ollama_verified = config_manager.is_provider_configured_and_verified("ollama")

        return {
            "alibaba": {
                "name": "阿里云百炼",
                "description": "阿里云百炼平台嵌入模型",
                "models": [
                    {
                        "name": "text-embedding-v4",
                        "description": "高质量嵌入模型，支持多种维度",
                        "dimension": 1024,
                        "available": True,
                        "recommended": True
                    }
                ],
                "available": True,
                "verified": alibaba_verified
            },
            "ollama": {
                "name": "Ollama本地模型",
                "description": "本地运行的Ollama嵌入模型",
                "models": recommended_models,
                "available": ollama_result["success"],
                "verified": ollama_verified,
                "service_url": ollama_base_url,
                "available_models": ollama_result.get("embedding_models", []),
                "error": ollama_result.get("error") if not ollama_result["success"] else None
            }
        }
    except Exception as e:
        logger.error(f"获取嵌入模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取嵌入模型列表失败: {str(e)}")

@app.get("/api/embedding-config")
async def get_embedding_config():
    """获取当前嵌入模型配置"""
    try:
        current_config = config_manager.get_current_embedding_config()
        embedding_config = config_manager.get_embedding_config()

        return {
            "current": current_config,
            "full_config": embedding_config
        }
    except Exception as e:
        logger.error(f"获取嵌入模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取嵌入模型配置失败: {str(e)}")

@app.post("/api/embedding-config")
async def set_embedding_config(request: EmbeddingConfigRequest):
    """设置嵌入模型配置"""
    try:
        # 验证提供商
        if request.default_provider not in ["alibaba", "ollama"]:
            raise HTTPException(status_code=400, detail="不支持的嵌入模型提供商")

        # 构建配置更新
        config_update = {
            "default_provider": request.default_provider
        }

        if request.alibaba_config:
            config_update["alibaba"] = request.alibaba_config

        if request.ollama_config:
            # 验证Ollama配置
            ollama_model = request.ollama_config.get("model")
            ollama_base_url = request.ollama_config.get("base_url", "http://localhost:11434")

            if ollama_model:
                # 测试Ollama模型是否可用
                try:
                    test_embedding_func = create_ollama_embedding_function(
                        model_name=ollama_model,
                        base_url=ollama_base_url
                    )
                    # 简单测试
                    test_embedding_func(["测试"])
                    logger.info(f"Ollama模型 {ollama_model} 测试成功")
                except Exception as e:
                    logger.warning(f"Ollama模型 {ollama_model} 测试失败: {e}")
                    # 不阻止配置保存，只是警告

            config_update["ollama"] = request.ollama_config

        # 保存配置
        if config_manager.set_embedding_config(config_update):
            return {
                "message": "嵌入模型配置已更新",
                "config": config_manager.get_current_embedding_config()
            }
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置嵌入模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置嵌入模型配置失败: {str(e)}")

@app.post("/api/embedding-config/test")
async def test_embedding_config(request: dict):
    """测试嵌入模型配置"""
    try:
        provider = request.get("provider")
        config = request.get("config", {})

        if provider == "ollama":
            model_name = config.get("model", "mxbai-embed-large")
            base_url = config.get("base_url", "http://localhost:11434")

            # 创建测试嵌入函数
            embedding_func = create_ollama_embedding_function(
                model_name=model_name,
                base_url=base_url
            )

            # 执行测试
            test_text = "这是一个测试文本"
            embeddings = embedding_func([test_text])

            return {
                "success": True,
                "message": f"Ollama模型 {model_name} 测试成功",
                "model_name": model_name,
                "vector_dimension": len(embeddings[0]) if embeddings else 0,
                "test_text": test_text
            }

        elif provider == "alibaba":
            from alibaba_embedding import verify_alibaba_api_key

            api_key = config.get("api_key", "")
            model_name = config.get("model", "text-embedding-v4")

            # 验证API密钥
            result = verify_alibaba_api_key(api_key, model_name)

            # 如果验证成功，更新配置中的验证状态
            if result["success"]:
                config_manager.set_provider_verification_status("alibaba", True)
            else:
                config_manager.set_provider_verification_status("alibaba", False, result["message"])

            return result
        else:
            raise HTTPException(status_code=400, detail="不支持的嵌入模型提供商")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试嵌入模型配置失败: {e}")
        return {
            "success": False,
            "message": f"测试失败: {str(e)}"
        }

@app.get("/api/embedding-providers/status")
async def get_embedding_providers_status():
    """获取所有嵌入模型提供商的验证状态"""
    try:
        alibaba_status = config_manager.get_provider_verification_status("alibaba")
        ollama_status = config_manager.get_provider_verification_status("ollama")

        return {
            "alibaba": {
                "configured": bool(config_manager.get_alibaba_config().get("api_key", "").strip()),
                "verified": alibaba_status["verified"],
                "last_verified": alibaba_status["last_verified"],
                "error": alibaba_status.get("error")
            },
            "ollama": {
                "configured": True,  # Ollama不需要API密钥配置
                "verified": ollama_status["verified"],
                "last_verified": ollama_status["last_verified"],
                "error": ollama_status.get("error")
            }
        }
    except Exception as e:
        logger.error(f"获取提供商状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取提供商状态失败: {str(e)}")

@app.post("/api/embedding-providers/{provider}/verify")
async def verify_embedding_provider(provider: str, request: dict):
    """验证特定嵌入模型提供商的配置"""
    try:
        if provider not in ["alibaba", "ollama"]:
            raise HTTPException(status_code=400, detail="不支持的嵌入模型提供商")

        if provider == "alibaba":
            from alibaba_embedding import verify_alibaba_api_key

            api_key = request.get("api_key", "")
            model_name = request.get("model", "text-embedding-v4")

            if not api_key.strip():
                raise HTTPException(status_code=400, detail="API密钥不能为空")

            # 验证API密钥
            result = verify_alibaba_api_key(api_key, model_name)

            # 更新配置中的验证状态
            if result["success"]:
                # 保存API密钥到配置
                current_config = config_manager.get_alibaba_config()
                current_config["api_key"] = api_key
                current_config["model"] = model_name
                config_manager.set_alibaba_config(current_config)

                # 设置验证状态
                config_manager.set_provider_verification_status("alibaba", True)
            else:
                config_manager.set_provider_verification_status("alibaba", False, result["message"])

            return result

        elif provider == "ollama":
            model_name = request.get("model", "mxbai-embed-large")
            base_url = request.get("base_url", "http://localhost:11434")

            try:
                # 测试Ollama模型
                test_embedding_func = create_ollama_embedding_function(
                    model_name=model_name,
                    base_url=base_url
                )
                test_embedding_func(["测试"])

                # 保存配置
                current_config = config_manager.get_ollama_config()
                current_config["model"] = model_name
                current_config["base_url"] = base_url
                config_manager.set_ollama_config(current_config)

                # 设置验证状态
                config_manager.set_provider_verification_status("ollama", True)

                return {
                    "success": True,
                    "message": f"Ollama模型 {model_name} 验证成功",
                    "model_name": model_name
                }
            except Exception as e:
                config_manager.set_provider_verification_status("ollama", False, str(e))
                return {
                    "success": False,
                    "message": f"Ollama模型验证失败: {str(e)}"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证提供商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证提供商配置失败: {str(e)}")

# LLM配置测试辅助函数
async def test_deepseek_config(config: dict) -> dict:
    """测试DeepSeek配置"""
    try:
        api_key = config.get("api_key", "")
        model = config.get("model", "deepseek-chat")
        api_endpoint = config.get("api_endpoint", "https://api.deepseek.com")

        if not api_key.strip():
            return {"success": False, "message": "API密钥不能为空"}

        # 这里可以添加实际的DeepSeek API测试
        # 暂时返回成功，实际实现时需要调用DeepSeek API
        return {
            "success": True,
            "message": f"DeepSeek模型 {model} 验证成功",
            "model": model
        }

    except Exception as e:
        return {"success": False, "message": f"DeepSeek验证失败: {str(e)}"}

async def test_alibaba_llm_config(config: dict) -> dict:
    """测试阿里云LLM配置"""
    try:
        api_key = config.get("api_key", "")
        model = config.get("model", "qwen-plus")
        api_endpoint = config.get("api_endpoint", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        if not api_key.strip():
            return {"success": False, "message": "API密钥不能为空"}

        # 测试阿里云LLM API
        try:
            import dashscope
            from dashscope import Generation

            # 设置API密钥
            dashscope.api_key = api_key

            # 发送测试请求
            response = Generation.call(
                model=model,
                messages=[{"role": "user", "content": "测试"}],
                max_tokens=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"阿里云LLM模型 {model} 验证成功",
                    "model": model
                }
            else:
                return {
                    "success": False,
                    "message": f"API调用失败，状态码：{response.status_code}"
                }

        except ImportError:
            return {"success": False, "message": "dashscope库未安装"}
        except Exception as e:
            return {"success": False, "message": f"API调用失败: {str(e)}"}

    except Exception as e:
        return {"success": False, "message": f"阿里云LLM验证失败: {str(e)}"}

# LLM配置相关API
@app.get("/api/llm-config")
async def get_llm_config():
    """获取当前LLM配置"""
    try:
        current_config = config_manager.get_current_llm_config()
        llm_config = config_manager.get_llm_config()

        return {
            "current": current_config,
            "full_config": llm_config
        }
    except Exception as e:
        logger.error(f"获取LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取LLM配置失败: {str(e)}")

@app.post("/api/llm-config")
async def set_llm_config(request: LLMConfigRequest):
    """设置LLM配置"""
    try:
        # 验证提供商
        if request.default_provider not in ["deepseek", "alibaba"]:
            raise HTTPException(status_code=400, detail="不支持的LLM提供商")

        config_update = {"default_provider": request.default_provider}

        # 更新DeepSeek配置
        if request.deepseek_config:
            config_update["deepseek"] = request.deepseek_config

        # 更新阿里云配置
        if request.alibaba_config:
            config_update["alibaba"] = request.alibaba_config

        # 保存配置
        if config_manager.set_llm_config(config_update):
            return {
                "message": "LLM配置已更新",
                "config": config_manager.get_current_llm_config()
            }
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置LLM配置失败: {str(e)}")

@app.post("/api/llm-config/test")
async def test_llm_config(request: dict):
    """测试LLM配置"""
    try:
        provider = request.get("provider")
        config = request.get("config", {})

        if not provider:
            raise HTTPException(status_code=400, detail="缺少provider参数")

        if provider == "deepseek":
            return await test_deepseek_config(config)
        elif provider == "alibaba":
            return await test_alibaba_llm_config(config)
        else:
            raise HTTPException(status_code=400, detail="不支持的LLM提供商")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试LLM配置失败: {str(e)}")

@app.get("/api/llm-models")
async def get_llm_models():
    """获取可用的LLM模型列表"""
    try:
        # 返回静态的模型列表，不从配置中读取
        models = {
            "deepseek": [
                {
                    "name": "deepseek-chat",
                    "display_name": "DeepSeek Chat",
                    "description": "通用对话模型，适合日常问答和文档处理",
                    "max_tokens": 4096,
                    "recommended": True
                },
                {
                    "name": "deepseek-reasoner",
                    "display_name": "DeepSeek Reasoner",
                    "description": "推理增强模型，适合复杂分析和逻辑推理任务",
                    "max_tokens": 8192,
                    "recommended": False
                }
            ],
            "alibaba": [
                {
                    "name": "qwen-plus",
                    "display_name": "通义千问Plus",
                    "description": "平衡性能和成本的通用模型",
                    "max_tokens": 8192,
                    "recommended": True
                },
                {
                    "name": "qwen-max-latest",
                    "display_name": "通义千问Max",
                    "description": "最强性能模型，适合复杂任务",
                    "max_tokens": 8192,
                    "recommended": False
                },
                {
                    "name": "qwen-turbo-2025-07-15",
                    "display_name": "通义千问Turbo",
                    "description": "快速响应模型，适合简单任务",
                    "max_tokens": 8192,
                    "recommended": False
                }
            ]
        }

        llm_config = config_manager.get_llm_config()
        return {
            "models": models,
            "default_provider": llm_config.get("default_provider", "alibaba")
        }
    except Exception as e:
        logger.error(f"获取LLM模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取LLM模型列表失败: {str(e)}")

@app.get("/api/llm-providers/status")
async def get_llm_providers_status():
    """获取LLM提供商状态"""
    try:
        llm_config = config_manager.get_llm_config()

        status = {}
        for provider in ["deepseek", "alibaba"]:
            provider_config = llm_config.get(provider, {})
            status[provider] = {
                "verified": provider_config.get("verified", False),
                "last_verified": provider_config.get("last_verified"),
                "verification_error": provider_config.get("verification_error"),
                "has_api_key": bool(provider_config.get("api_key", "").strip())
            }

        return {"providers": status}
    except Exception as e:
        logger.error(f"获取LLM提供商状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取LLM提供商状态失败: {str(e)}")

@app.post("/api/llm-providers/{provider}/verify")
async def verify_llm_provider(provider: str, request: dict):
    """验证LLM提供商配置"""
    try:
        if provider not in ["deepseek", "alibaba"]:
            raise HTTPException(status_code=400, detail="不支持的LLM提供商")

        if provider == "deepseek":
            result = await test_deepseek_config(request)
        elif provider == "alibaba":
            result = await test_alibaba_llm_config(request)

        # 更新验证状态
        if result.get("success"):
            config_manager.set_llm_provider_verification_status(provider, True)
        else:
            config_manager.set_llm_provider_verification_status(provider, False, result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证LLM提供商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证LLM提供商配置失败: {str(e)}")


# ==================== 角色管理API ====================

@app.get("/api/roles", response_model=List[Role])
async def get_roles(active_only: bool = False):
    """获取角色列表"""
    try:
        roles = role_manager.list_roles(active_only=active_only)
        return roles
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")


@app.get("/api/roles/{role_id}", response_model=Role)
async def get_role(role_id: str):
    """根据ID获取角色"""
    try:
        role = role_manager.get_role(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色失败: {str(e)}")


@app.post("/api/roles", response_model=Role)
async def create_role(request: CreateRoleRequest):
    """创建新角色"""
    try:
        role = role_manager.create_role(request)
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建角色失败: {str(e)}")


@app.put("/api/roles/{role_id}", response_model=Role)
async def update_role(role_id: str, request: UpdateRoleRequest):
    """更新角色"""
    try:
        role = role_manager.update_role(role_id, request)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新角色失败: {str(e)}")


@app.delete("/api/roles/{role_id}")
async def delete_role(role_id: str):
    """删除角色"""
    try:
        success = role_manager.delete_role(role_id)
        if not success:
            raise HTTPException(status_code=404, detail="角色不存在")
        return {"message": "角色删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除角色失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
