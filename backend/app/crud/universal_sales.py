import uuid
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.universal_sales import (
    UniversalSalesQuotation, UniversalSalesQuotationItem, UniversalSalesOrder, UniversalSalesOrderItem
)
from app.schemas.universal_sales import (
    UniversalSalesQuotationCreate, UniversalSalesQuotationUpdate,
    UniversalSalesOrderCreate, UniversalSalesOrderUpdate
)

async def create_quotation(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalSalesQuotationCreate) -> UniversalSalesQuotation:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalSalesQuotation(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush() # get obj.id
    
    for item in items_data:
        db.add(UniversalSalesQuotationItem(tenant_id=tenant_id, quotation_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    await db.refresh(obj, ["items"])
    return obj

async def list_quotations(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = (
        select(UniversalSalesQuotation)
        .options(selectinload(UniversalSalesQuotation.items))
        .where(UniversalSalesQuotation.tenant_id == tenant_id)
    )
    count_stmt = select(func.count(UniversalSalesQuotation.id)).where(UniversalSalesQuotation.tenant_id == tenant_id)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(UniversalSalesQuotation.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    return items, total

async def get_quotation(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalSalesQuotation | None:
    stmt = (
        select(UniversalSalesQuotation)
        .options(selectinload(UniversalSalesQuotation.items))
        .where(UniversalSalesQuotation.id == id, UniversalSalesQuotation.tenant_id == tenant_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()

async def create_order(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalSalesOrderCreate) -> UniversalSalesOrder:
    dump = payload.model_dump()
    items_data = dump.pop("items", [])
    
    obj = UniversalSalesOrder(tenant_id=tenant_id, **dump)
    db.add(obj)
    await db.flush()
    
    for item in items_data:
        db.add(UniversalSalesOrderItem(tenant_id=tenant_id, order_id=obj.id, **item))
        
    await db.flush()
    await db.refresh(obj)
    await db.refresh(obj, ["items"])
    return obj

async def list_orders(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = (
        select(UniversalSalesOrder)
        .options(selectinload(UniversalSalesOrder.items))
        .where(UniversalSalesOrder.tenant_id == tenant_id)
    )
    count_stmt = select(func.count(UniversalSalesOrder.id)).where(UniversalSalesOrder.tenant_id == tenant_id)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(UniversalSalesOrder.created_at.desc()).limit(limit).offset(offset)
    items = (await db.execute(stmt)).scalars().all()
    return items, total

async def get_order(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalSalesOrder | None:
    stmt = (
        select(UniversalSalesOrder)
        .options(selectinload(UniversalSalesOrder.items))
        .where(UniversalSalesOrder.id == id, UniversalSalesOrder.tenant_id == tenant_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()

async def convert_from_quote(db: AsyncSession, tenant_id: uuid.UUID, quote_id: uuid.UUID) -> UniversalSalesOrder | None:
    quote = await get_quotation(db, tenant_id, quote_id)
    if not quote or quote.status != 'APPROVED': return None
    
    quote_items = (await db.execute(select(UniversalSalesQuotationItem).where(UniversalSalesQuotationItem.quotation_id == quote_id))).scalars().all()
    
    order = UniversalSalesOrder(
        tenant_id=tenant_id,
        quotation_id=quote_id,
        customer_id=quote.customer_id,
        order_number=f"SO-CONV-{str(uuid.uuid4())[:8].upper()}",
        status='PENDING',
        approval_status='PENDING',
        total_amount=quote.total_amount
    )
    db.add(order)
    await db.flush()
    
    for item in quote_items:
        db.add(UniversalSalesOrderItem(
            tenant_id=tenant_id,
            order_id=order.id,
            item_id=item.item_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        ))
        
    quote.status = 'CONVERTED'
    await db.flush()
    await db.refresh(order)
    await db.refresh(order, ["items"])
    return order

async def approve_order(db: AsyncSession, tenant_id: uuid.UUID, order_id: uuid.UUID) -> UniversalSalesOrder | None:
    order = await get_order(db, tenant_id, order_id)
    if not order: return None
    order.approval_status = 'APPROVED'
    order.status = 'CONFIRMED'
    await db.flush()
    await db.refresh(order)
    await db.refresh(order, ["items"])
    return order

from app.models.universal_sales import UniversalCustomerPriceList
from app.schemas.universal_sales import UniversalCustomerPriceListCreate, UniversalCustomerPriceListUpdate

async def create_price_list(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalCustomerPriceListCreate) -> UniversalCustomerPriceList:
    obj = UniversalCustomerPriceList(tenant_id=tenant_id, **payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def list_price_lists(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int):
    stmt = select(UniversalCustomerPriceList).where(UniversalCustomerPriceList.tenant_id == tenant_id).order_by(UniversalCustomerPriceList.created_at.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count(UniversalCustomerPriceList.id)).where(UniversalCustomerPriceList.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all(), (await db.execute(count_stmt)).scalar_one()

async def get_price_list(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalCustomerPriceList | None:
    return (await db.execute(select(UniversalCustomerPriceList).where(UniversalCustomerPriceList.id == id, UniversalCustomerPriceList.tenant_id == tenant_id))).scalar_one_or_none()


async def get_price_for_item(
    db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID, customer_group_id: uuid.UUID | None,
) -> float | None:
    """Looks up an item's price for a customer group -- UniversalCustomerPriceList
    is keyed by (customer_group_id, item_id), not by individual customer.
    Returns None (never a fabricated/default price) when customer_group_id
    is None or no matching row exists -- callers (e.g. app/services/
    order_capture.py) must treat that as "no price available", not
    "price is free"."""
    if customer_group_id is None:
        return None
    stmt = select(UniversalCustomerPriceList.price).where(
        UniversalCustomerPriceList.tenant_id == tenant_id,
        UniversalCustomerPriceList.customer_group_id == customer_group_id,
        UniversalCustomerPriceList.item_id == item_id,
    )
    price = (await db.execute(stmt)).scalar_one_or_none()
    return float(price) if price is not None else None
