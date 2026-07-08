import json
import os
import re

transcript_path = r"C:\Users\DELL\.gemini\antigravity-ide\brain\84d97688-8f4a-4347-bb9c-b662f5c0aff8\.system_generated\logs\transcript_full.jsonl"
models_dir = r"d:\AI NATIVE ERP\backend\app\models"

files_content = {}
last_seen = {}

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
        except:
            continue
            
        # check tool calls for write_to_file
        if 'tool_calls' in data and data['tool_calls']:
            for tc in data['tool_calls']:
                if tc['name'] == 'default_api:write_to_file':
                    args = tc['arguments']
                    path = args.get('TargetFile', '')
                    if 'app/models/' in path.replace('\\', '/') or 'app\\models\\' in path:
                        basename = os.path.basename(path)
                        files_content[basename] = args.get('CodeContent', '')
                        
        # check responses for view_file or grep_search
        if data.get('type') == 'TOOL_RESPONSE':
            content = data.get('content', '')
            if 'app/models/' in content.replace('\\', '/') or 'app\\models\\' in content:
                # Try to extract full file if it was a view_file response
                if 'File Path: ' in content:
                    lines = content.split('\n')
                    for i, l in enumerate(lines):
                        if l.startswith('File Path: '):
                            path = l.split('`')[1]
                            if 'app/models/' in path or 'app%20models' in path or 'app/models' in path:
                                basename = path.split('/')[-1]
                                # extract lines
                                code_lines = []
                                for code_l in lines[i+4:]:
                                    if code_l.startswith('The above content'):
                                        break
                                    # remove line number like "15: "
                                    match = re.match(r'^\d+:\s(.*)$', code_l)
                                    if match:
                                        code_lines.append(match.group(1))
                                    else:
                                        code_lines.append(code_l)
                                if len(code_lines) > 5:
                                    if basename not in files_content:
                                        files_content[basename] = "\n".join(code_lines)

for filename, content in files_content.items():
    print(f"Recovered {filename} ({len(content)} bytes)")
    with open(os.path.join(models_dir, filename), 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Total files recovered: {len(files_content)}")
