"""
ChromaDB数据一致性管理器
确保前后端数据状态始终保持同步
"""

import os
import json
import sqlite3
import shutil
import hashlib
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

@dataclass
class ConsistencyCheckpoint:
    """一致性检查点"""
    checkpoint_id: str
    timestamp: str
    operation_type: str
    collection_name: str
    pre_state: Dict[str, Any]
    backup_path: Optional[str] = None

@dataclass
class ConsistencyReport:
    """一致性检查报告"""
    status: str  # 'consistent', 'inconsistent', 'error'
    frontend_collections: Set[str]
    backend_collections: Set[str]
    database_collections: Set[str]
    vector_directories: Set[str]
    issues: List[str]
    missing_in_frontend: Set[str]
    missing_in_backend: Set[str]
    orphaned_vectors: Set[str]
    orphaned_metadata: Set[str]

class StateValidator:
    """状态验证器"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"
    
    def validate_full_consistency(self) -> ConsistencyReport:
        """执行完整的一致性检查"""
        try:
            # 获取各层数据状态
            frontend_collections = self._get_frontend_collections()
            backend_collections = self._get_backend_collections()
            database_collections = self._get_database_collections()
            vector_directories = self._get_vector_directories()
            
            # 分析一致性
            issues = []
            status = 'consistent'
            
            # 检查缺失的集合
            missing_in_frontend = backend_collections - frontend_collections
            missing_in_backend = frontend_collections - backend_collections
            orphaned_vectors = vector_directories - database_collections
            orphaned_metadata = database_collections - vector_directories
            
            if missing_in_frontend:
                issues.append(f"前端缺失 {len(missing_in_frontend)} 个集合")
                status = 'inconsistent'
            
            if missing_in_backend:
                issues.append(f"后端缺失 {len(missing_in_backend)} 个集合")
                status = 'inconsistent'
            
            if orphaned_vectors:
                issues.append(f"发现 {len(orphaned_vectors)} 个孤立向量目录")
                status = 'inconsistent'
            
            if orphaned_metadata:
                issues.append(f"发现 {len(orphaned_metadata)} 个孤立元数据记录")
                status = 'inconsistent'
            
            return ConsistencyReport(
                status=status,
                frontend_collections=frontend_collections,
                backend_collections=backend_collections,
                database_collections=database_collections,
                vector_directories=vector_directories,
                issues=issues,
                missing_in_frontend=missing_in_frontend,
                missing_in_backend=missing_in_backend,
                orphaned_vectors=orphaned_vectors,
                orphaned_metadata=orphaned_metadata
            )
            
        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return ConsistencyReport(
                status='error',
                frontend_collections=set(),
                backend_collections=set(),
                database_collections=set(),
                vector_directories=set(),
                issues=[f"检查过程出错: {str(e)}"],
                missing_in_frontend=set(),
                missing_in_backend=set(),
                orphaned_vectors=set(),
                orphaned_metadata=set()
            )
    
    def _get_frontend_collections(self) -> Set[str]:
        """获取前端应该显示的集合列表"""
        try:
            collections = self.client.list_collections()
            frontend_collections = set()
            
            for collection in collections:
                metadata = collection.metadata or {}
                display_name = metadata.get('original_name', collection.name)
                frontend_collections.add(display_name)
            
            return frontend_collections
        except Exception as e:
            logger.error(f"获取前端集合列表失败: {e}")
            return set()
    
    def _get_backend_collections(self) -> Set[str]:
        """获取后端实际存在的集合"""
        try:
            collections = self.client.list_collections()
            return {col.name for col in collections}
        except Exception as e:
            logger.error(f"获取后端集合列表失败: {e}")
            return set()
    
    def _get_database_collections(self) -> Set[str]:
        """获取数据库中记录的集合"""
        try:
            if not self.db_path.exists():
                return set()
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM collections")
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"获取数据库集合列表失败: {e}")
            return set()
    
    def _get_vector_directories(self) -> Set[str]:
        """获取向量文件目录"""
        try:
            vector_dirs = set()
            for item in self.chroma_path.iterdir():
                if item.is_dir() and self._is_vector_directory(item):
                    vector_dirs.add(item.name)
            return vector_dirs
        except Exception as e:
            logger.error(f"获取向量目录列表失败: {e}")
            return set()
    
    def _is_vector_directory(self, path: Path) -> bool:
        """判断是否为有效的向量数据目录"""
        required_files = ["header.bin", "data_level0.bin", "length.bin", "link_lists.bin"]
        return all((path / file).exists() for file in required_files)
    
    def validate_collection_integrity(self, collection_name: str) -> Dict[str, Any]:
        """验证单个集合的完整性"""
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
                return {
                    "status": "not_found",
                    "message": f"集合不存在: {collection_name}"
                }
            
            # 检查各个组件
            checks = {
                "database_record": self._check_database_record(target_collection.name),
                "metadata_records": self._check_metadata_records(target_collection.name),
                "vector_files": self._check_vector_files(target_collection.name),
                "collection_accessible": self._check_collection_accessible(target_collection)
            }
            
            # 判断整体状态
            all_passed = all(check["status"] == "ok" for check in checks.values())
            
            return {
                "status": "ok" if all_passed else "error",
                "collection_id": target_collection.name,
                "display_name": collection_name,
                "checks": checks
            }
            
        except Exception as e:
            logger.error(f"验证集合完整性失败 {collection_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _check_database_record(self, collection_id: str) -> Dict[str, Any]:
        """检查数据库记录"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM collections WHERE id = ?", (collection_id,))
                count = cursor.fetchone()[0]
                
                return {
                    "status": "ok" if count > 0 else "missing",
                    "message": "数据库记录正常" if count > 0 else "数据库记录缺失"
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_metadata_records(self, collection_id: str) -> Dict[str, Any]:
        """检查元数据记录"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM collection_metadata WHERE collection_id = ?",
                    (collection_id,)
                )
                count = cursor.fetchone()[0]
                
                return {
                    "status": "ok",
                    "message": f"元数据记录: {count} 条"
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_vector_files(self, collection_id: str) -> Dict[str, Any]:
        """检查向量文件"""
        try:
            vector_dir = self.chroma_path / collection_id
            
            if not vector_dir.exists():
                return {"status": "missing", "message": "向量目录不存在"}
            
            if not self._is_vector_directory(vector_dir):
                return {"status": "incomplete", "message": "向量文件不完整"}
            
            # 计算文件大小
            total_size = sum(f.stat().st_size for f in vector_dir.rglob('*') if f.is_file())
            
            return {
                "status": "ok",
                "message": f"向量文件正常，大小: {total_size / 1024 / 1024:.2f} MB"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_collection_accessible(self, collection) -> Dict[str, Any]:
        """检查集合是否可访问"""
        try:
            count = collection.count()
            return {
                "status": "ok",
                "message": f"集合可访问，文档数: {count}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

class AutoRepair:
    """自动修复机制"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"
    
    def repair_consistency_issues(self, report: ConsistencyReport) -> Dict[str, Any]:
        """修复一致性问题"""
        repair_results = {
            "repaired": [],
            "failed": [],
            "skipped": []
        }
        
        try:
            # 修复孤立的向量文件
            for orphaned_vector in report.orphaned_vectors:
                try:
                    result = self._repair_orphaned_vector(orphaned_vector)
                    if result["success"]:
                        repair_results["repaired"].append(f"恢复孤立向量: {orphaned_vector}")
                    else:
                        repair_results["failed"].append(f"修复失败: {orphaned_vector} - {result['message']}")
                except Exception as e:
                    repair_results["failed"].append(f"修复异常: {orphaned_vector} - {str(e)}")
            
            # 清理孤立的元数据
            for orphaned_metadata in report.orphaned_metadata:
                try:
                    result = self._cleanup_orphaned_metadata(orphaned_metadata)
                    if result["success"]:
                        repair_results["repaired"].append(f"清理孤立元数据: {orphaned_metadata}")
                    else:
                        repair_results["failed"].append(f"清理失败: {orphaned_metadata} - {result['message']}")
                except Exception as e:
                    repair_results["failed"].append(f"清理异常: {orphaned_metadata} - {str(e)}")
            
            return repair_results
            
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            repair_results["failed"].append(f"修复过程异常: {str(e)}")
            return repair_results
    
    def _repair_orphaned_vector(self, collection_id: str) -> Dict[str, Any]:
        """修复孤立的向量文件"""
        try:
            vector_dir = self.chroma_path / collection_id
            
            if not vector_dir.exists():
                return {"success": False, "message": "向量目录不存在"}
            
            # 尝试重新注册到数据库
            display_name = f"恢复的集合_{collection_id[:8]}"
            metadata = {
                "original_name": display_name,
                "recovered": True,
                "recovery_time": datetime.now().isoformat()
            }
            
            # 注册到数据库
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 插入集合记录
                cursor.execute("""
                    INSERT OR REPLACE INTO collections (id, name, dimension, database_id, config_json_str)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    collection_id,
                    collection_id,
                    1024,  # 默认维度
                    "default",
                    json.dumps(metadata)
                ))
                
                # 插入元数据
                for key, value in metadata.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO collection_metadata 
                        (collection_id, key, str_value, int_value, float_value, bool_value)
                        VALUES (?, ?, ?, NULL, NULL, NULL)
                    """, (collection_id, key, str(value)))
                
                conn.commit()
            
            return {"success": True, "message": f"成功恢复集合: {display_name}"}
            
        except Exception as e:
            logger.error(f"修复孤立向量失败 {collection_id}: {e}")
            return {"success": False, "message": str(e)}
    
    def _cleanup_orphaned_metadata(self, collection_id: str) -> Dict[str, Any]:
        """清理孤立的元数据"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 删除集合记录
                cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                
                # 删除元数据记录
                cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (collection_id,))
                
                # 删除段记录
                cursor.execute("DELETE FROM segments WHERE collection = ?", (collection_id,))
                
                conn.commit()
            
            return {"success": True, "message": f"成功清理元数据: {collection_id}"}
            
        except Exception as e:
            logger.error(f"清理孤立元数据失败 {collection_id}: {e}")
            return {"success": False, "message": str(e)}
