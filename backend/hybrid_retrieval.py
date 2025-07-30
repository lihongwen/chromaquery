"""
层次化混合检索实现
解决大chunk与短查询的语义匹配问题，通过子chunk检索和父chunk上下文返回
"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba
import jieba.analyse

logger = logging.getLogger(__name__)

@dataclass
class ChunkPosition:
    """chunk位置信息"""
    start_pos: int
    end_pos: int
    start_char: int
    end_char: int

@dataclass
class ChildChunk:
    """子chunk信息"""
    id: str
    content: str
    parent_id: str
    position: ChunkPosition
    embedding: Optional[np.ndarray] = None

@dataclass
class ParentChunk:
    """父chunk信息"""
    id: str
    content: str
    child_ids: List[str]
    metadata: Dict[str, Any]

@dataclass
class HierarchicalResult:
    """层次化检索结果"""
    child_chunk_id: str
    parent_chunk_id: str
    child_content: str
    parent_content: str
    position: ChunkPosition
    semantic_score: float
    bm25_score: float
    hybrid_score: float
    final_score: float
    highlight_start: int
    highlight_end: int
    metadata: Dict[str, Any]

@dataclass
class HierarchicalConfig:
    """层次化检索配置"""
    # 分块配置
    parent_chunk_size: int = 1000      # 父chunk大小
    child_chunk_size: int = 200        # 子chunk大小
    overlap_size: int = 50             # 重叠大小

    # 检索配置
    semantic_weight: float = 0.6       # 语义检索权重
    bm25_weight: float = 0.4           # BM25权重
    position_weight: float = 0.1       # 位置权重

    # 结果配置
    top_k: int = 10                    # 返回结果数量
    min_score_threshold: float = 0.1   # 最小分数阈值
    max_child_results: int = 50        # 子chunk最大检索数量

    # 功能开关
    query_expansion: bool = True       # 是否启用查询扩展
    smart_boundary: bool = True        # 是否启用智能边界检测
    context_expansion: bool = True     # 是否启用上下文扩展

    # 智能粒度匹配配置
    enable_intelligent_granularity: bool = True  # 启用智能粒度匹配
    query_length_thresholds: dict = None         # 查询长度阈值
    granularity_weights: dict = None             # 不同粒度的权重配置

    def __post_init__(self):
        """初始化默认配置"""
        if self.query_length_thresholds is None:
            self.query_length_thresholds = {
                'short': 50,     # 短查询阈值（字符数）- 适合中文
                'medium': 120,   # 中查询阈值（字符数）- 适合中文
            }

        if self.granularity_weights is None:
            self.granularity_weights = {
                'short': {
                    'child_weight': 0.8,    # 短查询优先子chunk
                    'parent_weight': 0.2
                },
                'medium': {
                    'child_weight': 0.5,    # 中查询平衡
                    'parent_weight': 0.5
                },
                'long': {
                    'child_weight': 0.3,    # 长查询优先父chunk
                    'parent_weight': 0.7
                }
            }

class HierarchicalChunker:
    """层次化分块器"""

    def __init__(self, config: HierarchicalConfig):
        self.config = config

    def split_documents(self, documents: List[str]) -> Tuple[List[ParentChunk], List[ChildChunk]]:
        """将文档分割为层次化chunk"""
        parent_chunks = []
        child_chunks = []

        for doc_idx, document in enumerate(documents):
            # 1. 分割为父chunk
            parent_chunk_texts = self._split_to_parent_chunks(document)

            for parent_idx, parent_text in enumerate(parent_chunk_texts):
                parent_id = f"parent_{doc_idx}_{parent_idx}"

                # 2. 分割为子chunk
                child_chunk_data = self._split_to_child_chunks(parent_text, parent_id)

                # 创建父chunk
                child_ids = [child['id'] for child in child_chunk_data]
                parent_chunk = ParentChunk(
                    id=parent_id,
                    content=parent_text,
                    child_ids=child_ids,
                    metadata={"doc_index": doc_idx, "parent_index": parent_idx}
                )
                parent_chunks.append(parent_chunk)

                # 创建子chunk
                for child_data in child_chunk_data:
                    child_chunk = ChildChunk(
                        id=child_data['id'],
                        content=child_data['content'],
                        parent_id=parent_id,
                        position=child_data['position']
                    )
                    child_chunks.append(child_chunk)

        logger.info(f"分块完成: {len(parent_chunks)}个父chunk, {len(child_chunks)}个子chunk")
        return parent_chunks, child_chunks

    def _split_to_parent_chunks(self, document: str) -> List[str]:
        """分割为父chunk"""
        if len(document) <= self.config.parent_chunk_size:
            return [document]

        chunks = []
        start = 0

        while start < len(document):
            end = start + self.config.parent_chunk_size

            if end >= len(document):
                chunks.append(document[start:])
                break

            # 智能边界检测
            if self.config.smart_boundary:
                boundary_pos = self._find_smart_boundary(document, start, end)
                if boundary_pos > start:
                    end = boundary_pos

            chunks.append(document[start:end])
            start = end - self.config.overlap_size  # 父chunk之间也有重叠

        return chunks

    def _split_to_child_chunks(self, parent_text: str, parent_id: str) -> List[Dict]:
        """分割为子chunk"""
        child_chunks = []
        start = 0
        child_idx = 0

        while start < len(parent_text):
            end = start + self.config.child_chunk_size

            if end >= len(parent_text):
                # 最后一个chunk
                content = parent_text[start:]
                if content.strip():  # 确保不是空内容
                    child_chunks.append({
                        'id': f"{parent_id}_child_{child_idx}",
                        'content': content,
                        'position': ChunkPosition(
                            start_pos=child_idx,
                            end_pos=child_idx,
                            start_char=start,
                            end_char=len(parent_text)
                        )
                    })
                break

            # 智能边界检测
            if self.config.smart_boundary:
                boundary_pos = self._find_smart_boundary(parent_text, start, end)
                if boundary_pos > start:
                    end = boundary_pos

            content = parent_text[start:end]
            child_chunks.append({
                'id': f"{parent_id}_child_{child_idx}",
                'content': content,
                'position': ChunkPosition(
                    start_pos=child_idx,
                    end_pos=child_idx,
                    start_char=start,
                    end_char=end
                )
            })

            start = end - self.config.overlap_size
            child_idx += 1

        return child_chunks

    def _find_smart_boundary(self, text: str, start: int, end: int) -> int:
        """智能边界检测"""
        if end >= len(text):
            return len(text)

        # 在end位置前后寻找最佳分割点
        search_range = min(50, (end - start) // 4)  # 搜索范围
        best_pos = end

        # 优先级：段落 > 句子 > 词语边界
        for offset in range(search_range):
            # 向前搜索
            pos = end - offset
            if pos > start:
                if text[pos:pos+2] == '\n\n':  # 段落边界
                    return pos + 2
                elif text[pos] in '。！？.!?':  # 句子边界
                    best_pos = pos + 1
                elif text[pos] in ' \n\t，,；;':  # 词语边界
                    if best_pos == end:  # 只有没找到更好的才用词语边界
                        best_pos = pos + 1

        return best_pos


class BM25Retriever:
    """BM25检索器"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.term_frequencies = []
        self.document_frequencies = {}
        self.vocabulary = set()
        
    def fit(self, documents: List[str]):
        """训练BM25模型"""
        self.documents = documents
        self.doc_lengths = []
        self.term_frequencies = []
        self.document_frequencies = {}
        self.vocabulary = set()
        
        # 分词和统计
        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))
            
            # 计算词频
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
                self.vocabulary.add(token)
            self.term_frequencies.append(tf)
            
            # 计算文档频率
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.document_frequencies[token] = self.document_frequencies.get(token, 0) + 1
        
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        logger.info(f"BM25模型训练完成，文档数量: {len(documents)}, 词汇量: {len(self.vocabulary)}")
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 中文分词
        tokens = jieba.lcut(text)
        # 过滤停用词和标点
        tokens = [token.strip() for token in tokens if len(token.strip()) > 1 and token.isalnum()]
        return tokens
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """BM25检索"""
        query_tokens = self._tokenize(query)
        scores = []
        
        for doc_idx, tf in enumerate(self.term_frequencies):
            score = 0
            doc_length = self.doc_lengths[doc_idx]
            
            for token in query_tokens:
                if token in tf:
                    # BM25公式
                    tf_score = tf[token]
                    df = self.document_frequencies.get(token, 0)
                    idf = np.log((len(self.documents) - df + 0.5) / (df + 0.5))
                    
                    numerator = tf_score * (self.k1 + 1)
                    denominator = tf_score + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                    
                    score += idf * numerator / denominator
            
            scores.append((doc_idx, score))
        
        # 排序并返回top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

