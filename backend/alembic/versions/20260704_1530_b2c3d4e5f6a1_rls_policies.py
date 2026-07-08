"""
alembic/versions/20260704_1530_b2c3d4e5f6a1_rls_policies.py
===========================================================
Revision   : b2c3d4e5f6a1
Revises    : a1b2c3d4e5f6
Create Date: 2026-07-04 15:30:00.000000

Summary
-------
Phase 1 — Security & Identity Hardening
Deploy Supabase Row-Level Security (RLS) policies for tables matching tenant_id = auth.uid()
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # SQL to enable RLS and create policies
    op.execute("""
        -- Enable RLS on core tables
        ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.inventory_items ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_billing_invoices ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_saree_inventory ENABLE ROW LEVEL SECURITY;

        -- Create policies for tenant isolation matching tenant_id = auth.uid()
        
        CREATE POLICY "Tenant Isolation - tenants"
        ON public.tenants
        FOR ALL USING (id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
        
        CREATE POLICY "Tenant Isolation - user_profiles"
        ON public.user_profiles
        FOR ALL USING (user_id = auth.uid());

        CREATE POLICY "Tenant Isolation - inventory_items"
        ON public.inventory_items
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));

        CREATE POLICY "Tenant Isolation - tenant_billing_invoices"
        ON public.tenant_billing_invoices
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));

        CREATE POLICY "Tenant Isolation - tenant_saree_inventory"
        ON public.tenant_saree_inventory
        FOR ALL USING (tenant_id IN (SELECT tenant_id FROM public.user_profiles WHERE user_id = auth.uid()));
    """)

def downgrade() -> None:
    op.execute("""
        DROP POLICY IF EXISTS "Tenant Isolation - tenant_saree_inventory" ON public.tenant_saree_inventory;
        DROP POLICY IF EXISTS "Tenant Isolation - tenant_billing_invoices" ON public.tenant_billing_invoices;
        DROP POLICY IF EXISTS "Tenant Isolation - inventory_items" ON public.inventory_items;
        DROP POLICY IF EXISTS "Tenant Isolation - user_profiles" ON public.user_profiles;
        DROP POLICY IF EXISTS "Tenant Isolation - tenants" ON public.tenants;

        ALTER TABLE public.tenant_saree_inventory DISABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenant_billing_invoices DISABLE ROW LEVEL SECURITY;
        ALTER TABLE public.inventory_items DISABLE ROW LEVEL SECURITY;
        ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
        ALTER TABLE public.tenants DISABLE ROW LEVEL SECURITY;
    """)
