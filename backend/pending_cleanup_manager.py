"""
待清理管理器
处理因文件锁定无法立即删除的段文件夹
在应用启动时批量清理
"""

import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import platform_utils

logger = logging.getLogger(__name__)

class PendingCleanupManager:
    """待清理管理器"""
    
    def __init__(self, chroma_path: Path):
        self.chroma_path = chroma_path
        self.cleanup_file = platform_utils.PlatformUtils.get_project_root() / "pending_cleanup.json"
        self._ensure_cleanup_file()
    
    def _ensure_cleanup_file(self):
        """确保清理记录文件存在"""
        if not self.cleanup_file.exists():
            initial_data = {
                "pending_cleanup": [],
                "completed_cleanup": [],
                "last_startup_cleanup": None
            }
            self._save_cleanup_data(initial_data)
    
    def _load_cleanup_data(self) -> Dict[str, Any]:
        """加载清理数据"""
        try:
            with open(self.cleanup_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载清理数据失败: {e}")
            return {
                "pending_cleanup": [],
                "completed_cleanup": [],
                "last_startup_cleanup": None
            }
    
    def _save_cleanup_data(self, data: Dict[str, Any]):
        """保存清理数据"""
        try:
            with open(self.cleanup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存清理数据失败: {e}")
    
    def add_pending_cleanup(self, segment_dirs: List[str], collection_id: str, collection_name: str = ""):
        """添加待清理的段文件夹"""
        if not segment_dirs:
            return
        
        data = self._load_cleanup_data()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for segment_id in segment_dirs:
            # 检查是否已存在
            existing = any(item['segment_id'] == segment_id for item in data['pending_cleanup'])
            if existing:
                continue
            
            # 计算文件夹大小
            segment_dir = self.chroma_path / segment_id
            size_info = self._get_dir_size(segment_dir)
            
            cleanup_item = {
                "segment_id": segment_id,
                "collection_id": collection_id,
                "collection_name": collection_name,
                "created_time": timestamp,
                "file_size": size_info,
                "attempts": 0,
                "last_attempt": None
            }
            
            data['pending_cleanup'].append(cleanup_item)
            logger.info(f"添加待清理项: {segment_id} (集合: {collection_name})")
        
        self._save_cleanup_data(data)
    
    def _get_dir_size(self, dir_path: Path) -> str:
        """获取目录大小"""
        try:
            if not dir_path.exists():
                return "0B"
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
            
            # 格式化大小
            for unit in ['B', 'KB', 'MB', 'GB']:
                if total_size < 1024.0:
                    return f"{total_size:.1f}{unit}"
                total_size /= 1024.0
            return f"{total_size:.1f}TB"
        except Exception:
            return "未知"
    
    def startup_cleanup(self) -> Dict[str, Any]:
        """启动时清理待处理的段文件夹"""
        data = self._load_cleanup_data()
        startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not data['pending_cleanup']:
            logger.info("启动清理：无待清理项")
            return {"cleaned": 0, "failed": 0, "items": []}
        
        logger.info(f"启动清理：发现 {len(data['pending_cleanup'])} 个待清理项")
        
        cleaned_count = 0
        failed_count = 0
        results = []
        
        # 复制列表，避免迭代时修改
        pending_items = data['pending_cleanup'].copy()
        
        for item in pending_items:
            segment_id = item['segment_id']
            segment_dir = self.chroma_path / segment_id
            
            item['attempts'] += 1
            item['last_attempt'] = startup_time
            
            if not segment_dir.exists():
                # 文件夹已不存在，移除记录
                data['pending_cleanup'].remove(item)
                item['cleanup_time'] = startup_time
                item['cleanup_status'] = "已不存在"
                data['completed_cleanup'].append(item)
                results.append({"segment_id": segment_id, "status": "已不存在"})
                cleaned_count += 1
                logger.info(f"清理项已不存在: {segment_id}")
                continue
            
            # 尝试删除
            try:
                self._safe_remove_directory(segment_dir)
                
                # 删除成功，移动到已完成列表
                data['pending_cleanup'].remove(item)
                item['cleanup_time'] = startup_time
                item['cleanup_status'] = "成功"
                data['completed_cleanup'].append(item)
                results.append({"segment_id": segment_id, "status": "成功"})
                cleaned_count += 1
                logger.info(f"启动清理成功: {segment_dir}")
                
            except Exception as e:
                # 删除失败，保留在待清理列表
                item['last_error'] = str(e)
                results.append({"segment_id": segment_id, "status": f"失败: {e}"})
                failed_count += 1
                logger.warning(f"启动清理失败: {segment_dir} - {e}")
                
                # 如果尝试次数过多，移动到失败列表
                if item['attempts'] >= 5:
                    data['pending_cleanup'].remove(item)
                    item['cleanup_time'] = startup_time
                    item['cleanup_status'] = f"最终失败: {e}"
                    data['completed_cleanup'].append(item)
                    logger.error(f"清理项最终失败: {segment_id}")
        
        # 更新最后清理时间
        data['last_startup_cleanup'] = startup_time
        self._save_cleanup_data(data)
        
        summary = {
            "cleaned": cleaned_count,
            "failed": failed_count,
            "items": results,
            "timestamp": startup_time
        }
        
        logger.info(f"启动清理完成: 成功 {cleaned_count}, 失败 {failed_count}")
        return summary
    
    def _safe_remove_directory(self, dir_path: Path):
        """安全删除目录"""
        import stat
        
        # Windows特殊处理：移除只读属性
        if os.name == 'nt':  # Windows
            for root, dirs, files in os.walk(dir_path):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), stat.S_IWRITE)
                    except:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    except:
                        pass
        
        # 删除目录
        shutil.rmtree(dir_path)
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """获取清理状态"""
        data = self._load_cleanup_data()
        return {
            "pending_count": len(data['pending_cleanup']),
            "completed_count": len(data['completed_cleanup']),
            "last_startup_cleanup": data['last_startup_cleanup'],
            "pending_items": data['pending_cleanup'],
            "recent_completed": data['completed_cleanup'][-10:] if data['completed_cleanup'] else []
        }
    
    def manual_cleanup(self) -> Dict[str, Any]:
        """手动触发清理"""
        logger.info("手动触发清理")
        return self.startup_cleanup()
    
    def clear_completed_records(self, keep_recent: int = 50):
        """清理已完成的记录，保留最近的N条"""
        data = self._load_cleanup_data()
        if len(data['completed_cleanup']) > keep_recent:
            data['completed_cleanup'] = data['completed_cleanup'][-keep_recent:]
            self._save_cleanup_data(data)
            logger.info(f"已清理旧的完成记录，保留最近 {keep_recent} 条")


# 全局实例
_cleanup_manager = None

def get_cleanup_manager() -> PendingCleanupManager:
    """获取清理管理器实例"""
    global _cleanup_manager
    if _cleanup_manager is None:
        chroma_path = platform_utils.PlatformUtils.get_chroma_data_directory()
        _cleanup_manager = PendingCleanupManager(chroma_path)
    return _cleanup_manager

def init_cleanup_manager():
    """初始化清理管理器"""
    global _cleanup_manager
    chroma_path = platform_utils.PlatformUtils.get_chroma_data_directory()
    _cleanup_manager = PendingCleanupManager(chroma_path)
    return _cleanup_manager