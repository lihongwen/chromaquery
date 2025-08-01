"""
ChromaDB健壮管理配置
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChromaDBConfig:
    """ChromaDB配置"""
    # 基础路径配置
    chroma_data_path: Path
    backup_root_path: Path
    
    # 备份策略配置
    backup_retention_days: int = 30
    backup_retention_count: int = 10
    auto_backup_enabled: bool = True
    auto_backup_interval_hours: int = 24
    
    # 健康检查配置
    health_check_enabled: bool = True
    health_check_interval_hours: int = 1
    auto_repair_enabled: bool = True
    
    # 事务配置
    transaction_timeout_seconds: int = 300
    enable_operation_logging: bool = True
    
    # 数据恢复配置
    quarantine_enabled: bool = True
    recovery_attempts: int = 3
    
    # 迁移配置
    migration_backup_enabled: bool = True
    version_check_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChromaDBConfig':
        """从字典创建配置"""
        # 转换路径字段
        if 'chroma_data_path' in data:
            data['chroma_data_path'] = Path(data['chroma_data_path'])
        if 'backup_root_path' in data:
            data['backup_root_path'] = Path(data['backup_root_path'])
        
        return cls(**data)
    
    def save_to_file(self, config_path: Path):
        """保存配置到文件"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到: {config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'ChromaDBConfig':
        """从文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise
    
    def validate(self) -> bool:
        """验证配置"""
        errors = []
        
        # 检查路径
        if not self.chroma_data_path:
            errors.append("chroma_data_path 不能为空")
        
        if not self.backup_root_path:
            errors.append("backup_root_path 不能为空")
        
        # 检查数值范围
        if self.backup_retention_days < 1:
            errors.append("backup_retention_days 必须大于0")
        
        if self.backup_retention_count < 1:
            errors.append("backup_retention_count 必须大于0")
        
        if self.health_check_interval_hours < 1:
            errors.append("health_check_interval_hours 必须大于0")
        
        if self.transaction_timeout_seconds < 30:
            errors.append("transaction_timeout_seconds 必须大于等于30")
        
        if errors:
            logger.error(f"配置验证失败: {errors}")
            return False
        
        return True

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("chromadb_robust_config.json")
        self._config: Optional[ChromaDBConfig] = None
    
    def get_config(self) -> ChromaDBConfig:
        """获取配置"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> ChromaDBConfig:
        """加载配置"""
        if self.config_file.exists():
            try:
                config = ChromaDBConfig.load_from_file(self.config_file)
                if config.validate():
                    logger.info(f"配置加载成功: {self.config_file}")
                    return config
                else:
                    logger.warning("配置验证失败，使用默认配置")
            except Exception as e:
                logger.error(f"加载配置失败，使用默认配置: {e}")
        
        # 使用默认配置
        return self.create_default_config()
    
    def create_default_config(self) -> ChromaDBConfig:
        """创建默认配置"""
        from platform_utils import PlatformUtils
        
        chroma_path = PlatformUtils.get_chroma_data_directory()
        backup_path = chroma_path.parent / "chromadb_backups"
        
        config = ChromaDBConfig(
            chroma_data_path=chroma_path,
            backup_root_path=backup_path
        )
        
        # 保存默认配置
        try:
            config.save_to_file(self.config_file)
        except Exception as e:
            logger.warning(f"保存默认配置失败: {e}")
        
        return config
    
    def update_config(self, **kwargs) -> bool:
        """更新配置"""
        try:
            config = self.get_config()
            
            # 更新配置项
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    logger.warning(f"未知配置项: {key}")
            
            # 验证配置
            if not config.validate():
                logger.error("配置更新后验证失败")
                return False
            
            # 保存配置
            config.save_to_file(self.config_file)
            self._config = config
            
            logger.info("配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

# 全局配置管理器实例
config_manager = ConfigManager()

def get_robust_config() -> ChromaDBConfig:
    """获取健壮管理配置"""
    return config_manager.get_config()

def update_robust_config(**kwargs) -> bool:
    """更新健壮管理配置"""
    return config_manager.update_config(**kwargs)

# 预定义配置模板
PRODUCTION_CONFIG = {
    "backup_retention_days": 90,
    "backup_retention_count": 20,
    "auto_backup_enabled": True,
    "auto_backup_interval_hours": 12,
    "health_check_enabled": True,
    "health_check_interval_hours": 1,
    "auto_repair_enabled": True,
    "transaction_timeout_seconds": 600,
    "enable_operation_logging": True,
    "quarantine_enabled": True,
    "recovery_attempts": 5,
    "migration_backup_enabled": True,
    "version_check_enabled": True
}

DEVELOPMENT_CONFIG = {
    "backup_retention_days": 7,
    "backup_retention_count": 5,
    "auto_backup_enabled": False,
    "auto_backup_interval_hours": 24,
    "health_check_enabled": True,
    "health_check_interval_hours": 6,
    "auto_repair_enabled": True,
    "transaction_timeout_seconds": 300,
    "enable_operation_logging": True,
    "quarantine_enabled": False,
    "recovery_attempts": 3,
    "migration_backup_enabled": False,
    "version_check_enabled": False
}

def apply_config_template(template_name: str) -> bool:
    """应用配置模板"""
    templates = {
        "production": PRODUCTION_CONFIG,
        "development": DEVELOPMENT_CONFIG
    }
    
    if template_name not in templates:
        logger.error(f"未知配置模板: {template_name}")
        return False
    
    return update_robust_config(**templates[template_name])
