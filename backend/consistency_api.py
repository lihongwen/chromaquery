"""
数据一致性管理API端点
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

from consistency_manager import StateValidator, AutoRepair
from transactional_operations import TransactionalOperations
from sync_manager import SyncManager, WebSocketSyncNotifier
from version_manager import VersionManager
import platform_utils

logger = logging.getLogger(__name__)

# 创建路由器
consistency_router = APIRouter(prefix="/api/consistency", tags=["consistency"])

# 全局组件实例
_validator = None
_auto_repair = None
_sync_manager = None
_version_manager = None
_websocket_notifier = WebSocketSyncNotifier()

def get_components():
    """获取组件实例"""
    global _validator, _auto_repair, _sync_manager, _version_manager

    if not _validator:
        try:
            from main import chroma_client
        except ImportError:
            # 如果无法导入，返回None，让调用者处理
            return None, None, None, None

        chroma_path = platform_utils.get_chroma_data_directory()
        backup_path = Path("chromadb_backups")
        backup_path.mkdir(exist_ok=True)

        _validator = StateValidator(chroma_path, chroma_client)
        _auto_repair = AutoRepair(chroma_path, chroma_client)
        _sync_manager = SyncManager(chroma_path, chroma_client)
        _version_manager = VersionManager(chroma_path, backup_path)

        # 注册同步事件监听器
        try:
            _sync_manager.register_event_listener(_websocket_notifier.notify_sync_event)
        except Exception as e:
            logger.warning(f"注册同步事件监听器失败: {e}")

    return _validator, _auto_repair, _sync_manager, _version_manager

# 请求模型
class ConsistencyCheckRequest(BaseModel):
    full_check: bool = True
    auto_repair: bool = False

class RepairRequest(BaseModel):
    repair_orphaned_vectors: bool = True
    repair_orphaned_metadata: bool = True
    create_backup: bool = True

class SyncRequest(BaseModel):
    force_sync: bool = False
    clear_pending_events: bool = False

@consistency_router.get("/status")
async def get_consistency_status():
    """获取一致性状态"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()

        if not validator:
            return {
                "success": False,
                "message": "一致性管理组件未初始化"
            }

        # 执行一致性检查
        consistency_report = validator.validate_full_consistency()
        
        # 获取同步状态
        sync_status = sync_manager.get_sync_status()
        
        # 获取版本信息
        version_info = version_manager.get_current_version()
        compatibility = version_manager.check_compatibility()
        
        return {
            "success": True,
            "data": {
                "consistency": {
                    "status": consistency_report.status,
                    "issues": consistency_report.issues,
                    "orphaned_vectors": list(consistency_report.orphaned_vectors),
                    "orphaned_metadata": list(consistency_report.orphaned_metadata),
                    "missing_in_frontend": list(consistency_report.missing_in_frontend),
                    "missing_in_backend": list(consistency_report.missing_in_backend)
                },
                "sync": sync_status,
                "version": {
                    "chromadb_version": version_info.chromadb_version,
                    "schema_version": version_info.schema_version,
                    "compatibility": compatibility,
                    "last_migration": version_info.last_migration
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取一致性状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.post("/check")
async def check_consistency(request: ConsistencyCheckRequest):
    """执行一致性检查"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        # 执行检查
        if request.full_check:
            report = validator.validate_full_consistency()
        else:
            # 快速检查
            report = validator.validate_full_consistency()
        
        result = {
            "success": True,
            "report": {
                "status": report.status,
                "issues": report.issues,
                "frontend_collections": list(report.frontend_collections),
                "backend_collections": list(report.backend_collections),
                "database_collections": list(report.database_collections),
                "vector_directories": list(report.vector_directories),
                "orphaned_vectors": list(report.orphaned_vectors),
                "orphaned_metadata": list(report.orphaned_metadata)
            }
        }
        
        # 自动修复
        if request.auto_repair and report.status == 'inconsistent':
            repair_result = auto_repair.repair_consistency_issues(report)
            result["auto_repair"] = repair_result
        
        return result
        
    except Exception as e:
        logger.error(f"一致性检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.post("/repair")
async def repair_consistency(request: RepairRequest):
    """修复一致性问题"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        # 先执行检查
        report = validator.validate_full_consistency()
        
        if report.status == 'consistent':
            return {
                "success": True,
                "message": "数据一致性正常，无需修复"
            }
        
        # 创建备份
        backup_id = None
        if request.create_backup:
            backup_id = version_manager._create_migration_backup()
        
        # 执行修复
        repair_result = auto_repair.repair_consistency_issues(report)
        
        # 再次检查
        final_report = validator.validate_full_consistency()
        
        return {
            "success": True,
            "backup_id": backup_id,
            "repair_result": repair_result,
            "final_status": final_report.status,
            "remaining_issues": final_report.issues
        }
        
    except Exception as e:
        logger.error(f"修复一致性问题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.get("/sync/status")
async def get_sync_status():
    """获取同步状态"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        sync_status = sync_manager.get_sync_status()
        return {"success": True, "data": sync_status}
        
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.post("/sync/force")
async def force_sync(request: SyncRequest):
    """强制同步"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        if request.clear_pending_events:
            sync_manager.clear_pending_events()
        
        if request.force_sync:
            sync_result = sync_manager.force_sync()
            return {"success": True, "data": sync_result}
        else:
            return {"success": True, "message": "已清除待处理事件"}
        
    except Exception as e:
        logger.error(f"强制同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.get("/sync/events")
async def get_pending_events():
    """获取待处理的同步事件"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        events = sync_manager.get_pending_events()
        return {"success": True, "data": events}
        
    except Exception as e:
        logger.error(f"获取待处理事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.get("/collection/{collection_name}/integrity")
async def check_collection_integrity(collection_name: str):
    """检查单个集合的完整性"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        integrity_result = validator.validate_collection_integrity(collection_name)
        sync_info = sync_manager.get_collection_sync_info(collection_name)
        
        return {
            "success": True,
            "data": {
                "integrity": integrity_result,
                "sync_info": sync_info
            }
        }
        
    except Exception as e:
        logger.error(f"检查集合完整性失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.get("/version/info")
async def get_version_info():
    """获取版本信息"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        version_info = version_manager.get_current_version()
        compatibility = version_manager.check_compatibility()
        
        return {
            "success": True,
            "data": {
                "version_info": {
                    "chromadb_version": version_info.chromadb_version,
                    "schema_version": version_info.schema_version,
                    "last_migration": version_info.last_migration,
                    "migration_history": version_info.migration_history,
                    "compatibility_check": version_info.compatibility_check
                },
                "compatibility": compatibility
            }
        }
        
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.post("/version/migrate")
async def migrate_version():
    """执行版本迁移"""
    try:
        validator, auto_repair, sync_manager, version_manager = get_components()
        
        # 创建迁移计划
        migration_plan = version_manager.create_migration_plan()
        
        if not migration_plan.required_migrations:
            return {
                "success": True,
                "message": "无需迁移，版本已是最新"
            }
        
        # 执行迁移
        migration_result = version_manager.execute_migration(migration_plan)
        
        return {
            "success": migration_result["success"],
            "data": migration_result
        }
        
    except Exception as e:
        logger.error(f"版本迁移失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@consistency_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时同步通知"""
    await websocket.accept()
    _websocket_notifier.add_connection(websocket)
    
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            
            # 处理客户端消息
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_status":
                validator, auto_repair, sync_manager, version_manager = get_components()
                sync_status = sync_manager.get_sync_status()
                await websocket.send_text(json.dumps({
                    "type": "status_update",
                    "data": sync_status
                }))
                
    except WebSocketDisconnect:
        _websocket_notifier.remove_connection(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        _websocket_notifier.remove_connection(websocket)

# 用于集成到主应用的函数
def include_consistency_routes(app):
    """将一致性管理路由包含到主应用中"""
    app.include_router(consistency_router)
    logger.info("数据一致性管理路由已注册")
