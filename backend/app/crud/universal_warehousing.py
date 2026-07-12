import uuid
from decimal import Decimal
from sqlalchemy import select, func, update, exc, and_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import paginate
from app.models.universal_warehousing import (
    UniversalWarehouse,
    UniversalWarehouseZone,
    UniversalWarehouseBin,
    UniversalStockBalance,
    UniversalStockTransaction
)
from app.schemas.universal_warehousing import (
    UniversalWarehouseCreate, UniversalWarehouseUpdate,
    UniversalWarehouseZoneCreate, UniversalWarehouseZoneUpdate,
    UniversalWarehouseBinCreate, UniversalWarehouseBinUpdate,
    StockMovementRequest
)

# -----------------
# Warehouses
# -----------------
async def create_warehouse(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalWarehouseCreate) -> UniversalWarehouse:
    obj = UniversalWarehouse(tenant_id=tenant_id, **payload.model_dump(by_alias=True))
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_warehouse(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalWarehouse | None:
    stmt = select(UniversalWarehouse).where(UniversalWarehouse.id == id, UniversalWarehouse.tenant_id == tenant_id, UniversalWarehouse.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_warehouses(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int, search: str | None = None):
    stmt = select(UniversalWarehouse).where(UniversalWarehouse.tenant_id == tenant_id, UniversalWarehouse.is_active == True)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (func.lower(UniversalWarehouse.name).like(search_pattern.lower())) |
            (func.lower(UniversalWarehouse.code).like(search_pattern.lower()))
        )
    
    return await paginate(db, stmt, UniversalWarehouse.created_at.desc(), limit, offset)

# -----------------
# Bins
# -----------------
async def create_bin(db: AsyncSession, tenant_id: uuid.UUID, payload: UniversalWarehouseBinCreate) -> UniversalWarehouseBin:
    obj = UniversalWarehouseBin(tenant_id=tenant_id, **payload.model_dump(by_alias=True))
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_bin(db: AsyncSession, tenant_id: uuid.UUID, id: uuid.UUID) -> UniversalWarehouseBin | None:
    stmt = select(UniversalWarehouseBin).where(UniversalWarehouseBin.id == id, UniversalWarehouseBin.tenant_id == tenant_id, UniversalWarehouseBin.is_active == True)
    return (await db.execute(stmt)).scalar_one_or_none()

async def list_bins(db: AsyncSession, tenant_id: uuid.UUID, limit: int, offset: int, warehouse_id: uuid.UUID | None = None, search: str | None = None):
    stmt = select(UniversalWarehouseBin).where(UniversalWarehouseBin.tenant_id == tenant_id, UniversalWarehouseBin.is_active == True)
    if warehouse_id:
        stmt = stmt.where(UniversalWarehouseBin.warehouse_id == warehouse_id)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (func.lower(UniversalWarehouseBin.name).like(search_pattern.lower())) |
            (func.lower(UniversalWarehouseBin.code).like(search_pattern.lower()))
        )
    
    return await paginate(db, stmt, UniversalWarehouseBin.created_at.desc(), limit, offset)

# -----------------
# Stock Engine
# -----------------
async def _get_or_create_balance_locked(
    db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID,
    warehouse_id: uuid.UUID, bin_id: uuid.UUID | None
) -> UniversalStockBalance:
    """
    Get-or-create a UniversalStockBalance row for a location, race-free.

    A plain "SELECT ... FOR UPDATE, INSERT if missing" cannot be made safe
    with locking alone: FOR UPDATE locks rows that exist, so on a cache-cold
    location two concurrent callers both see no row, both pass the check,
    and both INSERT — the exact scenario in the original bug report. This
    guarantees the row exists first (via INSERT ... ON CONFLICT DO NOTHING
    against the partial unique indexes on UniversalStockBalance, see
    migration a4b6c8d1e3f5) and only then locks it, so the second caller's
    INSERT is a no-op and its SELECT ... FOR UPDATE simply blocks until the
    first caller's transaction commits.
    """
    # Postgres requires the ON CONFLICT target to match a specific index;
    # bin_id has two different partial unique indexes depending on whether
    # it's NULL, so the conflict target must be chosen accordingly.
    insert_stmt = pg_insert(UniversalStockBalance).values(
        tenant_id=tenant_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        bin_id=bin_id,
        quantity_on_hand=Decimal("0"),
    )
    if bin_id is not None:
        insert_stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=['tenant_id', 'item_id', 'warehouse_id', 'bin_id'],
            index_where=text('bin_id IS NOT NULL'),
        )
    else:
        insert_stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=['tenant_id', 'item_id', 'warehouse_id'],
            index_where=text('bin_id IS NULL'),
        )
    await db.execute(insert_stmt)

    bal_stmt = select(UniversalStockBalance).where(
        UniversalStockBalance.tenant_id == tenant_id,
        UniversalStockBalance.item_id == item_id,
        UniversalStockBalance.warehouse_id == warehouse_id,
        UniversalStockBalance.bin_id == bin_id,
    ).with_for_update()
    return (await db.execute(bal_stmt)).scalar_one()


