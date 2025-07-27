"""
跨平台工具模块
提供跨平台兼容的路径处理、文件操作等功能
"""

import os
import sys
import platform
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Union, List
import logging

logger = logging.getLogger(__name__)


class PlatformUtils:
    """跨平台工具类"""
    
    @staticmethod
    def get_platform_info() -> dict:
        """获取平台信息"""
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "is_windows": platform.system().lower() == "windows",
            "is_macos": platform.system().lower() == "darwin",
            "is_linux": platform.system().lower() == "linux"
        }
    
    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录的绝对路径"""
        # 从当前文件向上查找，直到找到包含特定文件的目录
        current_path = Path(__file__).parent.absolute()
        
        # 查找标识文件
        markers = ["README.md", "package.json", ".git"]
        
        while current_path != current_path.parent:
            for marker in markers:
                if (current_path / marker).exists():
                    return current_path
            current_path = current_path.parent
        
        # 如果没找到，返回当前文件的父目录的父目录
        return Path(__file__).parent.parent.absolute()
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """确保目录存在，如果不存在则创建"""
        path_obj = Path(path)
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            return path_obj
        except Exception as e:
            logger.error(f"创建目录失败 {path}: {e}")
            raise
    
    @staticmethod
    def get_data_directory(subdir: str = "") -> Path:
        """获取数据目录路径 - 用于对话数据等"""
        project_root = PlatformUtils.get_project_root()
        data_dir = project_root / "data"

        if subdir:
            data_dir = data_dir / subdir

        return PlatformUtils.ensure_directory(data_dir)

    @staticmethod
    def get_chroma_data_directory() -> Path:
        """获取 ChromaDB 数据目录路径 - 直接在根目录下"""
        project_root = PlatformUtils.get_project_root()
        chroma_dir = project_root / "chromadbdata"
        return PlatformUtils.ensure_directory(chroma_dir)
    
    @staticmethod
    def get_config_file_path() -> Path:
        """获取配置文件路径"""
        project_root = PlatformUtils.get_project_root()
        return project_root / "config.json"
    
    @staticmethod
    def get_temp_directory() -> Path:
        """获取临时目录路径"""
        temp_dir = Path(tempfile.gettempdir()) / "chromadb_web_manager"
        return PlatformUtils.ensure_directory(temp_dir)
    
    @staticmethod
    def check_file_permissions(path: Union[str, Path]) -> dict:
        """检查文件权限"""
        path_obj = Path(path)
        
        if not path_obj.exists():
            return {
                "exists": False,
                "readable": False,
                "writable": False,
                "executable": False
            }
        
        return {
            "exists": True,
            "readable": os.access(path_obj, os.R_OK),
            "writable": os.access(path_obj, os.W_OK),
            "executable": os.access(path_obj, os.X_OK)
        }
    
    @staticmethod
    def safe_remove(path: Union[str, Path]) -> bool:
        """安全删除文件或目录"""
        try:
            path_obj = Path(path)
            if path_obj.is_file():
                path_obj.unlink()
            elif path_obj.is_dir():
                shutil.rmtree(path_obj)
            return True
        except Exception as e:
            logger.error(f"删除失败 {path}: {e}")
            return False
    
    @staticmethod
    def get_executable_extension() -> str:
        """获取可执行文件扩展名"""
        return ".exe" if platform.system().lower() == "windows" else ""
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> str:
        """标准化路径，确保跨平台兼容"""
        return str(Path(path).resolve())
    
    @staticmethod
    def get_environment_variable(name: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量，支持跨平台"""
        return os.environ.get(name, default)
    
    @staticmethod
    def set_environment_variable(name: str, value: str) -> None:
        """设置环境变量"""
        os.environ[name] = value


# 全局实例
platform_utils = PlatformUtils()
