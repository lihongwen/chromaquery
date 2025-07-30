"""
Ollama嵌入模型集成
支持本地运行的Ollama嵌入模型，如mxbai-embed-large、nomic-embed-text等
"""

import logging
from typing import List, Optional, Union
import requests
import json
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

logger = logging.getLogger(__name__)


class OllamaEmbeddingFunction(EmbeddingFunction):
    """
    Ollama嵌入函数
    支持本地运行的Ollama嵌入模型
    """
    
    def __init__(
        self,
        model_name: str = "mxbai-embed-large",
        base_url: str = "http://localhost:11434",
        timeout: int = 60
    ):
        """
        初始化Ollama嵌入函数
        
        Args:
            model_name: 嵌入模型名称，如 'mxbai-embed-large', 'nomic-embed-text', 'all-minilm'
            base_url: Ollama服务器地址，默认为 http://localhost:11434
            timeout: 请求超时时间（秒）
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.embed_url = f"{self.base_url}/api/embed"
        
        # 验证Ollama服务是否可用
        self._check_ollama_service()
        
        # 验证模型是否可用
        self._check_model_availability()
        
        logger.info(f"初始化Ollama嵌入函数: 模型={model_name}, 服务器={base_url}")
    
    def _check_ollama_service(self):
        """检查Ollama服务是否运行"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Ollama服务不可用，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"无法连接到Ollama服务 ({self.base_url}): {str(e)}")
    
    def _check_model_availability(self):
        """检查指定模型是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model['name'] for model in models_data.get('models', [])]

                # 检查完整模型名称（包括版本号）
                model_found = False
                for available_model in available_models:
                    # 支持完整匹配或基础名称匹配
                    if (available_model == self.model_name or
                        available_model.split(':')[0] == self.model_name or
                        available_model.split(':')[0] == self.model_name.split(':')[0]):
                        model_found = True
                        # 如果用户指定的是基础名称，更新为完整名称
                        if ':' not in self.model_name and ':' in available_model:
                            logger.info(f"找到模型的完整版本: {available_model}")
                            self.model_name = available_model
                        break

                if not model_found:
                    logger.warning(f"模型 '{self.model_name}' 未找到。")
                    logger.info(f"可用模型: {available_models}")
                    logger.info(f"尝试拉取模型 '{self.model_name}'...")
                    self._pull_model()
                else:
                    logger.info(f"模型 '{self.model_name}' 已可用")
        except Exception as e:
            logger.warning(f"检查模型可用性时出错: {e}")
    
    def _pull_model(self):
        """拉取指定的模型"""
        try:
            pull_data = {"name": self.model_name}
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=pull_data,
                timeout=300  # 拉取模型可能需要较长时间
            )
            
            if response.status_code == 200:
                logger.info(f"成功拉取模型 '{self.model_name}'")
            else:
                logger.error(f"拉取模型失败: {response.status_code} - {response.text}")
                raise Exception(f"无法拉取模型 '{self.model_name}'")
        except requests.exceptions.RequestException as e:
            logger.error(f"拉取模型时网络错误: {e}")
            raise Exception(f"拉取模型 '{self.model_name}' 失败: {str(e)}")
    
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
            # Ollama支持批量处理，但为了稳定性，我们逐个处理
            embeddings = []
            
            for text in texts:
                # 构建请求数据
                request_data = {
                    "model": self.model_name,
                    "input": text
                }
                
                # 发送请求
                response = requests.post(
                    self.embed_url,
                    json=request_data,
                    timeout=self.timeout
                )
                
                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"Ollama API请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # 解析响应
                result = response.json()
                
                # 检查响应格式
                if "embeddings" not in result:
                    error_msg = f"Ollama API响应格式错误，缺少embeddings字段: {result}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                # 提取嵌入向量
                embedding = result["embeddings"]
                if isinstance(embedding, list) and len(embedding) > 0:
                    # 如果是嵌套列表，取第一个
                    if isinstance(embedding[0], list):
                        embedding = embedding[0]
                    embeddings.append(embedding)
                else:
                    raise Exception(f"无效的嵌入向量格式: {embedding}")
            
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
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model_name},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"无法获取模型信息: {response.status_code}"}
        except Exception as e:
            return {"error": f"获取模型信息失败: {str(e)}"}

    @staticmethod
    def get_available_models(base_url: str = "http://localhost:11434") -> dict:
        """获取所有可用的Ollama模型"""
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])

                # 分类模型：嵌入模型和其他模型
                embedding_models = []
                other_models = []

                for model in models:
                    model_name = model['name']
                    model_info = {
                        'name': model_name,
                        'size': model.get('size', 0),
                        'modified_at': model.get('modified_at', ''),
                        'digest': model.get('digest', '')
                    }

                    # 检查是否是嵌入模型（通过名称判断）
                    if any(keyword in model_name.lower() for keyword in ['embed', 'embedding']):
                        embedding_models.append(model_info)
                    else:
                        other_models.append(model_info)

                return {
                    "success": True,
                    "embedding_models": embedding_models,
                    "other_models": other_models,
                    "total_models": len(models)
                }
            else:
                return {
                    "success": False,
                    "error": f"获取模型列表失败: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"连接Ollama服务失败: {str(e)}"
            }


def create_ollama_embedding_function(
    model_name: str = "mxbai-embed-large",
    base_url: str = "http://localhost:11434",
    timeout: int = 60
) -> OllamaEmbeddingFunction:
    """
    创建Ollama嵌入函数的便捷方法
    
    Args:
        model_name: 嵌入模型名称
        base_url: Ollama服务器地址
        timeout: 请求超时时间
        
    Returns:
        Ollama嵌入函数实例
    """
    return OllamaEmbeddingFunction(
        model_name=model_name,
        base_url=base_url,
        timeout=timeout
    )


# 推荐的嵌入模型列表（用于参考，不限制用户选择）
RECOMMENDED_EMBEDDING_MODELS = [
    {
        "name": "mxbai-embed-large",
        "description": "高质量嵌入模型，334M参数",
        "dimension": 1024,
        "recommended": True
    },
    {
        "name": "nomic-embed-text",
        "description": "轻量级嵌入模型，137M参数",
        "dimension": 768,
        "recommended": True
    },
    {
        "name": "all-minilm",
        "description": "超轻量级嵌入模型，23M参数",
        "dimension": 384,
        "recommended": True
    },
    {
        "name": "snowflake-arctic-embed",
        "description": "Snowflake Arctic嵌入模型，高质量",
        "dimension": 1024,
        "recommended": True
    }
]


def get_recommended_models() -> List[dict]:
    """获取推荐的嵌入模型列表"""
    return RECOMMENDED_EMBEDDING_MODELS


def get_model_dimension(model_name: str) -> Optional[int]:
    """获取指定模型的向量维度（从推荐列表中查找）"""
    # 移除版本号进行匹配
    base_name = model_name.split(':')[0]
    for model in RECOMMENDED_EMBEDDING_MODELS:
        if model["name"] == base_name or model["name"] == model_name:
            return model["dimension"]
    return None  # 对于未知模型，返回None，让系统自动检测
