"""
ChromaDB数据恢复工具
用于从孤立的向量文件中恢复集合数据
"""

import os
import json
import pickle
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class DataRecoveryTool:
    """数据恢复工具"""
    
    def __init__(self, chroma_path: Path):
        self.chroma_path = Path(chroma_path)
        self.db_path = self.chroma_path / "chroma.sqlite3"
        self.recovery_log_path = self.chroma_path / "recovery.log"
    
    def scan_orphaned_collections(self) -> List[Dict[str, Any]]:
        """扫描孤立的集合数据"""
        orphaned_collections = []
        
        # 获取所有向量文件夹
        vector_dirs = [d for d in self.chroma_path.iterdir() 
                      if d.is_dir() and self._is_vector_directory(d)]
        
        # 获取数据库中已注册的集合ID
        registered_ids = set()
        try:
            if self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM collections")
                    registered_ids = {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning(f"无法读取数据库: {e}")
        
        # 分析每个向量文件夹
        for vector_dir in vector_dirs:
            if vector_dir.name not in registered_ids:
                collection_info = self._analyze_vector_directory(vector_dir)
                if collection_info:
                    orphaned_collections.append(collection_info)
        
        logger.info(f"发现 {len(orphaned_collections)} 个孤立的集合")
        return orphaned_collections
    
    def _is_vector_directory(self, path: Path) -> bool:
        """判断是否为有效的向量数据目录"""
        required_files = ["header.bin", "data_level0.bin", "length.bin", "link_lists.bin"]
        return all((path / file).exists() for file in required_files)
    
    def _analyze_vector_directory(self, vector_dir: Path) -> Optional[Dict[str, Any]]:
        """分析向量目录，提取集合信息"""
        try:
            collection_info = {
                "collection_id": vector_dir.name,
                "vector_path": str(vector_dir),
                "estimated_size_mb": self._calculate_directory_size(vector_dir),
                "files": list(vector_dir.iterdir()),
                "metadata": {},
                "estimated_document_count": 0,
                "dimension": None,
                "recoverable": False
            }
            
            # 尝试从index_metadata.pickle读取元数据
            metadata_file = vector_dir / "index_metadata.pickle"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'rb') as f:
                        index_metadata = pickle.load(f)
                    collection_info["metadata"]["index_metadata"] = str(index_metadata)
                    collection_info["recoverable"] = True
                except Exception as e:
                    logger.warning(f"读取索引元数据失败 {vector_dir.name}: {e}")
            
            # 分析header.bin获取基本信息
            header_file = vector_dir / "header.bin"
            if header_file.exists():
                try:
                    header_info = self._analyze_header_file(header_file)
                    collection_info.update(header_info)
                    collection_info["recoverable"] = True
                except Exception as e:
                    logger.warning(f"分析header文件失败 {vector_dir.name}: {e}")
            
            # 估算文档数量
            data_file = vector_dir / "data_level0.bin"
            if data_file.exists():
                try:
                    file_size = data_file.stat().st_size
                    # 粗略估算：假设每个向量平均占用空间
                    if collection_info["dimension"]:
                        estimated_vector_size = collection_info["dimension"] * 4  # float32
                        collection_info["estimated_document_count"] = file_size // estimated_vector_size
                except Exception as e:
                    logger.warning(f"估算文档数量失败 {vector_dir.name}: {e}")
            
            return collection_info
            
        except Exception as e:
            logger.error(f"分析向量目录失败 {vector_dir}: {e}")
            return None
    
    def _analyze_header_file(self, header_file: Path) -> Dict[str, Any]:
        """分析header.bin文件"""
        # 这里需要根据ChromaDB的具体格式来实现
        # 由于格式可能比较复杂，这里提供一个基础框架
        try:
            with open(header_file, 'rb') as f:
                # 读取文件头部信息
                data = f.read(1024)  # 读取前1KB
                
                # 尝试解析基本信息
                # 这里需要根据实际的二进制格式来实现
                return {
                    "dimension": None,  # 需要从二进制数据中解析
                    "header_size": len(data),
                    "file_size": header_file.stat().st_size
                }
        except Exception as e:
            logger.error(f"分析header文件失败: {e}")
            return {}
    
    def _calculate_directory_size(self, directory: Path) -> float:
        """计算目录大小（MB）"""
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)
    
    def recover_collection(self, collection_id: str, display_name: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """恢复单个集合"""
        try:
            vector_dir = self.chroma_path / collection_id
            if not vector_dir.exists() or not self._is_vector_directory(vector_dir):
                logger.error(f"向量目录不存在或无效: {collection_id}")
                return False
            
            # 准备集合元数据
            collection_metadata = metadata or {}
            collection_metadata.update({
                "original_name": display_name,
                "recovered": True,
                "recovery_time": datetime.now().isoformat(),
                "original_id": collection_id
            })
            
            # 创建ChromaDB客户端
            client = chromadb.PersistentClient(path=str(self.chroma_path))
            
            # 检查集合是否已存在
            existing_collections = client.list_collections()
            for existing in existing_collections:
                if existing.name == collection_id:
                    logger.warning(f"集合已存在: {collection_id}")
                    return False
            
            # 尝试重新注册集合到数据库
            success = self._register_collection_to_database(
                collection_id, display_name, collection_metadata
            )
            
            if success:
                # 验证恢复结果
                try:
                    collection = client.get_collection(collection_id)
                    count = collection.count()
                    logger.info(f"集合恢复成功: {display_name}, 文档数: {count}")
                    
                    # 记录恢复日志
                    self._log_recovery(collection_id, display_name, "success", 
                                     {"document_count": count})
                    return True
                except Exception as e:
                    logger.error(f"验证恢复结果失败: {e}")
                    return False
            else:
                logger.error(f"注册集合到数据库失败: {collection_id}")
                return False
                
        except Exception as e:
            logger.error(f"恢复集合失败 {collection_id}: {e}")
            self._log_recovery(collection_id, display_name, "failed", {"error": str(e)})
            return False
    
    def _register_collection_to_database(self, collection_id: str, display_name: str, 
                                       metadata: Dict[str, Any]) -> bool:
        """将集合注册到数据库"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 插入集合记录
                cursor.execute("""
                    INSERT OR REPLACE INTO collections (id, name, dimension, database_id, config_json_str)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    collection_id,
                    collection_id,  # 使用ID作为名称
                    metadata.get("dimension", 1024),  # 默认维度
                    "default",  # 默认数据库ID
                    json.dumps(metadata)
                ))
                
                # 插入元数据记录
                for key, value in metadata.items():
                    if isinstance(value, str):
                        cursor.execute("""
                            INSERT OR REPLACE INTO collection_metadata 
                            (collection_id, key, str_value, int_value, float_value, bool_value)
                            VALUES (?, ?, ?, NULL, NULL, NULL)
                        """, (collection_id, key, value))
                    elif isinstance(value, int):
                        cursor.execute("""
                            INSERT OR REPLACE INTO collection_metadata 
                            (collection_id, key, str_value, int_value, float_value, bool_value)
                            VALUES (?, ?, NULL, ?, NULL, NULL)
                        """, (collection_id, key, value))
                    elif isinstance(value, float):
                        cursor.execute("""
                            INSERT OR REPLACE INTO collection_metadata 
                            (collection_id, key, str_value, int_value, float_value, bool_value)
                            VALUES (?, ?, NULL, NULL, ?, NULL)
                        """, (collection_id, key, value))
                    elif isinstance(value, bool):
                        cursor.execute("""
                            INSERT OR REPLACE INTO collection_metadata 
                            (collection_id, key, str_value, int_value, float_value, bool_value)
                            VALUES (?, ?, NULL, NULL, NULL, ?)
                        """, (collection_id, key, int(value)))
                
                conn.commit()
                logger.info(f"集合已注册到数据库: {collection_id}")
                return True
                
        except Exception as e:
            logger.error(f"注册集合到数据库失败: {e}")
            return False
    
    def _log_recovery(self, collection_id: str, display_name: str, 
                     status: str, details: Dict[str, Any]):
        """记录恢复日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "collection_id": collection_id,
            "display_name": display_name,
            "status": status,
            "details": details
        }
        
        try:
            with open(self.recovery_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"写入恢复日志失败: {e}")
    
    def batch_recover_collections(self, recovery_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量恢复集合"""
        results = {
            "total": len(recovery_plan),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for plan in recovery_plan:
            collection_id = plan["collection_id"]
            display_name = plan.get("display_name", f"recovered_{collection_id[:8]}")
            metadata = plan.get("metadata", {})
            
            success = self.recover_collection(collection_id, display_name, metadata)
            
            result_detail = {
                "collection_id": collection_id,
                "display_name": display_name,
                "success": success
            }
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append(result_detail)
        
        logger.info(f"批量恢复完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results
    
    def generate_recovery_plan(self, orphaned_collections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成恢复计划"""
        recovery_plan = []
        
        for collection_info in orphaned_collections:
            if collection_info.get("recoverable", False):
                plan = {
                    "collection_id": collection_info["collection_id"],
                    "display_name": f"恢复的集合_{collection_info['collection_id'][:8]}",
                    "metadata": {
                        "recovered": True,
                        "original_size_mb": collection_info["estimated_size_mb"],
                        "estimated_document_count": collection_info["estimated_document_count"]
                    },
                    "priority": "high" if collection_info["estimated_size_mb"] > 10 else "normal"
                }
                recovery_plan.append(plan)
        
        # 按优先级和大小排序
        recovery_plan.sort(key=lambda x: (
            x["priority"] == "high",
            x["metadata"]["estimated_size_mb"]
        ), reverse=True)
        
        return recovery_plan
