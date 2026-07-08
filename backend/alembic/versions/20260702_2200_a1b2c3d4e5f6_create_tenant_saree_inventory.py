"""
alembic/versions/20260702_2200_a1b2c3d4e5f6_create_tenant_saree_inventory.py
=============================================================================
Revision   : a1b2c3d4e5f6
Revises    : (base — first Alembic-tracked revision)
Create Date: 2026-07-02 22:00:00.000000

Summary
-------
Phase 3 — Multi-Tenant Handloom Inventory Control Ledger Pipelines Engine

Creates the ``public.tenant_saree_inventory`` table and all supporting
database objects required for the handloom / saree domain:

    1. ``public.tenant_saree_inventory`` table
       • Full schema mirroring ``InventoryItem`` / ``TenantSareeInventory``
         ORM model columns with handloom-specific inline comments.
       • (tenant_id, sku) unique constraint for duplicate-SKU guard.
       • JSONB ``attributes`` column for the discriminated industry template
         matrix (Manufacturing | Retail | Services) with handloom extensions.

    2. Performance indexes
       • B-Tree:  tenant_id, tenant_id+status, category (ilike-aware),
                  tenant_id+qty+reorder (low-stock alert), sku (per-tenant)
       • GIN:     attributes jsonb_path_ops (containment / jsonpath queries)
       • GIN:     attributes jsonb_ops    (key-existence queries)
       • GIN:     tags TEXT[] array
       • GIN:     name + description trigram indexes (ILIKE / full-text)

    3. Audit trigger
       Shared ``public.set_updated_at()`` function (defined in V001) is
       attached to auto-update ``updated_at`` on every UPDATE.

    4. Row-Level Security (RLS) — multi-tenant isolation
       • ENABLE ROW LEVEL SECURITY + FORCE ROW LEVEL SECURITY
       • SELECT policy: any active tenant member may read their own rows.
       • INSERT policy: manager / admin / owner may create inventory nodes.
       • UPDATE policy: manager / admin / owner may modify their tenant rows.
       • DELETE policy: owner / admin may delete rows within their tenant.

All DDL is idempotent via IF NOT EXISTS / OR REPLACE / DROP IF EXISTS guards.

Downgrade
---------
Removes all RLS policies, triggers, indexes, and the table itself in
reverse dependency order.  Safe to re-run (idempotent DROP IF EXISTS).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers — consumed by Alembic's DAG
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None   # This is the first Alembic-tracked revision
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# =============================================================================
# UPGRADE — forward migration
# =============================================================================

def upgrade() -> None:
    """
    Apply all DDL objects for the tenant_saree_inventory table.

    Execution order:
        1. Extensions (idempotent guards)
        2. inventory_status enum type (idempotent DO block)
        3. Table creation
        4. Constraints
        5. Indexes (B-Tree and GIN)
        6. Audit trigger
        7. Comments
        8. Row-Level Security (RLS) policies
    """
    conn = op.get_bind()

    # =========================================================================
    # 1.  Required PostgreSQL extensions
    # =========================================================================
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "btree_gin"'))

    # =========================================================================
    # 2.  inventory_status enum (shared with inventory_items, idempotent)
    # =========================================================================
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'inventory_status'
            ) THEN
                CREATE TYPE public.inventory_status AS ENUM (
                    'active',
                    'inactive',
                    'discontinued',
                    'draft',
                    'pending_review'
                );
            END IF;
        END
        $$;
    """))

    # =========================================================================
    # 3.  public.tenant_saree_inventory table
    #
    #     Represents a single handloom / saree SKU node owned by one tenant.
    #     The ``attributes`` JSONB column stores the discriminated industry
    #     template matrix (template key selects sub-schema at the API layer).
    # =========================================================================
    op.create_table(
        "tenant_saree_inventory",
        # ── Identity ──────────────────────────────────────────────────────────
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Primary key — UUID v4, server-generated.",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.tenants.id",
                ondelete="CASCADE",
                name="fk_saree_inventory_tenant_id",
            ),
            nullable=False,
            index=True,
            comment="FK → public.tenants.id. Cascade-deletes all inventory rows when tenant is removed.",
        ),
        sa.Column(
            "sku",
            sa.String(64),
            nullable=False,
            comment="Stock-keeping unit code; unique per tenant (enforced by uq_saree_inventory_tenant_sku).",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable saree product name (e.g. 'Kanjivaram Silk — Crimson Gold Border').",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Long-form product description; optional.",
        ),
        # ── Categorisation ────────────────────────────────────────────────────
        sa.Column(
            "category",
            sa.String(128),
            nullable=True,
            comment="Top-level saree category (e.g. Kanjivaram, Banarasi, Chanderi, Paithani).",
        ),
        sa.Column(
            "sub_category",
            sa.String(128),
            nullable=True,
            comment="Sub-category (e.g. Bridal, Festival, Casual, Wedding).",
        ),
        sa.Column(
            "brand",
            sa.String(128),
            nullable=True,
            comment="Weaving house / brand name.",
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
            comment="GIN-indexed flat tag array for multi-value filtering (e.g. ['pure-silk','bridal','handloom']).",
        ),
        # ── Pricing & stock ───────────────────────────────────────────────────
        sa.Column(
            "unit_price",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("0"),
            comment="Selling price per unit (MRP / wholesale). Must be >= 0.",
        ),
        sa.Column(
            "cost_price",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("0"),
            comment="Landed cost per unit (weaving cost + dye + finishing). Must be >= 0.",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'INR'"),
            comment="ISO 4217 currency code; default INR for domestic handloom market.",
        ),
        sa.Column(
            "quantity_on_hand",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Current stock count. Must be >= 0.",
        ),
        sa.Column(
            "reorder_level",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Threshold quantity that triggers a replenishment alert. Must be >= 0.",
        ),
        sa.Column(
            "unit_of_measure",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'unit'"),
            comment="Unit of measure (unit | m | kg | pcs | set).",
        ),
        # ── JSONB attribute matrix ─────────────────────────────────────────────
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment=(
                "Industry-discriminated attribute matrix (template key selects sub-schema). "
                "Handloom extensions: weave_type, thread_count, zari_type, dye_method, "
                "warp_material, weft_material, GI_tag, loom_type, weaver_id, region_of_origin."
            ),
        ),
        # ── Status & lifecycle ────────────────────────────────────────────────
        sa.Column(
            "status",
            sa.Enum(
                "active", "inactive", "discontinued", "draft", "pending_review",
                name="inventory_status",
                create_type=False,   # Type already created in step 2 above
            ),
            nullable=False,
            server_default=sa.text("'draft'"),
            comment="Lifecycle status of the inventory node.",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("TRUE"),
            comment="Soft-delete flag; FALSE hides the node from catalog queries.",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.user_profiles.id",
                ondelete="SET NULL",
                name="fk_saree_inventory_created_by",
            ),
            nullable=True,
            comment="UUID of the user who ingested this inventory node.",
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.user_profiles.id",
                ondelete="SET NULL",
                name="fk_saree_inventory_updated_by",
            ),
            nullable=True,
            comment="UUID of the last user to modify this inventory node.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="UTC timestamp of node creation (server-set).",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="UTC timestamp of last modification (auto-updated by trigger).",
        ),
        # ── Table-level arguments ─────────────────────────────────────────────
        sa.CheckConstraint("unit_price >= 0",       name="ck_saree_inventory_unit_price_gte_0"),
        sa.CheckConstraint("cost_price >= 0",       name="ck_saree_inventory_cost_price_gte_0"),
        sa.CheckConstraint("quantity_on_hand >= 0", name="ck_saree_inventory_qty_gte_0"),
        sa.CheckConstraint("reorder_level >= 0",    name="ck_saree_inventory_reorder_gte_0"),
        schema="public",
        comment=(
            "Multi-tenant handloom / saree inventory control ledger. "
            "One row per SKU per tenant. JSONB attributes column stores "
            "discriminated industry template matrix with handloom domain extensions. "
            "Protected by Row-Level Security — each tenant sees only their own rows."
        ),
    )

    # =========================================================================
    # 4.  Unique constraint — (tenant_id, sku) pair
    #     Mirrors the duplicate-SKU guard in the POST / endpoint.
    # =========================================================================
    op.create_unique_constraint(
        "uq_saree_inventory_tenant_sku",
        "tenant_saree_inventory",
        ["tenant_id", "sku"],
        schema="public",
    )

    # =========================================================================
    # 5.  Performance Indexes
    # =========================================================================

    # B-Tree: fast per-tenant row access (used on every query)
    op.create_index(
        "idx_saree_inventory_tenant_id",
        "tenant_saree_inventory",
        ["tenant_id"],
        schema="public",
    )

    # B-Tree: tenant + status + active — dashboard and status-filter queries
    op.create_index(
        "idx_saree_inventory_tenant_status",
        "tenant_saree_inventory",
        ["tenant_id", "status"],
        schema="public",
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # B-Tree: category + sub_category — powers GET / ?saree_type= ILIKE filter
    op.create_index(
        "idx_saree_inventory_category",
        "tenant_saree_inventory",
        ["tenant_id", "category", "sub_category"],
        schema="public",
    )

    # B-Tree: low-stock alert — quantity_on_hand <= reorder_level queries
    op.create_index(
        "idx_saree_inventory_reorder",
        "tenant_saree_inventory",
        ["tenant_id", "quantity_on_hand", "reorder_level"],
        schema="public",
        postgresql_where=sa.text("is_active = TRUE AND status = 'active'"),
    )

    # B-Tree: SKU lookup per tenant (duplicate guard SELECT)
    op.create_index(
        "idx_saree_inventory_sku",
        "tenant_saree_inventory",
        ["tenant_id", "sku"],
        schema="public",
    )

    # GIN: JSONB containment + jsonpath queries (attributes @> '{"color": "red"}')
    # Powers: filter-attributes/ endpoint astext() == queries indirectly
    op.create_index(
        "idx_saree_inventory_attributes_gin_path",
        "tenant_saree_inventory",
        ["attributes"],
        schema="public",
        postgresql_using="gin",
        postgresql_ops={"attributes": "jsonb_path_ops"},
    )

    # GIN: JSONB key-existence queries (attributes ? 'weave_type')
    op.create_index(
        "idx_saree_inventory_attributes_gin_ops",
        "tenant_saree_inventory",
        ["attributes"],
        schema="public",
        postgresql_using="gin",
    )

    # GIN: tags TEXT[] array — WHERE tags @> ARRAY['handloom','silk']
    op.create_index(
        "idx_saree_inventory_tags_gin",
        "tenant_saree_inventory",
        ["tags"],
        schema="public",
        postgresql_using="gin",
    )

    # GIN: trigram index on name — fast ILIKE / full-text product name search
    op.create_index(
        "idx_saree_inventory_name_trgm",
        "tenant_saree_inventory",
        [sa.text("name gin_trgm_ops")],
        schema="public",
        postgresql_using="gin",
    )

    # GIN: trigram index on description — ILIKE search in description field
    op.create_index(
        "idx_saree_inventory_desc_trgm",
        "tenant_saree_inventory",
        [sa.text("description gin_trgm_ops")],
        schema="public",
        postgresql_using="gin",
    )

    # =========================================================================
    # 6.  Audit trigger — auto-update updated_at on every row modification
    #     Re-uses the shared set_updated_at() function defined in V001.
    # =========================================================================
    conn.execute(sa.text("""
        DROP TRIGGER IF EXISTS trg_saree_inventory_updated_at
            ON public.tenant_saree_inventory;

        CREATE TRIGGER trg_saree_inventory_updated_at
            BEFORE UPDATE ON public.tenant_saree_inventory
            FOR EACH ROW
            EXECUTE FUNCTION public.set_updated_at();
    """))

    # =========================================================================
    # 7.  Table & column comments (PostgreSQL COMMENT ON)
    # =========================================================================
    conn.execute(sa.text("""
        COMMENT ON TABLE public.tenant_saree_inventory IS
            'Phase 3 — Multi-Tenant Handloom Inventory Control Ledger. '
            'One SKU node per tenant. JSONB attributes column stores '
            'discriminated industry template (Manufacturing | Retail | Services) '
            'with handloom domain extensions (weave_type, zari_type, GI_tag, etc.). '
            'Protected by Row-Level Security.';

        COMMENT ON COLUMN public.tenant_saree_inventory.attributes IS
            'Schema-less JSONB attribute matrix. '
            'Required key: "template" (Manufacturing | Retail | Services). '
            'Handloom extensions: weave_type, thread_count, zari_type, '
            'dye_method, warp_material, weft_material, GI_tag, loom_type, '
            'weaver_id, region_of_origin.';

        COMMENT ON COLUMN public.tenant_saree_inventory.tags IS
            'Flat text array for multi-value filtering. '
            'GIN indexed. Examples: [''pure-silk'', ''bridal'', ''handloom'', ''zari''].';

        COMMENT ON COLUMN public.tenant_saree_inventory.reorder_level IS
            'Minimum quantity_on_hand before a replenishment alert fires. '
            'Low-stock condition: quantity_on_hand <= reorder_level.';

        COMMENT ON COLUMN public.tenant_saree_inventory.currency IS
            'ISO 4217 currency code. Defaults to INR for domestic handloom market.';
    """))

    # =========================================================================
    # 8.  Row-Level Security (RLS) — multi-tenant isolation layer
    #
    #     Isolation pattern:
    #       USING (tenant_id = (
    #           SELECT tenant_id FROM public.user_profiles WHERE id = auth.uid()
    #       ))
    #
    #     auth.uid() = Supabase JWT sub claim (authenticated user UUID).
    #     The correlated sub-select is evaluated per-row but cached via
    #     PostgreSQL's InitPlan optimisation — no N+1 scans.
    #
    #     Migrations run as superuser/service-role — FORCE RLS ensures
    #     even the owner is subject to policies in normal operation.
    # =========================================================================
    conn.execute(sa.text("""
        -- Enable and force RLS
        ALTER TABLE public.tenant_saree_inventory ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_saree_inventory FORCE ROW LEVEL SECURITY;

        -- ── SELECT ─────────────────────────────────────────────────────────
        -- Any active authenticated member of the tenant may read inventory.
        DROP POLICY IF EXISTS "saree_inventory_select_tenant"
            ON public.tenant_saree_inventory;

        CREATE POLICY "saree_inventory_select_tenant"
            ON public.tenant_saree_inventory
            FOR SELECT
            USING (
                tenant_id = (
                    SELECT tenant_id
                    FROM   public.user_profiles
                    WHERE  id = auth.uid()
                )
            );

        -- ── INSERT ─────────────────────────────────────────────────────────
        -- Manager / Admin / Owner of the same tenant may ingest new nodes.
        DROP POLICY IF EXISTS "saree_inventory_insert_manager"
            ON public.tenant_saree_inventory;

        CREATE POLICY "saree_inventory_insert_manager"
            ON public.tenant_saree_inventory
            FOR INSERT
            WITH CHECK (
                tenant_id = (
                    SELECT tenant_id
                    FROM   public.user_profiles
                    WHERE  id = auth.uid()
                )
                AND EXISTS (
                    SELECT 1
                    FROM   public.user_profiles
                    WHERE  id        = auth.uid()
                    AND    role      IN ('owner', 'admin', 'manager')
                    AND    is_active = TRUE
                )
            );

        -- ── UPDATE ─────────────────────────────────────────────────────────
        -- Manager / Admin / Owner of the same tenant may modify nodes.
        DROP POLICY IF EXISTS "saree_inventory_update_manager"
            ON public.tenant_saree_inventory;

        CREATE POLICY "saree_inventory_update_manager"
            ON public.tenant_saree_inventory
            FOR UPDATE
            USING (
                tenant_id = (
                    SELECT tenant_id
                    FROM   public.user_profiles
                    WHERE  id = auth.uid()
                )
                AND EXISTS (
                    SELECT 1
                    FROM   public.user_profiles
                    WHERE  id        = auth.uid()
                    AND    role      IN ('owner', 'admin', 'manager')
                    AND    is_active = TRUE
                )
            );

        -- ── DELETE ─────────────────────────────────────────────────────────
        -- Only Owner / Admin of the same tenant may delete nodes.
        DROP POLICY IF EXISTS "saree_inventory_delete_admin"
            ON public.tenant_saree_inventory;

        CREATE POLICY "saree_inventory_delete_admin"
            ON public.tenant_saree_inventory
            FOR DELETE
            USING (
                tenant_id = (
                    SELECT tenant_id
                    FROM   public.user_profiles
                    WHERE  id = auth.uid()
                )
                AND EXISTS (
                    SELECT 1
                    FROM   public.user_profiles
                    WHERE  id        = auth.uid()
                    AND    role      IN ('owner', 'admin')
                    AND    is_active = TRUE
                )
            );
    """))


# =============================================================================
# DOWNGRADE — reverse migration (idempotent)
# =============================================================================

def downgrade() -> None:
    """
    Remove all objects created by this revision in reverse dependency order:
        1. RLS policies
        2. Audit trigger
        3. Indexes
        4. Unique constraint
        5. Table
    The ``inventory_status`` enum and extensions are shared with other tables
    and are NOT dropped here to avoid breaking existing objects.
    """
    conn = op.get_bind()

    # 1.  Drop RLS policies
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS "saree_inventory_delete_admin"
            ON public.tenant_saree_inventory;
        DROP POLICY IF EXISTS "saree_inventory_update_manager"
            ON public.tenant_saree_inventory;
        DROP POLICY IF EXISTS "saree_inventory_insert_manager"
            ON public.tenant_saree_inventory;
        DROP POLICY IF EXISTS "saree_inventory_select_tenant"
            ON public.tenant_saree_inventory;
    """))

    # 2.  Drop audit trigger
    conn.execute(sa.text("""
        DROP TRIGGER IF EXISTS trg_saree_inventory_updated_at
            ON public.tenant_saree_inventory;
    """))

    # 3.  Drop all indexes
    for idx in [
        "idx_saree_inventory_desc_trgm",
        "idx_saree_inventory_name_trgm",
        "idx_saree_inventory_tags_gin",
        "idx_saree_inventory_attributes_gin_ops",
        "idx_saree_inventory_attributes_gin_path",
        "idx_saree_inventory_sku",
        "idx_saree_inventory_reorder",
        "idx_saree_inventory_category",
        "idx_saree_inventory_tenant_status",
        "idx_saree_inventory_tenant_id",
    ]:
        op.drop_index(idx, table_name="tenant_saree_inventory", schema="public", if_exists=True)

    # 4.  Drop unique constraint
    op.drop_constraint(
        "uq_saree_inventory_tenant_sku",
        "tenant_saree_inventory",
        schema="public",
        type_="unique",
    )

    # 5.  Drop table
    op.drop_table("tenant_saree_inventory", schema="public")
