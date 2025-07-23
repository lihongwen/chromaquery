#!/usr/bin/env python3
"""
智能粒度匹配功能测试脚本
测试不同长度查询的检索效果
"""

import sys
import os
import logging
from typing import List

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from hybrid_retrieval import HierarchicalRetriever, HierarchicalConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_embedding_function():
    """创建模拟的embedding函数"""
    import numpy as np
    
    def mock_embedding(texts: List[str]) -> List[List[float]]:
        """简单的模拟embedding函数"""
        embeddings = []
        for text in texts:
            # 基于文本长度和内容创建简单的向量
            vector = np.random.rand(384).tolist()  # 384维向量
            embeddings.append(vector)
        return embeddings
    
    return mock_embedding

def test_intelligent_granularity_matching():
    """测试智能粒度匹配功能"""
    logger.info("开始测试智能粒度匹配功能")
    
    # 创建配置
    config = HierarchicalConfig(
        parent_chunk_size=1000,
        child_chunk_size=200,
        overlap_size=50,
        enable_intelligent_granularity=True,
        query_expansion=False  # 暂时关闭查询扩展以便测试
    )
    
    # 创建检索器
    retriever = HierarchicalRetriever(config)
    
    # 准备测试文档
    test_documents = [
        """
        人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，
        并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、
        语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，
        应用领域也不断扩大，可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。
        人工智能可以对人的意识、思维的信息过程的模拟。人工智能不是人的智能，但能像人那样思考、
        也可能超过人的智能。
        """,
        """
        机器学习是人工智能的一个重要分支，它是一种通过算法使计算机系统能够自动学习和改进的技术。
        机器学习算法通过分析大量数据来识别模式，并使用这些模式来对新数据进行预测或决策。
        主要的机器学习方法包括监督学习、无监督学习和强化学习。监督学习使用标记的训练数据来学习
        输入和输出之间的映射关系。无监督学习则在没有标记数据的情况下发现数据中的隐藏模式。
        强化学习通过与环境的交互来学习最优的行为策略。
        """,
        """
        深度学习是机器学习的一个子领域，它基于人工神经网络的结构和功能。深度学习模型由多层
        神经网络组成，能够学习数据的复杂表示。卷积神经网络（CNN）在图像识别任务中表现出色，
        循环神经网络（RNN）和长短期记忆网络（LSTM）在序列数据处理方面很有效。近年来，
        Transformer架构的出现革命性地改变了自然语言处理领域，GPT和BERT等模型都基于这种架构。
        深度学习在计算机视觉、自然语言处理、语音识别等领域都取得了突破性进展。
        """
    ]
    
    # 训练检索器
    logger.info("训练检索器...")
    embedding_function = create_mock_embedding_function()
    retriever.fit(test_documents, embedding_function)
    
    # 测试不同长度的查询
    test_queries = [
        # 短查询（<150字符）
        ("什么是AI", "short"),
        ("机器学习算法", "short"),
        ("深度学习", "short"),
        
        # 中查询（150-300字符）
        ("人工智能的主要应用领域有哪些，包括机器人、语言识别等技术，这些技术如何在实际生活中发挥作用，对人类社会产生什么样的影响？", "medium"),
        ("机器学习中的监督学习和无监督学习有什么区别，它们分别适用于什么样的场景，在实际应用中如何选择合适的学习方法？", "medium"),
        
        # 长查询（>300字符）
        ("请详细解释深度学习的发展历程，从最初的人工神经网络到现在的Transformer架构，包括卷积神经网络在图像识别中的应用，循环神经网络在序列数据处理中的作用，以及GPT和BERT等大型语言模型如何革命性地改变了自然语言处理领域，这些技术进步对计算机视觉、语音识别等相关领域产生了什么样的深远影响？", "long")
    ]
    
    logger.info("开始测试不同长度查询的检索效果")
    
    for query, expected_type in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"测试查询: {query}")
        logger.info(f"查询长度: {len(query)} 字符")
        logger.info(f"预期类型: {expected_type}")
        
        # 执行检索
        results = retriever.search(query)
        
        logger.info(f"检索结果数量: {len(results)}")
        
        # 显示前3个结果
        for i, result in enumerate(results[:3]):
            logger.info(f"\n结果 {i+1}:")
            logger.info(f"  最终分数: {result.final_score:.4f}")
            logger.info(f"  混合分数: {result.hybrid_score:.4f}")
            logger.info(f"  语义分数: {result.semantic_score:.4f}")
            logger.info(f"  BM25分数: {result.bm25_score:.4f}")
            logger.info(f"  子chunk内容: {result.child_content[:100]}...")
            
            # 显示智能粒度匹配信息
            if 'granularity_weights' in result.metadata and result.metadata['granularity_weights']:
                weights = result.metadata['granularity_weights']
                logger.info(f"  粒度权重: 子chunk={weights['child_weight']}, 父chunk={weights['parent_weight']}")
                if 'original_hybrid_score' in result.metadata:
                    logger.info(f"  原始分数: {result.metadata['original_hybrid_score']:.4f}")
    
    logger.info(f"\n{'='*60}")
    logger.info("智能粒度匹配功能测试完成")

if __name__ == "__main__":
    test_intelligent_granularity_matching()
