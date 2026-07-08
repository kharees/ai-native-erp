import apiClient from '@/lib/apiClient';
import type { Role, Permission, RolePermission, UserRole } from '@/types/rbac';

export async function fetchRoles(): Promise<Role[]> {
  const { data } = await apiClient.get<Role[]>('/api/v1/rbac/roles');
  return data;
}

export async function createRole(payload: Partial<Role>): Promise<Role> {
  const { data } = await apiClient.post<Role>('/api/v1/rbac/roles', payload);
  return data;
}

export async function updateRole(id: string, payload: Partial<Role>): Promise<Role> {
  const { data } = await apiClient.put<Role>(`/api/v1/rbac/roles/${id}`, payload);
  return data;
}

export async function deleteRole(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/rbac/roles/${id}`);
}

export async function fetchPermissions(): Promise<Permission[]> {
  const { data } = await apiClient.get<Permission[]>('/api/v1/rbac/permissions');
  return data;
}

export async function updateRolePermissions(matrix: { role_id: string; permission_ids: string[] }[]): Promise<void> {
  await apiClient.put('/api/v1/rbac/permissions', matrix);
}

export async function fetchRolePermissions(roleId: string): Promise<RolePermission[]> {
  const { data } = await apiClient.get<RolePermission[]>(`/api/v1/rbac/roles/${roleId}/permissions`);
  return data;
}

export async function fetchUserRoles(userId: string): Promise<UserRole[]> {
  const { data } = await apiClient.get<UserRole[]>(`/api/v1/rbac/users/${userId}/roles`);
  return data;
}

export async function assignRoleToUser(payload: { user_id: string; role_id: string; branch_id?: string; warehouse_id?: string }): Promise<UserRole> {
  const { data } = await apiClient.post<UserRole>('/api/v1/rbac/users/roles', payload);
  return data;
}
