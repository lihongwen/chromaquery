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

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        # 获取项目根目录的绝对路径
        self.project_root = Path(__file__).parent.parent.absolute()
        self.config_file = self.project_root / config_file
        self.default_chroma_path = self.project_root / "chroma_data"
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        default_config = {
            "chroma_db_path": str(self.default_chroma_path),
            "path_history": [str(self.default_chroma_path)],
            "last_updated": datetime.now().isoformat(),
            "max_history_count": 10
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
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
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
            
            # 如果路径不存在，尝试创建
            if not path_obj.exists():
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
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

# 全局配置管理器实例
config_manager = ConfigManager()
