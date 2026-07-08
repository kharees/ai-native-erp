"""
app/schemas/inventory.py
========================
Pydantic v2 request / response schema layer for the Inventory module.

Design principles
-----------------
  • Every schema class inherits from a minimal BaseModel; shared fields live
    in ``InventoryItemBase`` to avoid repetition.
  • The attributes JSONB column is typed as a discriminated union using
    Pydantic's ``Annotated`` + ``Discriminator`` so the validator narrows the
    correct attribute model at parse time — no manual if/else branching.
  • Separate ``Create``, ``Update``, and ``Response`` schemas follow the
    standard CRUD split: Create is strict, Update makes every field Optional,
    Response adds server-generated read-only fields.
  • ``model_config`` uses ``from_attributes=True`` on all ORM-facing models so
    SQLAlchemy mapped instances can be passed directly to ``model_validate()``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# =============================================================================
# 1.  Shared Enumerations (plain str literals — no import from enum module needed)
# =============================================================================

InventoryStatus   = Literal["active", "inactive", "discontinued", "draft", "pending_review"]
IndustryTemplate  = Literal["Manufacturing", "Retail", "Services"]
QualityGrade      = Literal["A", "B", "C", "rejected"]
RetailGender      = Literal["men", "women", "unisex", "kids", "na"]
RetailSeason      = Literal["spring_summer", "autumn_winter", "all_season", "limited_edition"]
LicenseType       = Literal[
    "perpetual", "subscription_monthly", "subscription_annual",
    "pay_per_use", "open_source", "custom",
]
UnitOfMeasure     = Literal[
    "unit", "kg", "g", "mg", "l", "ml",
    "m", "cm", "mm", "m2", "m3",
    "box", "pallet", "dozen", "pack",
    "hour", "day", "month",
]


# =============================================================================
# 2.  Industry Attribute Sub-Schemas
#     Each sub-schema carries a literal `template` discriminant field so
#     Pydantic can narrow the union without calling isinstance().
# =============================================================================

class ManufacturingAttributes(BaseModel):
    """
    Attribute matrix for manufactured goods.
    Stored as-is in the JSONB ``attributes`` column.
    """
    model_config = ConfigDict(extra="allow")  # allow unknown future fields

    template:             Literal["Manufacturing"]
    batch_number:         str          = Field(...,   min_length=1, max_length=128,
                                               description="Unique production batch identifier")
    unit_of_measure:      UnitOfMeasure = Field(default="unit")
    production_date:      str          = Field(...,   description="ISO 8601 date (YYYY-MM-DD)")
    expiry_date:          Optional[str]= Field(None,  description="ISO 8601 date — shelf-life / warranty end")
    quality_grade:        QualityGrade = Field(default="A")
    raw_material_source:  Optional[str]= Field(None,  max_length=255)
    machine_id:           Optional[str]= Field(None,  max_length=64)
    tolerances:           Optional[str]= Field(None,  max_length=64,  examples=["±0.05mm"])
    bom_reference:        Optional[str]= Field(None,  max_length=64)
    certification:        Optional[str]= Field(None,  max_length=64,  examples=["ISO 9001"])
    hazmat_code:          Optional[str]= Field(None,  max_length=32,  examples=["UN1263"])
    weight_kg:            Optional[float] = Field(None, ge=0)
    volume_m3:            Optional[float] = Field(None, ge=0)

    @field_validator("production_date", "expiry_date", mode="before")
    @classmethod
    def validate_date_string(cls, v: Any) -> Any:
        """Accept date objects or ISO strings; pass through None."""
        if v is None:
            return v
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)


class RetailAttributes(BaseModel):
    """
    Attribute matrix for retail / consumer products.
    Stored as-is in the JSONB ``attributes`` column.
    """
    model_config = ConfigDict(extra="allow")

    template:           Literal["Retail"]
    size:               str              = Field(..., min_length=1, max_length=32)
    color:              str              = Field(..., min_length=1, max_length=64)
    material:           Optional[str]    = Field(None, max_length=255)
    brand_line:         Optional[str]    = Field(None, max_length=128)
    barcode:            Optional[str]    = Field(None, max_length=64,
                                                 description="EAN / GTIN / UPC barcode value")
    season:             Optional[RetailSeason]  = None
    gender:             Optional[RetailGender]  = Field(default="na")
    style_code:         Optional[str]    = Field(None, max_length=64)
    country_of_origin:  Optional[str]    = Field(None, min_length=2, max_length=2,
                                                 description="ISO 3166-1 alpha-2, e.g. IN, US")
    mrp:                Optional[float]  = Field(None, ge=0,
                                                 description="Manufacturer's / max retail price")
    discount_pct:       Optional[float]  = Field(None, ge=0, le=100)
    shelf_min_qty:      Optional[int]    = Field(None, ge=0)
    planogram_slot:     Optional[str]    = Field(None, max_length=32)

    @field_validator("country_of_origin", mode="before")
    @classmethod
    def upper_country(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v


class ServicesAttributes(BaseModel):
    """
    Attribute matrix for intangible service items.
    Stored as-is in the JSONB ``attributes`` column.
    """
    model_config = ConfigDict(extra="allow")

    template:                Literal["Services"]
    service_type:            str             = Field(..., min_length=1, max_length=128)
    service_duration_hours:  float           = Field(..., gt=0,
                                                     description="Contracted effort in hours")
    deliverable_format:      Optional[str]   = Field(None, max_length=1000)
    team_size:               Optional[int]   = Field(None, ge=1)
    license_type:            Optional[LicenseType] = None
    renewal_period_days:     Optional[int]   = Field(None, ge=1)
    max_seats:               Optional[int]   = Field(None, ge=1)
    sla_response_hours:      Optional[float] = Field(None, ge=0)
    sla_uptime_pct:          Optional[float] = Field(None, ge=0, le=100)
    sow_url:                 Optional[AnyHttpUrl] = Field(None,
                                                           description="URL to the scope-of-work document")
    required_skills:         Optional[list[str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Discriminated union — Pydantic narrows via the `template` field value
# ---------------------------------------------------------------------------
InventoryAttributes = Annotated[
    Union[ManufacturingAttributes, RetailAttributes, ServicesAttributes],
    Field(discriminator="template"),
]


# =============================================================================
# 3.  Core Item Schemas
# =============================================================================

class InventoryItemBase(BaseModel):
    """
    Shared fields present in both Create and Response payloads.
    Validation rules are applied once here and inherited everywhere.
    """
    model_config = ConfigDict(populate_by_name=True)

    sku:              str            = Field(..., min_length=1, max_length=64,
                                             description="Stock-keeping unit code; unique per tenant")
    name:             str            = Field(..., min_length=2, max_length=255)
    description:      Optional[str]  = Field(None, max_length=2000)
    category:         Optional[str]  = Field(None, max_length=128)
    sub_category:     Optional[str]  = Field(None, max_length=128)
    brand:            Optional[str]  = Field(None, max_length=128)
    tags:             list[str]      = Field(default_factory=list,
                                             description="Flat tag array (GIN indexed in Postgres)")
    unit_price:       float          = Field(..., ge=0)
    cost_price:       float          = Field(..., ge=0)
    currency:         str            = Field(default="USD", min_length=3, max_length=3,
                                             description="ISO 4217 currency code")
    quantity_on_hand: int            = Field(default=0, ge=0)
    reorder_level:    int            = Field(default=0, ge=0)
    unit_of_measure:  UnitOfMeasure  = Field(default="unit")
    status:           InventoryStatus = Field(default="draft")

    @field_validator("currency", mode="before")
    @classmethod
    def upper_currency(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: Any) -> Any:
        """Accept a comma-separated string or a list; strip blank entries."""
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v if v is not None else []


# ---------------------------------------------------------------------------
# 3a.  CREATE — strict; all required fields must be present
# ---------------------------------------------------------------------------

class InventoryItemCreate(InventoryItemBase):
    """
    Request body for POST /api/v1/inventory.

    The ``attributes`` field is a discriminated union — its ``template``
    key determines which sub-schema is validated.

    Pydantic raises ``422 Unprocessable Entity`` automatically if:
      • ``template`` is missing or has an unknown value.
      • Required attribute fields for the chosen template are absent.
    """
    attributes: InventoryAttributes = Field(
        ...,
        description=(
            'Industry-specific JSONB attribute matrix. '
            'Must contain a ``template`` key: "Manufacturing" | "Retail" | "Services"'
        ),
    )

    @model_validator(mode="after")
    def validate_uom_consistency(self) -> "InventoryItemCreate":
        """
        Cross-field rule: Manufacturing items must use a physical UoM —
        'hour' / 'day' / 'month' are service-only units.
        """
        service_uoms = {"hour", "day", "month"}
        if (
            isinstance(self.attributes, ManufacturingAttributes)
            and self.unit_of_measure in service_uoms
        ):
            raise ValueError(
                f"unit_of_measure '{self.unit_of_measure}' is not valid for "
                "Manufacturing items. Use a physical unit (kg, unit, m, …)."
            )
        return self


# ---------------------------------------------------------------------------
# 3b.  UPDATE — every field is Optional (PATCH semantics)
# ---------------------------------------------------------------------------

class InventoryItemUpdate(BaseModel):
    """
    Request body for PATCH /api/v1/inventory/{item_id}.
    Every field is optional — only supplied fields are written to the DB.
    ``attributes`` is typed as a raw dict here so partial JSONB updates
    are supported without requiring the full attribute object.
    """
    model_config = ConfigDict(populate_by_name=True)

    name:             Optional[str]            = Field(None, min_length=2, max_length=255)
    description:      Optional[str]            = Field(None, max_length=2000)
    category:         Optional[str]            = Field(None, max_length=128)
    sub_category:     Optional[str]            = Field(None, max_length=128)
    brand:            Optional[str]            = Field(None, max_length=128)
    tags:             Optional[list[str]]      = None
    unit_price:       Optional[float]          = Field(None, ge=0)
    cost_price:       Optional[float]          = Field(None, ge=0)
    currency:         Optional[str]            = Field(None, min_length=3, max_length=3)
    quantity_on_hand: Optional[int]            = Field(None, ge=0)
    reorder_level:    Optional[int]            = Field(None, ge=0)
    unit_of_measure:  Optional[UnitOfMeasure]  = None
    status:           Optional[InventoryStatus]= None
    attributes:       Optional[InventoryAttributes] = None

    def non_null_fields(self) -> dict[str, Any]:
        """Return only fields that were explicitly provided (not None)."""
        return self.model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# 3c.  RESPONSE — includes server-generated read-only fields
# ---------------------------------------------------------------------------

class InventoryItemResponse(InventoryItemBase):
    """
    Response schema for all inventory endpoints.
    Constructed from ORM model instances via ``model_validate(orm_obj)``.

    ``attributes`` is returned as a raw dict (the JSONB value from Postgres)
    so the frontend receives the full discriminated object including ``template``.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id:         uuid.UUID  = Field(..., description="Primary key (UUID v4)")
    tenant_id:  uuid.UUID
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw JSONB attribute matrix — contains 'template' discriminant key",
    )
    is_active:  bool
    created_by: Optional[uuid.UUID] = None
    updated_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 4.  Pagination & List Response
