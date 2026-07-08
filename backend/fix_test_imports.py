import os
import glob

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # The bad patterns
    bad1 = "from datetime import timezone, timezone, timezone, timedelta\n"
    bad2 = "from datetime import timezone, timezone\n"
    bad3 = "from datetime import timezone, timezone, timedelta\n"
    
    # We will just replace these strings if they are placed weirdly.
    # The error is 'unexpected indent' because these lines were inserted with NO indentation inside a function.
    # Actually, we can just remove them and ensure `from datetime import datetime, timezone, timedelta` is at the top of the file, or just replace them with properly indented ones.
    # Let's just do a string replacement.
    
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.startswith('from datetime import timezone, timezone'):
            # Just skip it, we will add the import at the top of the file
            continue
        new_lines.append(line)
        
    # Ensure imports exist at the top
    final_content = "\n".join(new_lines)
    if 'from datetime import datetime' not in final_content:
        final_content = "from datetime import datetime, timezone, timedelta\n" + final_content
        
    with open(filepath, 'w') as f:
        f.write(final_content)

if __name__ == '__main__':
    for root, _, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                fix_file(os.path.join(root, file))
