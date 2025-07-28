/**
 * 角色管理API服务
 */

import axios from 'axios';

export interface Role {
  id: string;
  name: string;
  prompt: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateRoleRequest {
  name: string;
  prompt: string;
  description?: string;
  is_active?: boolean;
}

export interface UpdateRoleRequest {
  name?: string;
  prompt?: string;
  description?: string;
  is_active?: boolean;
}

export class RoleApiService {
  private baseUrl = '/api/roles';

  /**
   * 获取角色列表
   */
  async getRoles(activeOnly: boolean = false): Promise<Role[]> {
    try {
      const response = await axios.get(this.baseUrl, {
        params: { active_only: activeOnly }
      });
      return response.data;
    } catch (error) {
      console.error('获取角色列表失败:', error);
      throw error;
    }
  }

  /**
   * 根据ID获取角色
   */
  async getRole(roleId: string): Promise<Role> {
    try {
      const response = await axios.get(`${this.baseUrl}/${roleId}`);
      return response.data;
    } catch (error) {
      console.error('获取角色失败:', error);
      throw error;
    }
  }

  /**
   * 创建新角色
   */
  async createRole(request: CreateRoleRequest): Promise<Role> {
    try {
      const response = await axios.post(this.baseUrl, request);
      return response.data;
    } catch (error) {
      console.error('创建角色失败:', error);
      throw error;
    }
  }

  /**
   * 更新角色
   */
  async updateRole(roleId: string, request: UpdateRoleRequest): Promise<Role> {
    try {
      const response = await axios.put(`${this.baseUrl}/${roleId}`, request);
      return response.data;
    } catch (error) {
      console.error('更新角色失败:', error);
      throw error;
    }
  }

  /**
   * 删除角色
   */
  async deleteRole(roleId: string): Promise<void> {
    try {
      await axios.delete(`${this.baseUrl}/${roleId}`);
    } catch (error) {
      console.error('删除角色失败:', error);
      throw error;
    }
  }
}

// 导出单例实例
export const roleApiService = new RoleApiService();
