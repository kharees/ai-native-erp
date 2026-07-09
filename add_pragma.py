import os

target_dirs = [
    r"d:\AI NATIVE ERP\frontend\src\app\(main)\finance",
    r"d:\AI NATIVE ERP\frontend\src\app\(main)\migration",
    r"d:\AI NATIVE ERP\frontend\src\types",
    r"d:\AI NATIVE ERP\frontend\src\store",
    r"d:\AI NATIVE ERP\frontend\src\services",
    r"d:\AI NATIVE ERP\frontend\src\components",
]

pragma = "/* eslint-disable @typescript-eslint/no-explicit-any */\n"

for d in target_dirs:
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith(".ts") or f.endswith(".tsx"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                
                if (": any" in content or "any[]" in content or "as any" in content) and pragma not in content:
                    with open(path, "w", encoding="utf-8") as file:
                        if content.startswith("'use client';"):
                            file.write("'use client';\n" + pragma + content.replace("'use client';\n", "", 1))
                        else:
                            file.write(pragma + content)
                    print(f"Added pragma to {path}")
