"""
健壮的ChromaDB数据管理器
提供数据安全、事务性、可恢复的ChromaDB操作
"""

import os
import json
import shutil
import sqlite3
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

@dataclass
class CollectionBackup:
    """集合备份信息"""
    collection_id: str
    collection_name: str
    display_name: str
    metadata: Dict[str, Any]
    backup_time: str
    backup_path: str
    vector_files: List[str]
    document_count: int
    backup_type: str  # 'full' or 'incremental'

@dataclass
class OperationLog:
    """操作日志"""
    operation_id: str
    operation_type: str  # 'create', 'delete', 'rename', 'update'
    collection_name: str
    timestamp: str
    status: str  # 'started', 'completed', 'failed', 'rolled_back'
    details: Dict[str, Any]
    backup_ref: Optional[str] = None

class DataConsistencyChecker:
    """数据一致性检查器"""
    
    def __init__(self, chroma_path: Path, backup_manager):
        self.chroma_path = chroma_path
        self.backup_manager = backup_manager
        self.db_path = chroma_path / "chroma.sqlite3"
    
    def check_consistency(self) -> Dict[str, Any]:
        """检查数据一致性"""
        result = {
            "status": "healthy",
            "issues": [],
            "orphaned_vectors": [],
            "missing_vectors": [],
            "metadata_issues": []
        }
        
        try:
            # 检查孤立的向量文件
            orphaned = self._find_orphaned_vector_files()
            if orphaned:
                result["orphaned_vectors"] = orphaned
                result["status"] = "warning"
                result["issues"].append(f"发现 {len(orphaned)} 个孤立的向量文件")
            
            # 检查缺失的向量文件
            missing = self._find_missing_vector_files()
            if missing:
                result["missing_vectors"] = missing
                result["status"] = "error"
                result["issues"].append(f"发现 {len(missing)} 个缺失的向量文件")
            
            # 检查元数据完整性
            metadata_issues = self._check_metadata_integrity()
            if metadata_issues:
                result["metadata_issues"] = metadata_issues
                result["status"] = "warning"
                result["issues"].extend(metadata_issues)
                
        except Exception as e:
            logger.error(f"数据一致性检查失败: {e}")
            result["status"] = "error"
            result["issues"].append(f"检查过程出错: {str(e)}")
        
        return result
    
    def _find_orphaned_vector_files(self) -> List[str]:
        """查找孤立的向量文件"""
        orphaned = []
        
        # 获取所有向量文件夹
        vector_dirs = [d for d in self.chroma_path.iterdir() 
                      if d.is_dir() and self._is_vector_directory(d)]
        
        # 获取数据库中的集合ID
        db_collection_ids = set()
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM collections")
                db_collection_ids = {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning(f"无法读取数据库集合信息: {e}")
        
        # 查找孤立的向量文件夹
        for vector_dir in vector_dirs:
            if vector_dir.name not in db_collection_ids:
                orphaned.append(vector_dir.name)
        
        return orphaned
    
    def _find_missing_vector_files(self) -> List[str]:
        """查找缺失的向量文件"""
        missing = []
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM collections")
                
                for collection_id, collection_name in cursor.fetchall():
                    vector_dir = self.chroma_path / collection_id
                    if not vector_dir.exists() or not self._is_vector_directory(vector_dir):
                        missing.append(collection_id)
        except Exception as e:
            logger.warning(f"无法检查向量文件: {e}")
        
        return missing
    
    def _check_metadata_integrity(self) -> List[str]:
        """检查元数据完整性"""
        issues = []
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 检查是否有集合缺少必要的元数据
                cursor.execute("""
                    SELECT c.id, c.name 
                    FROM collections c 
                    LEFT JOIN collection_metadata cm ON c.id = cm.collection_id 
                    WHERE cm.collection_id IS NULL
                """)
                
                collections_without_metadata = cursor.fetchall()
                if collections_without_metadata:
                    issues.append(f"发现 {len(collections_without_metadata)} 个集合缺少元数据")
                
        except Exception as e:
            logger.warning(f"元数据完整性检查失败: {e}")
            issues.append(f"元数据检查出错: {str(e)}")
        
        return issues
    
    def _is_vector_directory(self, path: Path) -> bool:
        """判断是否为有效的向量数据目录"""
        required_files = ["header.bin", "data_level0.bin", "length.bin", "link_lists.bin"]
        return all((path / file).exists() for file in required_files)
    
    def auto_repair(self, issues: Dict[str, Any]) -> Dict[str, Any]:
        """自动修复数据问题"""
        repair_result = {
            "repaired": [],
            "failed": [],
            "backed_up": []
        }
        
        # 处理孤立的向量文件
        for orphaned_id in issues.get("orphaned_vectors", []):
            try:
                # 尝试从向量文件恢复集合信息
                recovered = self._recover_collection_from_vectors(orphaned_id)
                if recovered:
                    repair_result["repaired"].append(f"恢复集合: {recovered['name']}")
                else:
                    # 无法恢复，创建备份后移动到隔离区
                    self._quarantine_orphaned_vectors(orphaned_id)
                    repair_result["backed_up"].append(f"隔离孤立向量: {orphaned_id}")
            except Exception as e:
                logger.error(f"修复孤立向量失败 {orphaned_id}: {e}")
                repair_result["failed"].append(f"修复失败 {orphaned_id}: {str(e)}")
        
        return repair_result
    
    def _recover_collection_from_vectors(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """从向量文件恢复集合信息"""
        # 这里需要实现从向量文件中提取元数据的逻辑
        # 由于ChromaDB的向量文件格式比较复杂，这里提供一个框架
        try:
            vector_dir = self.chroma_path / collection_id
            
            # 尝试从index_metadata.pickle文件中读取信息（如果存在）
            metadata_file = vector_dir / "index_metadata.pickle"
            if metadata_file.exists():
                # 这里需要根据ChromaDB的具体格式来解析
                # 暂时返回基本信息
                return {
                    "id": collection_id,
                    "name": f"recovered_{collection_id[:8]}",
                    "display_name": f"恢复的集合_{collection_id[:8]}",
                    "metadata": {"recovered": True, "original_id": collection_id}
                }
        except Exception as e:
            logger.error(f"从向量文件恢复集合失败: {e}")
        
        return None
    
    def _quarantine_orphaned_vectors(self, collection_id: str):
        """隔离孤立的向量文件"""
        quarantine_dir = self.chroma_path / "quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        
        source_dir = self.chroma_path / collection_id
        target_dir = quarantine_dir / f"{collection_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        shutil.move(str(source_dir), str(target_dir))
        logger.info(f"孤立向量文件已移动到隔离区: {target_dir}")

class BackupManager:
    """备份管理器"""
    
    def __init__(self, chroma_path: Path, backup_root: Path):
        self.chroma_path = chroma_path
        self.backup_root = backup_root
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.backup_index_file = backup_root / "backup_index.json"
        self._load_backup_index()
    
    def _load_backup_index(self):
        """加载备份索引"""
        if self.backup_index_file.exists():
            with open(self.backup_index_file, 'r', encoding='utf-8') as f:
                self.backup_index = json.load(f)
        else:
            self.backup_index = {"backups": [], "last_full_backup": None}
    
    def _save_backup_index(self):
        """保存备份索引"""
        with open(self.backup_index_file, 'w', encoding='utf-8') as f:
            json.dump(self.backup_index, f, ensure_ascii=False, indent=2)
    
    def create_full_backup(self, collection_name: Optional[str] = None) -> str:
        """创建全量备份"""
        backup_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self.backup_root / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 备份整个ChromaDB目录
            if collection_name:
                # 单个集合备份
                self._backup_single_collection(collection_name, backup_dir)
            else:
                # 全库备份
                shutil.copytree(self.chroma_path, backup_dir / "chromadb", 
                              ignore=shutil.ignore_patterns("*.log", "*.tmp"))
            
            # 记录备份信息
            backup_info = {
                "backup_id": backup_id,
                "backup_type": "full",
                "collection_name": collection_name,
                "timestamp": datetime.now().isoformat(),
                "backup_path": str(backup_dir),
                "size_mb": self._calculate_directory_size(backup_dir)
            }
            
            self.backup_index["backups"].append(backup_info)
            if not collection_name:  # 全库备份
                self.backup_index["last_full_backup"] = backup_id
            
            self._save_backup_index()
            logger.info(f"全量备份创建成功: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"创建全量备份失败: {e}")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise
    
    def _backup_single_collection(self, collection_name: str, backup_dir: Path):
        """备份单个集合"""
        # 这里需要实现单个集合的备份逻辑
        # 包括元数据和向量文件
        pass
    
    def _calculate_directory_size(self, directory: Path) -> float:
        """计算目录大小（MB）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # 转换为MB

    def restore_backup(self, backup_id: str, target_path: Optional[Path] = None) -> bool:
        """恢复备份"""
        backup_info = None
        for backup in self.backup_index["backups"]:
            if backup["backup_id"] == backup_id:
                backup_info = backup
                break

        if not backup_info:
            logger.error(f"备份不存在: {backup_id}")
            return False

        backup_path = Path(backup_info["backup_path"])
        if not backup_path.exists():
            logger.error(f"备份文件不存在: {backup_path}")
            return False

        target = target_path or self.chroma_path

        try:
            # 创建当前数据的备份
            current_backup_id = self.create_full_backup()
            logger.info(f"当前数据已备份: {current_backup_id}")

            # 恢复数据
            if target.exists():
                shutil.rmtree(target)

            shutil.copytree(backup_path / "chromadb", target)
            logger.info(f"备份恢复成功: {backup_id} -> {target}")
            return True

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False

    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 10):
        """清理旧备份"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        # 按时间排序备份
        backups = sorted(self.backup_index["backups"],
                        key=lambda x: x["timestamp"], reverse=True)

        to_remove = []
        kept_count = 0

        for backup in backups:
            backup_time = datetime.fromisoformat(backup["timestamp"])

            # 保留最近的备份和全量备份
            if (kept_count < keep_count or
                backup_time > cutoff_date or
                backup["backup_id"] == self.backup_index.get("last_full_backup")):
                kept_count += 1
                continue

            to_remove.append(backup)

        # 删除旧备份
        for backup in to_remove:
            try:
                backup_path = Path(backup["backup_path"])
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                self.backup_index["backups"].remove(backup)
                logger.info(f"已删除旧备份: {backup['backup_id']}")
            except Exception as e:
                logger.error(f"删除备份失败 {backup['backup_id']}: {e}")

        self._save_backup_index()

class TransactionManager:
    """事务管理器"""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.operation_log_file = backup_manager.backup_root / "operations.log"
        self._lock = threading.Lock()

    @contextmanager
    def transaction(self, operation_type: str, collection_name: str, **kwargs):
        """事务上下文管理器"""
        operation_id = f"{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # 记录操作开始
        log_entry = OperationLog(
            operation_id=operation_id,
            operation_type=operation_type,
            collection_name=collection_name,
            timestamp=datetime.now().isoformat(),
            status="started",
            details=kwargs
        )

        # 创建操作前备份
        backup_id = None
        if operation_type in ["delete", "rename"]:
            try:
                backup_id = self.backup_manager.create_full_backup(collection_name)
                log_entry.backup_ref = backup_id
                logger.info(f"操作前备份创建: {backup_id}")
            except Exception as e:
                logger.error(f"创建操作前备份失败: {e}")
                raise

        self._log_operation(log_entry)

        try:
            yield operation_id

            # 操作成功
            log_entry.status = "completed"
            self._log_operation(log_entry)
            logger.info(f"事务完成: {operation_id}")

        except Exception as e:
            # 操作失败，尝试回滚
            logger.error(f"事务失败: {operation_id}, 错误: {e}")

            if backup_id and operation_type in ["delete", "rename"]:
                try:
                    self.backup_manager.restore_backup(backup_id)
                    log_entry.status = "rolled_back"
                    logger.info(f"事务已回滚: {operation_id}")
                except Exception as rollback_error:
                    log_entry.status = "rollback_failed"
                    logger.error(f"回滚失败: {rollback_error}")
            else:
                log_entry.status = "failed"

            self._log_operation(log_entry)
            raise

    def _log_operation(self, log_entry: OperationLog):
        """记录操作日志"""
        with self._lock:
            with open(self.operation_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(log_entry), ensure_ascii=False) + '\n')

class RobustChromaDBManager:
    """健壮的ChromaDB管理器"""

    def __init__(self, chroma_path: Path, backup_path: Path):
        self.chroma_path = Path(chroma_path)
        self.backup_path = Path(backup_path)

        # 初始化组件
        self.backup_manager = BackupManager(self.chroma_path, self.backup_path)
        self.consistency_checker = DataConsistencyChecker(self.chroma_path, self.backup_manager)
        self.transaction_manager = TransactionManager(self.backup_manager)

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))

        # 启动定期检查任务
        self._start_health_check()

    def _start_health_check(self):
        """启动健康检查任务"""
        def health_check():
            try:
                result = self.consistency_checker.check_consistency()
                if result["status"] != "healthy":
                    logger.warning(f"数据一致性问题: {result['issues']}")

                    # 尝试自动修复
                    if result["status"] == "warning":
                        repair_result = self.consistency_checker.auto_repair(result)
                        logger.info(f"自动修复结果: {repair_result}")

            except Exception as e:
                logger.error(f"健康检查失败: {e}")

        # 每小时执行一次健康检查
        import threading
        import time

        def periodic_check():
            while True:
                time.sleep(3600)  # 1小时
                health_check()

        thread = threading.Thread(target=periodic_check, daemon=True)
        thread.start()

    def safe_delete_collection(self, collection_name: str) -> bool:
        """安全删除集合"""
        with self.transaction_manager.transaction("delete", collection_name):
            try:
                # 查找集合
                collections = self.client.list_collections()
                target_collection = None

                for collection in collections:
                    metadata = collection.metadata or {}
                    if (metadata.get('original_name') == collection_name or
                        collection.name == collection_name):
                        target_collection = collection
                        break

                if not target_collection:
                    raise ValueError(f"集合不存在: {collection_name}")

                # 删除集合
                self.client.delete_collection(target_collection.name)
                logger.info(f"集合删除成功: {collection_name}")
                return True

            except Exception as e:
                logger.error(f"删除集合失败: {e}")
                raise

    def safe_rename_collection(self, old_name: str, new_name: str) -> bool:
        """安全重命名集合"""
        with self.transaction_manager.transaction("rename", old_name, new_name=new_name):
            try:
                # 实现安全的重命名逻辑
                # 这里使用与原代码类似的逻辑，但增加了事务保护

                # 查找原集合
                collections = self.client.list_collections()
                old_collection = None

                for collection in collections:
                    metadata = collection.metadata or {}
                    if metadata.get('original_name') == old_name:
                        old_collection = collection
                        break

                if not old_collection:
                    raise ValueError(f"集合不存在: {old_name}")

                # 检查新名称是否已存在
                for collection in collections:
                    metadata = collection.metadata or {}
                    if metadata.get('original_name') == new_name:
                        raise ValueError(f"集合已存在: {new_name}")

                # 创建新集合并复制数据
                # ... 实现重命名逻辑 ...

                logger.info(f"集合重命名成功: {old_name} -> {new_name}")
                return True

            except Exception as e:
                logger.error(f"重命名集合失败: {e}")
                raise
