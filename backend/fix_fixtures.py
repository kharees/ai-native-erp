import os

filepath = 'tests/fixtures/inventory_fixtures.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('schema_name="public"', 'slug="test"')
content = content.replace('tier="enterprise"', 'plan="enterprise"')
content = content.replace('schema_name="alt"', 'slug="alt"')
content = content.replace('schema_name', 'slug')
content = content.replace('tier', 'plan')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
