import os
import re

def fix_all_tests():
    test_dir = "tests/finance"
    for filename in os.listdir(test_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(test_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # 1. Fix account code
            content = re.sub(r'"code":\s*("[0-9]+")', r'"account_code": \1', content)
            # Revert the one for groups
            content = re.sub(r'("/api/v1/finance-core/account-groups"[\s\S]*?)"account_code":', r'\1"code":', content)
            
            # 2. Fix category casing
            content = content.replace('"category": "ASSET"', '"category": "asset"')
            content = content.replace('"category": "LIABILITY"', '"category": "liability"')
            content = content.replace('"category": "EQUITY"', '"category": "equity"')
            content = content.replace('"category": "INCOME"', '"category": "income"')
            content = content.replace('"category": "EXPENSE"', '"category": "expense"')
            
            # 3. Fix finance-phase2 URLs
            content = content.replace('/api/v1/finance-phase2/ar-ledger', '/api/v1/finance-ar-ap/ar/ledgers')
            content = content.replace('/api/v1/finance-phase2/ap-vendors', '/api/v1/finance-ar-ap/ap/vendors')
            content = content.replace('/api/v1/finance-phase2/bank-reconciliations', '/api/v1/finance-ar-ap/banking/reconciliations')
            content = content.replace('/api/v1/finance-phase2/cash-accounts', '/api/v1/finance-ar-ap/banking/cash-accounts')
            content = content.replace('/api/v1/finance-phase2/expense-categories', '/api/v1/finance-ar-ap/expenses/categories')

            with open(filepath, "w") as f:
                f.write(content)

if __name__ == "__main__":
    fix_all_tests()
