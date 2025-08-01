# ChromaDB健壮管理系统使用指南

## 🎯 概述

ChromaDB健壮管理系统是一个全面的数据安全和管理解决方案，旨在解决ChromaDB在生产环境中可能遇到的数据一致性、备份恢复、版本升级等问题。

## 🚀 快速开始

### 1. 立即解决当前问题

如果你当前遇到了数据不一致问题（有向量文件但集合不显示），可以立即使用恢复工具：

```python
# 在backend目录下运行
from data_recovery_tool import DataRecoveryTool
from pathlib import Path

# 初始化恢复工具
recovery_tool = DataRecoveryTool(Path("chromadbdata"))

# 扫描孤立的集合
orphaned_collections = recovery_tool.scan_orphaned_collections()
print(f"发现 {len(orphaned_collections)} 个孤立集合")

# 生成恢复计划
recovery_plan = recovery_tool.generate_recovery_plan(orphaned_collections)

# 执行恢复
if recovery_plan:
    results = recovery_tool.batch_recover_collections(recovery_plan)
    print(f"恢复完成: 成功 {results['success']}, 失败 {results['failed']}")
```

### 2. 集成到现有系统

#### 后端集成

1. **更新main.py**：

```python
# 在main.py中添加
from robust_api_endpoints import include_robust_routes, robust_middleware
from chromadb_integration import get_robust_chromadb_client

# 替换原有的ChromaDB客户端初始化
def init_chroma_client():
    global chroma_client
    try:
        chroma_client = get_robust_chromadb_client()
        logger.info("健壮ChromaDB客户端初始化成功")
    except Exception as e:
        logger.error(f"健壮ChromaDB客户端初始化失败: {e}")
        # 回退到原有方式
        chroma_path = platform_utils.get_chroma_data_directory()
        chroma_client = chromadb.PersistentClient(path=str(chroma_path))

# 注册健壮管理路由
include_robust_routes(app)

# 添加中间件
app.middleware("http")(robust_middleware)
```

2. **更新集合操作**：

```python
# 使用安全的删除和重命名操作
from chromadb_integration import get_integration_manager

@app.delete("/api/collections/{collection_name}")
async def delete_collection(collection_name: str):
    try:
        manager = get_integration_manager()
        success = manager.robust_manager.safe_delete_collection(collection_name)
        
        if success:
            return {"message": f"集合 '{collection_name}' 删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except Exception as e:
        logger.error(f"删除集合失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/collections/rename")
async def rename_collection(request: RenameCollectionRequest):
    try:
        manager = get_integration_manager()
        success = manager.robust_manager.safe_rename_collection(
            request.old_name, request.new_name
        )
        
        if success:
            return {"message": f"集合重命名成功: {request.old_name} -> {request.new_name}"}
        else:
            raise HTTPException(status_code=500, detail="重命名失败")
    except Exception as e:
        logger.error(f"重命名集合失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 前端集成

1. **添加路由**：

```typescript
// 在路由配置中添加
import RobustManagement from './components/RobustManagement';

// 添加到路由表
{
  path: '/robust-management',
  component: RobustManagement,
  name: '健壮管理'
}
```

2. **添加导航菜单**：

```typescript
// 在主菜单中添加
{
  key: 'robust',
  icon: <SafetyOutlined />,
  label: '健壮管理',
  path: '/robust-management'
}
```

## 📋 功能特性

### 1. 数据一致性检查

- **自动检查**：每小时自动检查数据一致性
- **问题检测**：
  - 孤立的向量文件（有文件但无元数据记录）
  - 缺失的向量文件（有元数据记录但无文件）
  - 元数据完整性问题
- **自动修复**：轻微问题自动修复，严重问题报警

### 2. 备份管理

- **自动备份**：可配置的定期自动备份
- **手动备份**：支持全量和单集合备份
- **多版本保留**：智能备份保留策略
- **快速恢复**：一键从备份恢复数据

### 3. 事务性操作

- **操作保护**：删除和重命名操作自动创建备份
- **回滚机制**：操作失败时自动回滚
- **操作日志**：详细记录所有操作历史

### 4. 数据恢复

- **孤立数据扫描**：自动发现可恢复的孤立数据
- **智能恢复**：从向量文件重建集合元数据
- **批量恢复**：支持批量恢复多个集合

### 5. 配置管理

- **灵活配置**：支持生产和开发环境配置模板
- **动态更新**：运行时更新配置无需重启
- **配置验证**：自动验证配置有效性

## ⚙️ 配置说明

### 基础配置

```json
{
  "chroma_data_path": "/path/to/chromadbdata",
  "backup_root_path": "/path/to/backups",
  "backup_retention_days": 30,
  "backup_retention_count": 10,
  "auto_backup_enabled": true,
  "auto_backup_interval_hours": 24,
  "health_check_enabled": true,
  "health_check_interval_hours": 1,
  "auto_repair_enabled": true
}
```

### 生产环境配置

```python
from chromadb_config import apply_config_template

