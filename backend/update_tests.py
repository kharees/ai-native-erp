import os
import glob

test_files = glob.glob('tests/finance/test_*.py')

for f in test_files:
    with open(f, 'r') as file:
        content = file.read()
    
    # Simple replace
    content = content.replace("client: AsyncClient, mock_tenant_id: UUID", "async_client: AsyncClient, setup_tenant, auth_headers")
    content = content.replace("mock_tenant_id", "setup_tenant.id")
    content = content.replace("client.get", "async_client.get")
    content = content.replace("client.post", "async_client.post")
    content = content.replace("client: AsyncClient", "async_client: AsyncClient")
    
    # We need to make sure headers=auth_headers is passed in all async_client.post and get requests.
    # We will do this via a small regex if needed, but wait, it's easier to just use `tests/conftest.py`'s `client` which already overrides get_db!
    # Wait, the root conftest.py's `client` fixture IS an `httpx.AsyncClient`!
    
    with open(f, 'w') as file:
        file.write(content)

print("Done")