# =============================================================================

class PaginationMeta(BaseModel):
    """Metadata block attached to every list endpoint response."""
    total:   int = Field(..., ge=0, description="Total records matching the filter")
    limit:   int = Field(..., ge=1)
    offset:  int = Field(..., ge=0)
    has_more: bool


class InventoryListResponse(BaseModel):
    """Paginated list response for GET /api/v1/inventory."""
    items: list[InventoryItemResponse]
    meta:  PaginationMeta


# =============================================================================
# 5.  Query Filter Schema (incoming GET query params)
# =============================================================================

class InventoryFilterParams(BaseModel):
    """
    Query-parameter filter model consumed by the CRUD layer.
    Constructed from FastAPI ``Query(...)`` dependencies in the router.
    """
    model_config = ConfigDict(populate_by_name=True)

    template:    Optional[IndustryTemplate]   = None
    status:      Optional[InventoryStatus]    = None
    category:    Optional[str]               = None
    search:      Optional[str]               = Field(
        None, max_length=200,
        description="Full-text search against name, sku, description (trigram index)"
    )
    tags:        Optional[list[str]]          = None
    min_price:   Optional[float]             = Field(None, ge=0)
    max_price:   Optional[float]             = Field(None, ge=0)
    low_stock:   bool                        = Field(
        False,
        description="If true, return only items where quantity_on_hand <= reorder_level"
    )
    limit:       int                         = Field(default=20, ge=1, le=200)
    offset:      int                         = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_price_range(self) -> "InventoryFilterParams":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be ≤ max_price")
        return self


# =============================================================================
# 6.  Attribute-level Patch (JSONB merge)
# =============================================================================

class AttributesPatchPayload(BaseModel):
    """
    Allows partial merging of the JSONB attributes column using Postgres
    ``||`` (merge) operator without replacing the entire object.

    POST /api/v1/inventory/{item_id}/attributes
    """
    patch: dict[str, Any] = Field(
        ...,
        description=(
            "Key-value pairs to merge into the existing attributes JSONB. "
            "Existing keys not present in this payload are preserved."
        ),
    )
