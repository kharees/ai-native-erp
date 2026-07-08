import os

filepath = 'tests/conftest.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('name="Alt Tenant", slug="test"', 'name="Alt Tenant", slug="alt"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
