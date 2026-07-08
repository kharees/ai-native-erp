import glob
import re
import os

for filepath in glob.glob('app/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace text(''value'') with text("'value'")
    content = re.sub(r"text\(''(.*?)''\)", r"text(\"'\1'\")", content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
