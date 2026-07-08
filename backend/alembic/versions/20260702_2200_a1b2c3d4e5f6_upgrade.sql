BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a1b2c3d4e5f6

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE EXTENSION IF NOT EXISTS "btree_gin";

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
        $$;;

CREATE TYPE inventory_status AS ENUM ('active', 'inactive', 'discontinued', 'draft', 'pending_review');

CREATE TABLE public.tenant_saree_inventory (
    id UUID DEFAULT uuid_generate_v4() NOT NULL, 
    tenant_id UUID NOT NULL, 
    sku VARCHAR(64) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    category VARCHAR(128), 
    sub_category VARCHAR(128), 
    brand VARCHAR(128), 
    tags TEXT[] DEFAULT '{}'::text[] NOT NULL, 
    unit_price NUMERIC(18, 4) DEFAULT 0 NOT NULL, 
    cost_price NUMERIC(18, 4) DEFAULT 0 NOT NULL, 
    currency VARCHAR(3) DEFAULT 'INR' NOT NULL, 
    quantity_on_hand INTEGER DEFAULT 0 NOT NULL, 
    reorder_level INTEGER DEFAULT 0 NOT NULL, 
    unit_of_measure VARCHAR(32) DEFAULT 'unit' NOT NULL, 
    attributes JSONB DEFAULT '{}'::jsonb NOT NULL, 
    status inventory_status DEFAULT 'draft' NOT NULL, 
    is_active BOOLEAN DEFAULT TRUE NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_saree_inventory_unit_price_gte_0 CHECK (unit_price >= 0), 
    CONSTRAINT ck_saree_inventory_cost_price_gte_0 CHECK (cost_price >= 0), 
    CONSTRAINT ck_saree_inventory_qty_gte_0 CHECK (quantity_on_hand >= 0), 
    CONSTRAINT ck_saree_inventory_reorder_gte_0 CHECK (reorder_level >= 0), 
    CONSTRAINT fk_saree_inventory_tenant_id FOREIGN KEY(tenant_id) REFERENCES public.tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_saree_inventory_created_by FOREIGN KEY(created_by) REFERENCES public.user_profiles (id) ON DELETE SET NULL, 
    CONSTRAINT fk_saree_inventory_updated_by FOREIGN KEY(updated_by) REFERENCES public.user_profiles (id) ON DELETE SET NULL
);

CREATE INDEX ix_public_tenant_saree_inventory_tenant_id ON public.tenant_saree_inventory (tenant_id);

COMMENT ON TABLE public.tenant_saree_inventory IS 'Multi-tenant handloom / saree inventory control ledger. One row per SKU per tenant. JSONB attributes column stores discriminated industry template matrix with handloom domain extensions. Protected by Row-Level Security ù each tenant sees only their own rows.';

COMMENT ON COLUMN public.tenant_saree_inventory.id IS 'Primary key ù UUID v4, server-generated.';

