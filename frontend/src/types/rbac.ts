export interface Role {
  id: string;
  tenant_id: string | null;
  name: string;
  description: string | null;
  is_system: boolean;
  hierarchy_level: number;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  id: string;
  module: string;
  feature: string;
  action: string;
  description: string | null;
  created_at: string;
}

export interface RolePermission {
  id: string;
  role_id: string;
  permission_id: string;
  conditions: Record<string, unknown>;
  created_at: string;
}

export interface UserRole {
  id: string;
  tenant_id: string;
  user_id: string;
  role_id: string;
  branch_id: string | null;
  warehouse_id: string | null;
  created_at: string;
}
