"""
健壮ChromaDB管理的API端点
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
from chromadb_integration import get_integration_manager

logger = logging.getLogger(__name__)

# 创建路由器
robust_router = APIRouter(prefix="/api/robust", tags=["robust-chromadb"])

# 请求模型
class BackupRequest(BaseModel):
    collection_name: Optional[str] = None

class RestoreRequest(BaseModel):
    backup_id: str

class RecoveryRequest(BaseModel):
    recovery_plan: List[Dict[str, Any]]

class ConfigUpdateRequest(BaseModel):
    config_updates: Dict[str, Any]

@robust_router.get("/health")
async def get_health_status():
    """获取系统健康状态"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        health_status = manager.get_health_status()
        return {"success": True, "data": health_status}
        
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.post("/backup")
async def create_backup(request: BackupRequest, background_tasks: BackgroundTasks):
    """创建备份"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        # 在后台执行备份任务
        def backup_task():
            try:
                result = manager.create_manual_backup(request.collection_name)
                logger.info(f"备份任务完成: {result}")
            except Exception as e:
                logger.error(f"备份任务失败: {e}")
        
        background_tasks.add_task(backup_task)
        
        return {
            "success": True,
            "message": "备份任务已启动，将在后台执行"
        }
        
    except Exception as e:
        logger.error(f"启动备份任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.get("/backups")
async def list_backups():
    """列出所有备份"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        backups = manager.list_available_backups()
        return {"success": True, "data": backups}
        
    except Exception as e:
        logger.error(f"列出备份失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.post("/restore")
async def restore_backup(request: RestoreRequest):
    """从备份恢复"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        result = manager.restore_from_backup(request.backup_id)
        
        if result["success"]:
            return {"success": True, "message": result["message"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.get("/scan-recovery")
async def scan_for_recovery():
    """扫描可恢复的数据"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        result = manager.scan_for_recovery()
        
        if result["success"]:
            return {"success": True, "data": result}
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫描恢复数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.post("/execute-recovery")
async def execute_recovery(request: RecoveryRequest, background_tasks: BackgroundTasks):
    """执行数据恢复"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        # 在后台执行恢复任务
        def recovery_task():
            try:
                result = manager.execute_recovery_plan(request.recovery_plan)
                logger.info(f"恢复任务完成: {result}")
            except Exception as e:
                logger.error(f"恢复任务失败: {e}")
        
        background_tasks.add_task(recovery_task)
        
        return {
            "success": True,
            "message": f"恢复任务已启动，将恢复 {len(request.recovery_plan)} 个集合"
        }
        
    except Exception as e:
        logger.error(f"启动恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.post("/cleanup-backups")
async def cleanup_backups(background_tasks: BackgroundTasks):
    """清理旧备份"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        # 在后台执行清理任务
        def cleanup_task():
            try:
                result = manager.cleanup_old_backups()
                logger.info(f"清理任务完成: {result}")
            except Exception as e:
                logger.error(f"清理任务失败: {e}")
        
        background_tasks.add_task(cleanup_task)
        
        return {
            "success": True,
            "message": "备份清理任务已启动"
        }
        
    except Exception as e:
        logger.error(f"启动清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.get("/config")
async def get_config():
    """获取当前配置"""
    try:
        from chromadb_config import get_robust_config
        
        config = get_robust_config()
        return {"success": True, "data": config.to_dict()}
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """更新配置"""
    try:
        from chromadb_config import update_robust_config
        
        success = update_robust_config(**request.config_updates)
        
        if success:
            return {"success": True, "message": "配置更新成功"}
        else:
            raise HTTPException(status_code=400, detail="配置更新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.post("/config/template/{template_name}")
async def apply_config_template(template_name: str):
    """应用配置模板"""
    try:
        from chromadb_config import apply_config_template
        
        success = apply_config_template(template_name)
        
        if success:
            return {"success": True, "message": f"配置模板 {template_name} 应用成功"}
        else:
            raise HTTPException(status_code=400, detail=f"未知配置模板: {template_name}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用配置模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@robust_router.get("/statistics")
async def get_statistics():
    """获取统计信息"""
    try:
        manager = get_integration_manager()
        if not manager._initialized:
            manager.initialize()
        
        health_status = manager.get_health_status()
        backups = manager.list_available_backups()
        
        # 计算统计信息
        stats = {
            "system_status": health_status.get("status", "unknown"),
            "total_backups": len(backups),
            "last_backup": None,
            "orphaned_vectors": len(health_status.get("consistency", {}).get("orphaned_vectors", [])),
            "missing_vectors": len(health_status.get("consistency", {}).get("missing_vectors", [])),
            "disk_usage": health_status.get("disk_usage", {}),
            "backup_size_mb": sum(backup.get("size_mb", 0) for backup in backups)
        }
        
        if backups:
            latest_backup = max(backups, key=lambda x: x["timestamp"])
            stats["last_backup"] = latest_backup["timestamp"]
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 用于集成到主应用的函数
def include_robust_routes(app):
    """将健壮管理路由包含到主应用中"""
    app.include_router(robust_router)
    logger.info("健壮ChromaDB管理路由已注册")

# 中间件：自动初始化健壮管理系统
async def robust_middleware(request, call_next):
    """健壮管理中间件"""
    # 确保系统已初始化
    manager = get_integration_manager()
    if not manager._initialized:
        try:
            manager.initialize()
        except Exception as e:
            logger.error(f"初始化健壮管理系统失败: {e}")
    
    response = await call_next(request)
    return response
