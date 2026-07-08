import uuid
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_numbering import UniversalNumberSeries
from app.schemas.universal_numbering import UniversalNumberSeriesCreate, UniversalNumberSeriesUpdate

async def create_series(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalNumberSeriesCreate) -> UniversalNumberSeries:
    obj = UniversalNumberSeries(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_series(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalNumberSeries | None:
    return (await db.execute(select(UniversalNumberSeries).where(UniversalNumberSeries.id == id, UniversalNumberSeries.tenant_id == tenant_id))).scalar_one_or_none()

async def generate_next_number(db: AsyncSession, tenant_id: uuid.UUID, entity_type: str) -> str:
    # Optimistic concurrency / atomic update would ideally be here. 
    # For now, simple select-and-increment.
    stmt = select(UniversalNumberSeries).where(
        UniversalNumberSeries.tenant_id == tenant_id, 
        UniversalNumberSeries.entity_type == entity_type,
        UniversalNumberSeries.is_active == True
    ).with_for_update()
    
    result = await db.execute(stmt)
    series = result.scalar_one_or_none()
    
    if not series:
        return f"{entity_type.upper()}-0001"
        
    series.current_sequence += 1
    seq_str = str(series.current_sequence).zfill(series.padding)
    
    formatted = series.prefix
    if series.financial_year:
        formatted += f"/{series.financial_year}"
    formatted += f"/{seq_str}"
    
    await db.commit()
    return formatted