# 应用生产环境配置
apply_config_template("production")
```

### 开发环境配置

```python
# 应用开发环境配置
apply_config_template("development")
```

## 🔧 API接口

### 健康检查

```bash
GET /api/robust/health
```

### 备份管理

```bash
# 创建备份
POST /api/robust/backup
{
  "collection_name": "optional_collection_name"
}

# 列出备份
GET /api/robust/backups

# 恢复备份
POST /api/robust/restore
{
  "backup_id": "backup_id_here"
}

# 清理旧备份
POST /api/robust/cleanup-backups
```

### 数据恢复

```bash
# 扫描可恢复数据
GET /api/robust/scan-recovery

# 执行数据恢复
POST /api/robust/execute-recovery
{
  "recovery_plan": [...]
}
```

### 配置管理

```bash
# 获取配置
GET /api/robust/config

# 更新配置
PUT /api/robust/config
{
  "config_updates": {...}
}

# 应用配置模板
POST /api/robust/config/template/production
```

## 🚨 故障处理

### 常见问题

1. **数据不一致**：
   - 症状：有向量文件但集合列表为空
   - 解决：使用数据恢复工具扫描并恢复

2. **备份失败**：
   - 检查磁盘空间
   - 检查文件权限
   - 查看日志文件

3. **恢复失败**：
   - 检查向量文件完整性
   - 验证数据库权限
   - 查看恢复日志

### 紧急恢复步骤

1. **停止应用服务**
2. **备份当前状态**
3. **使用恢复工具扫描**
4. **执行数据恢复**
5. **验证恢复结果**
6. **重启应用服务**

## 📊 监控和告警

### 关键指标

- 数据一致性状态
- 备份成功率
- 磁盘使用率
- 孤立数据数量

### 告警条件

- 数据一致性检查失败
- 备份连续失败
- 磁盘空间不足
- 发现大量孤立数据

## 🔄 版本升级

### 升级前准备

1. **创建全量备份**
2. **导出配置**
3. **记录当前版本信息**

### 升级步骤

1. **停止服务**
2. **备份数据**
3. **更新代码**
4. **运行迁移脚本**
5. **验证数据完整性**
6. **启动服务**

### 回滚计划

如果升级失败：
1. **停止新版本服务**
2. **恢复代码到旧版本**
3. **从备份恢复数据**
4. **启动旧版本服务**

## 📝 最佳实践

### 日常维护

1. **定期检查健康状态**
2. **监控备份任务**
3. **清理旧备份**
4. **检查磁盘空间**

### 操作建议

1. **重要操作前先备份**
2. **使用事务性操作**
3. **定期验证数据完整性**
4. **保留操作日志**

### 性能优化

1. **合理设置备份频率**
2. **优化备份存储位置**
3. **定期清理无用数据**
4. **监控系统资源使用**

## 🆘 技术支持

如果遇到问题：

1. **查看日志文件**：
   - 应用日志
   - 操作日志
   - 恢复日志

2. **检查系统状态**：
   - 健康检查结果
   - 磁盘使用情况
   - 备份状态

3. **联系技术支持**：
   - 提供详细错误信息
   - 附上相关日志
   - 描述操作步骤
