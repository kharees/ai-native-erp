import os
import glob
import re

for filepath in glob.glob('app/models/*.py'):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove "public." from ForeignKeys and strings
    content = content.replace('"public.', '"')
    content = content.replace("'public.", "'")
    
    # Remove {"schema": "public"} and variations
    content = re.sub(r'\{\s*"schema"\s*:\s*"public"\s*\}', '', content)
    content = re.sub(r"\{\s*'schema'\s*:\s*'public'\s*\}", "", content)
    
    # Cleanup empty dicts followed by comma, or comma followed by empty dicts from table args
    content = re.sub(r',\s*(?=\))', '', content)
    
    with open(filepath, 'w') as f:
        f.write(content)
