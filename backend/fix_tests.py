import os
import re

def fix_enum_cases():
    test_dir = "tests/finance"
    for filename in os.listdir(test_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(test_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()
            
            # Replace category values
            content = content.replace('"category": "ASSET"', '"category": "asset"')
            content = content.replace('"category": "LIABILITY"', '"category": "liability"')
            content = content.replace('"category": "EQUITY"', '"category": "equity"')
            content = content.replace('"category": "INCOME"', '"category": "income"')
            content = content.replace('"category": "EXPENSE"', '"category": "expense"')

            # Some might have 'code' instead of 'account_code' in accounts endpoints
            # This is hard to regex safely, but let's fix security.py manually in the script
            
            with open(filepath, "w") as f:
                f.write(content)

if __name__ == "__main__":
    fix_enum_cases()
