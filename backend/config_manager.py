"""
配置管理模块
管理ChromaDB数据存储路径和相关配置
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from platform_utils import platform_utils

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        # 使用跨平台工具获取项目根目录
        self.project_root = platform_utils.get_project_root()
        self.config_file = platform_utils.get_config_file_path()
        self.default_chroma_path = platform_utils.get_chroma_data_directory()
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        default_config = {
            "chroma_db_path": str(self.default_chroma_path),
            "path_history": [str(self.default_chroma_path)],
            "last_updated": datetime.now().isoformat(),
            "max_history_count": 10,
            # 嵌入模型配置
            "embedding_config": {
                "default_provider": "alibaba",  # "alibaba" 或 "ollama"
                "alibaba": {
                    "model": "text-embedding-v4",
                    "dimension": 1024,
                    "api_key": "",  # 用户配置的API密钥
                    "verified": False,  # 验证状态
                    "last_verified": None  # 最后验证时间
                },
                "ollama": {
                    "model": "mxbai-embed-large",
                    "base_url": "http://localhost:11434",
                    "timeout": 60,
                    "verified": False,  # 验证状态
                    "last_verified": None  # 最后验证时间
                }
            },
            # LLM模型配置
            "llm_config": {
                "default_provider": "alibaba",  # "deepseek" 或 "alibaba"
                "deepseek": {
                    "api_key": "",
                    "api_endpoint": "https://api.deepseek.com",
                    "model": "deepseek-chat",
                    "models": [
                        {
                            "name": "deepseek-chat",
                            "display_name": "DeepSeek Chat",
                            "description": "通用对话模型，适合日常问答和文档处理",
                            "max_tokens": 4096,
                            "recommended": True
                        },
                        {
                            "name": "deepseek-reasoner",
                            "display_name": "DeepSeek Reasoner",
                            "description": "推理增强模型，适合复杂分析和逻辑推理任务",
                            "max_tokens": 8192,
                            "recommended": False
                        }
                    ],
                    "verified": False,
                    "last_verified": None,
                    "verification_error": None
                },
                "alibaba": {
                    "api_key": "",
                    "api_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": "qwen-plus",
                    "models": [
                        {
                            "name": "qwen-plus",
                            "display_name": "通义千问Plus",
                            "description": "平衡性能和成本的通用模型",
                            "max_tokens": 8192,
                            "recommended": True
                        },
                        {
                            "name": "qwen-max-latest",
                            "display_name": "通义千问Max",
                            "description": "最强性能模型，适合复杂任务",
                            "max_tokens": 8192,
                            "recommended": False
                        },
                        {
                            "name": "qwen-turbo-2025-07-15",
                            "display_name": "通义千问Turbo",
                            "description": "快速响应模型，适合简单任务",
                            "max_tokens": 8192,
                            "recommended": False
                        }
                    ],
                    "verified": False,
                    "last_verified": None,
                    "verification_error": None
                }
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保必要的字段存在
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return default_config
        else:
            # 创建默认配置文件
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict = None) -> bool:
        """保存配置文件"""
        try:
            config_to_save = config or self._config
            config_to_save["last_updated"] = datetime.now().isoformat()

            # 确保配置目录存在
            platform_utils.ensure_directory(self.config_file.parent)

            # Windows特殊处理：确保文件不是只读的
            if platform_utils.get_platform_info()["is_windows"] and self.config_file.exists():
                try:
                    import stat
                    self.config_file.chmod(stat.S_IWRITE | stat.S_IREAD)
                except Exception as e:
                    logger.warning(f"移除配置文件只读属性失败: {e}")

            # 使用临时文件写入，然后原子性替换（Windows安全写入）
            temp_config_file = self.config_file.with_suffix('.tmp')
            try:
                with open(temp_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)

                # 原子性替换
                if platform_utils.get_platform_info()["is_windows"]:
                    # Windows下需要先删除目标文件
                    if self.config_file.exists():
                        self.config_file.unlink()
                temp_config_file.replace(self.config_file)

            except Exception as e:
                # 清理临时文件
                if temp_config_file.exists():
                    temp_config_file.unlink()
                raise e

            if config:
                self._config = config

            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get_chroma_db_path(self) -> str:
        """获取当前ChromaDB数据路径（绝对路径）"""
        path = self._config.get("chroma_db_path", str(self.default_chroma_path))
        return str(Path(path).absolute())
    
    def set_chroma_db_path(self, new_path: str) -> bool:
        """设置新的ChromaDB数据路径"""
        try:
            # 转换为绝对路径
            abs_path = str(Path(new_path).absolute())
            
            # 验证路径
            if not self.validate_path(abs_path):
                return False
            
            # 更新配置
            old_path = self._config["chroma_db_path"]
            self._config["chroma_db_path"] = abs_path
            
            # 更新历史记录
            self._add_to_history(abs_path)
            
            # 保存配置
            if self._save_config():
                logger.info(f"ChromaDB路径已更新: {old_path} -> {abs_path}")
                return True
            else:
                # 回滚
                self._config["chroma_db_path"] = old_path
                return False
                
        except Exception as e:
            logger.error(f"设置ChromaDB路径失败: {e}")
            return False
    
    def validate_path(self, path: str) -> bool:
        """验证路径有效性"""
        try:
            path_obj = Path(path)

            # 检查路径是否为绝对路径
            if not path_obj.is_absolute():
                logger.warning(f"路径必须是绝对路径: {path}")
                return False

            # Windows特殊验证
            if platform_utils.get_platform_info()["is_windows"]:
                if not platform_utils.is_valid_windows_path(path):
                    logger.error(f"路径在Windows下无效: {path}")
                    return False

            # 如果路径不存在，尝试创建
            if not path_obj.exists():
                try:
                    platform_utils.ensure_directory(path_obj)
                    logger.info(f"已创建目录: {path}")
                except Exception as e:
                    logger.error(f"无法创建目录 {path}: {e}")
                    return False

            # 检查是否为目录
            if not path_obj.is_dir():
                logger.warning(f"路径不是目录: {path}")
                return False

            # 检查读写权限
            if not os.access(path, os.R_OK | os.W_OK):
                logger.warning(f"路径没有读写权限: {path}")
                return False

            # Windows特殊检查：确保不是只读目录
            if platform_utils.get_platform_info()["is_windows"]:
                permissions = platform_utils.check_file_permissions(path_obj)
                if permissions.get("is_readonly", False):
                    logger.error(f"目录是只读的: {path}")
                    return False

            return True

        except Exception as e:
            logger.error(f"验证路径失败 {path}: {e}")
            return False
    
    def _add_to_history(self, path: str):
        """添加路径到历史记录"""
        history = self._config.get("path_history", [])
        
        # 移除重复项
        if path in history:
            history.remove(path)
        
        # 添加到开头
        history.insert(0, path)
        
        # 限制历史记录数量
        max_count = self._config.get("max_history_count", 10)
        if len(history) > max_count:
            history = history[:max_count]
        
        self._config["path_history"] = history
    
    def get_path_history(self) -> List[str]:
        """获取路径历史记录"""
        return self._config.get("path_history", [])
    
    def remove_from_history(self, path: str) -> bool:
        """从历史记录中移除路径"""
        try:
            history = self._config.get("path_history", [])
            if path in history:
                history.remove(path)
                self._config["path_history"] = history
                return self._save_config()
            return True
        except Exception as e:
            logger.error(f"移除历史记录失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self._config["chroma_db_path"] = str(self.default_chroma_path)
            self._add_to_history(str(self.default_chroma_path))
            return self._save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def get_path_info(self, path: str) -> Dict:
        """获取路径信息"""
        try:
            path_obj = Path(path)
            info = {
                "path": str(path_obj.absolute()),
                "exists": path_obj.exists(),
                "is_directory": path_obj.is_dir() if path_obj.exists() else False,
                "readable": os.access(path, os.R_OK) if path_obj.exists() else False,
                "writable": os.access(path, os.W_OK) if path_obj.exists() else False,
                "collections_count": 0,
                "size_mb": 0
            }
            
            if path_obj.exists() and path_obj.is_dir():
                # 检查是否有chroma.sqlite3文件（ChromaDB的标识）
                chroma_db_file = path_obj / "chroma.sqlite3"
                if chroma_db_file.exists():
                    info["collections_count"] = self._count_collections(path)
                    info["size_mb"] = self._calculate_directory_size(path_obj)
            
            return info
            
        except Exception as e:
            logger.error(f"获取路径信息失败 {path}: {e}")
            return {
                "path": path,
                "exists": False,
                "is_directory": False,
                "readable": False,
                "writable": False,
                "collections_count": 0,
                "size_mb": 0,
                "error": str(e)
            }
    
    def _count_collections(self, path: str) -> int:
        """统计路径下的集合数量"""
        try:
            # 这里可以通过读取chroma.sqlite3来获取准确的集合数量
            # 暂时使用简单的目录计数方法
            path_obj = Path(path)
            collection_dirs = [d for d in path_obj.iterdir() 
                             if d.is_dir() and len(d.name) == 36]  # UUID格式的目录
            return len(collection_dirs)
        except Exception:
            return 0
    
    def _calculate_directory_size(self, path: Path) -> float:
        """计算目录大小（MB）"""
        try:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0

    # 嵌入模型配置管理方法
    def get_embedding_config(self) -> Dict:
        """获取嵌入模型配置"""
        return self._config.get("embedding_config", {})

    def set_embedding_config(self, config: Dict) -> bool:
        """设置嵌入模型配置"""
        try:
            if "embedding_config" not in self._config:
                self._config["embedding_config"] = {}

            # 更新配置
            self._config["embedding_config"].update(config)

            # 保存配置
            if self._save_config():
                logger.info(f"嵌入模型配置已更新: {config}")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"设置嵌入模型配置失败: {e}")
            return False

    def get_default_embedding_provider(self) -> str:
        """获取默认嵌入模型提供商"""
        embedding_config = self.get_embedding_config()
        return embedding_config.get("default_provider", "alibaba")

    def set_default_embedding_provider(self, provider: str) -> bool:
        """设置默认嵌入模型提供商"""
        if provider not in ["alibaba", "ollama"]:
            logger.error(f"不支持的嵌入模型提供商: {provider}")
            return False

        return self.set_embedding_config({"default_provider": provider})

    def get_alibaba_config(self) -> Dict:
        """获取阿里云嵌入模型配置"""
        embedding_config = self.get_embedding_config()
        return embedding_config.get("alibaba", {
            "model": "text-embedding-v4",
            "dimension": 1024,
            "api_key": "",
            "verified": False,
            "last_verified": None
        })

    def set_alibaba_config(self, config: Dict) -> bool:
        """设置阿里云嵌入模型配置"""
        return self.set_embedding_config({"alibaba": config})

    def get_ollama_config(self) -> Dict:
        """获取Ollama嵌入模型配置"""
        embedding_config = self.get_embedding_config()
        return embedding_config.get("ollama", {
            "model": "mxbai-embed-large",
            "base_url": "http://localhost:11434",
            "timeout": 60,
            "verified": False,
            "last_verified": None
        })

    def set_ollama_config(self, config: Dict) -> bool:
        """设置Ollama嵌入模型配置"""
        return self.set_embedding_config({"ollama": config})

    def get_current_embedding_config(self) -> Dict:
        """获取当前使用的嵌入模型配置"""
        provider = self.get_default_embedding_provider()
        embedding_config = self.get_embedding_config()

        if provider == "ollama":
            return {
                "provider": "ollama",
                "config": self.get_ollama_config()
            }
        else:
            return {
                "provider": "alibaba",
                "config": self.get_alibaba_config()
            }

    def set_provider_verification_status(self, provider: str, verified: bool, error_message: str = None) -> bool:
        """设置提供商的验证状态"""
        if provider not in ["alibaba", "ollama"]:
            logger.error(f"不支持的嵌入模型提供商: {provider}")
            return False

        current_config = self.get_embedding_config()
        provider_config = current_config.get(provider, {})

        provider_config["verified"] = verified
        provider_config["last_verified"] = datetime.now().isoformat()

        if error_message:
            provider_config["verification_error"] = error_message
        elif "verification_error" in provider_config:
            del provider_config["verification_error"]

        return self.set_embedding_config({provider: provider_config})

    # LLM配置管理方法
    def get_llm_config(self) -> Dict:
        """获取LLM配置"""
        return self._config.get("llm_config", {
            "default_provider": "alibaba",
            "deepseek": {
                "api_key": "",
                "api_endpoint": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "models": [],
                "verified": False,
                "last_verified": None,
                "verification_error": None
            },
            "alibaba": {
                "api_key": "",
                "api_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-plus",
                "models": [],
                "verified": False,
                "last_verified": None,
                "verification_error": None
            }
        })

    def set_llm_config(self, config: Dict) -> bool:
        """设置LLM配置"""
        try:
            current_config = self.get_llm_config()
            current_config.update(config)
            self._config["llm_config"] = current_config
            self._config["last_updated"] = datetime.now().isoformat()
            return self._save_config()
        except Exception as e:
            logger.error(f"设置LLM配置失败: {e}")
            return False

    def get_default_llm_provider(self) -> str:
        """获取默认LLM提供商"""
        llm_config = self.get_llm_config()
        return llm_config.get("default_provider", "alibaba")

    def set_default_llm_provider(self, provider: str) -> bool:
        """设置默认LLM提供商"""
        if provider not in ["deepseek", "alibaba"]:
            logger.error(f"不支持的LLM提供商: {provider}")
            return False

        return self.set_llm_config({"default_provider": provider})

    def get_deepseek_config(self) -> Dict:
        """获取DeepSeek配置"""
        llm_config = self.get_llm_config()
        return llm_config.get("deepseek", {
            "api_key": "",
            "api_endpoint": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "models": [],
            "verified": False,
            "last_verified": None,
            "verification_error": None
        })

    def set_deepseek_config(self, config: Dict) -> bool:
        """设置DeepSeek配置"""
        return self.set_llm_config({"deepseek": config})

    def get_alibaba_llm_config(self) -> Dict:
        """获取阿里云LLM配置"""
        llm_config = self.get_llm_config()
        return llm_config.get("alibaba", {
            "api_key": "",
            "api_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "models": [],
            "verified": False,
            "last_verified": None,
            "verification_error": None
        })

    def set_alibaba_llm_config(self, config: Dict) -> bool:
        """设置阿里云LLM配置"""
        return self.set_llm_config({"alibaba": config})

    def get_current_llm_config(self) -> Dict:
        """获取当前使用的LLM配置"""
        provider = self.get_default_llm_provider()
        llm_config = self.get_llm_config()

        if provider == "deepseek":
            return {
                "provider": "deepseek",
                "config": self.get_deepseek_config()
            }
        else:
            return {
                "provider": "alibaba",
                "config": self.get_alibaba_llm_config()
            }

    def set_llm_provider_verification_status(self, provider: str, verified: bool, error_message: str = None) -> bool:
        """设置LLM提供商的验证状态"""
        if provider not in ["deepseek", "alibaba"]:
            logger.error(f"不支持的LLM提供商: {provider}")
            return False

        current_config = self.get_llm_config()
        provider_config = current_config.get(provider, {})

        provider_config["verified"] = verified
        provider_config["last_verified"] = datetime.now().isoformat()

        if error_message:
            provider_config["verification_error"] = error_message
        elif "verification_error" in provider_config:
            del provider_config["verification_error"]

        return self.set_llm_config({provider: provider_config})

    def get_provider_verification_status(self, provider: str) -> Dict:
        """获取提供商的验证状态"""
        if provider not in ["alibaba", "ollama"]:
            return {"verified": False, "error": "不支持的提供商"}

        config = self.get_alibaba_config() if provider == "alibaba" else self.get_ollama_config()

        return {
            "verified": config.get("verified", False),
            "last_verified": config.get("last_verified"),
            "error": config.get("verification_error")
        }

    def get_verified_providers(self) -> List[str]:
        """获取已验证的提供商列表"""
        verified_providers = []

        alibaba_status = self.get_provider_verification_status("alibaba")
        if alibaba_status["verified"]:
            verified_providers.append("alibaba")

        ollama_status = self.get_provider_verification_status("ollama")
        if ollama_status["verified"]:
            verified_providers.append("ollama")

        return verified_providers

    def is_provider_configured_and_verified(self, provider: str) -> bool:
        """检查提供商是否已配置并验证"""
        if provider == "alibaba":
            config = self.get_alibaba_config()
            return bool(config.get("api_key", "").strip()) and config.get("verified", False)
        elif provider == "ollama":
            config = self.get_ollama_config()
            return config.get("verified", False)
        return False

# 全局配置管理器实例
config_manager = ConfigManager()
