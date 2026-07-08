import sys
import os
import glob
import importlib.util

def load_pyc(filepath):
    module_name = os.path.basename(filepath).split('.')[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return module

pyc_files = glob.glob('app/models/__pycache__/*.pyc')
for pyc in pyc_files:
    load_pyc(pyc)

from app.core.database import Base
from sqlalchemy import MetaData
import sqlalchemy

def generate_models():
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        table = mapper.local_table
        
        module_name = cls.__module__
        if not module_name.startswith('app.models') or module_name == 'app.models':
            module_name = cls.__module__
            
        code = f"from sqlalchemy import *\nfrom sqlalchemy.orm import Mapped, mapped_column\nfrom sqlalchemy.dialects.postgresql import UUID, JSONB\nimport uuid\nfrom app.core.database import Base\n\n"
        code += f"class {cls.__name__}(Base):\n"
        code += f"    __tablename__ = '{table.name}'\n"
        
        for col in table.columns:
            # Construct column definition
            col_type = repr(col.type)
            pk = "primary_key=True, " if col.primary_key else ""
            nullable = f"nullable={col.nullable}, "
            
            fks = ""
            if col.foreign_keys:
                fk = list(col.foreign_keys)[0]
                target = fk.target_fullname
                ondelete = f', ondelete="{fk.ondelete}"' if fk.ondelete else ""
                fks = f'ForeignKey("{target}"{ondelete}), '
                
            default = ""
            if col.server_default is not None:
                arg = getattr(col.server_default, 'arg', None)
                if arg is not None:
                    default = f"server_default=text('{arg}'), "
                    
            index = "index=True, " if col.index else ""
            unique = "unique=True, " if col.unique else ""
            
            code += f"    {col.name} = mapped_column({col_type}, {fks}{pk}{nullable}{default}{index}{unique})\n"
            
        file_path = f"app/models/{module_name.split('.')[-1]}.py"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n# --- {cls.__name__} ---\n{code}")

for filepath in glob.glob('app/models/*.py'):
    if not filepath.endswith('__init__.py') and os.path.getsize(filepath) == 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("from sqlalchemy import *\nfrom sqlalchemy.orm import Mapped, mapped_column, relationship\nfrom sqlalchemy.dialects.postgresql import UUID, JSONB\nimport uuid\nfrom app.core.database import Base\n\n")

generate_models()
