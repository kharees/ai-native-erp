import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.database import Base

import pkgutil
import importlib
import app.models

for _, module_name, _ in pkgutil.walk_packages(app.models.__path__):
    try:
        importlib.import_module(f"app.models.{module_name}")
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")

from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:', echo=True)

# Patch sqlite models as done in conftest.py
import uuid
from sqlalchemy.schema import DefaultClause
from sqlalchemy import text, ColumnDefault
for table in Base.metadata.tables.values():
    for column in table.columns:
        if column.server_default is not None:
            arg = str(getattr(column.server_default, 'arg', column.server_default))
            if "uuid_generate_v4" in arg:
                column.server_default = None
                column.default = ColumnDefault(uuid.uuid4)
            elif "::jsonb" in arg:
                column.server_default = DefaultClause(text(arg.replace("::jsonb", "")))
            elif "::text[]" in arg:
                column.server_default = DefaultClause(text(arg.replace("::text[]", "")))
            elif arg.upper() == "TRUE" or arg.upper() == "TEXT('TRUE')":
                column.server_default = DefaultClause(text("1"))
            elif arg.upper() == "FALSE" or arg.upper() == "TEXT('FALSE')":
                column.server_default = DefaultClause(text("0"))

print("Running create_all...")
Base.metadata.create_all(engine)
print("Success!")
