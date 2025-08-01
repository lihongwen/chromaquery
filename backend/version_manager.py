"""
版本管理器
处理ChromaDB版本升级和数据迁移
"""

import os
import json
import sqlite3
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import chromadb
from packaging import version

logger = logging.getLogger(__name__)

@dataclass
class VersionInfo:
    """版本信息"""
    chromadb_version: str
    schema_version: str
    last_migration: Optional[str]
    migration_history: List[str]
    compatibility_check: bool

@dataclass
class MigrationPlan:
    """迁移计划"""
    from_version: str
    to_version: str
    required_migrations: List[str]
    backup_required: bool
    estimated_time: str
    risks: List[str]

class VersionManager:
    """版本管理器"""
    
    def __init__(self, chroma_path: Path, backup_path: Path):
        self.chroma_path = chroma_path
        self.backup_path = backup_path
        self.version_file = chroma_path / "version_info.json"
        self.migration_log = chroma_path / "migration.log"
        
        # 支持的迁移版本
        self.supported_migrations = {
            "0.4.0_to_0.4.15": self._migrate_0_4_0_to_0_4_15,
            "0.4.15_to_1.0.0": self._migrate_0_4_15_to_1_0_0,
            "1.0.0_to_1.1.0": self._migrate_1_0_0_to_1_1_0,
        }
    
    def get_current_version(self) -> VersionInfo:
        """获取当前版本信息"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return VersionInfo(**data)
            else:
                # 首次运行，检测版本
                return self._detect_version()
        except Exception as e:
            logger.error(f"获取版本信息失败: {e}")
            return self._create_default_version_info()
    
    def _detect_version(self) -> VersionInfo:
        """检测当前ChromaDB版本"""
        try:
            chromadb_version = chromadb.__version__
            
            # 根据数据库结构判断schema版本
            schema_version = self._detect_schema_version()
            
            version_info = VersionInfo(
                chromadb_version=chromadb_version,
                schema_version=schema_version,
                last_migration=None,
                migration_history=[],
                compatibility_check=True
            )
            
            self._save_version_info(version_info)
            return version_info
            
        except Exception as e:
            logger.error(f"检测版本失败: {e}")
            return self._create_default_version_info()
    
    def _detect_schema_version(self) -> str:
        """检测数据库schema版本"""
        try:
            db_path = self.chroma_path / "chroma.sqlite3"
            if not db_path.exists():
                return "1.0.0"  # 新安装
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # 检查表结构来判断版本
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cursor.fetchall()}
                
                # 根据表的存在情况判断版本
                if "embedding_fulltext_search" in tables:
                    return "1.0.0"
                elif "segments" in tables:
                    return "0.4.15"
                else:
                    return "0.4.0"
                    
        except Exception as e:
            logger.error(f"检测schema版本失败: {e}")
            return "unknown"
    
    def _create_default_version_info(self) -> VersionInfo:
        """创建默认版本信息"""
        return VersionInfo(
            chromadb_version=chromadb.__version__,
            schema_version="unknown",
            last_migration=None,
            migration_history=[],
            compatibility_check=False
        )
    
    def _save_version_info(self, version_info: VersionInfo):
        """保存版本信息"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(version_info), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")
    
    def check_compatibility(self) -> Dict[str, Any]:
        """检查版本兼容性"""
        try:
            current_version = self.get_current_version()
            chromadb_version = chromadb.__version__
            
            compatibility_result = {
                "compatible": True,
                "current_chromadb": chromadb_version,
                "recorded_chromadb": current_version.chromadb_version,
                "schema_version": current_version.schema_version,
                "migration_needed": False,
                "issues": []
            }
            
            # 检查ChromaDB版本变化
            if current_version.chromadb_version != chromadb_version:
                compatibility_result["migration_needed"] = True
                compatibility_result["issues"].append(
                    f"ChromaDB版本变化: {current_version.chromadb_version} -> {chromadb_version}"
                )
                
                # 检查是否为重大版本变化
                old_version = version.parse(current_version.chromadb_version)
                new_version = version.parse(chromadb_version)
                
                if old_version.major != new_version.major:
                    compatibility_result["compatible"] = False
                    compatibility_result["issues"].append("检测到重大版本变化，需要数据迁移")
            
            # 检查schema兼容性
            expected_schema = self._get_expected_schema_version(chromadb_version)
            if current_version.schema_version != expected_schema:
                compatibility_result["migration_needed"] = True
                compatibility_result["issues"].append(
                    f"Schema版本不匹配: {current_version.schema_version} -> {expected_schema}"
                )
            
            return compatibility_result
            
        except Exception as e:
            logger.error(f"检查兼容性失败: {e}")
            return {
                "compatible": False,
                "issues": [f"兼容性检查失败: {str(e)}"]
            }
    
    def _get_expected_schema_version(self, chromadb_version: str) -> str:
        """获取期望的schema版本"""
        version_obj = version.parse(chromadb_version)
        
        if version_obj >= version.parse("1.0.0"):
            return "1.0.0"
        elif version_obj >= version.parse("0.4.15"):
            return "0.4.15"
        else:
            return "0.4.0"
    
    def create_migration_plan(self, target_version: Optional[str] = None) -> MigrationPlan:
        """创建迁移计划"""
        try:
            current_version = self.get_current_version()
            target_version = target_version or chromadb.__version__
            
            # 确定需要的迁移步骤
            required_migrations = self._determine_migration_path(
                current_version.chromadb_version, target_version
            )
            
            # 评估风险
            risks = self._assess_migration_risks(required_migrations)
            
            # 估算时间
            estimated_time = self._estimate_migration_time(required_migrations)
            
            return MigrationPlan(
                from_version=current_version.chromadb_version,
                to_version=target_version,
                required_migrations=required_migrations,
                backup_required=len(required_migrations) > 0,
                estimated_time=estimated_time,
                risks=risks
            )
            
        except Exception as e:
            logger.error(f"创建迁移计划失败: {e}")
            raise
    
    def _determine_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """确定迁移路径"""
        migrations = []
        
        from_ver = version.parse(from_version)
        to_ver = version.parse(to_version)
        
        if from_ver < version.parse("0.4.15") <= to_ver:
            migrations.append("0.4.0_to_0.4.15")
        
        if from_ver < version.parse("1.0.0") <= to_ver:
            migrations.append("0.4.15_to_1.0.0")
        
        if from_ver < version.parse("1.1.0") <= to_ver:
            migrations.append("1.0.0_to_1.1.0")
        
        return migrations
    
    def _assess_migration_risks(self, migrations: List[str]) -> List[str]:
        """评估迁移风险"""
        risks = []
        
        if not migrations:
            return risks
        
        if "0.4.15_to_1.0.0" in migrations:
            risks.append("重大版本升级，可能存在API变化")
            risks.append("数据格式可能发生变化")
        
        if len(migrations) > 1:
            risks.append("多步骤迁移，中间步骤失败可能导致数据不一致")
        
        risks.append("迁移过程中服务不可用")
        risks.append("大量数据时迁移时间较长")
        
        return risks
    
    def _estimate_migration_time(self, migrations: List[str]) -> str:
        """估算迁移时间"""
        if not migrations:
            return "无需迁移"
        
        base_time = 5  # 基础时间（分钟）
        per_migration_time = 10  # 每个迁移步骤的时间
        
        total_time = base_time + len(migrations) * per_migration_time
        
        if total_time < 60:
            return f"约 {total_time} 分钟"
        else:
            hours = total_time // 60
            minutes = total_time % 60
            return f"约 {hours} 小时 {minutes} 分钟"
    
    def execute_migration(self, migration_plan: MigrationPlan) -> Dict[str, Any]:
        """执行迁移"""
        migration_result = {
            "success": False,
            "completed_migrations": [],
            "failed_migration": None,
            "backup_created": False,
            "rollback_available": False
        }
        
        try:
            # 创建迁移前备份
            if migration_plan.backup_required:
                backup_id = self._create_migration_backup()
                migration_result["backup_created"] = True
                migration_result["rollback_available"] = True
                logger.info(f"迁移前备份创建: {backup_id}")
            
            # 执行迁移步骤
            for migration_name in migration_plan.required_migrations:
                try:
                    logger.info(f"开始执行迁移: {migration_name}")
                    
                    if migration_name in self.supported_migrations:
                        self.supported_migrations[migration_name]()
                        migration_result["completed_migrations"].append(migration_name)
                        
                        # 记录迁移历史
                        self._record_migration(migration_name)
                        
                        logger.info(f"迁移完成: {migration_name}")
                    else:
                        raise Exception(f"不支持的迁移: {migration_name}")
                        
                except Exception as e:
                    migration_result["failed_migration"] = migration_name
                    logger.error(f"迁移失败: {migration_name}, 错误: {e}")
                    raise
            
            # 更新版本信息
            self._update_version_after_migration(migration_plan.to_version)
            
            migration_result["success"] = True
            logger.info("所有迁移步骤完成")
            
            return migration_result
            
        except Exception as e:
            logger.error(f"迁移执行失败: {e}")
            migration_result["error"] = str(e)
            return migration_result
    
    def _create_migration_backup(self) -> str:
        """创建迁移备份"""
        backup_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self.backup_path / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份整个ChromaDB目录
        shutil.copytree(self.chroma_path, backup_dir / "chromadb",
                       ignore=shutil.ignore_patterns("*.log", "*.tmp"))
        
        return backup_id
    
    def _record_migration(self, migration_name: str):
        """记录迁移历史"""
        try:
            current_version = self.get_current_version()
            current_version.migration_history.append(f"{migration_name}:{datetime.now().isoformat()}")
            current_version.last_migration = migration_name
            self._save_version_info(current_version)
            
            # 记录到迁移日志
            with open(self.migration_log, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - 完成迁移: {migration_name}\n")
                
        except Exception as e:
            logger.error(f"记录迁移历史失败: {e}")
    
    def _update_version_after_migration(self, new_version: str):
        """迁移后更新版本信息"""
        try:
            current_version = self.get_current_version()
            current_version.chromadb_version = new_version
            current_version.schema_version = self._get_expected_schema_version(new_version)
            current_version.compatibility_check = True
            self._save_version_info(current_version)
        except Exception as e:
            logger.error(f"更新版本信息失败: {e}")
    
    # 具体的迁移方法
    def _migrate_0_4_0_to_0_4_15(self):
        """从0.4.0迁移到0.4.15"""
        logger.info("执行0.4.0到0.4.15的迁移")
        # 这里实现具体的迁移逻辑
        pass
    
    def _migrate_0_4_15_to_1_0_0(self):
        """从0.4.15迁移到1.0.0"""
        logger.info("执行0.4.15到1.0.0的迁移")
        # 这里实现具体的迁移逻辑
        # 主要是数据库schema的变化
        pass
    
    def _migrate_1_0_0_to_1_1_0(self):
        """从1.0.0迁移到1.1.0"""
        logger.info("执行1.0.0到1.1.0的迁移")
        # 这里实现具体的迁移逻辑
        pass
    
    def rollback_migration(self, backup_id: str) -> Dict[str, Any]:
        """回滚迁移"""
        try:
            backup_dir = self.backup_path / backup_id / "chromadb"
            
            if not backup_dir.exists():
                return {
                    "success": False,
                    "message": f"备份不存在: {backup_id}"
                }
            
            # 停止当前服务（这里需要根据实际情况实现）
            
            # 恢复数据
            if self.chroma_path.exists():
                shutil.rmtree(self.chroma_path)
            
            shutil.copytree(backup_dir, self.chroma_path)
            
            logger.info(f"成功回滚到备份: {backup_id}")
            
            return {
                "success": True,
                "message": f"成功回滚到备份: {backup_id}"
            }
            
        except Exception as e:
            logger.error(f"回滚迁移失败: {e}")
            return {
                "success": False,
                "message": f"回滚失败: {str(e)}"
            }
