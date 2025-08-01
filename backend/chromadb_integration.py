"""
ChromaDB健壮管理集成模块
将健壮管理功能集成到现有系统中
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from robust_chromadb_manager import RobustChromaDBManager
from data_recovery_tool import DataRecoveryTool
from chromadb_config import get_robust_config, apply_config_template
import chromadb

logger = logging.getLogger(__name__)

class ChromaDBIntegration:
    """ChromaDB集成管理器"""
    
    def __init__(self):
        self.config = get_robust_config()
        self.robust_manager = None
        self.recovery_tool = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化健壮管理系统"""
        try:
            # 确保目录存在
            self.config.chroma_data_path.mkdir(parents=True, exist_ok=True)
            self.config.backup_root_path.mkdir(parents=True, exist_ok=True)
            
            # 初始化健壮管理器
            self.robust_manager = RobustChromaDBManager(
                self.config.chroma_data_path,
                self.config.backup_root_path
            )
            
            # 初始化恢复工具
            self.recovery_tool = DataRecoveryTool(self.config.chroma_data_path)
            
            # 执行初始健康检查
            self._perform_initial_health_check()
            
            self._initialized = True
            logger.info("ChromaDB健壮管理系统初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化健壮管理系统失败: {e}")
            return False
    
    def _perform_initial_health_check(self):
        """执行初始健康检查"""
        try:
            # 检查数据一致性
            consistency_result = self.robust_manager.consistency_checker.check_consistency()
            
            if consistency_result["status"] != "healthy":
                logger.warning(f"发现数据一致性问题: {consistency_result['issues']}")
                
                # 如果有孤立的向量文件，提供恢复建议
                if consistency_result.get("orphaned_vectors"):
                    orphaned_count = len(consistency_result["orphaned_vectors"])
                    logger.info(f"发现 {orphaned_count} 个孤立的向量文件，可以尝试恢复")
                    
                    # 自动尝试恢复（如果启用）
                    if self.config.auto_repair_enabled:
                        self._attempt_auto_recovery(consistency_result["orphaned_vectors"])
            
        except Exception as e:
            logger.error(f"初始健康检查失败: {e}")
    
    def _attempt_auto_recovery(self, orphaned_vectors: List[str]):
        """尝试自动恢复孤立的向量"""
        try:
            logger.info("开始自动恢复孤立的向量文件...")
            
            # 扫描孤立集合
            orphaned_collections = self.recovery_tool.scan_orphaned_collections()
            
            # 生成恢复计划
            recovery_plan = self.recovery_tool.generate_recovery_plan(orphaned_collections)
            
            if recovery_plan:
                logger.info(f"生成恢复计划，包含 {len(recovery_plan)} 个集合")
                
                # 执行恢复（限制数量，避免一次恢复太多）
                limited_plan = recovery_plan[:5]  # 最多恢复5个
                results = self.recovery_tool.batch_recover_collections(limited_plan)
                
                logger.info(f"自动恢复完成: 成功 {results['success']}, 失败 {results['failed']}")
            
        except Exception as e:
            logger.error(f"自动恢复失败: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        if not self._initialized:
            return {"status": "not_initialized", "message": "系统未初始化"}
        
        try:
            # 数据一致性检查
            consistency_result = self.robust_manager.consistency_checker.check_consistency()
            
            # 备份状态
            backup_status = self._get_backup_status()
            
            # 磁盘使用情况
            disk_usage = self._get_disk_usage()
            
            return {
                "status": "healthy" if consistency_result["status"] == "healthy" else "warning",
                "consistency": consistency_result,
                "backup": backup_status,
                "disk_usage": disk_usage,
                "last_check": consistency_result.get("timestamp", "unknown")
            }
            
        except Exception as e:
            logger.error(f"获取健康状态失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_backup_status(self) -> Dict[str, Any]:
        """获取备份状态"""
        try:
            backup_index = self.robust_manager.backup_manager.backup_index
            
            total_backups = len(backup_index["backups"])
            last_backup = None
            
            if backup_index["backups"]:
                # 获取最新备份
                latest_backup = max(backup_index["backups"], 
                                  key=lambda x: x["timestamp"])
                last_backup = latest_backup["timestamp"]
            
            return {
                "total_backups": total_backups,
                "last_backup": last_backup,
                "last_full_backup": backup_index.get("last_full_backup"),
                "backup_enabled": self.config.auto_backup_enabled
            }
            
        except Exception as e:
            logger.error(f"获取备份状态失败: {e}")
            return {"error": str(e)}
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            import shutil
            
            # ChromaDB数据目录使用情况
            chroma_usage = shutil.disk_usage(self.config.chroma_data_path)
            
            # 备份目录使用情况
            backup_usage = shutil.disk_usage(self.config.backup_root_path)
            
            return {
                "chroma_data": {
                    "total_gb": chroma_usage.total / (1024**3),
                    "used_gb": (chroma_usage.total - chroma_usage.free) / (1024**3),
                    "free_gb": chroma_usage.free / (1024**3)
                },
                "backup_data": {
                    "total_gb": backup_usage.total / (1024**3),
                    "used_gb": (backup_usage.total - backup_usage.free) / (1024**3),
                    "free_gb": backup_usage.free / (1024**3)
                }
            }
            
        except Exception as e:
            logger.error(f"获取磁盘使用情况失败: {e}")
            return {"error": str(e)}
    
    def create_manual_backup(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """创建手动备份"""
        if not self._initialized:
            return {"success": False, "message": "系统未初始化"}
        
        try:
            backup_id = self.robust_manager.backup_manager.create_full_backup(collection_name)
            
            return {
                "success": True,
                "backup_id": backup_id,
                "message": f"备份创建成功: {backup_id}"
            }
            
        except Exception as e:
            logger.error(f"创建手动备份失败: {e}")
            return {"success": False, "message": str(e)}
    
    def list_available_backups(self) -> List[Dict[str, Any]]:
        """列出可用备份"""
        if not self._initialized:
            return []
        
        try:
            return self.robust_manager.backup_manager.backup_index["backups"]
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    def restore_from_backup(self, backup_id: str) -> Dict[str, Any]:
        """从备份恢复"""
        if not self._initialized:
            return {"success": False, "message": "系统未初始化"}
        
        try:
            success = self.robust_manager.backup_manager.restore_backup(backup_id)
            
            if success:
                return {"success": True, "message": f"从备份 {backup_id} 恢复成功"}
            else:
                return {"success": False, "message": f"从备份 {backup_id} 恢复失败"}
                
        except Exception as e:
            logger.error(f"从备份恢复失败: {e}")
            return {"success": False, "message": str(e)}
    
    def scan_for_recovery(self) -> Dict[str, Any]:
        """扫描可恢复的数据"""
        if not self._initialized:
            return {"success": False, "message": "系统未初始化"}
        
        try:
            orphaned_collections = self.recovery_tool.scan_orphaned_collections()
            recovery_plan = self.recovery_tool.generate_recovery_plan(orphaned_collections)
            
            return {
                "success": True,
                "orphaned_count": len(orphaned_collections),
                "recoverable_count": len(recovery_plan),
                "orphaned_collections": orphaned_collections,
                "recovery_plan": recovery_plan
            }
            
        except Exception as e:
            logger.error(f"扫描恢复数据失败: {e}")
            return {"success": False, "message": str(e)}
    
    def execute_recovery_plan(self, recovery_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行恢复计划"""
        if not self._initialized:
            return {"success": False, "message": "系统未初始化"}
        
        try:
            results = self.recovery_tool.batch_recover_collections(recovery_plan)
            
            return {
                "success": True,
                "results": results,
                "message": f"恢复完成: 成功 {results['success']}, 失败 {results['failed']}"
            }
            
        except Exception as e:
            logger.error(f"执行恢复计划失败: {e}")
            return {"success": False, "message": str(e)}
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """清理旧备份"""
        if not self._initialized:
            return {"success": False, "message": "系统未初始化"}
        
        try:
            self.robust_manager.backup_manager.cleanup_old_backups(
                keep_days=self.config.backup_retention_days,
                keep_count=self.config.backup_retention_count
            )
            
            return {"success": True, "message": "旧备份清理完成"}
            
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return {"success": False, "message": str(e)}
    
    def get_client(self) -> chromadb.PersistentClient:
        """获取ChromaDB客户端"""
        if not self._initialized:
            raise RuntimeError("系统未初始化")
        
        return self.robust_manager.client

# 全局集成管理器实例
integration_manager = ChromaDBIntegration()

def get_robust_chromadb_client() -> chromadb.PersistentClient:
    """获取健壮的ChromaDB客户端"""
    if not integration_manager._initialized:
        integration_manager.initialize()
    
    return integration_manager.get_client()

def get_integration_manager() -> ChromaDBIntegration:
    """获取集成管理器"""
    return integration_manager
