import csv
import io
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud import universal_analytics as crud
from app.schemas import universal_reports as schemas
from app.middleware.tenant_auth import TenantIDDep
from app.middleware.rbac import RequirePermission

router = APIRouter()
DBDep = Annotated[AsyncSession, Depends(get_db)]

@router.get("/summary", response_model=schemas.StockValuationSummary, dependencies=[Depends(RequirePermission("UniversalInventory", "Reports", "Read"))])
async def get_summary(tenant_id: TenantIDDep, db: DBDep):
    return await crud.get_valuation_summary(db, tenant_id)

@router.get("/aging", dependencies=[Depends(RequirePermission("UniversalInventory", "Reports", "Read"))])
async def get_aging(tenant_id: TenantIDDep, db: DBDep, export: str | None = None):
    data = await crud.get_aging_report(db, tenant_id)
    
    if export == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["item_id", "warehouse_id", "quantity_on_hand", "days_since_last_movement", "aging_bucket"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory_aging.csv"}
        )
    
    return data

@router.get("/abc-analysis", response_model=list[schemas.ABCAnalysisItem], dependencies=[Depends(RequirePermission("UniversalInventory", "Reports", "Read"))])
async def get_abc(tenant_id: TenantIDDep, db: DBDep, export: str | None = None):
    data = await crud.get_abc_analysis(db, tenant_id)
    
    if export == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["item_id", "item_code", "item_name", "total_value_consumed", "cumulative_percentage", "classification"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=abc_analysis.csv"}
        )
        
    return data
