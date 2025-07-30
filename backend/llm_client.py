"""
LLM客户端模块
支持多个LLM提供商（DeepSeek和阿里云通义千问）
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
    """多提供商LLM客户端"""

    def __init__(self, provider: str = None, config: Dict = None):
        """
        初始化LLM客户端

        Args:
            provider: LLM提供商 ("deepseek" 或 "alibaba")
            config: 提供商配置
        """
        # 如果没有提供配置，从配置管理器获取
        if provider is None or config is None:
            try:
                from config_manager import ConfigManager
                config_manager = ConfigManager()
                current_config = config_manager.get_current_llm_config()
                self.provider = current_config["provider"]
                self.config = current_config["config"]
            except Exception as e:
                logger.warning(f"无法从配置管理器获取LLM配置，使用默认配置: {e}")
                # 使用默认配置
                self.provider = "alibaba"
                self.config = {
                    "api_key": os.getenv('DASHSCOPE_API_KEY', ''),
                    "api_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": "qwen-plus"
                }
        else:
            self.provider = provider
            self.config = config

        # 验证配置
        self._validate_config()

        # 设置提供商特定的属性
        self._setup_provider()

    def _validate_config(self):
        """验证配置"""
        if not self.config.get("api_key"):
            raise ValueError(f"{self.provider} API密钥未设置")

        if not self.config.get("model"):
            raise ValueError(f"{self.provider} 模型未设置")

    def _setup_provider(self):
        """设置提供商特定的属性"""
        self.api_key = self.config["api_key"]
        self.model_name = self.config["model"]
        self.api_endpoint = self.config.get("api_endpoint", "")

        if self.provider == "deepseek":
            if not self.api_endpoint:
                self.api_endpoint = "https://api.deepseek.com"
        elif self.provider == "alibaba":
            if not self.api_endpoint:
                self.api_endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
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

**检索结果：没有找到相关文档**

根据提供的文档内容，我无法找到与您问题相关的信息。

可能的原因：
1. 知识库中没有相关信息
2. 查询关键词与文档内容匹配度较低
3. 相似度阈值设置过于严格

建议您：
- 检查文档是否包含相关内容
- 尝试使用不同的关键词重新查询
- 降低相似度阈值设置
- 确认相关文档已上传到集合中"""
        
        context_parts = ["基于以下相关文档内容，请回答用户的问题：\n"]
        
        for i, result in enumerate(query_results, 1):
            similarity = (1 - result.get('distance', 0)) * 100
            collection_name = result.get('collection_name', '未知集合')
            document = result.get('document', '')
            metadata = result.get('metadata', {})

            # 限制单个文档的长度，避免上下文过长
            max_doc_length = 600  # 减少document长度为metadata留出空间
            if len(document) > max_doc_length:
                document = document[:max_doc_length] + "..."

            # 构建文档内容部分
            doc_content = f"文档{i}（相似度：{similarity:.1f}%，来源：{collection_name}）：\n"
            doc_content += f"内容：{document}\n"

            # 添加重要的元数据信息
            if metadata:
                important_metadata = []

                # 提取重要的表格元数据（以table_开头的字段）
                table_fields = {k: v for k, v in metadata.items() if k.startswith('table_') and v is not None and str(v).strip() != '' and str(v) != 'nan'}

                # 选择最重要的元数据字段显示
                priority_fields = [
                    'table_案件编号', 'table_序号', 'table_案件标的额 （万元）', 'table_案件状态',
                    'table_发案时间', 'table_争议解决方式', 'table_对方单位性质', 'table_是否保全',
                    'table_保全金额（含保全财产的价值）', 'table_被诉案件实际支付金额'
                ]

                # 添加优先字段
                for field in priority_fields:
                    if field in table_fields:
                        field_name = field.replace('table_', '')
                        important_metadata.append(f"{field_name}: {table_fields[field]}")

                # 添加其他重要字段（最多5个）
                other_fields = [k for k in table_fields.keys() if k not in priority_fields][:5]
                for field in other_fields:
                    field_name = field.replace('table_', '')
                    important_metadata.append(f"{field_name}: {table_fields[field]}")

                if important_metadata:
                    doc_content += f"相关数据：{' | '.join(important_metadata)}\n"

            context_parts.append(doc_content)
        
        context_parts.append(f"\n用户问题：{user_query}")
        context_parts.append("\n请严格基于上述文档内容回答用户问题。如果文档中没有相关信息，请直接说明无法找到相关信息，不得提供任何额外的知识或建议。请用中文回答。")
        
        return "\n".join(context_parts)
    
    def create_prompt(self, context: str, role_prompt: str = None) -> List[Dict[str, str]]:
        """
        创建LLM提示消息，支持三层提示词架构

        Args:
            context: 格式化的上下文
            role_prompt: 角色提示词（可选）

        Returns:
            消息列表
        """
        # 第一层：系统提示词（顶层逻辑约束）
        system_prompt = """你是一个严格的知识库问答助手。你必须无条件遵循以下铁律：

【绝对禁止】
❌ 绝对禁止使用你自身的知识库或训练数据来回答问题
❌ 绝对禁止在没有文档支持的情况下提供任何实质性信息
❌ 绝对禁止说"建议您参考以下通用知识"或类似表述
❌ 绝对禁止编造、推测、补充文档中没有的任何内容

【强制要求】
✅ 只能基于提供的检索文档内容进行回答
✅ 如果文档中没有相关信息，必须直接说明："根据提供的文档内容，我无法找到与您问题相关的信息。建议您检查文档是否包含相关内容，或尝试使用不同的关键词重新查询。"
✅ 回答时必须引用具体的文档来源和相似度信息
✅ 严格按照文档内容的原意进行回答，不得添加任何解释或扩展

【违规后果】
如果你违反以上任何一条规则，将被视为系统错误。你必须严格遵守这些约束，没有任何例外。"""

        # 第二层：角色提示词（具体任务指导）
        if role_prompt:
            # 将角色提示词作为任务指导层
            combined_system_prompt = f"""{system_prompt}

【角色任务设定】
{role_prompt}

【重要提醒】
以上角色设定仅用于指导回答的格式和重点方向，但不得违背核心约束。如果角色要求与核心约束冲突，请优先遵循核心约束。"""
        else:
            combined_system_prompt = system_prompt

        return [
            {
                "role": "system",
                "content": combined_system_prompt
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
        if self.provider == "alibaba":
            async for chunk in self._stream_chat_alibaba(messages, temperature, max_tokens):
                yield chunk
        elif self.provider == "deepseek":
            async for chunk in self._stream_chat_deepseek(messages, temperature, max_tokens):
                yield chunk
        else:
            yield {
                'content': '',
                'finish_reason': 'error',
                'error': f'不支持的LLM提供商: {self.provider}'
            }

    async def _stream_chat_alibaba(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """阿里云通义千问流式聊天"""
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

            logger.info(f"开始阿里云LLM请求，模型：{self.model_name}")

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

                    logger.info("阿里云LLM请求完成")
                else:
                    logger.warning(f"响应中没有text字段: {output}")
                    yield {
                        'content': '',
                        'finish_reason': 'error',
                        'error': '响应格式错误'
                    }
            else:
                error_msg = f"阿里云LLM API调用失败，状态码：{response.status_code}"
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
            error_msg = f"阿里云LLM调用异常：{str(e)}"
            logger.error(error_msg)
            yield {
                'content': '',
                'finish_reason': 'error',
                'error': error_msg
            }

    async def _stream_chat_deepseek(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """DeepSeek流式聊天"""
        try:
            import httpx
            import json

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False  # 暂时使用非流式，后续可以改为流式
            }

            logger.info(f"开始DeepSeek LLM请求，模型：{self.model_name}")
            logger.info(f"请求参数: max_tokens={max_tokens}, temperature={temperature}")
            logger.info(f"消息数量: {len(messages)}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_endpoint}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"DeepSeek完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        usage = result.get("usage")
                        finish_reason = result["choices"][0].get("finish_reason")

                        logger.info(f"DeepSeek响应长度: {len(content)} 字符")
                        logger.info(f"DeepSeek完成原因: {finish_reason}")
                        logger.info(f"DeepSeek使用情况: {usage}")

                        # 模拟流式效果
                        chunk_size = 2
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i + chunk_size]

                            yield {
                                'content': chunk,
                                'finish_reason': None,
                                'usage': None
                            }

                            await asyncio.sleep(0.05)

                        # 发送完成信号
                        yield {
                            'content': '',
                            'finish_reason': 'stop',
                            'usage': usage
                        }

                        logger.info("DeepSeek LLM请求完成")
                    else:
                        yield {
                            'content': '',
                            'finish_reason': 'error',
                            'error': 'DeepSeek响应格式错误'
                        }
                else:
                    error_msg = f"DeepSeek API调用失败，状态码：{response.status_code}"
                    try:
                        error_detail = response.json()
                        if "error" in error_detail:
                            error_msg += f"，错误信息：{error_detail['error']}"
                    except:
                        pass

                    logger.error(error_msg)
                    yield {
                        'content': '',
                        'finish_reason': 'error',
                        'error': error_msg
                    }

        except ImportError:
            error_msg = "httpx库未安装，请运行：pip install httpx"
            logger.error(error_msg)
            yield {
                'content': '',
                'finish_reason': 'error',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"DeepSeek LLM调用异常：{str(e)}"
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
        max_tokens: int = 2000,
        role_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        基于查询结果和用户问题进行LLM问答，支持角色提示词

        Args:
            query_results: ChromaDB查询结果
            user_query: 用户查询
            temperature: 温度参数
            max_tokens: 最大token数
            role_id: 角色ID（可选）

        Yields:
            流式响应数据块
        """
        # 格式化上下文
        context = self.format_context(query_results, user_query)

        # 获取角色提示词
        role_prompt = None
        if role_id:
            try:
                # 导入角色管理器
                from role_manager import role_manager
                role = role_manager.get_role(role_id)
                if role and role.is_active:
                    role_prompt = role.prompt
                    logger.info(f"使用角色提示词: {role.name}")
                else:
                    logger.warning(f"角色不存在或未启用: {role_id}")
            except Exception as e:
                logger.warning(f"获取角色提示词失败: {e}")

        # 创建提示消息
        messages = self.create_prompt(context, role_prompt)

        # 流式调用LLM
        async for chunk in self.stream_chat(messages, temperature, max_tokens):
            yield chunk

# 全局LLM客户端实例
llm_client = None

def get_llm_client() -> Optional[LLMClient]:
    """获取LLM客户端实例"""
    global llm_client
    try:
        # 每次都重新创建客户端以确保使用最新配置
        llm_client = LLMClient()
        return llm_client
    except Exception as e:
        logger.error(f"获取LLM客户端失败：{e}")
        return None

def init_llm_client():
    """初始化LLM客户端"""
    global llm_client
    try:
        llm_client = LLMClient()
        logger.info("LLM客户端初始化成功")
        return llm_client
    except Exception as e:
        logger.error(f"LLM客户端初始化失败：{e}")
        return None

def create_llm_client(provider: str, config: Dict) -> Optional[LLMClient]:
    """创建指定配置的LLM客户端"""
    try:
        return LLMClient(provider=provider, config=config)
    except Exception as e:
        logger.error(f"创建LLM客户端失败：{e}")
        return None
