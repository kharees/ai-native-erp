import apiClient from '@/lib/apiClient';
import type { UserProfile, UserProvisionPayload, UserUpdatePayload } from '@/types/user';

export async function fetchUsers(params?: Record<string, any>): Promise<UserProfile[]> {
  const { data } = await apiClient.get<UserProfile[]>('/api/v1/users/', { params });
  return data;
}

export async function getUserProfile(id: string): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>(`/api/v1/users/${id}`);
  return data;
}

export async function provisionUser(payload: UserProvisionPayload): Promise<UserProfile> {
  const { data } = await apiClient.post<UserProfile>('/api/v1/users/', payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdatePayload): Promise<UserProfile> {
  const { data } = await apiClient.patch<UserProfile>(`/api/v1/users/${id}`, payload);
  return data;
}

export async function changeUserStatus(id: string, is_active: boolean): Promise<UserProfile> {
  const { data } = await apiClient.patch<UserProfile>(`/api/v1/users/${id}/status`, null, {
    params: { is_active }
  });
  return data;
}

export async function deleteUser(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${id}`);
}
