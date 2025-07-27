"""
向量相似度计算优化模块
针对大文档块与小查询之间的相似度计算进行优化
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DistanceMetric(str, Enum):
    """距离度量枚举"""
    COSINE = "cosine"
    L2 = "l2"
    IP = "ip"  # Inner Product


class VectorOptimizationConfig(BaseModel):
    """向量优化配置"""
    distance_metric: DistanceMetric = DistanceMetric.COSINE
    vector_dimension: int = 512  # 降低维度以减少维度诅咒
    chunk_size_small: int = 300  # 小块大小，适合短查询
    chunk_size_medium: int = 600  # 中等块大小
    chunk_size_large: int = 1000  # 大块大小，保留原有配置
    chunk_overlap: int = 100  # 重叠大小
    enable_hierarchical_chunking: bool = True  # 启用分层分块
    enable_query_expansion: bool = True  # 启用查询扩展


class ChunkSizeStrategy(str, Enum):
    """分块大小策略"""
    ADAPTIVE = "adaptive"  # 自适应：根据查询长度选择块大小
    SMALL = "small"  # 小块：300字符
    MEDIUM = "medium"  # 中等块：600字符
    LARGE = "large"  # 大块：1000字符
    HIERARCHICAL = "hierarchical"  # 分层：多种大小混合


def get_optimized_collection_metadata(
    config: VectorOptimizationConfig,
    original_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    获取优化的集合元数据配置
    
    Args:
        config: 向量优化配置
        original_metadata: 原始元数据
        
    Returns:
        优化后的元数据
    """
    metadata = original_metadata or {}
    
    # 设置距离度量
    if config.distance_metric == DistanceMetric.COSINE:
        metadata["hnsw:space"] = "cosine"
    elif config.distance_metric == DistanceMetric.L2:
        metadata["hnsw:space"] = "l2"
    elif config.distance_metric == DistanceMetric.IP:
        metadata["hnsw:space"] = "ip"
    
    # Note: ChromaDB 0.4.18 only supports hnsw:space parameter
    # Advanced HNSW parameters like ef_construction, ef_search, max_neighbors are not supported
    
    # 向量维度配置
    metadata["vector_dimension"] = config.vector_dimension
    metadata["optimization_enabled"] = "true"  # ChromaDB 0.3.29不支持布尔值，使用字符串
    metadata["chunk_strategy"] = "adaptive"
    
    logger.info(f"优化集合元数据: 距离度量={config.distance_metric}, 维度={config.vector_dimension}")
    
    return metadata


def get_adaptive_chunk_size(query_length: int, config: VectorOptimizationConfig) -> int:
    """
    根据查询长度自适应选择块大小
    
    Args:
        query_length: 查询文本长度
        config: 优化配置
        
    Returns:
        推荐的块大小
    """
    if query_length <= 100:
        # 短查询使用小块
        return config.chunk_size_small
    elif query_length <= 300:
        # 中等查询使用中等块
        return config.chunk_size_medium
    else:
        # 长查询使用大块
        return config.chunk_size_large


def optimize_query_for_retrieval(query: str, config: VectorOptimizationConfig) -> List[str]:
    """
    优化查询以提高检索效果
    
    Args:
        query: 原始查询
        config: 优化配置
        
    Returns:
        优化后的查询列表（可能包含扩展查询）
    """
    queries = [query]
    
    if config.enable_query_expansion and len(query) < 200:
        # 对短查询进行扩展
        expanded_query = expand_short_query(query)
        if expanded_query != query:
            queries.append(expanded_query)
    
    return queries


def expand_short_query(query: str) -> str:
    """
    扩展短查询以提高匹配效果
    
    Args:
        query: 原始查询
        
    Returns:
        扩展后的查询
    """
    # 简单的查询扩展策略
    if len(query) < 50:
        # 为非常短的查询添加上下文提示
        expanded = f"关于{query}的详细信息和相关内容"
        return expanded
    elif len(query) < 100:
        # 为短查询添加同义词提示
        expanded = f"{query} 相关 详细 说明"
        return expanded
    
    return query


def calculate_optimized_similarity(distance: float, metric: DistanceMetric) -> float:
    """
    根据距离度量计算优化的相似度分数
    
    Args:
        distance: 原始距离值
        metric: 距离度量类型
        
    Returns:
        优化的相似度分数 (0-100%)
    """
    if metric == DistanceMetric.COSINE:
        # Cosine距离: d = 1 - cosine_similarity
        # 相似度 = (1 - d) * 100
        similarity = max(0, min(100, (1 - distance) * 100))
    elif metric == DistanceMetric.L2:
        # L2距离: 使用改进的公式
        similarity = max(0, min(100, (1 / (1 + distance)) * 100))
    elif metric == DistanceMetric.IP:
        # Inner Product: d = 1 - inner_product
        similarity = max(0, min(100, (1 - distance) * 100))
    else:
        # 默认使用改进的L2公式
        similarity = max(0, min(100, (1 / (1 + distance)) * 100))
    
    return round(similarity, 1)


def get_recommended_chunking_strategy(
    document_length: int,
    query_patterns: List[str],
    config: VectorOptimizationConfig
) -> ChunkSizeStrategy:
    """
    根据文档特征和查询模式推荐分块策略
    
    Args:
        document_length: 文档长度
        query_patterns: 查询模式列表
        config: 优化配置
        
    Returns:
        推荐的分块策略
    """
    avg_query_length = sum(len(q) for q in query_patterns) / len(query_patterns) if query_patterns else 100
    
    if config.enable_hierarchical_chunking and document_length > 5000:
        return ChunkSizeStrategy.HIERARCHICAL
    elif avg_query_length < 100:
        return ChunkSizeStrategy.SMALL
    elif avg_query_length < 300:
        return ChunkSizeStrategy.MEDIUM
    else:
        return ChunkSizeStrategy.ADAPTIVE


# 默认优化配置
DEFAULT_OPTIMIZATION_CONFIG = VectorOptimizationConfig(
    distance_metric=DistanceMetric.COSINE,
    vector_dimension=512,
    chunk_size_small=300,
    chunk_size_medium=600,
    chunk_size_large=1000,
    chunk_overlap=100,
    enable_hierarchical_chunking=True,
    enable_query_expansion=True
)

# 高精度配置（适用于对准确性要求很高的场景）
HIGH_PRECISION_CONFIG = VectorOptimizationConfig(
    distance_metric=DistanceMetric.COSINE,
    vector_dimension=1024,  # 保持高维度以获得更好的语义表示
    chunk_size_small=200,   # 更小的块以提高精确匹配
    chunk_size_medium=400,
    chunk_size_large=800,
    chunk_overlap=150,      # 更大的重叠以确保连续性
    enable_hierarchical_chunking=True,
    enable_query_expansion=True
)

# 性能优化配置（适用于对速度要求较高的场景）
PERFORMANCE_CONFIG = VectorOptimizationConfig(
    distance_metric=DistanceMetric.COSINE,
    vector_dimension=384,   # 较低维度以提高速度
    chunk_size_small=400,
    chunk_size_medium=800,
    chunk_size_large=1200,
    chunk_overlap=50,       # 较小重叠以减少计算量
    enable_hierarchical_chunking=False,
    enable_query_expansion=False
)
