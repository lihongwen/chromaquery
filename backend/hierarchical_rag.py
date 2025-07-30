"""
层次化RAG集成模块
将层次化检索系统集成到现有的ChromaDB Web Manager中
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import chromadb
from chromadb.utils import embedding_functions

from hybrid_retrieval import HierarchicalRetriever, HierarchicalConfig, HierarchicalResult

logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """RAG配置"""
    # 层次化检索配置
    hierarchical_config: HierarchicalConfig
    
    # ChromaDB配置
    collection_name: str
    embedding_model: str = "alibaba-text-embedding-v4"
    
    # 检索配置
    enable_hierarchical: bool = True
    fallback_to_simple: bool = True

class HierarchicalRAGManager:
    """层次化RAG管理器"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.chroma_client = None
        self.collection = None
        self.hierarchical_retriever = None
        self.embedding_function = None
        
    def initialize(self, chroma_client, collection_name: str):
        """初始化RAG系统"""
        self.chroma_client = chroma_client
        self.collection = chroma_client.get_collection(collection_name)
        
        # 获取embedding函数
        self.embedding_function = self._get_embedding_function()
        
        # 初始化层次化检索器
        if self.config.enable_hierarchical:
            self.hierarchical_retriever = HierarchicalRetriever(self.config.hierarchical_config)
            logger.info("层次化RAG系统初始化完成")
    
    def _get_embedding_function(self):
        """获取embedding函数"""
        try:
            # 这里应该使用与ChromaDB相同的embedding函数
            # 实际实现时需要根据具体的embedding模型调整
            if self.config.embedding_model == "alibaba-text-embedding-v4":
                # 模拟阿里云embedding函数
                def alibaba_embedding(texts):
                    # 实际实现时替换为真实的阿里云API调用
                    import numpy as np
                    return [np.random.rand(1024) for _ in texts]
                return alibaba_embedding
            else:
                # 使用ChromaDB默认embedding
                return embedding_functions.DefaultEmbeddingFunction()
        except Exception as e:
            logger.error(f"获取embedding函数失败: {e}")
            return None
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """添加文档到RAG系统"""
        if not documents:
            return
        
        # 1. 添加到ChromaDB（保持原有逻辑）
        self._add_to_chromadb(documents, metadatas)
        
        # 2. 训练层次化检索器
        if self.config.enable_hierarchical and self.hierarchical_retriever:
            try:
                self.hierarchical_retriever.fit(documents, self.embedding_function)
                logger.info(f"层次化检索器训练完成，文档数量: {len(documents)}")
            except Exception as e:
                logger.error(f"层次化检索器训练失败: {e}")
    
    def _add_to_chromadb(self, documents: List[str], metadatas: List[Dict] = None):
        """添加文档到ChromaDB"""
        try:
            ids = [f"doc_{i}" for i in range(len(documents))]
            self.collection.add(
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids
            )
            logger.info(f"成功添加 {len(documents)} 个文档到ChromaDB")
        except Exception as e:
            logger.error(f"添加文档到ChromaDB失败: {e}")
    
    def search(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        """执行检索"""
        results = {
            "query": query,
            "hierarchical_results": [],
            "chromadb_results": [],
            "method": "unknown"
        }
        
        # 1. 尝试层次化检索
        if self.config.enable_hierarchical and self.hierarchical_retriever:
            try:
                hierarchical_results = self.hierarchical_retriever.search(query)
                results["hierarchical_results"] = self._format_hierarchical_results(hierarchical_results)
                results["method"] = "hierarchical"
                logger.info(f"层次化检索返回 {len(hierarchical_results)} 个结果")
                
                # 如果层次化检索有结果，直接返回
                if hierarchical_results:
                    return results
                    
            except Exception as e:
                logger.error(f"层次化检索失败: {e}")
        
        # 2. 回退到ChromaDB检索
        if self.config.fallback_to_simple:
            try:
                chromadb_results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                results["chromadb_results"] = self._format_chromadb_results(chromadb_results)
                results["method"] = "chromadb_fallback"
                logger.info(f"ChromaDB检索返回 {len(chromadb_results.get('documents', [[]])[0])} 个结果")
                
            except Exception as e:
                logger.error(f"ChromaDB检索失败: {e}")
        
        return results
    
    def _format_hierarchical_results(self, results: List[HierarchicalResult]) -> List[Dict]:
        """格式化层次化检索结果"""
        formatted_results = []
        
        for result in results:
            formatted_result = {
                "id": result.child_chunk_id,
                "content": result.child_content,
                "parent_content": result.parent_content,
                "score": result.final_score,
                "semantic_score": result.semantic_score,
                "bm25_score": result.bm25_score,
                "hybrid_score": result.hybrid_score,
                "position": {
                    "start_char": result.position.start_char,
                    "end_char": result.position.end_char,
                    "highlight_start": result.highlight_start,
                    "highlight_end": result.highlight_end
                },
                "metadata": result.metadata,
                "type": "hierarchical"
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _format_chromadb_results(self, results: Dict) -> List[Dict]:
        """格式化ChromaDB检索结果"""
        formatted_results = []
        
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        ids = results.get('ids', [[]])[0]
        
        for i, (doc, distance, metadata, doc_id) in enumerate(zip(documents, distances, metadatas, ids)):
            formatted_result = {
                "id": doc_id,
                "content": doc,
                "score": 1 - distance,  # 转换为相似度分数
                "distance": distance,
                "metadata": metadata or {},
                "type": "chromadb"
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def get_highlighted_result(self, result_id: str, query: str) -> Optional[str]:
        """获取带高亮的结果"""
        if not self.hierarchical_retriever:
            return None
        
        # 查找对应的层次化结果
        # 这里需要实现结果缓存机制，简化示例
        try:
            results = self.hierarchical_retriever.search(query)
            for result in results:
                if result.child_chunk_id == result_id:
                    return self.hierarchical_retriever.get_highlighted_content(result, query)
        except Exception as e:
            logger.error(f"获取高亮结果失败: {e}")
        
        return None
    
    def get_context_window(self, result_id: str, query: str, window_size: int = 200) -> Optional[str]:
        """获取上下文窗口"""
        if not self.hierarchical_retriever:
            return None
        
        try:
            results = self.hierarchical_retriever.search(query)
            for result in results:
                if result.child_chunk_id == result_id:
                    return self.hierarchical_retriever.get_context_window(result, window_size)
        except Exception as e:
            logger.error(f"获取上下文窗口失败: {e}")
        
        return None


# 使用示例
def create_hierarchical_rag_example():
    """创建层次化RAG示例"""
    
    # 配置
    hierarchical_config = HierarchicalConfig(
        parent_chunk_size=1000,
        child_chunk_size=200,
        overlap_size=50,
        semantic_weight=0.6,
        bm25_weight=0.4,
        position_weight=0.1,
        top_k=5,
        query_expansion=True,
        smart_boundary=True
    )
    
    rag_config = RAGConfig(
        hierarchical_config=hierarchical_config,
        collection_name="test_collection",
        embedding_model="alibaba-text-embedding-v4",
        enable_hierarchical=True,
        fallback_to_simple=True
    )
    
    # 创建RAG管理器
    rag_manager = HierarchicalRAGManager(rag_config)
    
    return rag_manager