class QueryExpander:
    """查询扩展器"""
    
    def __init__(self):
        self.synonym_dict = {
            # 可以添加同义词词典
            "机器学习": ["深度学习", "人工智能", "AI", "ML"],
            "算法": ["模型", "方法", "技术"],
            "数据": ["信息", "资料", "内容"],
        }
    
    def expand_query(self, query: str) -> str:
        """扩展查询"""
        # 提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=5)
        
        expanded_terms = []
        for keyword in keywords:
            expanded_terms.append(keyword)
            # 添加同义词
            if keyword in self.synonym_dict:
                expanded_terms.extend(self.synonym_dict[keyword][:2])  # 限制同义词数量
        
        # 去重并组合
        unique_terms = list(set(expanded_terms))
        expanded_query = " ".join(unique_terms)
        
        logger.info(f"查询扩展: '{query}' -> '{expanded_query}'")
        return expanded_query

class HierarchicalRetriever:
    """层次化混合检索器"""

    def __init__(self, config: HierarchicalConfig = None):
        self.config = config or HierarchicalConfig()
        self.chunker = HierarchicalChunker(self.config)
        self.bm25_retriever = BM25Retriever()
        self.query_expander = QueryExpander()

        # 存储层次化数据
        self.parent_chunks: List[ParentChunk] = []
        self.child_chunks: List[ChildChunk] = []
        self.child_embeddings: Optional[np.ndarray] = None
        self.embedding_function = None

        # 索引映射
        self.child_id_to_index = {}
        self.parent_id_to_chunk = {}

    def fit(self, documents: List[str], embedding_function):
        """训练层次化检索模型"""
        self.embedding_function = embedding_function

        # 1. 层次化分块
        self.parent_chunks, self.child_chunks = self.chunker.split_documents(documents)

        # 2. 建立索引映射
        self._build_indices()

        # 3. 生成子chunk的embedding
        self._generate_child_embeddings()

        # 4. 训练BM25（基于子chunk）
        child_contents = [chunk.content for chunk in self.child_chunks]
        self.bm25_retriever.fit(child_contents)

        logger.info(f"层次化检索模型训练完成: {len(self.parent_chunks)}个父chunk, {len(self.child_chunks)}个子chunk")

    def _build_indices(self):
        """建立索引映射"""
        for idx, child_chunk in enumerate(self.child_chunks):
            self.child_id_to_index[child_chunk.id] = idx

        for parent_chunk in self.parent_chunks:
            self.parent_id_to_chunk[parent_chunk.id] = parent_chunk

    def _generate_child_embeddings(self):
        """生成子chunk的embedding"""
        if not self.embedding_function:
            return

        child_contents = [chunk.content for chunk in self.child_chunks]

        # 批量生成embedding（考虑API限制）
        batch_size = 10
        all_embeddings = []

        for i in range(0, len(child_contents), batch_size):
            batch = child_contents[i:i + batch_size]
            try:
                batch_embeddings = self.embedding_function(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"生成embedding失败: {e}")
                # 使用零向量作为fallback
                all_embeddings.extend([np.zeros(1024) for _ in batch])

        self.child_embeddings = np.array(all_embeddings)

        # 存储到子chunk对象中
        for i, chunk in enumerate(self.child_chunks):
            chunk.embedding = self.child_embeddings[i]

    def _analyze_query_length(self, query: str) -> str:
        """分析查询长度并返回查询类型"""
        query_length = len(query)

        if query_length < self.config.query_length_thresholds['short']:
            query_type = 'short'
        elif query_length < self.config.query_length_thresholds['medium']:
            query_type = 'medium'
        else:
            query_type = 'long'

        logger.info(f"查询长度分析: 查询长度={query_length}, 类型={query_type}")
        return query_type

    def _get_granularity_weights(self, query_type: str) -> dict:
        """根据查询类型获取粒度权重"""
        weights = self.config.granularity_weights.get(query_type,
                                                     self.config.granularity_weights['medium'])
        logger.info(f"粒度权重配置: {query_type} -> {weights}")
        return weights

    def search(self, query: str) -> List[HierarchicalResult]:
        """智能粒度匹配的层次化混合检索"""
        if not self.child_chunks:
            return []

        # 智能粒度匹配：分析查询长度
        query_type = None
        granularity_weights = None
        if self.config.enable_intelligent_granularity:
            query_type = self._analyze_query_length(query)
            granularity_weights = self._get_granularity_weights(query_type)

        # 查询扩展
        if self.config.query_expansion:
            expanded_query = self.query_expander.expand_query(query)
        else:
            expanded_query = query

        # 第一级：子chunk级别的混合检索
        child_results = self._search_child_chunks(query, expanded_query)

        # 第二级：父chunk级别的聚合和重排序（应用智能粒度权重）
        hierarchical_results = self._aggregate_to_parent_level(child_results, granularity_weights)

        # 第三级：基于位置和语义连贯性的最终排序
        final_results = self._final_ranking(query, hierarchical_results, query_type)

        logger.info(f"智能粒度匹配检索完成: 查询类型={query_type}, 返回结果数={len(final_results)}")
        return final_results[:self.config.top_k]

    def _search_child_chunks(self, original_query: str, expanded_query: str) -> List[Dict]:
        """在子chunk级别进行混合检索"""
        # 1. 语义检索
        semantic_scores = self._semantic_search_children(original_query)

        # 2. BM25检索
        bm25_scores = self._bm25_search_children(expanded_query)

        # 3. 融合分数
        child_results = []
        for i, child_chunk in enumerate(self.child_chunks):
            semantic_score = semantic_scores.get(i, 0.0)
            bm25_score = bm25_scores.get(i, 0.0)

            # 加权融合
            hybrid_score = (self.config.semantic_weight * semantic_score +
                          self.config.bm25_weight * bm25_score)

            if hybrid_score >= self.config.min_score_threshold:
                child_results.append({
                    'child_index': i,
                    'child_chunk': child_chunk,
                    'semantic_score': semantic_score,
                    'bm25_score': bm25_score,
                    'hybrid_score': hybrid_score
                })

        # 按分数排序，取top_k
        child_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return child_results[:self.config.max_child_results]

    def _semantic_search_children(self, query: str) -> Dict[int, float]:
        """子chunk语义检索"""
        if self.child_embeddings is None or self.embedding_function is None:
            return {}

        try:
            # 生成查询向量
            query_embedding = self.embedding_function([query])[0]
            query_embedding = np.array(query_embedding).reshape(1, -1)

            # 计算相似度
            similarities = cosine_similarity(query_embedding, self.child_embeddings)[0]

            return {i: float(score) for i, score in enumerate(similarities)}
        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return {}

    def _bm25_search_children(self, query: str) -> Dict[int, float]:
        """子chunk BM25检索"""
        try:
            results = self.bm25_retriever.search(query, top_k=len(self.child_chunks))

            # 归一化分数
            if results:
                max_score = max(score for _, score in results) if results else 1.0
                if max_score > 0:
                    return {doc_idx: score / max_score for doc_idx, score in results}

            return {}
        except Exception as e:
            logger.error(f"BM25检索失败: {e}")
            return {}

    def _aggregate_to_parent_level(self, child_results: List[Dict], granularity_weights: dict = None) -> List[HierarchicalResult]:
        """聚合到父chunk级别（支持智能粒度权重）"""
        parent_aggregation = {}

        for child_result in child_results:
            child_chunk = child_result['child_chunk']
            parent_id = child_chunk.parent_id

            if parent_id not in parent_aggregation:
                parent_aggregation[parent_id] = {
                    'parent_chunk': self.parent_id_to_chunk[parent_id],
                    'child_results': [],
                    'max_score': 0.0,
                    'avg_score': 0.0
                }

            parent_aggregation[parent_id]['child_results'].append(child_result)
            parent_aggregation[parent_id]['max_score'] = max(
                parent_aggregation[parent_id]['max_score'],
                child_result['hybrid_score']
            )

        # 计算平均分数并创建层次化结果
        hierarchical_results = []
        for parent_id, agg_data in parent_aggregation.items():
            child_results = agg_data['child_results']
            avg_score = sum(r['hybrid_score'] for r in child_results) / len(child_results)
            agg_data['avg_score'] = avg_score

            # 为每个子chunk创建层次化结果
            for child_result in child_results:
                child_chunk = child_result['child_chunk']
                parent_chunk = agg_data['parent_chunk']

                # 计算高亮位置
                highlight_start = child_chunk.position.start_char
                highlight_end = child_chunk.position.end_char

                # 应用智能粒度权重调整分数
                adjusted_hybrid_score = child_result['hybrid_score']
                if granularity_weights:
                    # 子chunk分数 * 子chunk权重 + 父chunk平均分数 * 父chunk权重
                    adjusted_hybrid_score = (
                        child_result['hybrid_score'] * granularity_weights['child_weight'] +
                        avg_score * granularity_weights['parent_weight']
                    )

                hierarchical_result = HierarchicalResult(
                    child_chunk_id=child_chunk.id,
                    parent_chunk_id=parent_id,
                    child_content=child_chunk.content,
                    parent_content=parent_chunk.content,
                    position=child_chunk.position,
                    semantic_score=child_result['semantic_score'],
                    bm25_score=child_result['bm25_score'],
                    hybrid_score=adjusted_hybrid_score,  # 使用调整后的分数
                    final_score=0.0,  # 将在最终排序中计算
                    highlight_start=highlight_start,
                    highlight_end=highlight_end,
                    metadata={
                        'parent_max_score': agg_data['max_score'],
                        'parent_avg_score': avg_score,
                        'child_count': len(child_results),
                        'original_hybrid_score': child_result['hybrid_score'],  # 保存原始分数
                        'granularity_weights': granularity_weights,  # 保存权重信息
                        **parent_chunk.metadata
                    }
                )
                hierarchical_results.append(hierarchical_result)

        return hierarchical_results

    def _final_ranking(self, query: str, hierarchical_results: List[HierarchicalResult], query_type: str = None) -> List[HierarchicalResult]:
        """基于位置和语义连贯性的最终排序（支持查询类型优化）"""
        query_tokens = set(jieba.lcut(query.lower()))

        for result in hierarchical_results:
            # 基础分数
            base_score = result.hybrid_score

            # 位置权重：子chunk在父chunk中的位置
            position_bonus = self._calculate_position_bonus(result, query_tokens)

            # 语义连贯性权重：考虑相邻子chunk的相关性
            coherence_bonus = self._calculate_coherence_bonus(result)

            # 父chunk质量权重：考虑父chunk的整体质量
            parent_quality_bonus = self._calculate_parent_quality_bonus(result)

            # 根据查询类型调整权重
            position_weight = self.config.position_weight
            if query_type == 'short':
                # 短查询更注重精确匹配，减少位置权重
                position_weight *= 0.5
            elif query_type == 'long':
                # 长查询更注重上下文，增加位置权重
                position_weight *= 1.5

            # 计算最终分数
            result.final_score = (
                base_score +
                position_weight * position_bonus +
                0.05 * coherence_bonus +
                0.05 * parent_quality_bonus
            )

        # 按最终分数排序
        hierarchical_results.sort(key=lambda x: x.final_score, reverse=True)

        if query_type:
            logger.info(f"最终排序完成: 查询类型={query_type}, 结果数={len(hierarchical_results)}")

        return hierarchical_results

    def _calculate_position_bonus(self, result: HierarchicalResult, query_tokens: set) -> float:
        """计算位置权重"""
        content_tokens = jieba.lcut(result.child_content.lower())
        position_bonus = 0.0

        # 查询词在子chunk中的位置权重
        for i, token in enumerate(content_tokens):
            if token in query_tokens:
                # 位置越靠前权重越高
                position_bonus += 1.0 / (i + 1)

        # 子chunk在父chunk中的位置权重
        position_in_parent = result.position.start_char / len(result.parent_content)
        if position_in_parent < 0.3:  # 在前30%的位置
            position_bonus += 0.2
        elif position_in_parent < 0.6:  # 在前60%的位置
            position_bonus += 0.1

        return position_bonus

    def _calculate_coherence_bonus(self, result: HierarchicalResult) -> float:
        """计算语义连贯性权重"""
        # 简单实现：基于父chunk中子chunk的数量和分布
        child_count = result.metadata.get('child_count', 1)
        parent_avg_score = result.metadata.get('parent_avg_score', 0.0)

        # 如果父chunk有多个高分子chunk，给予连贯性奖励
        if child_count > 1 and parent_avg_score > 0.3:
            return min(0.3, child_count * 0.1)

        return 0.0

    def _calculate_parent_quality_bonus(self, result: HierarchicalResult) -> float:
        """计算父chunk质量权重"""
        parent_max_score = result.metadata.get('parent_max_score', 0.0)
        parent_avg_score = result.metadata.get('parent_avg_score', 0.0)

        # 父chunk的最高分和平均分都高时给予奖励
        if parent_max_score > 0.5 and parent_avg_score > 0.3:
            return 0.2
        elif parent_max_score > 0.3:
            return 0.1

        return 0.0

    def get_highlighted_content(self, result: HierarchicalResult, query: str) -> str:
        """获取带高亮的内容"""
        parent_content = result.parent_content
        start = result.highlight_start
        end = result.highlight_end

        # 构建高亮内容
        before = parent_content[:start]
        highlighted = parent_content[start:end]
        after = parent_content[end:]

        # 简单的高亮标记（可以根据前端需求调整）
        return f"{before}<mark>{highlighted}</mark>{after}"

    def get_context_window(self, result: HierarchicalResult, window_size: int = 100) -> str:
        """获取上下文窗口"""
        parent_content = result.parent_content
        start = max(0, result.highlight_start - window_size)
        end = min(len(parent_content), result.highlight_end + window_size)

        context = parent_content[start:end]

        # 标记实际匹配的部分
        relative_start = result.highlight_start - start
        relative_end = result.highlight_end - start

        if relative_start >= 0 and relative_end <= len(context):
            before = context[:relative_start]
            highlighted = context[relative_start:relative_end]
            after = context[relative_end:]
            return f"{before}<mark>{highlighted}</mark>{after}"

        return context


