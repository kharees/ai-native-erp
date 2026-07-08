import os
import glob

test_files = glob.glob('tests/finance/test_*.py')

for f in test_files:
    with open(f, 'r') as file:
        content = file.read()
    
    content = content.replace("async_client", "client")
    
    with open(f, 'w') as file:
        file.write(content)

print("Done")
