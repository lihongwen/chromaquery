"""
角色管理模块
处理角色的数据库操作和业务逻辑
"""

import sqlite3
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
import uuid

from platform_utils import platform_utils

logger = logging.getLogger(__name__)


class Role(BaseModel):
    """角色数据模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100, description="角色名称")
    prompt: str = Field(..., min_length=1, description="角色提示词内容")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreateRoleRequest(BaseModel):
    """创建角色请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    prompt: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)


class UpdateRoleRequest(BaseModel):
    """更新角色请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    prompt: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class RoleManager:
    """角色管理器"""
    
    def __init__(self):
        self.db_path = platform_utils.get_data_directory() / "roles.db"
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 创建角色表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        prompt TEXT NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # 创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_roles_active ON roles(is_active)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_roles_created_at ON roles(created_at)
                """)
                
                conn.commit()
                logger.info("角色数据库初始化成功")
                
                # 检查是否需要创建默认角色
                self._create_default_roles_if_needed(cursor)
                conn.commit()
                
        except Exception as e:
            logger.error(f"初始化角色数据库失败: {e}")
            raise
    
    def _create_default_roles_if_needed(self, cursor):
        """如果没有角色，创建默认角色"""
        cursor.execute("SELECT COUNT(*) FROM roles")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("创建默认角色")
            default_roles = [
                {
                    "name": "通用助手",
                    "prompt": "你是一个专业的AI助手，擅长回答各种问题。请基于提供的文档内容，给出准确、有用的回答。",
                    "description": "适用于一般性问题的通用助手角色"
                },
                {
                    "name": "技术专家",
                    "prompt": "你是一个技术专家，专门解答技术相关问题。请基于提供的技术文档，给出专业、详细的技术解答，包括代码示例和最佳实践。",
                    "description": "专门处理技术问题的专家角色"
                },
                {
                    "name": "业务分析师",
                    "prompt": "你是一个业务分析师，擅长分析业务需求和流程。请基于提供的业务文档，从业务角度分析问题，提供实用的业务建议。",
                    "description": "专注于业务分析和流程优化的角色"
                }
            ]
            
            for role_data in default_roles:
                role = Role(
                    name=role_data["name"],
                    prompt=role_data["prompt"],
                    description=role_data["description"]
                )
                cursor.execute("""
                    INSERT INTO roles (id, name, prompt, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    role.id, role.name, role.prompt, role.description,
                    role.is_active, role.created_at, role.updated_at
                ))
    
    def create_role(self, request: CreateRoleRequest) -> Role:
        """创建新角色"""
        try:
            role = Role(
                name=request.name,
                prompt=request.prompt,
                description=request.description,
                is_active=request.is_active
            )
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO roles (id, name, prompt, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    role.id, role.name, role.prompt, role.description,
                    role.is_active, role.created_at, role.updated_at
                ))
                conn.commit()
            
            logger.info(f"创建角色成功: {role.name}")
            return role
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"角色名称 '{request.name}' 已存在")
            raise
        except Exception as e:
            logger.error(f"创建角色失败: {e}")
            raise
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """根据ID获取角色"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, prompt, description, is_active, created_at, updated_at
                    FROM roles WHERE id = ?
                """, (role_id,))
                
                row = cursor.fetchone()
                if row:
                    return Role(
                        id=row[0],
                        name=row[1],
                        prompt=row[2],
                        description=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                        updated_at=row[6]
                    )
                return None
                
        except Exception as e:
            logger.error(f"获取角色失败: {e}")
            raise
    
    def get_role_by_name(self, name: str) -> Optional[Role]:
        """根据名称获取角色"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, prompt, description, is_active, created_at, updated_at
                    FROM roles WHERE name = ?
                """, (name,))
                
                row = cursor.fetchone()
                if row:
                    return Role(
                        id=row[0],
                        name=row[1],
                        prompt=row[2],
                        description=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                        updated_at=row[6]
                    )
                return None
                
        except Exception as e:
            logger.error(f"根据名称获取角色失败: {e}")
            raise
    
    def list_roles(self, active_only: bool = False) -> List[Role]:
        """获取角色列表"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                if active_only:
                    cursor.execute("""
                        SELECT id, name, prompt, description, is_active, created_at, updated_at
                        FROM roles WHERE is_active = 1
                        ORDER BY created_at DESC
                    """)
                else:
                    cursor.execute("""
                        SELECT id, name, prompt, description, is_active, created_at, updated_at
                        FROM roles
                        ORDER BY created_at DESC
                    """)
                
                roles = []
                for row in cursor.fetchall():
                    roles.append(Role(
                        id=row[0],
                        name=row[1],
                        prompt=row[2],
                        description=row[3],
                        is_active=bool(row[4]),
                        created_at=row[5],
                        updated_at=row[6]
                    ))
                
                return roles
                
        except Exception as e:
            logger.error(f"获取角色列表失败: {e}")
            raise
    
    def update_role(self, role_id: str, request: UpdateRoleRequest) -> Optional[Role]:
        """更新角色"""
        try:
            # 首先检查角色是否存在
            existing_role = self.get_role(role_id)
            if not existing_role:
                return None
            
            # 构建更新字段
            update_fields = []
            update_values = []
            
            if request.name is not None:
                update_fields.append("name = ?")
                update_values.append(request.name)
            
            if request.prompt is not None:
                update_fields.append("prompt = ?")
                update_values.append(request.prompt)
            
            if request.description is not None:
                update_fields.append("description = ?")
                update_values.append(request.description)
            
            if request.is_active is not None:
                update_fields.append("is_active = ?")
                update_values.append(request.is_active)
            
            if not update_fields:
                return existing_role  # 没有更新字段
            
            # 添加更新时间
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now().isoformat())
            
            # 添加WHERE条件的值
            update_values.append(role_id)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE roles SET {', '.join(update_fields)}
                    WHERE id = ?
                """, update_values)
                conn.commit()
            
            # 返回更新后的角色
            return self.get_role(role_id)
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"角色名称 '{request.name}' 已存在")
            raise
        except Exception as e:
            logger.error(f"更新角色失败: {e}")
            raise
    
    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM roles WHERE id = ?", (role_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                logger.info(f"删除角色成功: {role_id}")
                return True
            else:
                logger.warning(f"角色不存在: {role_id}")
                return False
                
        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            raise


# 全局角色管理器实例
role_manager = RoleManager()