# 使用示例和测试函数
def create_hierarchical_retriever_example():
    """创建层次化检索器示例"""

    # 示例文档（模拟1000字的大文档）
    documents = [
        """人工智能的发展历程可以追溯到20世纪50年代。当时，科学家们开始探索让机器模拟人类智能的可能性。阿兰·图灵在1950年提出了著名的图灵测试，这成为了判断机器是否具有智能的重要标准。

机器学习是人工智能的一个重要分支，它使计算机能够在没有明确编程的情况下学习和改进。机器学习算法通过分析大量数据来识别模式，并使用这些模式来做出预测或决策。监督学习、无监督学习和强化学习是机器学习的三大主要类型。

深度学习是机器学习的一个子集，它模仿人脑神经网络的工作方式。深度学习使用多层神经网络来处理复杂的数据模式。卷积神经网络（CNN）在图像识别方面取得了突破性进展，而循环神经网络（RNN）和长短期记忆网络（LSTM）在自然语言处理领域表现出色。

自然语言处理（NLP）是人工智能的另一个重要领域，它专注于使计算机能够理解、解释和生成人类语言。近年来，Transformer架构的出现彻底改变了NLP领域。BERT、GPT等预训练模型在各种语言任务中都取得了显著的成果。""",

        """计算机视觉致力于使机器能够"看见"和理解视觉世界。从早期的边缘检测算法到现代的深度卷积网络，计算机视觉技术已经在人脸识别、物体检测、图像分割等任务中达到了人类水平的性能。

人工智能技术正在各个行业中得到广泛应用。在医疗健康领域，AI可以协助医生进行疾病诊断和治疗方案制定。在金融服务中，智能算法用于风险评估和欺诈检测。在教育领域，个性化学习系统能够根据学生的学习特点提供定制化的教学内容。

尽管人工智能取得了巨大进步，但仍面临许多挑战。数据隐私、算法偏见、就业影响等问题需要得到妥善解决。同时，人工智能的发展也带来了前所未有的机遇，它有望帮助人类解决气候变化、疾病治疗、教育普及等全球性挑战。"""
    ]

    # 配置
    config = HierarchicalConfig(
        parent_chunk_size=800,
        child_chunk_size=200,
        overlap_size=50,
        semantic_weight=0.6,
        bm25_weight=0.4,
        position_weight=0.1,
        top_k=5,
        query_expansion=True,
        smart_boundary=True
    )

    # 创建检索器
    retriever = HierarchicalRetriever(config)

    return retriever, documents


def test_hierarchical_retrieval():
    """测试层次化检索功能"""

    # 模拟embedding函数
    def mock_embedding_function(texts):
        # 简单的模拟embedding（实际使用时替换为真实的embedding函数）
        return [np.random.rand(1024) for _ in texts]

    # 创建检索器和文档
    retriever, documents = create_hierarchical_retriever_example()

    # 训练模型
    retriever.fit(documents, mock_embedding_function)

    # 测试查询
    test_queries = [
        "机器学习算法",
        "深度学习神经网络",
        "自然语言处理",
        "计算机视觉应用"
    ]

    print("=== 层次化检索测试结果 ===")
    for query in test_queries:
        print(f"\n查询: {query}")
        results = retriever.search(query)

        for i, result in enumerate(results[:3]):  # 只显示前3个结果
            print(f"  结果 {i+1}:")
            print(f"    子chunk: {result.child_content[:100]}...")
            print(f"    混合分数: {result.hybrid_score:.3f}")
            print(f"    最终分数: {result.final_score:.3f}")
            print(f"    位置: {result.position.start_char}-{result.position.end_char}")


if __name__ == "__main__":
    test_hierarchical_retrieval()
