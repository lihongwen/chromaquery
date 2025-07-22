"""
阿里云百炼平台嵌入模型集成
支持text-embedding-v4模型，生成1024维向量
"""

import os
import requests
import json
import logging
from typing import List, Optional
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

logger = logging.getLogger(__name__)


class AlibabaDashScopeEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    阿里云百炼平台嵌入函数
    使用text-embedding-v4模型生成1024维向量
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-v4",
        dimension: int = 1024,
        endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    ):
        """
        初始化阿里云嵌入函数
        
        Args:
            api_key: 阿里云API密钥，如果为None则从环境变量DASHSCOPE_API_KEY获取
            model_name: 模型名称，默认为text-embedding-v4
            dimension: 向量维度，默认为1024
            endpoint: API端点
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("阿里云API密钥未设置，请设置DASHSCOPE_API_KEY环境变量或传入api_key参数")
        
        self.model_name = model_name
        self.dimension = dimension
        self.endpoint = endpoint
        
        # 验证模型和维度配置
        if model_name in ["text-embedding-v3", "text-embedding-v4"]:
            if dimension not in [64, 128, 256, 512, 768, 1024]:
                if model_name == "text-embedding-v4" and dimension in [1536, 2048]:
                    pass  # v4支持更高维度
                else:
                    raise ValueError(f"模型{model_name}不支持{dimension}维度")
        
        logger.info(f"初始化阿里云嵌入函数: 模型={model_name}, 维度={dimension}")
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        生成文档的嵌入向量
        
        Args:
            input: 输入文档列表
            
        Returns:
            嵌入向量列表
        """
        if not input:
            return []
        
        # 确保输入是列表格式
        texts = list(input) if isinstance(input, (list, tuple)) else [input]
        
        try:
            # 构建请求数据
            request_data = {
                "model": self.model_name,
                "input": {
                    "texts": texts
                },
                "parameters": {
                    "dimension": self.dimension
                }
            }
            
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 发送请求
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"阿里云API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 解析响应
            result = response.json()

            # 打印完整响应用于调试
            logger.info(f"阿里云API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

            # 检查API响应是否包含错误
            if "error" in result or "code" in result:
                error_msg = f"阿里云API返回错误: {result.get('message', result.get('error', '未知错误'))} - 完整响应: {result}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 检查是否有输出数据
            if "output" not in result or "embeddings" not in result["output"]:
                error_msg = f"阿里云API响应格式错误，缺少embeddings数据: {result}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 提取嵌入向量
            embeddings = []
            for embedding_data in result["output"]["embeddings"]:
                embeddings.append(embedding_data["embedding"])
            
            logger.info(f"成功生成{len(embeddings)}个嵌入向量，维度: {len(embeddings[0]) if embeddings else 0}")
            return embeddings
            
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"生成嵌入向量时发生错误: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)


def create_alibaba_embedding_function(
    api_key: Optional[str] = None,
    dimension: int = 1024
) -> AlibabaDashScopeEmbeddingFunction:
    """
    创建阿里云嵌入函数的便捷方法
    
    Args:
        api_key: API密钥
        dimension: 向量维度
        
    Returns:
        阿里云嵌入函数实例
    """
    return AlibabaDashScopeEmbeddingFunction(
        api_key=api_key,
        dimension=dimension
    )



