import os

filepath = 'tests/conftest.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'engine = create_async_engine(TEST_DATABASE_URL, echo=False)',
    'from sqlalchemy.pool import StaticPool\nengine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool, connect_args={"check_same_thread": False})'
)
content = content.replace(
    '"sqlite+aiosqlite:///./test.db"',
    '"sqlite+aiosqlite:///:memory:"'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
