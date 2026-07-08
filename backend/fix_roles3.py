import os
import glob
import re

for test_file in glob.glob("tests/test_*.py"):
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. TenantPermission has no tenant_id and no updated_at
    content = re.sub(r'insert\(TenantPermission\)\.values\(id=perm_id, tenant_id=tenant_id, module="([^"]+)", feature="([^"]+)", action="([^"]+)", created_at=now, updated_at=now\)', r'insert(TenantPermission).values(id=perm_id, module="\1", feature="\2", action="\3", created_at=now)', content)

    # 2. TenantRolePermission has no tenant_id
    content = re.sub(r'insert\(TenantRolePermission\)\.values\(id=uuid\.uuid4\(\), tenant_id=tenant_id, role_id=role_id, permission_id=perm_id\)', r'insert(TenantRolePermission).values(id=uuid.uuid4(), role_id=role_id, permission_id=perm_id)', content)

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
