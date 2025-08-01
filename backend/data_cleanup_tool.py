"""
数据清理工具
检测和清理重命名操作可能留下的孤立数据
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any
import chromadb
from chromadb.errors import NotFoundError

logger = logging.getLogger(__name__)

class DataCleanupTool:
    """数据清理工具"""
    
    def __init__(self, chroma_path: Path, client: chromadb.PersistentClient):
        self.chroma_path = chroma_path
        self.client = client
        self.db_path = chroma_path / "chroma.sqlite3"
    
    def scan_for_orphaned_data(self) -> Dict[str, Any]:
        """扫描孤立数据"""
        logger.info("开始扫描孤立数据...")
        
        # 获取ChromaDB中的集合
        chromadb_collections = self._get_chromadb_collections()
        
        # 获取文件系统中的向量目录
        filesystem_dirs = self._get_filesystem_directories()
        
        # 获取数据库中的记录
        database_records = self._get_database_records()
        
        # 分析差异
        analysis = self._analyze_differences(
            chromadb_collections, 
            filesystem_dirs, 
            database_records
        )
        
        logger.info(f"扫描完成，发现 {len(analysis['orphaned_dirs'])} 个孤立目录")
        
        return analysis
    
    def _get_chromadb_collections(self) -> Set[str]:
        """获取ChromaDB中的所有集合ID"""
        try:
            collections = self.client.list_collections()
            return {collection.name for collection in collections}
        except Exception as e:
            logger.error(f"获取ChromaDB集合失败: {e}")
            return set()
    
    def _get_filesystem_directories(self) -> Set[str]:
        """获取文件系统中的向量目录"""
        try:
            dirs = set()
            for item in self.chroma_path.iterdir():
                if item.is_dir() and item.name.startswith('col_'):
                    dirs.add(item.name)
            return dirs
        except Exception as e:
            logger.error(f"扫描文件系统目录失败: {e}")
            return set()
    
    def _get_database_records(self) -> Set[str]:
        """获取数据库中的集合记录"""
        try:
            if not self.db_path.exists():
                return set()
            
            records = set()
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 查询collections表
                cursor.execute("SELECT id FROM collections")
                for row in cursor.fetchall():
                    records.add(row[0])
            
            return records
        except Exception as e:
            logger.error(f"查询数据库记录失败: {e}")
            return set()
    
    def _analyze_differences(self, chromadb_collections: Set[str], 
                           filesystem_dirs: Set[str], 
                           database_records: Set[str]) -> Dict[str, Any]:
        """分析数据差异"""
        
        # 孤立的文件系统目录（存在于文件系统但不在ChromaDB中）
        orphaned_dirs = filesystem_dirs - chromadb_collections
        
        # 孤立的数据库记录（存在于数据库但不在ChromaDB中）
        orphaned_db_records = database_records - chromadb_collections
        
        # 缺失的文件系统目录（存在于ChromaDB但文件系统中没有）
        missing_dirs = chromadb_collections - filesystem_dirs
        
        # 计算大小
        orphaned_sizes = {}
        total_orphaned_size = 0
        
        for dir_name in orphaned_dirs:
            dir_path = self.chroma_path / dir_name
            try:
                size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                orphaned_sizes[dir_name] = size
                total_orphaned_size += size
            except Exception as e:
                logger.warning(f"计算目录大小失败 {dir_name}: {e}")
                orphaned_sizes[dir_name] = 0
        
        return {
            "chromadb_collections": list(chromadb_collections),
            "filesystem_dirs": list(filesystem_dirs),
            "database_records": list(database_records),
            "orphaned_dirs": list(orphaned_dirs),
            "orphaned_db_records": list(orphaned_db_records),
            "missing_dirs": list(missing_dirs),
            "orphaned_sizes": orphaned_sizes,
            "total_orphaned_size_mb": total_orphaned_size / (1024 * 1024),
            "summary": {
                "total_collections": len(chromadb_collections),
                "orphaned_dirs_count": len(orphaned_dirs),
                "orphaned_db_records_count": len(orphaned_db_records),
                "missing_dirs_count": len(missing_dirs),
                "cleanup_needed": len(orphaned_dirs) > 0 or len(orphaned_db_records) > 0
            }
        }
    
    def cleanup_orphaned_data(self, dry_run: bool = True) -> Dict[str, Any]:
        """清理孤立数据"""
        logger.info(f"开始清理孤立数据 (dry_run={dry_run})...")
        
        # 先扫描
        analysis = self.scan_for_orphaned_data()
        
        if not analysis['summary']['cleanup_needed']:
            return {
                "success": True,
                "message": "没有发现需要清理的孤立数据",
                "cleaned_items": []
            }
        
        cleaned_items = []
        
        # 清理孤立的文件系统目录
        for dir_name in analysis['orphaned_dirs']:
            try:
                dir_path = self.chroma_path / dir_name
                size_mb = analysis['orphaned_sizes'].get(dir_name, 0) / (1024 * 1024)
                
                if dry_run:
                    cleaned_items.append({
                        "type": "filesystem_dir",
                        "name": dir_name,
                        "size_mb": size_mb,
                        "action": "would_delete",
                        "path": str(dir_path)
                    })
                else:
                    import shutil
                    shutil.rmtree(dir_path)
                    cleaned_items.append({
                        "type": "filesystem_dir",
                        "name": dir_name,
                        "size_mb": size_mb,
                        "action": "deleted",
                        "path": str(dir_path)
                    })
                    logger.info(f"删除孤立目录: {dir_path}")
                    
            except Exception as e:
                logger.error(f"清理孤立目录失败 {dir_name}: {e}")
                cleaned_items.append({
                    "type": "filesystem_dir",
                    "name": dir_name,
                    "action": "failed",
                    "error": str(e)
                })
        
        # 清理孤立的数据库记录
        if analysis['orphaned_db_records'] and self.db_path.exists():
            try:
                if not dry_run:
                    with sqlite3.connect(str(self.db_path)) as conn:
                        cursor = conn.cursor()
                        
                        for record_id in analysis['orphaned_db_records']:
                            cursor.execute("DELETE FROM collections WHERE id = ?", (record_id,))
                            cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (record_id,))
                            cursor.execute("DELETE FROM segments WHERE collection = ?", (record_id,))
                        
                        conn.commit()
                
                for record_id in analysis['orphaned_db_records']:
                    cleaned_items.append({
                        "type": "database_record",
                        "name": record_id,
                        "action": "deleted" if not dry_run else "would_delete"
                    })
                    
            except Exception as e:
                logger.error(f"清理数据库记录失败: {e}")
                cleaned_items.append({
                    "type": "database_records",
                    "action": "failed",
                    "error": str(e)
                })
        
        total_cleaned_size = sum(
            item.get('size_mb', 0) for item in cleaned_items 
            if item.get('action') in ['deleted', 'would_delete']
        )
        
        return {
            "success": True,
            "message": f"清理完成，处理了 {len(cleaned_items)} 个项目",
            "dry_run": dry_run,
            "cleaned_items": cleaned_items,
            "total_cleaned_size_mb": total_cleaned_size,
            "original_analysis": analysis
        }
    
    def get_cleanup_report(self) -> Dict[str, Any]:
        """获取清理报告"""
        analysis = self.scan_for_orphaned_data()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": analysis['summary'],
            "details": {
                "orphaned_directories": [],
                "orphaned_database_records": analysis['orphaned_db_records'],
                "missing_directories": analysis['missing_dirs']
            },
            "recommendations": []
        }
        
        # 详细的孤立目录信息
        for dir_name in analysis['orphaned_dirs']:
            size_mb = analysis['orphaned_sizes'].get(dir_name, 0) / (1024 * 1024)
            report['details']['orphaned_directories'].append({
                "name": dir_name,
                "size_mb": round(size_mb, 2),
                "path": str(self.chroma_path / dir_name)
            })
        
        # 生成建议
        if analysis['summary']['cleanup_needed']:
            if analysis['orphaned_dirs']:
                report['recommendations'].append(
                    f"发现 {len(analysis['orphaned_dirs'])} 个孤立目录，"
                    f"占用 {analysis['total_orphaned_size_mb']:.1f} MB 空间，建议清理"
                )
            
            if analysis['orphaned_db_records']:
                report['recommendations'].append(
                    f"发现 {len(analysis['orphaned_db_records'])} 个孤立数据库记录，建议清理"
                )
            
            if analysis['missing_dirs']:
                report['recommendations'].append(
                    f"发现 {len(analysis['missing_dirs'])} 个集合缺少文件目录，可能需要重建"
                )
        else:
            report['recommendations'].append("数据状态良好，无需清理")
        
        return report

def get_data_cleanup_tool(chroma_path: Path, client: chromadb.PersistentClient) -> DataCleanupTool:
    """获取数据清理工具实例"""
    return DataCleanupTool(chroma_path, client)
