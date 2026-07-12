"""
app/core/pagination.py
=======================
Shared offset/limit pagination helper for list endpoints.

Every "list X" CRUD function in this codebase previously ran two full
round trips per call: a `SELECT count(*) FROM (subquery)` to get the total,
then the actual page query. This merges both into one query using a
`count(*) OVER()` window function, which Postgres computes alongside the
page rows in a single pass.
"""

from typing import Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


async def paginate(
    db: AsyncSession,
    stmt: Select,
    order_by,
    limit: int,
    offset: int,
) -> tuple[Sequence[T], int]:
    """
    Execute `stmt` (a filtered, unordered/unlimited SELECT of a single ORM
    entity) as one page of `limit` rows starting at `offset`, plus the total
    row count matching the filters — in one query for the common case.

    Falls back to a second, plain `count(*)` query only when the requested
    page comes back empty (zero total matches, or an out-of-range offset),
    since a window function has nothing to attach a count to when there are
    no rows to return.
    """
    paged_stmt = stmt.order_by(order_by).limit(limit).offset(offset)
    windowed_stmt = paged_stmt.add_columns(func.count().over().label("_total_count"))
    rows = (await db.execute(windowed_stmt)).all()

    if not rows:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()
        return [], total

    items = [row[0] for row in rows]
    total = rows[0]._total_count
    return items, total
