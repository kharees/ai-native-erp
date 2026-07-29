"""
app/api/v1/endpoints/gst_reports.py
=======================================
GSTR-1 / GSTR-3B export endpoints for a tenant's CA to file GST returns
with -- see app/services/gst_reports.py for the aggregation logic and
app/services/gst_report_export.py for the .xlsx rendering. The app
itself never files with the government; this only produces the data a
CA needs.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.core.database import get_db
from app.middleware.tenant_auth import get_verified_tenant_id
from app.middleware.rbac import RequirePermission
from app.services.audit import AuditLogger
from app.services import gst_reports as gst_reports_service
from app.services.gst_report_export import render_gstr1_workbook, render_gstr3b_workbook

router = APIRouter()

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/gstr1", dependencies=[Depends(RequirePermission("Finance", "GSTReports", "Read"))])
async def get_gstr1(
    request: Request,
    financial_year: str,
    month: int,
    format: Literal["xlsx", "json"] = "xlsx",
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        data = await gst_reports_service.generate_gstr1_data(db, tenant_id, financial_year, month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE_REPORTING",
        action_type="GENERATE_GSTR1", new_values={"financial_year": financial_year, "month": month, "format": format},
    )

    if format == "json":
        return data

    workbook_bytes = render_gstr1_workbook(data)
    filename = f"GSTR1_{financial_year}_{month:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(workbook_bytes),
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/gstr3b", dependencies=[Depends(RequirePermission("Finance", "GSTReports", "Read"))])
async def get_gstr3b(
    request: Request,
    financial_year: str,
    month: int,
    format: Literal["xlsx", "json"] = "json",
    db: AsyncSession = Depends(get_db),
):
    tenant_id = await get_verified_tenant_id(request)
    try:
        data = await gst_reports_service.generate_gstr3b_summary(db, tenant_id, financial_year, month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await AuditLogger.log_action(
        db=db, request=request, action_category="FINANCE_REPORTING",
        action_type="GENERATE_GSTR3B", new_values={"financial_year": financial_year, "month": month, "format": format},
    )

    if format == "json":
        return data

    workbook_bytes = render_gstr3b_workbook(data)
    filename = f"GSTR3B_{financial_year}_{month:02d}.xlsx"
    return StreamingResponse(
        io.BytesIO(workbook_bytes),
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
