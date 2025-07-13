"""
RAG文档分块处理模块
支持三种分块方式：递归分块、固定字数分块、语义分块
"""

import re
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)

logger = logging.getLogger(__name__)


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
        """语义分块"""
        # 简化的语义分块实现
        # 在实际项目中，可以使用更复杂的语义相似度计算
        
        # 首先按段落分割
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


# 测试函数
def test_chunking():
    """测试分块功能"""
    test_text = """
    这是第一段文本。它包含了一些基本信息。
    
    这是第二段文本。它提供了更多的详细信息。
    
    第三段文本包含了总结性的内容。它帮助读者理解整体概念。
    
    最后一段文本提供了结论和展望。
    """
    
    chunker = RAGChunker()
    
    # 测试递归分块
    config = get_default_chunking_config(ChunkingMethod.RECURSIVE)
    config.chunk_size = 100
    config.chunk_overlap = 20
    
    result = chunker.chunk_text(test_text, config)
    
    print(f"分块方式: {result.method_used}")
    print(f"总块数: {result.total_chunks}")
    print(f"处理时间: {result.processing_time:.3f}秒")
    print(f"原文长度: {result.original_length}")
    
    for chunk in result.chunks:
        print(f"\n块 {chunk.index}: {chunk.text[:50]}...")
        print(f"位置: {chunk.start_pos}-{chunk.end_pos}")


if __name__ == "__main__":
    test_chunking()
