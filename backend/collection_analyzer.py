"""
集合分析器
用于评估集合大小和预估处理时间
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import chromadb
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CollectionAnalysis:
    """集合分析结果"""
    collection_name: str
    display_name: str
    document_count: int
    estimated_size_mb: float
    estimated_processing_time_seconds: float
    vector_dimension: int
    should_show_progress: bool
    complexity_level: str  # 'simple', 'medium', 'complex'

class CollectionAnalyzer:
    """集合分析器"""
    
    # 阈值配置
    PROGRESS_THRESHOLDS = {
        'document_count': 500,      # 文档数量阈值
        'size_mb': 10,             # 数据大小阈值(MB)
        'processing_time': 5       # 处理时间阈值(秒)
    }
    
    # 性能估算参数
    PERFORMANCE_ESTIMATES = {
        'docs_per_second': 100,    # 每秒处理文档数
        'mb_per_second': 5,        # 每秒处理数据量(MB)
        'base_overhead': 2,        # 基础开销时间(秒)
        'bytes_per_doc': 2048      # 每个文档平均字节数(包含向量)
    }
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
    
    def analyze_collection(self, collection_name: str) -> Optional[CollectionAnalysis]:
        """分析集合并返回评估结果"""
        try:
            # 查找集合
            collections = self.client.list_collections()
            target_collection = None
            
            for collection in collections:
                metadata = collection.metadata or {}
                display_name = metadata.get('original_name', collection.name)
                if display_name == collection_name:
                    target_collection = collection
                    break
            
            if not target_collection:
                logger.warning(f"集合不存在: {collection_name}")
                return None
            
            # 获取基本信息
            metadata = target_collection.metadata or {}
            display_name = metadata.get('original_name', collection_name)
            document_count = target_collection.count()
            vector_dimension = metadata.get('vector_dimension', 1024)
            
            # 估算数据大小
            estimated_size_mb = self._estimate_collection_size(
                document_count, vector_dimension, target_collection
            )
            
            # 估算处理时间
            estimated_time = self._estimate_processing_time(
                document_count, estimated_size_mb
            )
            
            # 判断是否需要显示进度
            should_show_progress = self._should_show_progress(
                document_count, estimated_size_mb, estimated_time
            )
            
            # 确定复杂度级别
            complexity_level = self._determine_complexity(
                document_count, estimated_size_mb, estimated_time
            )
            
            return CollectionAnalysis(
                collection_name=collection_name,
                display_name=display_name,
                document_count=document_count,
                estimated_size_mb=estimated_size_mb,
                estimated_processing_time_seconds=estimated_time,
                vector_dimension=vector_dimension,
                should_show_progress=should_show_progress,
                complexity_level=complexity_level
            )
            
        except Exception as e:
            logger.error(f"分析集合失败: {collection_name}, 错误: {e}")
            return None
    
    def _estimate_collection_size(self, doc_count: int, vector_dim: int, collection) -> float:
        """估算集合数据大小(MB)"""
        try:
            # 方法1: 尝试从文件系统获取实际大小
            collection_dir = self.chroma_path / collection.name
            if collection_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in collection_dir.rglob('*') if f.is_file()
                )
                return total_size / (1024 * 1024)  # 转换为MB
        except Exception as e:
            logger.debug(f"无法获取文件系统大小: {e}")
        
        # 方法2: 基于文档数量和向量维度估算
        # 向量数据: 每个维度4字节(float32) + 元数据开销
        vector_size_per_doc = vector_dim * 4  # float32
        metadata_size_per_doc = 512  # 估算元数据大小
        total_size_per_doc = vector_size_per_doc + metadata_size_per_doc
        
        total_size_bytes = doc_count * total_size_per_doc
        return total_size_bytes / (1024 * 1024)  # 转换为MB
    
    def _estimate_processing_time(self, doc_count: int, size_mb: float) -> float:
        """估算处理时间(秒)"""
        # 基于文档数量的时间估算
        time_by_docs = doc_count / self.PERFORMANCE_ESTIMATES['docs_per_second']
        
        # 基于数据大小的时间估算
        time_by_size = size_mb / self.PERFORMANCE_ESTIMATES['mb_per_second']
        
        # 取较大值并加上基础开销
        estimated_time = max(time_by_docs, time_by_size) + self.PERFORMANCE_ESTIMATES['base_overhead']
        
        return round(estimated_time, 1)
    
    def _should_show_progress(self, doc_count: int, size_mb: float, time_seconds: float) -> bool:
        """判断是否应该显示进度弹窗"""
        return (
            doc_count > self.PROGRESS_THRESHOLDS['document_count'] or
            size_mb > self.PROGRESS_THRESHOLDS['size_mb'] or
            time_seconds > self.PROGRESS_THRESHOLDS['processing_time']
        )
    
    def _determine_complexity(self, doc_count: int, size_mb: float, time_seconds: float) -> str:
        """确定复杂度级别"""
        if doc_count > 5000 or size_mb > 100 or time_seconds > 60:
            return 'complex'
        elif doc_count > 1000 or size_mb > 20 or time_seconds > 15:
            return 'medium'
        else:
            return 'simple'
    
    def get_progress_message(self, complexity_level: str, doc_count: int) -> str:
        """根据复杂度获取进度提示消息"""
        if complexity_level == 'complex':
            return f"数据量较大({doc_count:,}条记录)，正在处理中，请耐心等待..."
        elif complexity_level == 'medium':
            return f"正在处理{doc_count:,}条记录，预计需要一些时间..."
        else:
            return f"正在快速处理{doc_count:,}条记录..."

def get_collection_analyzer(chroma_path: Path, client: chromadb.PersistentClient) -> CollectionAnalyzer:
    """获取集合分析器实例"""
    return CollectionAnalyzer(chroma_path, client)