async def execute_stock_movement(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None, payload: StockMovementRequest) -> UniversalStockTransaction:
    if payload.transaction_type == "TRANSFER" and not payload.destination_warehouse_id:
        raise ValueError("TRANSFER requires destination_warehouse_id.")

    # 1. Create Transaction Record
    # destination_* fields are transfer-routing instructions, not columns on
    # UniversalStockTransaction (which records a single location's leg).
    txn_data = payload.model_dump(by_alias=True, exclude={'destination_warehouse_id', 'destination_bin_id'})
    txn = UniversalStockTransaction(
        tenant_id=tenant_id,
        user_id=user_id,
        **txn_data
    )
    db.add(txn)

    # 2. Get or Create Balance Record (race-free — see _get_or_create_balance_locked)
    balance = await _get_or_create_balance_locked(
        db, tenant_id, payload.item_id, payload.warehouse_id, payload.bin_id
    )

    # 3. Apply Movement & Create Ledger Entry
    # balance.quantity_on_hand is a Numeric column (Decimal); payload.quantity is a
    # Pydantic float. Mixing them in +=/-= raises TypeError, so cast up front.
    quantity_before = balance.quantity_on_hand
    movement_qty = Decimal(str(payload.quantity))
    
    if payload.transaction_type == "IN":
        balance.quantity_on_hand += movement_qty
    elif payload.transaction_type == "OUT":
        balance.quantity_on_hand -= movement_qty
        movement_qty = -movement_qty
    elif payload.transaction_type == "ADJUST":
        balance.quantity_on_hand += movement_qty
    elif payload.transaction_type == "TRANSFER":
        balance.quantity_on_hand -= movement_qty
        movement_qty = -movement_qty
    else:
        raise ValueError(f"Unknown transaction type: {payload.transaction_type}")

    # The negative check is enforced by PostgreSQL `quantity_on_hand >= 0` check constraint,
    # but we do a python level check first for a clean, catchable error: the
    # old code raised sqlalchemy.exc.IntegrityError directly with statement/
    # params set to None, which crashes any caller that catches IntegrityError
    # and inspects `.orig` (a real DB-raised IntegrityError always has one).
    if balance.quantity_on_hand < 0:
        raise ValueError("Negative stock prevented: insufficient quantity on hand at this location.")
        
    # --- PHASE 4: BATCH STOCK UPDATE ---
    if payload.batch_id:
        from app.models.universal_tracking import UniversalBatchStock
        b_stmt = select(UniversalBatchStock).where(
            UniversalBatchStock.tenant_id == tenant_id,
            UniversalBatchStock.batch_id == payload.batch_id,
            UniversalBatchStock.warehouse_id == payload.warehouse_id,
            UniversalBatchStock.bin_id == payload.bin_id
        ).with_for_update()
        batch_bal = (await db.execute(b_stmt)).scalar_one_or_none()
        if not batch_bal:
            batch_bal = UniversalBatchStock(
                tenant_id=tenant_id,
                batch_id=payload.batch_id,
                warehouse_id=payload.warehouse_id,
                bin_id=payload.bin_id,
                quantity_on_hand=Decimal("0")
            )
            db.add(batch_bal)
            await db.flush()
        
        batch_bal.quantity_on_hand += movement_qty
        if batch_bal.quantity_on_hand < 0:
             raise ValueError("Insufficient batch stock.")
             
    # --- PHASE 4: SERIAL NUMBER UPDATE ---
    if payload.serial_numbers:
        from app.models.universal_tracking import UniversalSerialMaster
        # Verify length matches quantity if strictly enforced (skipping strict length check for partials, but ideally len(serials) == qty)
        s_stmt = select(UniversalSerialMaster).where(
            UniversalSerialMaster.tenant_id == tenant_id,
            UniversalSerialMaster.item_id == payload.item_id,
            UniversalSerialMaster.serial_number.in_(payload.serial_numbers)
        ).with_for_update()
        serials = (await db.execute(s_stmt)).scalars().all()
        
        # If IN, they might be new, but if they exist, just update location
        # If they don't exist, we should theoretically create them.
        existing_serials = {s.serial_number: s for s in serials}
        
        for s_num in payload.serial_numbers:
            serial_obj = existing_serials.get(s_num)
            if payload.transaction_type == "IN":
                if not serial_obj:
                    serial_obj = UniversalSerialMaster(
                        tenant_id=tenant_id,
                        item_id=payload.item_id,
                        batch_id=payload.batch_id,
                        serial_number=s_num,
                        status="available",
                        warehouse_id=payload.warehouse_id,
                        bin_id=payload.bin_id
                    )
                    db.add(serial_obj)
                else:
                    serial_obj.status = "available"
                    serial_obj.warehouse_id = payload.warehouse_id
                    serial_obj.bin_id = payload.bin_id
            elif payload.transaction_type in ("OUT", "TRANSFER"):
                if not serial_obj:
                    raise ValueError(f"Serial number {s_num} not found.")
                if serial_obj.status != "available":
                    raise ValueError(f"Serial number {s_num} is not available for dispatch.")
                if serial_obj.warehouse_id != payload.warehouse_id:
                    raise ValueError(f"Serial number {s_num} is not in the source warehouse.")
                    
                if payload.transaction_type == "OUT":
                    serial_obj.status = "dispatched"
                    serial_obj.warehouse_id = None
                    serial_obj.bin_id = None
                else:
                    serial_obj.status = "in-transit" # Or just dispatch it from current location

    # 4. Create Ledger Entry
    unit_cost_val = Decimal(str(payload.metadata_fields.get("unit_cost", 0.0))) if payload.metadata_fields else Decimal("0")
    total_cost_val = unit_cost_val * abs(movement_qty)
    
    from app.models.universal_ledger import UniversalInventoryLedger
    ledger_entry = UniversalInventoryLedger(
        tenant_id=tenant_id,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        bin_id=payload.bin_id,
        transaction_id=txn.id, # Needs flush if we want ID, but txn.id will be populated after flush/commit. Wait, let's flush txn first.
        quantity_before=quantity_before,
        movement_quantity=movement_qty,
        quantity_after=balance.quantity_on_hand,
        unit_cost=unit_cost_val,
        total_cost=total_cost_val,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        user_id=user_id
    )
    
    db.add(txn) # we already added it, but let's make sure it flushes
    await db.flush()
    ledger_entry.transaction_id = txn.id
    db.add(ledger_entry)

    # --- TRANSFER: credit the destination location in the SAME transaction ---
    # Previously TRANSFER only ever decremented the source balance — nothing
    # credited a destination, so a transfer was indistinguishable from a
    # write-off, and if the caller was expected to issue a second IN call
    # separately, a crash between the two left stock destroyed with no
    # atomicity. This does both legs under the one commit below.
    if payload.transaction_type == "TRANSFER":
        dest_balance = await _get_or_create_balance_locked(
            db, tenant_id, payload.item_id,
            payload.destination_warehouse_id, payload.destination_bin_id
        )
        dest_quantity_before = dest_balance.quantity_on_hand
        dest_movement_qty = abs(movement_qty)
        dest_balance.quantity_on_hand += dest_movement_qty

        dest_txn = UniversalStockTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=payload.item_id,
            warehouse_id=payload.destination_warehouse_id,
            bin_id=payload.destination_bin_id,
            batch_id=payload.batch_id,
            serial_numbers=payload.serial_numbers,
            transaction_type="TRANSFER_IN",
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            quantity=payload.quantity,
            metadata_=payload.metadata_fields,
        )
        db.add(dest_txn)
        await db.flush()

        dest_ledger_entry = UniversalInventoryLedger(
            tenant_id=tenant_id,
            item_id=payload.item_id,
            warehouse_id=payload.destination_warehouse_id,
            bin_id=payload.destination_bin_id,
            transaction_id=dest_txn.id,
            quantity_before=dest_quantity_before,
            movement_quantity=dest_movement_qty,
            quantity_after=dest_balance.quantity_on_hand,
            unit_cost=unit_cost_val,
            total_cost=total_cost_val,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            user_id=user_id,
        )
        db.add(dest_ledger_entry)

    await db.flush()
    await db.refresh(txn)
    return txn

