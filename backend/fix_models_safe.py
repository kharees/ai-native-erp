import glob
import re
import os

for filepath in glob.glob('app/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace('"public.', '"')
    content = content.replace("'public.", "'")
    content = re.sub(r'\bmetadata\s*=\s*mapped_column\(', 'metadata_ = mapped_column(\'metadata\', ', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
