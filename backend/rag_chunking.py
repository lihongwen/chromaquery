"""
RAG文档分块处理模块
支持三种分块方式：递归分块、固定字数分块、语义分块
"""

import re
import logging
import time
import numpy as np
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# 确保NLTK数据已下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("下载NLTK punkt tokenizer...")
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    logger.info("下载NLTK punkt_tab tokenizer...")
    nltk.download('punkt_tab', quiet=True)


class ChunkingMethod(str, Enum):
    """分块方式枚举"""
    RECURSIVE = "recursive"
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"


class ChunkingConfig(BaseModel):
    """分块配置"""
    method: ChunkingMethod
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: Optional[List[str]] = None
    semantic_threshold: Optional[float] = 0.7


class DocumentChunk(BaseModel):
    """文档块"""
    text: str
    index: int
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]


class ChunkingResult(BaseModel):
    """分块结果"""
    chunks: List[DocumentChunk]
    total_chunks: int
    method_used: ChunkingMethod
    processing_time: float
    original_length: int


class RAGChunker:
    """RAG文档分块器"""
    
    def __init__(self):
        self.default_separators = {
            ChunkingMethod.RECURSIVE: ["\n\n", "\n", "。", "！", "？", ";", ":", "，", " ", ""],
            ChunkingMethod.FIXED_SIZE: ["\n", " "],
            ChunkingMethod.SEMANTIC: ["\n\n", "\n", "。", "！", "？"]
        }
        self._embedding_function = None

    def _get_embedding_function(self):
        """获取嵌入函数（延迟加载）"""
        if self._embedding_function is None:
            try:
                from alibaba_embedding import create_alibaba_embedding_function
                self._embedding_function = create_alibaba_embedding_function(dimension=1024)
                logger.info("成功创建阿里云嵌入函数用于语义分块")
            except Exception as e:
                logger.error(f"创建阿里云嵌入函数失败: {e}")
                raise Exception(f"语义分块需要阿里云嵌入函数，但创建失败: {str(e)}")
        return self._embedding_function
    
    def chunk_text(self, text: str, config: ChunkingConfig) -> ChunkingResult:
        """
        对文本进行分块处理
        
        Args:
            text: 要分块的文本
            config: 分块配置
            
        Returns:
            分块结果
        """
        import time
        start_time = time.time()
        
        try:
            if config.method == ChunkingMethod.RECURSIVE:
                chunks = self._recursive_chunk(text, config)
            elif config.method == ChunkingMethod.FIXED_SIZE:
                chunks = self._fixed_size_chunk(text, config)
            elif config.method == ChunkingMethod.SEMANTIC:
                chunks = self._semantic_chunk(text, config)
            else:
                raise ValueError(f"不支持的分块方式: {config.method}")
            
            processing_time = time.time() - start_time
            
            return ChunkingResult(
                chunks=chunks,
                total_chunks=len(chunks),
                method_used=config.method,
                processing_time=processing_time,
                original_length=len(text)
            )
            
        except Exception as e:
            logger.error(f"文本分块失败: {e}")
            raise
    
    def _recursive_chunk(self, text: str, config: ChunkingConfig) -> List[DocumentChunk]:
        """递归分块"""
        separators = config.separators or self.default_separators[ChunkingMethod.RECURSIVE]
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False
        )
        
        chunks = splitter.split_text(text)
        return self._create_document_chunks(chunks, text, config.method)
    
    def _fixed_size_chunk(self, text: str, config: ChunkingConfig) -> List[DocumentChunk]:
        """固定字数分块"""
        separators = config.separators or self.default_separators[ChunkingMethod.FIXED_SIZE]
        
        splitter = CharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separator=separators[0] if separators else "\n",
            length_function=len
        )
        
        chunks = splitter.split_text(text)
        return self._create_document_chunks(chunks, text, config.method)
    
    def _semantic_chunk(self, text: str, config: ChunkingConfig) -> List[DocumentChunk]:
        """语义分块 - 基于语义相似度的智能分块"""
        try:
            logger.info(f"开始语义分块，文本长度: {len(text)}, 阈值: {config.semantic_threshold}")

            # 1. 将文本分割为句子
            sentences = self._split_into_sentences(text)
            if len(sentences) <= 1:
                # 如果只有一个句子或没有句子，直接返回
                return self._create_document_chunks([text], text, config.method)

            logger.info(f"分割为 {len(sentences)} 个句子")

            # 2. 计算句子的嵌入向量
            embeddings = self._get_sentence_embeddings(sentences)
            logger.info(f"生成 {len(embeddings)} 个嵌入向量")

            # 3. 计算相邻句子的语义相似度
            similarities = self._calculate_similarities(embeddings)
            logger.info(f"计算了 {len(similarities)} 个相似度值")

            # 4. 根据相似度阈值确定分割点
            split_points = self._find_split_points(similarities, config.semantic_threshold or 0.7)
            logger.info(f"找到 {len(split_points)} 个分割点")

            # 5. 根据分割点创建语义块
            chunks = self._create_semantic_chunks(sentences, split_points, config)
            logger.info(f"创建了 {len(chunks)} 个语义块")

            return self._create_document_chunks(chunks, text, config.method)

        except Exception as e:
            logger.error(f"语义分块失败，回退到段落分块: {e}")
            # 如果语义分块失败，回退到简单的段落分块
            return self._fallback_paragraph_chunk(text, config)
    
    def _create_document_chunks(
        self, 
        chunks: List[str], 
        original_text: str, 
        method: ChunkingMethod
    ) -> List[DocumentChunk]:
        """创建文档块对象"""
        document_chunks = []
        current_pos = 0
        
        for i, chunk_text in enumerate(chunks):
            # 在原文中查找块的位置
            start_pos = original_text.find(chunk_text, current_pos)
            if start_pos == -1:
                # 如果找不到精确匹配，使用估算位置
                start_pos = current_pos
            
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            metadata = {
                "chunk_method": method.value,
                "chunk_index": i,
                "chunk_size": len(chunk_text),
                "start_position": start_pos,
                "end_position": end_pos
            }
            
            document_chunks.append(DocumentChunk(
                text=chunk_text,
                index=i,
                start_pos=start_pos,
                end_pos=end_pos,
                metadata=metadata
            ))
        
        return document_chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        try:
            # 检测文本语言并选择合适的分割方法
            if self._is_chinese_text(text):
                # 中文文本使用正则表达式分割
                sentences = re.split(r'[。！？；;]+', text)
                logger.info("使用中文句子分割")
            else:
                # 英文文本使用NLTK分割
                sentences = sent_tokenize(text, language='english')
                logger.info("使用英文句子分割")

            # 过滤掉空句子和过短的句子
            filtered_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:  # 过滤掉过短的句子
                    filtered_sentences.append(sentence)

            logger.info(f"句子分割完成: {len(filtered_sentences)} 个句子")
            return filtered_sentences if filtered_sentences else [text]

        except Exception as e:
            logger.warning(f"句子分割失败，使用简单分割: {e}")
            # 回退到简单的句子分割
            sentences = re.split(r'[。！？.!?；;]+', text)
            return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _is_chinese_text(self, text: str) -> bool:
        """检测是否为中文文本"""
        chinese_chars = 0
        total_chars = 0

        for char in text:
            if char.strip():  # 忽略空白字符
                total_chars += 1
                if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                    chinese_chars += 1

        # 如果中文字符占比超过30%，认为是中文文本
        return total_chars > 0 and (chinese_chars / total_chars) > 0.3

    def _get_sentence_embeddings(self, sentences: List[str]) -> np.ndarray:
        """获取句子的嵌入向量"""
        try:
            embedding_func = self._get_embedding_function()
            logger.info(f"开始生成 {len(sentences)} 个句子的嵌入向量")

            # 阿里云API限制：批量大小不能超过10
            batch_size = 10
            all_embeddings = []

            for i in range(0, len(sentences), batch_size):
                batch = sentences[i:i + batch_size]
                logger.info(f"处理批次 {i//batch_size + 1}: {len(batch)} 个句子")

                try:
                    batch_embeddings = embedding_func(batch)
                    all_embeddings.extend(batch_embeddings)
                    logger.info(f"成功生成批次 {i//batch_size + 1} 的嵌入向量")
                except Exception as e:
                    logger.error(f"批次 {i//batch_size + 1} 嵌入向量生成失败: {e}")
                    raise e

            # 转换为numpy数组
            embeddings_array = np.array(all_embeddings)
            logger.info(f"所有嵌入向量生成完成，形状: {embeddings_array.shape}")
            return embeddings_array

        except Exception as e:
            logger.error(f"获取句子嵌入向量失败: {e}")
            raise e

    def _calculate_similarities(self, embeddings: np.ndarray) -> List[float]:
        """计算相邻句子的语义相似度"""
        similarities = []

        for i in range(len(embeddings) - 1):
            # 计算相邻句子的余弦相似度
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)

        return similarities

    def _find_split_points(self, similarities: List[float], threshold: float) -> List[int]:
        """根据相似度阈值找到分割点"""
        split_points = []

        for i, sim in enumerate(similarities):
            # 当相似度低于阈值时，在此处分割
            if sim < threshold:
                split_points.append(i + 1)  # 在下一个句子前分割

        return split_points

    def _create_semantic_chunks(self, sentences: List[str], split_points: List[int], config: ChunkingConfig) -> List[str]:
        """根据分割点创建语义块"""
        chunks = []
        start_idx = 0

        # 添加所有分割点
        all_split_points = split_points + [len(sentences)]

        for split_point in all_split_points:
            # 合并句子形成块
            chunk_sentences = sentences[start_idx:split_point]
            if chunk_sentences:
                chunk_text = ' '.join(chunk_sentences)

                # 检查块大小，如果太大则进一步分割
                if len(chunk_text) > config.chunk_size:
                    # 如果块太大，按大小限制进一步分割
                    sub_chunks = self._split_large_chunk(chunk_text, config.chunk_size, config.chunk_overlap)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)

            start_idx = split_point

        return chunks

    def _split_large_chunk(self, text: str, max_size: int, overlap: int) -> List[str]:
        """分割过大的块"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + max_size

            if end >= len(text):
                # 最后一块
                chunks.append(text[start:])
                break

            # 尝试在句子边界分割
            chunk = text[start:end]
            last_sentence_end = max(
                chunk.rfind('。'),
                chunk.rfind('！'),
                chunk.rfind('？'),
                chunk.rfind('.'),
                chunk.rfind('!'),
                chunk.rfind('?')
            )

            if last_sentence_end > 0:
                # 在句子边界分割
                chunks.append(text[start:start + last_sentence_end + 1])
                start = start + last_sentence_end + 1 - overlap
            else:
                # 没有找到句子边界，强制分割
                chunks.append(chunk)
                start = end - overlap

        return chunks

    def _fallback_paragraph_chunk(self, text: str, config: ChunkingConfig) -> List[DocumentChunk]:
        """回退的段落分块方法"""
        logger.info("使用回退的段落分块方法")

        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        if not paragraphs:
            paragraphs = [text]

        chunks = []
        current_chunk = ""
        current_size = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 如果当前段落加上现有块超过大小限制，则创建新块
            if current_size + len(paragraph) > config.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
                current_size = len(paragraph)
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                    current_size += len(paragraph) + 2
                else:
                    current_chunk = paragraph
                    current_size = len(paragraph)

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())

        return self._create_document_chunks(chunks, text, config.method)


def get_default_chunking_config(method: ChunkingMethod) -> ChunkingConfig:
    """获取默认分块配置"""
    configs = {
        ChunkingMethod.RECURSIVE: ChunkingConfig(
            method=ChunkingMethod.RECURSIVE,
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "？", ";", ":", "，"]
        ),
        ChunkingMethod.FIXED_SIZE: ChunkingConfig(
            method=ChunkingMethod.FIXED_SIZE,
            chunk_size=500,
            chunk_overlap=50
        ),
        ChunkingMethod.SEMANTIC: ChunkingConfig(
            method=ChunkingMethod.SEMANTIC,
            chunk_size=800,
            chunk_overlap=100,
            semantic_threshold=0.7
        )
    }
    return configs.get(method, configs[ChunkingMethod.RECURSIVE])



