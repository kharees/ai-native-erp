import sys
from alembic.config import main

if __name__ == '__main__':
    sys.argv = ['alembic', 'revision', '--autogenerate', '-m', 'add_user_accounts']
    main()
