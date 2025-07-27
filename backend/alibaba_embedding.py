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


class AlibabaDashScopeEmbeddingFunction(EmbeddingFunction):
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
            api_key: 阿里云API密钥，如果为None则从配置文件或环境变量获取
            model_name: 模型名称，默认为text-embedding-v4
            dimension: 向量维度，默认为1024
            endpoint: API端点
        """
        # 优先级：传入的api_key > 配置文件中的api_key > 环境变量
        if api_key:
            self.api_key = api_key
        else:
            # 尝试从配置文件获取
            try:
                from config_manager import config_manager
                alibaba_config = config_manager.get_alibaba_config()
                self.api_key = alibaba_config.get("api_key", "").strip()
            except Exception as e:
                logger.warning(f"无法从配置文件获取API密钥: {e}")
                self.api_key = ""

            # 如果配置文件中没有，则从环境变量获取
            if not self.api_key:
                self.api_key = os.getenv("DASHSCOPE_API_KEY", "")

        if not self.api_key:
            raise ValueError("阿里云API密钥未设置，请在设置页面配置API密钥、设置DASHSCOPE_API_KEY环境变量或传入api_key参数")
        
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


def verify_alibaba_api_key(api_key: str, model_name: str = "text-embedding-v4") -> dict:
    """
    验证阿里云API密钥是否有效

    Args:
        api_key: 要验证的API密钥
        model_name: 模型名称

    Returns:
        验证结果字典，包含success、message等字段
    """
    if not api_key or not api_key.strip():
        return {
            "success": False,
            "message": "API密钥不能为空"
        }

    try:
        # 创建测试嵌入函数
        test_embedding_func = AlibabaDashScopeEmbeddingFunction(
            api_key=api_key.strip(),
            model_name=model_name,
            dimension=1024
        )

        # 执行简单的测试
        test_text = "测试文本"
        embeddings = test_embedding_func([test_text])

        if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 0:
            return {
                "success": True,
                "message": f"API密钥验证成功，模型 {model_name} 可正常使用",
                "model_name": model_name,
                "vector_dimension": len(embeddings[0])
            }
        else:
            return {
                "success": False,
                "message": "API密钥验证失败：返回的嵌入向量为空"
            }

    except ValueError as e:
        error_msg = str(e)
        if "API密钥未设置" in error_msg:
            return {
                "success": False,
                "message": "API密钥格式错误或为空"
            }
        else:
            return {
                "success": False,
                "message": f"API密钥验证失败：{error_msg}"
            }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {
                "success": False,
                "message": "API密钥无效或已过期"
            }
        elif "403" in error_msg or "Forbidden" in error_msg:
            return {
                "success": False,
                "message": "API密钥权限不足，请检查是否有访问该模型的权限"
            }
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            return {
                "success": False,
                "message": "API配额不足或达到调用限制"
            }
        else:
            return {
                "success": False,
                "message": f"API密钥验证失败：{error_msg}"
            }