async def reserve_stock(db: AsyncSession, tenant_id: uuid.UUID, payload: StockMovementRequest) -> UniversalStockBalance:
    bal_stmt = select(UniversalStockBalance).where(
        UniversalStockBalance.tenant_id == tenant_id,
        UniversalStockBalance.item_id == payload.item_id,
        UniversalStockBalance.warehouse_id == payload.warehouse_id,
        UniversalStockBalance.bin_id == payload.bin_id
    ).with_for_update()
    
    balance = (await db.execute(bal_stmt)).scalar_one_or_none()
    if not balance:
        raise ValueError("Cannot reserve stock: no balance found at location")
        
    balance.quantity_reserved += Decimal(str(payload.quantity))

    if balance.quantity_on_hand < balance.quantity_reserved + balance.quantity_allocated:
        raise ValueError("Insufficient available stock for reservation")
        
    await db.flush()
    await db.refresh(balance)
    return balance

async def allocate_stock(db: AsyncSession, tenant_id: uuid.UUID, payload: StockMovementRequest) -> UniversalStockBalance:
    bal_stmt = select(UniversalStockBalance).where(
        UniversalStockBalance.tenant_id == tenant_id,
        UniversalStockBalance.item_id == payload.item_id,
        UniversalStockBalance.warehouse_id == payload.warehouse_id,
        UniversalStockBalance.bin_id == payload.bin_id
    ).with_for_update()
    
    balance = (await db.execute(bal_stmt)).scalar_one_or_none()
    if not balance:
        raise ValueError("Cannot allocate stock: no balance found at location")
        
    # Allocation often converts a reservation to an allocation.
    # For simplicity in this engine, we just increase allocated.
    balance.quantity_allocated += Decimal(str(payload.quantity))

    if balance.quantity_on_hand < balance.quantity_reserved + balance.quantity_allocated:
        raise ValueError("Insufficient available stock for allocation")
        
    await db.flush()
    await db.refresh(balance)
    return balance
