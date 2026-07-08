export interface UserProfile {
  id: string;
  user_id: string;
  tenant_id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  profile_image: string | null;
  phone: string | null;
  timezone: string;
  locale: string;
  employee_code: string | null;
  status: string;
  designation: string | null;
  department_id: string | null;
  branch_id: string | null;
  warehouse_id: string | null;
  manager_id: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserProvisionPayload {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  employee_code?: string;
  designation?: string;
  department_id?: string;
  roles: string[];
}

export interface UserUpdatePayload {
  first_name?: string;
  last_name?: string;
  phone?: string;
  employee_code?: string;
  designation?: string;
  department_id?: string;
  is_active?: boolean;
}
