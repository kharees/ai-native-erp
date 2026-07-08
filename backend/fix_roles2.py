import os
import glob
import re

for test_file in glob.glob("tests/test_*.py"):
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace TenantRole inserts
    content = re.sub(r'name="([^"]+)", is_system=False\)', r'name="\1", is_system=False, hierarchy_level=100, created_at=now, updated_at=now)', content)
    content = re.sub(r'name="([^"]+)"\)', r'name="\1", is_system=False, hierarchy_level=100, created_at=now, updated_at=now)', content)

    # TenantPermission inserts
    content = re.sub(r'action="([^"]+)"\)', r'action="\1", created_at=now, updated_at=now)', content)

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
