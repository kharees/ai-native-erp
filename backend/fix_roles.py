import os
import glob
import re

for test_file in glob.glob("tests/test_*.py"):
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace TenantRole inserts
    content = re.sub(r'name="([^"]+)"\)', r'name="\1", is_system=False)', content)

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
