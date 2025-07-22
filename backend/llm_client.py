"""
LLM客户端模块
处理与阿里云通义千问LLM的交互
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    """阿里云通义千问LLM客户端"""
    
    def __init__(self):
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        self.model_name = 'qwen-turbo'
        self.base_url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
        
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY环境变量未设置")
    
    def format_context(self, query_results: List[Dict[str, Any]], user_query: str) -> str:
        """
        将ChromaDB查询结果格式化为LLM上下文
        
        Args:
            query_results: ChromaDB查询结果列表
            user_query: 用户查询文本
            
        Returns:
            格式化的上下文字符串
        """
        if not query_results:
            return f"""用户问题：{user_query}

**没有找到相关文档**

抱歉，我在知识库中没有找到与您的问题相关的文档内容。这可能是因为：
1. 知识库中没有相关信息
2. 查询关键词与文档内容匹配度较低
3. 相似度阈值设置过于严格

建议您：
- 尝试使用不同的关键词重新提问
- 降低相似度阈值设置
- 确认相关文档已上传到集合中

请注意：由于没有找到相关文档，我无法基于知识库内容为您提供准确的回答。"""
        
        context_parts = ["基于以下相关文档内容，请回答用户的问题：\n"]
        
        for i, result in enumerate(query_results, 1):
            similarity = (1 - result.get('distance', 0)) * 100
            collection_name = result.get('collection_name', '未知集合')
            document = result.get('document', '')
            
            # 限制单个文档的长度，避免上下文过长
            max_doc_length = 800
            if len(document) > max_doc_length:
                document = document[:max_doc_length] + "..."
            
            context_parts.append(
                f"文档{i}（相似度：{similarity:.1f}%，来源：{collection_name}）：\n{document}\n"
            )
        
        context_parts.append(f"\n用户问题：{user_query}")
        context_parts.append("\n请基于上述文档内容提供准确、有用的回答。如果文档中没有相关信息，请明确说明。请用中文回答。")
        
        return "\n".join(context_parts)
    
    def create_prompt(self, context: str) -> List[Dict[str, str]]:
        """
        创建LLM提示消息
        
        Args:
            context: 格式化的上下文
            
        Returns:
            消息列表
        """
        return [
            {
                "role": "system",
                "content": "你是一个专业的AI助手，擅长基于提供的文档内容回答用户问题。请仔细阅读文档内容，提供准确、有用的回答。如果文档中没有相关信息，请诚实地说明。回答要简洁明了，重点突出。"
            },
            {
                "role": "user", 
                "content": context
            }
        ]
    
    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式聊天接口
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            流式响应数据块
        """
        try:
            import dashscope
            from dashscope import Generation
            import asyncio

            # 设置API密钥
            dashscope.api_key = self.api_key

            # 构建请求参数 - 使用非流式调用来避免DashScope流式API的bug
            request_params = {
                'model': self.model_name,
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': False  # 使用非流式调用
            }

            logger.info(f"开始LLM请求（非流式+模拟流式），模型：{self.model_name}")

            # 调用非流式API
            response = Generation.call(**request_params)

            if response.status_code == 200:
                # 解析响应
                output = response.output
                if output and 'text' in output:
                    full_content = output['text']
                    usage = response.usage if hasattr(response, 'usage') else None

                    logger.info(f"完整内容长度: {len(full_content)} 字符")

                    # 模拟流式效果：将完整内容分块发送
                    chunk_size = 2  # 每次发送2个字符
                    for i in range(0, len(full_content), chunk_size):
                        chunk = full_content[i:i + chunk_size]

                        # 发送当前块
                        yield {
                            'content': chunk,
                            'finish_reason': None,
                            'usage': None
                        }

                        # 添加小延迟模拟流式效果
                        await asyncio.sleep(0.05)  # 50ms延迟

                    # 发送完成信号
                    yield {
                        'content': '',
                        'finish_reason': 'stop',
                        'usage': usage
                    }

                    logger.info("LLM模拟流式请求完成")
                else:
                    logger.warning(f"响应中没有text字段: {output}")
                    yield {
                        'content': '',
                        'finish_reason': 'error',
                        'error': '响应格式错误'
                    }
            else:
                error_msg = f"LLM API调用失败，状态码：{response.status_code}"
                if hasattr(response, 'message'):
                    error_msg += f"，错误信息：{response.message}"

                logger.error(error_msg)
                yield {
                    'content': '',
                    'finish_reason': 'error',
                    'error': error_msg
                }
                    
        except ImportError:
            error_msg = "dashscope库未安装，请运行：pip install dashscope"
            logger.error(error_msg)
            yield {
                'content': '',
                'finish_reason': 'error',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"LLM调用异常：{str(e)}"
            logger.error(error_msg)
            yield {
                'content': '',
                'finish_reason': 'error',
                'error': error_msg
            }
    
    async def query_with_context(
        self,
        query_results: List[Dict[str, Any]],
        user_query: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        基于查询结果和用户问题进行LLM问答
        
        Args:
            query_results: ChromaDB查询结果
            user_query: 用户查询
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            流式响应数据块
        """
        # 格式化上下文
        context = self.format_context(query_results, user_query)
        
        # 创建提示消息
        messages = self.create_prompt(context)
        
        # 流式调用LLM
        async for chunk in self.stream_chat(messages, temperature, max_tokens):
            yield chunk

# 全局LLM客户端实例
llm_client = None

def get_llm_client() -> LLMClient:
    """获取LLM客户端实例"""
    global llm_client
    if llm_client is None:
        llm_client = LLMClient()
    return llm_client

def init_llm_client():
    """初始化LLM客户端"""
    global llm_client
    try:
        llm_client = LLMClient()
        logger.info("LLM客户端初始化成功")
    except Exception as e:
        logger.error(f"LLM客户端初始化失败：{e}")
        raise
