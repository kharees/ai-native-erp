import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base

# Import all models so they register on Base.metadata
import app.models.inventory
import app.models.billing
import app.models.finance
import app.models.migration
import app.models.universal_customers
import app.models.universal_sales
import app.models.universal_numbering
import app.models.universal_taxes
import app.models.universal_invoices
import app.models.universal_documents
import app.models.universal_returns
import app.models.universal_banks
import app.models.universal_payments
import app.models.universal_pos
import app.models.universal_omnichannel
import app.models.universal_shipping
import app.models.universal_ai_billing
import app.models.universal_inventory
import app.models.universal_warehousing
import app.models.universal_ledger
import app.models.universal_tracking
import app.models.auth
import app.models.users
import app.models.tenants
import app.models.sessions
import app.models.organization
import app.models.rbac
import app.models.audit

async def create_all():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")

if __name__ == "__main__":
    asyncio.run(create_all())
