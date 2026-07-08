BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

=============================================================================
Revision   : a1b2c3d4e5f6
-- Running upgrade  -> a1b2c3d4e5f6
Revises    : (base ù first Alembic-tracked revision)
Create Date: 2026-07-02 22:00:00.000000

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

Traceback (most recent call last):
  File "<frozen runpy>", line 203, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\AI NATIVE ERP\.venv\Scripts\alembic.exe\__main__.py", line 5, in <module>
    sys.exit(main())
             ~~~~^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\config.py", line 641, in main
    CommandLine(prog=prog).main(argv=argv)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\config.py", line 631, in main
    self.run_cmd(cfg, options)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\config.py", line 608, in run_cmd
    fn(
    ~~^
        config,
        ^^^^^^^
        *[getattr(options, k, None) for k in positional],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        **{k: getattr(options, k, None) for k in kwarg},
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\command.py", line 403, in upgrade
    script.run_env()
    ~~~~~~~~~~~~~~^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\script\base.py", line 583, in run_env
    util.load_python_file(self.dir, "env.py")
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\util\pyfiles.py", line 95, in load_python_file
    module = load_module_py(module_id, path)
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\util\pyfiles.py", line 113, in load_module_py
    spec.loader.exec_module(module)  # type: ignore
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "<frozen importlib._bootstrap_external>", line 759, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "D:\AI NATIVE ERP\backend\alembic\env.py", line 179, in <module>
    run_migrations_offline()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "D:\AI NATIVE ERP\backend\alembic\env.py", line 143, in run_migrations_offline
    context.run_migrations()
    ~~~~~~~~~~~~~~~~~~~~~~^^
  File "<string>", line 8, in run_migrations
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\runtime\environment.py", line 948, in run_migrations
    self.get_context().run_migrations(**kw)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\runtime\migration.py", line 627, in run_migrations
    step.migration_fn(**kw)
    ~~~~~~~~~~~~~~~~~^^^^^^
  File "D:\AI NATIVE ERP\backend\alembic\versions\20260702_2200_a1b2c3d4e5f6_create_tenant_saree_inventory.py", line 
119, in upgrade
    op.create_table(
    ~~~~~~~~~~~~~~~^
        "tenant_saree_inventory",
        ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<185 lines>...
        ),
        ^^
    )
    ^
  File "<string>", line 8, in create_table
  File "<string>", line 3, in create_table
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\operations\ops.py", line 1311, in create_table
    return operations.invoke(op)
           ~~~~~~~~~~~~~~~~~^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\operations\base.py", line 445, in invoke
    return fn(self, operation)
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\operations\toimpl.py", line 131, in create_table
    operations.impl.create_table(table)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\ddl\impl.py", line 383, in create_table
    self.create_column_comment(column)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\ddl\impl.py", line 404, in create_column_comment
    self._exec(schema.SetColumnComment(column))
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\ddl\impl.py", line 193, in _exec
    self.static_output(
    ~~~~~~~~~~~~~~~~~~^
        str(compiled).replace("\t", "    ").strip()
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        + self.command_terminator
        ^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "D:\AI NATIVE ERP\.venv\Lib\site-packages\alembic\ddl\impl.py", line 137, in static_output
    self.output_buffer.write(text + "\n\n")
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "C:\Users\DELL\AppData\Local\Programs\Python\Python314\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 65: character maps to <undefined>
