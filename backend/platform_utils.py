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
                "executable": False,
                "is_windows": platform.system().lower() == "windows"
            }

        result = {
            "exists": True,
            "readable": os.access(path_obj, os.R_OK),
            "writable": os.access(path_obj, os.W_OK),
            "executable": os.access(path_obj, os.X_OK),
            "is_windows": platform.system().lower() == "windows"
        }

        # Windows特殊检查
        if platform.system().lower() == "windows":
            try:
                import stat
                file_stat = path_obj.stat()
                result["is_readonly"] = not (file_stat.st_mode & stat.S_IWRITE)
                result["is_hidden"] = bool(file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN) if hasattr(file_stat, 'st_file_attributes') else False
            except Exception as e:
                logger.warning(f"Windows文件属性检查失败: {e}")
                result["is_readonly"] = False
                result["is_hidden"] = False

        return result
    
    @staticmethod
    def safe_remove(path: Union[str, Path]) -> bool:
        """安全删除文件或目录"""
        try:
            path_obj = Path(path)

            # Windows特殊处理：处理文件锁定问题
            if platform.system().lower() == "windows":
                import time
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if path_obj.is_file():
                            # Windows下可能需要先移除只读属性
                            if path_obj.exists():
                                path_obj.chmod(0o777)
                            path_obj.unlink()
                        elif path_obj.is_dir():
                            # Windows下递归移除只读属性
                            for root, dirs, files in os.walk(path_obj):
                                for d in dirs:
                                    os.chmod(os.path.join(root, d), 0o777)
                                for f in files:
                                    os.chmod(os.path.join(root, f), 0o777)
                            shutil.rmtree(path_obj)
                        return True
                    except (PermissionError, OSError) as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"删除失败，重试 {attempt + 1}/{max_retries}: {e}")
                            time.sleep(0.5)
                        else:
                            raise e
            else:
                # Unix系统的标准删除
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

    @staticmethod
    def is_valid_windows_path(path: Union[str, Path]) -> bool:
        """检查路径在Windows下是否有效"""
        if platform.system().lower() != "windows":
            return True

        path_str = str(path)

        # Windows路径长度限制
        if len(path_str) > 260:
            logger.warning(f"路径长度超过Windows限制(260字符): {len(path_str)}")
            return False

        # Windows保留名称检查
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        path_parts = Path(path_str).parts
        for part in path_parts:
            if part.upper().split('.')[0] in reserved_names:
                logger.warning(f"路径包含Windows保留名称: {part}")
                return False

        # Windows非法字符检查
        illegal_chars = '<>:"|?*'
        for char in illegal_chars:
            if char in path_str:
                logger.warning(f"路径包含非法字符: {char}")
                return False

        return True

    @staticmethod
    def get_windows_long_path(path: Union[str, Path]) -> str:
        """获取Windows长路径格式（支持超过260字符的路径）"""
        if platform.system().lower() != "windows":
            return str(path)

        path_str = str(Path(path).absolute())

        # 如果路径已经是长路径格式，直接返回
        if path_str.startswith('\\\\?\\'):
            return path_str

        # 如果路径长度超过240字符，转换为长路径格式
        if len(path_str) > 240:
            if path_str.startswith('\\\\'):
                # UNC路径
                return '\\\\?\\UNC\\' + path_str[2:]
            else:
                # 本地路径
                return '\\\\?\\' + path_str

        return path_str

    @staticmethod
    def create_windows_shortcut(target_path: Union[str, Path], shortcut_path: Union[str, Path]) -> bool:
        """在Windows下创建快捷方式"""
        if platform.system().lower() != "windows":
            logger.warning("快捷方式创建仅在Windows下支持")
            return False

        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(target_path)
            shortcut.save()
            return True
        except ImportError:
            logger.warning("创建快捷方式需要安装pywin32: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"创建快捷方式失败: {e}")
            return False


# 全局实例
platform_utils = PlatformUtils()
