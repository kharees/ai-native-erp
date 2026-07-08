import glob
import re

for filepath in glob.glob('app/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find all occurrences of text(...)
    def replace_text(match):
        inner = match.group(1)
        # inner is something like: ''{}'::text[]'
        # we want to replace two consecutive single quotes at the beginning with "'
        if inner.startswith("''"):
            # It's broken. It literally starts with '' in the string which is not valid python.
            # Wait, the content is a python source code string!
            pass
        return match.group(0)

    # Let's just fix the specific ones
    content = content.replace("text(''{}'::text[]')", "text(\"'{}'::text[]\")")
    content = content.replace("text(''pending'')", "text(\"'pending'\")")
    content = content.replace("text(''draft'')", "text(\"'draft'\")")
    content = content.replace("text(''user'')", "text(\"'user'\")")
    
    # Actually, let's just use regex to fix any text(''... string that is broken
    # It looks like text(''SOMETHING'') or text(''SOMETHING''::type)
    content = re.sub(r"text\(''(.*?)''(.*?)\)", r"text(\"'\1'\2\")", content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
