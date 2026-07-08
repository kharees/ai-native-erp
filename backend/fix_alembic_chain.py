import os
import re

dir_path = r"d:\AI NATIVE ERP\backend\alembic\versions"

# 1. Rename universal_warehousing
file1_old = "20260705_1215_a1b2c3d4e5f6_universal_warehousing.py"
file1_new = "20260705_1215_u1b2c3d4e5f6_universal_warehousing.py"
with open(os.path.join(dir_path, file1_old), 'r') as f:
    content = f.read()
content = content.replace("revision: str = 'a1b2c3d4e5f6'", "revision: str = 'u1b2c3d4e5f6'")
content = content.replace("Revision ID: a1b2c3d4e5f6", "Revision ID: u1b2c3d4e5f6")
with open(os.path.join(dir_path, file1_new), 'w') as f:
    f.write(content)
os.remove(os.path.join(dir_path, file1_old))

# 2. Rename universal_ledger
file2_old = "20260705_1220_b2c3d4e5f6a1_universal_ledger.py"
file2_new = "20260705_1220_u2c3d4e5f6a1_universal_ledger.py"
with open(os.path.join(dir_path, file2_old), 'r') as f:
    content = f.read()
content = content.replace("revision: str = 'b2c3d4e5f6a1'", "revision: str = 'u2c3d4e5f6a1'")
content = content.replace("Revision ID: b2c3d4e5f6a1", "Revision ID: u2c3d4e5f6a1")
content = content.replace("down_revision: Union[str, None] = 'a1b2c3d4e5f6'", "down_revision: Union[str, None] = 'u1b2c3d4e5f6'")
content = content.replace("Revises: a1b2c3d4e5f6", "Revises: u1b2c3d4e5f6")
# Handle missing type hints just in case
content = content.replace("down_revision = 'a1b2c3d4e5f6'", "down_revision = 'u1b2c3d4e5f6'")
with open(os.path.join(dir_path, file2_new), 'w') as f:
    f.write(content)
os.remove(os.path.join(dir_path, file2_old))

# 3. Rename universal_tracking
file3_old = "20260705_1230_c3d4e5f6a1b2_universal_tracking.py"
file3_new = "20260705_1230_u3d4e5f6a1b2_universal_tracking.py"
with open(os.path.join(dir_path, file3_old), 'r') as f:
    content = f.read()
content = content.replace("revision: str = 'c3d4e5f6a1b2'", "revision: str = 'u3d4e5f6a1b2'")
content = content.replace("Revision ID: c3d4e5f6a1b2", "Revision ID: u3d4e5f6a1b2")
content = content.replace("down_revision: Union[str, None] = 'b2c3d4e5f6a1'", "down_revision: Union[str, None] = 'u2c3d4e5f6a1'")
content = content.replace("Revises: b2c3d4e5f6a1", "Revises: u2c3d4e5f6a1")
content = content.replace("down_revision = 'b2c3d4e5f6a1'", "down_revision = 'u2c3d4e5f6a1'")
with open(os.path.join(dir_path, file3_new), 'w') as f:
    f.write(content)
os.remove(os.path.join(dir_path, file3_old))

# 4. Update V002_phase4_rbac
file4 = "V002_phase4_rbac.py"
with open(os.path.join(dir_path, file4), 'r') as f:
    content = f.read()
content = content.replace("down_revision: Union[str, None] = None", "down_revision: Union[str, None] = 'u3d4e5f6a1b2'")
content = content.replace("down_revision = None", "down_revision = 'u3d4e5f6a1b2'")
content = content.replace("Revises: ", "Revises: u3d4e5f6a1b2")
with open(os.path.join(dir_path, file4), 'w') as f:
    f.write(content)

print("Alembic chain updated.")
