import glob
import os

for filepath in glob.glob('app/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace('text(\\"\'', 'text("\'')
    content = content.replace('\'\\")', '\'")')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
