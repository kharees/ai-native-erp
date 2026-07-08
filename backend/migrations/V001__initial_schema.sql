-- =============================================================================
--  AI-Native ERP — Initial Schema Migration
--  File   : backend/migrations/V001__initial_schema.sql
--  Engine : PostgreSQL 15+ (Supabase)
--  Author : AI-Native ERP Platform
--
--  Tables created:
--    1. public.tenants           — top-level organisation / company record
--    2. public.user_profiles     — per-tenant user metadata linked to auth.users
--    3. public.inventory_items   — multi-tenant inventory with JSONB attributes
--
--  Run order: execute this file once against a fresh Supabase project database.
--  All objects are idempotent via IF NOT EXISTS / CREATE OR REPLACE guards.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0.  Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- trigram full-text on name columns
CREATE EXTENSION IF NOT EXISTS "btree_gin";        -- composite GIN indexes including btree cols

-- ---------------------------------------------------------------------------
-- 0b.  Shared audit trigger function
--      Auto-updates updated_at on every UPDATE without per-table boilerplate.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- =============================================================================
-- 1.  public.tenants
--     One row per organisation. The "root" multi-tenancy boundary.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.tenants (
    -- -------------------------------------------------------------------------
    -- Identity
    -- -------------------------------------------------------------------------
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug                TEXT            NOT NULL UNIQUE,   -- URL-safe short name, e.g. "acme-corp"
    name                TEXT            NOT NULL,

    -- -------------------------------------------------------------------------
    -- Subscription / plan metadata
    -- -------------------------------------------------------------------------
    plan                TEXT            NOT NULL DEFAULT 'free'
                            CHECK (plan IN ('free', 'starter', 'growth', 'enterprise')),
    plan_expires_at     TIMESTAMPTZ,

    -- -------------------------------------------------------------------------
    -- Flexible schema-less config (theme colours, feature flags, AI settings …)
    -- -------------------------------------------------------------------------
    settings            JSONB           NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Status & lifecycle
    -- -------------------------------------------------------------------------
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tenants_slug
    ON public.tenants (slug);

CREATE INDEX IF NOT EXISTS idx_tenants_plan
    ON public.tenants (plan)
    WHERE is_active = TRUE;

-- GIN index on settings JSONB for fast key/value look-ups
CREATE INDEX IF NOT EXISTS idx_tenants_settings_gin
    ON public.tenants USING GIN (settings jsonb_path_ops);

-- Audit trigger
DROP TRIGGER IF EXISTS trg_tenants_updated_at ON public.tenants;
CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Comments
COMMENT ON TABLE  public.tenants              IS 'Top-level organisation / company record (multi-tenancy root).';
COMMENT ON COLUMN public.tenants.slug         IS 'URL-safe unique identifier used in subdomains and API paths.';
COMMENT ON COLUMN public.tenants.settings     IS 'Arbitrary JSONB config: feature flags, theme, AI model preferences, etc.';


-- =============================================================================
-- 2.  public.user_profiles
--     Extends auth.users (Supabase managed) with tenant membership & role data.
--     Linked 1-to-1 with auth.users via user_id FK.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    -- -------------------------------------------------------------------------
    -- Identity — mirrors auth.users
    -- -------------------------------------------------------------------------
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID            NOT NULL UNIQUE
                            REFERENCES auth.users (id) ON DELETE CASCADE,
    tenant_id           UUID            NOT NULL
                            REFERENCES public.tenants (id) ON DELETE CASCADE,

    -- -------------------------------------------------------------------------
    -- Personal details
    -- -------------------------------------------------------------------------
    first_name TEXT,
    last_name TEXT,
    profile_image TEXT,
    phone               TEXT,
    timezone            TEXT            NOT NULL DEFAULT 'UTC',
    locale              TEXT            NOT NULL DEFAULT 'en',

    -- -------------------------------------------------------------------------
    -- Role-based access control
    -- -------------------------------------------------------------------------
    role                TEXT            NOT NULL DEFAULT 'member'
                            CHECK (role IN ('owner', 'admin', 'manager', 'member', 'viewer')),
    permissions         JSONB           NOT NULL DEFAULT '{}',   -- granular capability overrides

    -- -------------------------------------------------------------------------
    -- Flexible per-user extension data
    -- -------------------------------------------------------------------------
    metadata            JSONB           NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Status & lifecycle
    -- -------------------------------------------------------------------------
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    last_seen_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_id
    ON public.user_profiles (tenant_id);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id
    ON public.user_profiles (user_id);

-- Composite: fast per-tenant role look-ups
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_role
    ON public.user_profiles (tenant_id, role)
    WHERE is_active = TRUE;

-- GIN index on permissions JSONB
CREATE INDEX IF NOT EXISTS idx_user_profiles_permissions_gin
    ON public.user_profiles USING GIN (permissions jsonb_path_ops);

-- GIN index on metadata JSONB
CREATE INDEX IF NOT EXISTS idx_user_profiles_metadata_gin
    ON public.user_profiles USING GIN (metadata jsonb_path_ops);

-- Trigram index for name search
CREATE INDEX IF NOT EXISTS idx_user_profiles_fullname_trgm
    ON public.user_profiles USING GIN (first_name gin_trgm_ops);

-- Audit trigger
DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Comments
COMMENT ON TABLE  public.user_profiles              IS 'Per-tenant user metadata extending Supabase auth.users.';
COMMENT ON COLUMN public.user_profiles.user_id      IS 'FK → auth.users.id; cascade delete removes profile when auth user is deleted.';
COMMENT ON COLUMN public.user_profiles.role         IS 'Coarse RBAC role; fine-grained overrides stored in permissions JSONB.';
COMMENT ON COLUMN public.user_profiles.permissions  IS 'Granular capability flags e.g. {"inventory.write": true, "reports.export": false}.';
COMMENT ON COLUMN public.user_profiles.metadata     IS 'Arbitrary extension data: ERP module preferences, onboarding state, etc.';


-- =============================================================================
-- 3.  public.inventory_items
--     Multi-tenant product / SKU catalogue with a flexible JSONB attributes
--     matrix for arbitrary product properties (dimensions, specs, custom fields).
-- =============================================================================

-- Enum-like domain for stock status
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

CREATE TABLE IF NOT EXISTS public.inventory_items (
    -- -------------------------------------------------------------------------
    -- Identity
    -- -------------------------------------------------------------------------
    id                  UUID                        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID                        NOT NULL
                            REFERENCES public.tenants (id) ON DELETE CASCADE,
    sku                 TEXT                        NOT NULL,           -- stock-keeping unit code
    name                TEXT                        NOT NULL,
    description         TEXT,

    -- -------------------------------------------------------------------------
    -- Categorisation
    -- -------------------------------------------------------------------------
    category            TEXT,
    sub_category        TEXT,
    brand               TEXT,
    tags                TEXT[]                      NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Pricing & stock
    -- -------------------------------------------------------------------------
    unit_price          NUMERIC(18, 4)              NOT NULL DEFAULT 0  CHECK (unit_price >= 0),
    cost_price          NUMERIC(18, 4)              NOT NULL DEFAULT 0  CHECK (cost_price >= 0),
    currency            CHAR(3)                     NOT NULL DEFAULT 'USD',
    quantity_on_hand    INTEGER                     NOT NULL DEFAULT 0  CHECK (quantity_on_hand >= 0),
    reorder_level       INTEGER                     NOT NULL DEFAULT 0  CHECK (reorder_level >= 0),
    unit_of_measure     TEXT                        NOT NULL DEFAULT 'unit',

    -- -------------------------------------------------------------------------
    -- JSONB attribute matrix
    --   Stores dynamic, schema-less product properties:
    --     • physical dimensions  { "weight_kg": 1.2, "length_cm": 30 }
    --     • technical specs      { "voltage": "220V", "colour": "red" }
    --     • compliance fields    { "hs_code": "8471.30", "origin": "IN" }
    --     • AI embeddings ref    { "embedding_model": "text-embedding-3-small", "vector_id": "…" }
    -- -------------------------------------------------------------------------
    attributes          JSONB                       NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Status & lifecycle
    -- -------------------------------------------------------------------------
    status              public.inventory_status     NOT NULL DEFAULT 'draft',
    is_active           BOOLEAN                     NOT NULL DEFAULT TRUE,
    created_by          UUID                        REFERENCES public.user_profiles (id) ON DELETE SET NULL,
    updated_by          UUID                        REFERENCES public.user_profiles (id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ                 NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ                 NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- Constraints
-- -------------------------------------------------------------------------
-- SKU must be unique per tenant
ALTER TABLE public.inventory_items
    DROP CONSTRAINT IF EXISTS uq_inventory_items_tenant_sku;
ALTER TABLE public.inventory_items
    ADD CONSTRAINT uq_inventory_items_tenant_sku UNIQUE (tenant_id, sku);

-- -------------------------------------------------------------------------
-- Standard B-Tree Indexes
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_items_tenant_id
    ON public.inventory_items (tenant_id);

CREATE INDEX IF NOT EXISTS idx_inventory_items_tenant_status
    ON public.inventory_items (tenant_id, status)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_inventory_items_category
    ON public.inventory_items (tenant_id, category, sub_category);

CREATE INDEX IF NOT EXISTS idx_inventory_items_reorder
    ON public.inventory_items (tenant_id, quantity_on_hand, reorder_level)
    WHERE is_active = TRUE AND status = 'active';

-- -------------------------------------------------------------------------
-- GIN — Primary JSONB attribute matrix index (jsonb_path_ops)
--   Best for:  @>, @?, @@  operators — containment & jsonpath queries
--   Query e.g: WHERE attributes @> '{"colour": "red"}'
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_attributes_gin_path
    ON public.inventory_items USING GIN (attributes jsonb_path_ops);

-- -------------------------------------------------------------------------
-- GIN — Full jsonb_ops index for key-existence queries
--   Best for:  ?, ?|, ?&  operators — checking key existence
--   Query e.g: WHERE attributes ? 'hs_code'
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_attributes_gin_ops
    ON public.inventory_items USING GIN (attributes);

-- -------------------------------------------------------------------------
-- GIN — tags TEXT[] array index
--   Query e.g: WHERE tags @> ARRAY['perishable', 'cold-chain']
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_items_tags_gin
    ON public.inventory_items USING GIN (tags);

-- -------------------------------------------------------------------------
-- GIN — Trigram index on name & description for fast ILIKE / full-text search
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_inventory_items_name_trgm
    ON public.inventory_items USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_inventory_items_desc_trgm
    ON public.inventory_items USING GIN (description gin_trgm_ops);

-- -------------------------------------------------------------------------
-- Audit trigger
-- -------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_inventory_items_updated_at ON public.inventory_items;
CREATE TRIGGER trg_inventory_items_updated_at
    BEFORE UPDATE ON public.inventory_items
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Comments
COMMENT ON TABLE  public.inventory_items                  IS 'Multi-tenant product/SKU catalogue with flexible JSONB attribute matrix.';
COMMENT ON COLUMN public.inventory_items.sku              IS 'Stock-keeping unit code; unique per tenant.';
COMMENT ON COLUMN public.inventory_items.attributes       IS 'Schema-less JSONB matrix: dimensions, specs, compliance codes, AI embedding refs, custom fields.';
COMMENT ON COLUMN public.inventory_items.tags             IS 'Flat text array for fast multi-value filtering (GIN indexed).';
COMMENT ON COLUMN public.inventory_items.reorder_level    IS 'Minimum quantity_on_hand before a replenishment alert fires.';


-- =============================================================================
-- 4.  Row-Level Security (RLS)
--     Enforces tenant isolation at the Postgres layer.
--
--     Isolation pattern used throughout:
--       USING (tenant_id = (SELECT tenant_id FROM public.user_profiles
--                           WHERE id = auth.uid()))
--
--     • auth.uid() is the Supabase JWT sub claim — the authenticated user UUID.
--     • The inline correlated sub-select is evaluated per-row by the Postgres
--       planner; it is automatically cached within a single statement via the
--       InitPlan optimisation, so it does NOT cause N+1 scans.
--     • This pattern is SAFER than a STABLE helper function because it always
--       re-reads the current JWT claim rather than relying on a cached result.
-- =============================================================================

-- Enable RLS on all tenant-scoped tables
ALTER TABLE public.tenants          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_items  ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (belt-and-suspenders for Supabase service role)
ALTER TABLE public.tenants          FORCE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles    FORCE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_items  FORCE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------------
-- public.tenants — RLS policies
-- ---------------------------------------------------------------------------

-- SELECT: user may read their own tenant record only
DROP POLICY IF EXISTS "tenants_select_own" ON public.tenants;
CREATE POLICY "tenants_select_own"
    ON public.tenants
    FOR SELECT
    USING (
        id = (
            SELECT tenant_id
            FROM   public.user_profiles
            WHERE  id = auth.uid()
        )
    );

-- UPDATE: only owner / admin of the same tenant may update
DROP POLICY IF EXISTS "tenants_update_admin" ON public.tenants;
CREATE POLICY "tenants_update_admin"
    ON public.tenants
    FOR UPDATE
    USING (
        id = (
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


-- ---------------------------------------------------------------------------
-- public.user_profiles — RLS policies
-- ---------------------------------------------------------------------------

-- SELECT: user may read all profiles within their own tenant
DROP POLICY IF EXISTS "profiles_select_same_tenant" ON public.user_profiles;
CREATE POLICY "profiles_select_same_tenant"
    ON public.user_profiles
    FOR SELECT
    USING (
        tenant_id = (
            SELECT tenant_id
            FROM   public.user_profiles
            WHERE  id = auth.uid()
        )
    );

-- UPDATE: user may update their own profile row only
DROP POLICY IF EXISTS "profiles_update_self" ON public.user_profiles;
CREATE POLICY "profiles_update_self"
    ON public.user_profiles
    FOR UPDATE
    USING (id = auth.uid());

-- INSERT: user may insert a profile row for themselves only
DROP POLICY IF EXISTS "profiles_insert_self" ON public.user_profiles;
CREATE POLICY "profiles_insert_self"
    ON public.user_profiles
    FOR INSERT
    WITH CHECK (id = auth.uid());


-- ---------------------------------------------------------------------------
-- public.inventory_items — RLS policies
-- ---------------------------------------------------------------------------

-- SELECT: any authenticated member of the tenant may read inventory
DROP POLICY IF EXISTS "inventory_select_tenant" ON public.inventory_items;
CREATE POLICY "inventory_select_tenant"
    ON public.inventory_items
    FOR SELECT
    USING (
        tenant_id = (
            SELECT tenant_id
            FROM   public.user_profiles
            WHERE  id = auth.uid()
        )
    );

-- INSERT: manager / admin / owner within the same tenant may create items
DROP POLICY IF EXISTS "inventory_insert_manager" ON public.inventory_items;
CREATE POLICY "inventory_insert_manager"
    ON public.inventory_items
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

-- UPDATE: manager / admin / owner within the same tenant may modify items
DROP POLICY IF EXISTS "inventory_update_manager" ON public.inventory_items;
CREATE POLICY "inventory_update_manager"
    ON public.inventory_items
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

-- DELETE: only owner / admin may delete inventory items
DROP POLICY IF EXISTS "inventory_delete_admin" ON public.inventory_items;
CREATE POLICY "inventory_delete_admin"
    ON public.inventory_items
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


-- =============================================================================
-- 5.  Seed: default tenant + system user profile for local development
--     Wrapped in a DO block so it is skipped silently if the slug already exists.
-- =============================================================================
DO $$
DECLARE
    v_tenant_id UUID;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.tenants WHERE slug = 'dev-tenant') THEN
        INSERT INTO public.tenants (slug, name, plan, settings)
        VALUES (
            'dev-tenant',
            'Development Tenant',
            'enterprise',
            '{
                "theme": "dark",
                "features": {
                    "ai_copilot": true,
                    "advanced_analytics": true,
                    "multi_warehouse": false
                },
                "ai": {
                    "default_model": "gpt-4o",
                    "embedding_model": "text-embedding-3-small"
                }
            }'::jsonb
        )
        RETURNING id INTO v_tenant_id;

        RAISE NOTICE 'Seeded dev-tenant with id: %', v_tenant_id;
    ELSE
        RAISE NOTICE 'dev-tenant already exists — skipping seed.';
    END IF;
END;
$$;

COMMIT;

-- =============================================================================
-- END OF MIGRATION V001
-- =============================================================================
