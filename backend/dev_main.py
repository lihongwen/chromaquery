#!/usr/bin/env python3
"""
ChromaDB Web Manager - 开发/测试版本
简化的启动版本，用于开发和测试基本功能
依赖较少，启动更快，适合开发环境使用
"""

import os
import logging
import uvicorn
import hashlib
import tempfile
import time
import json
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from alibaba_embedding import create_alibaba_embedding_function

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

# 全局变量
chroma_client = None

# 数据模型
class CollectionInfo(BaseModel):
    name: str
    display_name: str
    count: int
    metadata: dict
    dimension: Optional[int] = None

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

class LLMQueryRequest(BaseModel):
    query: str
    collections: List[str]
    limit: Optional[int] = 5
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    similarity_threshold: Optional[float] = 1.5

def init_chroma_client():
    """初始化ChromaDB客户端"""
    global chroma_client
    try:
        # 使用持久化存储
        persist_directory = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_data')
        
        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        chroma_client = chromadb.PersistentClient(path=persist_directory)
        logger.info(f"ChromaDB客户端初始化成功，数据目录: {persist_directory}")
    except Exception as e:
        logger.error(f"ChromaDB客户端初始化失败: {e}")
        raise

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
            # 获取集合元数据
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
            
            # 获取文档数量
            count = collection.count()
            
            # 获取维度信息
            dimension = metadata.get('vector_dimension') or metadata.get('dimension')
            
            result.append(CollectionInfo(
                name=collection.name,
                display_name=display_name,
                count=count,
                metadata=metadata,
                dimension=dimension
            ))
        
        logger.info(f"返回 {len(result)} 个集合")
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
            display_name = metadata.get('display_name', collection.name)
            # 支持通过原始名称或编码名称查找
            if display_name == collection_name or collection.name == collection_name:
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 获取基本信息
        metadata = target_collection.metadata or {}
        display_name = metadata.get('display_name', target_collection.name)
        count = target_collection.count()

        # 获取文档样本
        documents = []
        sample_documents = []
        uploaded_files = set()

        if count > 0:
            # 获取文档数据
            result = target_collection.get(
                limit=min(limit, count),
                include=['documents', 'metadatas', 'embeddings']
            )

            if result:
                for i, doc_id in enumerate(result['ids']):
                    doc_metadata = result['metadatas'][i] if result['metadatas'] else {}
                    doc_text = result['documents'][i] if result['documents'] else ""
                    doc_embedding = result['embeddings'][i] if result['embeddings'] else None

                    # 收集文件名
                    file_name = doc_metadata.get('source_file') or doc_metadata.get('file_name')
                    if file_name:
                        uploaded_files.add(file_name)

                    doc_info = DocumentInfo(
                        id=doc_id,
                        document=doc_text,
                        metadata=doc_metadata,
                        embedding=doc_embedding
                    )

                    documents.append(doc_info)
                    sample_documents.append(doc_info)

        # 构建统计信息
        chunk_statistics = {
            "total_chunks": count,
            "files_count": len(uploaded_files),
            "methods_used": []
        }

        return CollectionDetail(
            name=target_collection.name,
            display_name=display_name,
            count=count,
            metadata=metadata,
            created_time=None,
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

@app.post("/api/collections", response_model=dict)
async def create_collection(request: CreateCollectionRequest):
    """创建新集合"""
    try:
        # 处理中文集合名称
        import hashlib
        if any('\u4e00' <= char <= '\u9fff' for char in request.name):
            # 包含中文字符，使用MD5编码
            encoded_name = hashlib.md5(request.name.encode('utf-8')).hexdigest()
            metadata = {
                'display_name': request.name,
                'original_name': request.name,
                'embedding_model': 'alibaba-text-embedding-v4',
                'vector_dimension': 1024,
                **request.metadata
            }
        else:
            encoded_name = request.name
            metadata = {
                'display_name': request.name,
                'embedding_model': 'alibaba-text-embedding-v4',
                'vector_dimension': 1024,
                **request.metadata
            }

        # 创建阿里云嵌入函数
        try:
            alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
            logger.info(f"成功创建阿里云嵌入函数，维度: 1024")
        except Exception as e:
            logger.error(f"创建阿里云嵌入函数失败: {e}")
            raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")

        # 创建集合，使用阿里云嵌入函数
        collection = chroma_client.create_collection(
            name=encoded_name,
            metadata=metadata,
            embedding_function=alibaba_embedding_func
        )
        
        logger.info(f"集合创建成功: {request.name} -> {encoded_name}")
        return {
            "message": f"集合 '{request.name}' 创建成功",
            "name": encoded_name,
            "display_name": request.name
        }
        
    except Exception as e:
        logger.error(f"创建集合失败: {e}")
        if "already exists" in str(e):
            raise HTTPException(status_code=400, detail=f"集合 '{request.name}' 已存在")
        raise HTTPException(status_code=500, detail=f"创建集合失败: {str(e)}")

@app.delete("/api/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """删除集合"""
    try:
        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None
        
        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
            if display_name == collection_name or collection.name == collection_name:
                target_collection = collection
                break
        
        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")
        
        # 删除集合
        chroma_client.delete_collection(target_collection.name)
        
        logger.info(f"集合删除成功: {collection_name}")
        return {"message": f"集合 '{collection_name}' 删除成功"}
        
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
            display_name = metadata.get('display_name', collection.name)
            if display_name == request.old_name:
                old_collection = collection
                break

        if not old_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{request.old_name}' 不存在")

        # 检查新名称是否已存在
        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
            if display_name == request.new_name:
                raise HTTPException(status_code=400, detail=f"集合 '{request.new_name}' 已存在")

        # 编码新名称
        def encode_collection_name(name: str) -> str:
            """编码集合名称为安全的标识符"""
            import hashlib
            return hashlib.md5(name.encode('utf-8')).hexdigest()

        new_encoded = encode_collection_name(request.new_name)

        # 准备新的元数据
        new_metadata = old_collection.metadata.copy() if old_collection.metadata else {}
        new_metadata['display_name'] = request.new_name

        # 创建阿里云嵌入函数（如果原集合使用的话）
        embedding_function = None
        if new_metadata.get('embedding_model') == 'alibaba-text-embedding-v4':
            try:
                embedding_function = create_alibaba_embedding_function(dimension=1024)
            except Exception as e:
                logger.warning(f"创建阿里云嵌入函数失败，使用默认函数: {e}")

        # ChromaDB不支持直接重命名，需要创建新集合并复制数据
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
                logger.info(f"成功复制 {len(results['ids'])} 个文档到新集合")
        except Exception as e:
            logger.warning(f"复制集合数据时出现警告: {e}")

        # 删除旧集合
        chroma_client.delete_collection(old_collection.name)

        logger.info(f"集合重命名成功: {request.old_name} -> {request.new_name}")
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

def simple_text_chunk(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """简单的文本分块函数"""
    chunks = []
    text_length = len(text)
    step = max(1, chunk_size - chunk_overlap)

    for i in range(0, text_length, step):
        end_pos = min(i + chunk_size, text_length)
        chunk_text = text[i:end_pos]

        if chunk_text.strip():
            chunks.append(chunk_text.strip())

    return chunks

@app.post("/api/collections/{collection_name}/upload", response_model=FileUploadResponse)
async def upload_document(
    collection_name: str,
    file: UploadFile = File(...),
    chunking_method: str = Form("recursive"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """上传文档到指定集合"""
    start_time = time.time()

    try:
        # 查找目标集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
            if display_name == collection_name or collection.name == collection_name:
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 读取文件内容
        content = await file.read()
        text_content = content.decode('utf-8')

        # 使用RAG分块器进行文本分块
        try:
            from rag_chunking import RAGChunker, ChunkingConfig, ChunkingMethod

            # 创建分块配置
            chunking_config = ChunkingConfig(
                method=ChunkingMethod(chunking_method),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # 创建分块器并进行分块
            chunker = RAGChunker()
            chunking_result = chunker.chunk_text(text_content, chunking_config)

            # 提取分块文本
            chunks = [chunk.text for chunk in chunking_result.chunks]

            logger.info(f"使用 {chunking_method} 分块方法，创建了 {len(chunks)} 个块")

        except Exception as e:
            logger.warning(f"RAG分块失败，回退到简单分块: {e}")
            # 回退到简单分块
            chunks = simple_text_chunk(
                text=text_content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        # 准备文档数据
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{file.filename}_{i}"
            documents.append(chunk)
            metadatas.append({
                'source_file': file.filename,
                'chunk_index': i,
                'chunk_size': len(chunk),
                'chunking_method': chunking_method,
                'upload_time': time.time()
            })
            ids.append(chunk_id)

        # 检查集合是否使用阿里云嵌入模型
        collection_metadata = target_collection.metadata or {}
        embedding_model = collection_metadata.get('embedding_model')

        if embedding_model == 'alibaba-text-embedding-v4':
            # 重新创建阿里云嵌入函数
            try:
                alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
                logger.info(f"为集合 '{collection_name}' 重新创建阿里云嵌入函数")

                # 使用阿里云嵌入函数生成向量
                embeddings = alibaba_embedding_func(documents)
                logger.info(f"成功生成 {len(embeddings)} 个1024维向量")

                # 添加文档到集合，包含预生成的向量
                target_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )

            except Exception as e:
                logger.error(f"创建阿里云嵌入函数失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建阿里云嵌入函数失败: {str(e)}")
        else:
            # 使用默认嵌入函数
            target_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"集合 '{collection_name}' 使用默认嵌入函数")

        processing_time = time.time() - start_time

        logger.info(f"文档上传成功: {file.filename}, 创建了 {len(chunks)} 个块")

        return FileUploadResponse(
            message=f"文档 '{file.filename}' 上传成功",
            file_name=file.filename,
            chunks_created=len(chunks),
            total_size=len(text_content),
            processing_time=processing_time,
            collection_name=collection_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@app.delete("/api/collections/{collection_name}/documents/{file_name}")
async def delete_document_by_filename(collection_name: str, file_name: str):
    """删除指定文件名的所有文档块"""
    try:
        # 查找集合
        collections = chroma_client.list_collections()
        target_collection = None

        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
            if display_name == collection_name or collection.name == collection_name:
                target_collection = collection
                break

        if not target_collection:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")

        # 获取所有文档的元数据
        result = target_collection.get(include=['metadatas'])

        if not result or not result['metadatas']:
            raise HTTPException(status_code=404, detail=f"文件 '{file_name}' 不存在")

        # 找到匹配的文档ID
        target_ids = []
        for i, metadata in enumerate(result['metadatas']):
            if metadata:
                doc_file_name = metadata.get('source_file') or metadata.get('file_name')
                if doc_file_name == file_name:
                    target_ids.append(result['ids'][i])

        if not target_ids:
            raise HTTPException(status_code=404, detail=f"文件 '{file_name}' 不存在")

        # 删除这些文档块
        target_collection.delete(ids=target_ids)

        logger.info(f"成功删除文件 '{file_name}' 的 {len(target_ids)} 个文档块")

        return {
            "message": f"成功删除文件 '{file_name}' 的所有文档块",
            "file_name": file_name,
            "deleted_chunks": len(target_ids),
            "collection_name": collection_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@app.post("/api/query", response_model=QueryResponse)
async def query_collections(request: QueryRequest):
    """在指定集合中进行向量查询"""
    start_time = time.time()

    try:
        # 获取所有集合
        collections = chroma_client.list_collections()
        collection_map = {}

        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
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
                if search_results['documents'] and search_results['documents'][0]:
                    for i in range(len(search_results['documents'][0])):
                        result = QueryResult(
                            id=search_results['ids'][0][i] if search_results['ids'] else f"result_{i}",
                            document=search_results['documents'][0][i],
                            metadata=search_results['metadatas'][0][i] if search_results['metadatas'] else {},
                            distance=search_results['distances'][0][i] if search_results['distances'] else 0.0,
                            collection_name=collection_name
                        )
                        all_results.append(result)

            except Exception as e:
                logger.warning(f"在集合 {collection_name} 中查询失败: {e}")
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

async def simple_llm_query(query_results: List[Dict], user_query: str) -> str:
    """简化的LLM查询函数"""
    try:
        import dashscope
        from dashscope import Generation

        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            return "LLM功能需要配置DASHSCOPE_API_KEY环境变量"

        dashscope.api_key = api_key

        # 构建上下文
        if not query_results:
            context_parts = [f"用户问题：{user_query}\n\n抱歉，我没有找到相关的文档内容来回答您的问题。请尝试使用不同的关键词重新提问。"]
        else:
            context_parts = [f"我找到了 {len(query_results)} 个相关文档，基于以下内容为您回答：\n"]

            for i, result in enumerate(query_results[:5], 1):  # 增加到5个文档
                similarity = (1 - result.get('distance', 0)) * 100
                collection_name = result.get('collection_name', '未知集合')
                document = result.get('document', '')[:800]  # 增加文档长度

                context_parts.append(
                    f"文档{i}（相似度：{similarity:.1f}%，来源：{collection_name}）：\n{document}\n"
                )

            context_parts.append(f"\n用户问题：{user_query}")
            context_parts.append(f"\n请基于上述 {len(query_results)} 个相关文档内容提供准确、有用的回答。如果文档中没有直接相关的信息，请明确说明。请用中文回答。")

        context = "\n".join(context_parts)

        messages = [
            {
                "role": "system",
                "content": "你是一个专业的AI助手，擅长基于提供的文档内容回答用户问题。"
            },
            {
                "role": "user",
                "content": context
            }
        ]

        response = Generation.call(
            model='qwen-turbo',
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=False
        )

        if response.status_code == 200:
            return response.output.text
        else:
            return f"LLM调用失败：{response.message}"

    except ImportError:
        return "dashscope库未安装，请运行：pip install dashscope"
    except Exception as e:
        return f"LLM调用异常：{str(e)}"

@app.post("/api/llm-query")
async def llm_query(request: LLMQueryRequest):
    """
    LLM智能查询接口
    结合ChromaDB向量查询和LLM生成回答
    """
    try:
        # 1. 先进行向量查询获取相关文档
        query_request = QueryRequest(
            query=request.query,
            collections=request.collections,
            limit=request.limit
        )

        # 获取所有集合
        collections = chroma_client.list_collections()
        collection_map = {}

        for collection in collections:
            metadata = collection.metadata or {}
            display_name = metadata.get('display_name', collection.name)
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
            # 使用阿里云embedding函数生成查询向量
            alibaba_embedding_func = create_alibaba_embedding_function(dimension=1024)
            query_embeddings = alibaba_embedding_func([request.query])
            query_embedding = query_embeddings[0]
            logger.info(f"使用阿里云嵌入模型生成查询向量，维度: {len(query_embedding)}")
        except Exception as e:
            logger.warning(f"生成查询向量失败，将使用文本查询: {e}")

        # 在每个集合中进行查询
        all_results = []

        for collection_name, collection in target_collections:
            try:
                # 检查集合的embedding模型
                collection_metadata = collection.metadata or {}
                embedding_model = collection_metadata.get('embedding_model')

                if query_embedding and embedding_model == 'alibaba-text-embedding-v4':
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

                if search_results['documents'] and search_results['documents'][0]:
                    for i in range(len(search_results['documents'][0])):
                        distance = search_results['distances'][0][i] if search_results['distances'] else 0.0

                        # 相似度阈值过滤：使用用户设置的阈值
                        # 注意：distance越小表示越相似，阈值越小要求越严格
                        # 前端传递的是0-1的相似度，需要转换为distance阈值
                        distance_threshold = 2.0 - (request.similarity_threshold * 2.0)  # 转换公式
                        if distance < distance_threshold:
                            result = {
                                'id': search_results['ids'][0][i] if search_results['ids'] else f"result_{i}",
                                'document': search_results['documents'][0][i],
                                'metadata': search_results['metadatas'][0][i] if search_results['metadatas'] else {},
                                'distance': distance,
                                'collection_name': collection_name
                            }
                            all_results.append(result)

            except Exception as e:
                logger.warning(f"在集合 {collection_name} 中查询失败: {e}")
                continue

        # 按相似度排序并限制结果数量
        all_results.sort(key=lambda x: x['distance'])
        final_results = all_results[:request.limit]

        logger.info(f"向量查询完成，找到 {len(final_results)} 个结果")

        # 2. 调用LLM生成回答
        llm_response = await simple_llm_query(final_results, request.query)

        # 3. 返回流式响应
        async def generate_stream():
            try:
                # 首先发送文档数量信息
                metadata_chunk = {
                    'content': '',
                    'finish_reason': None,
                    'metadata': {
                        'documents_found': len(final_results),
                        'collections_searched': len(request.collections)
                    }
                }
                data = json.dumps(metadata_chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"

                # 模拟流式效果：将完整内容分块发送
                chunk_size = 3  # 每次发送3个字符
                for i in range(0, len(llm_response), chunk_size):
                    chunk = llm_response[i:i + chunk_size]

                    # 发送当前块
                    data = json.dumps({
                        'content': chunk,
                        'finish_reason': None,
                        'usage': None
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                    # 添加小延迟模拟流式效果
                    await asyncio.sleep(0.05)  # 50ms延迟

                # 发送完成信号
                data = json.dumps({
                    'content': '',
                    'finish_reason': 'stop',
                    'usage': None
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"

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

@app.get("/api/chunking/config/{method}")
async def get_chunking_config(method: str):
    """获取分块配置"""
    configs = {
        'recursive': {
            'method': 'recursive',
            'chunk_size': 1000,
            'chunk_overlap': 200
        },
        'fixed_size': {
            'method': 'fixed_size',
            'chunk_size': 800,
            'chunk_overlap': 100
        },
        'semantic': {
            'method': 'semantic',
            'chunk_size': 1200,
            'chunk_overlap': 150
        }
    }

    if method not in configs:
        raise HTTPException(status_code=400, detail=f"不支持的分块方式: {method}")

    return configs[method]

if __name__ == "__main__":
    uvicorn.run(
        "dev_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
