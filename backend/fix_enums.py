import glob

def append_to_file(filepath, content):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(content)

append_to_file('app/models/billing.py', '''
from enum import Enum
class PaymentMode(str, Enum):
    CREDIT_CARD = 'credit_card'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    PAYPAL = 'paypal'

class PaymentStatus(str, Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
''')

append_to_file('app/models/finance.py', '''
from enum import Enum
class TransactionType(str, Enum):
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'
''')

append_to_file('app/models/migration.py', '''
from enum import Enum
class MigrationStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
''')
