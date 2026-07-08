import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base
import logging
import importlib
import pkgutil
import app.models

for _, module_name, _ in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{module_name}")

target_metadata = Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_schema():
    # We use psycopg2-style URL but since we are async, we use asyncpg
    url = settings.DATABASE_URL
    engine = create_async_engine(url)

    async with engine.connect() as conn:
        for table_name, table in target_metadata.tables.items():
            # Check if table exists
            res = await conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
            ), {"table_name": table_name})
            exists = res.scalar()

            if not exists:
                logger.info(f"Table {table_name} does not exist. It needs to be created.")
                continue

            # Get columns from DB
            res = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"
            ), {"table_name": table_name})
            db_columns = {row[0] for row in res.fetchall()}

            # Compare with model
            for column in table.columns:
                if column.name not in db_columns:
                    col_type = str(column.type.compile(engine.dialect))
                    
                    # We might need to handle VARCHAR(length)
                    if "VARCHAR" in col_type and column.type.length:
                        col_type = f"VARCHAR({column.type.length})"

                    # Check if nullable
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    
                    # Construct ALTER TABLE
                    alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                    
                    try:
                        logger.info(f"Adding column {column.name} to {table_name}")
                        await conn.execute(text(alter_stmt))
                        
                        # We won't set NOT NULL immediately if there's data, but since it's a dev environment, let's just do it
                        # wait, it's safer to just ADD COLUMN
                    except Exception as e:
                        logger.error(f"Failed to add {column.name} to {table_name}: {e}")
        
        await conn.commit()
    
    await engine.dispose()
    logger.info("Schema fix complete.")

if __name__ == "__main__":
    asyncio.run(fix_schema())
