import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM user_profiles"))
        await conn.execute(text("DELETE FROM user_accounts"))
        await conn.execute(text("DELETE FROM tenants"))

if __name__ == "__main__":
    asyncio.run(check())
