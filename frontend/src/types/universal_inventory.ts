export interface PaginationMeta {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

export interface PaginatedResponse<T> {
    items: T[];
    meta: PaginationMeta;
}

export interface UniversalCategory {
    id: string;
    tenant_id: string;
    name: string;
    description?: string;
    parent_id?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface UniversalBrand {
    id: string;
    tenant_id: string;
    name: string;
    description?: string;
    website?: string;
    logo_url?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface UniversalUOM {
    id: string;
    tenant_id: string;
    name: string;
    abbreviation: string;
    base_uom_id?: string;
    conversion_factor: number;
    decimal_precision: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface UniversalItemMaster {
    id: string;
    tenant_id: string;
    item_code: string;
    sku: string;
    barcode?: string;
    qr_code?: string;
    name: string;
    short_name?: string;
    description?: string;
    status: string;
    is_active: boolean;
    category_id?: string;
    brand_id?: string;
    uom_id?: string;
    images: string[];
    documents: string[];
    notes?: string;
    variants: Record<string, any>;
    attributes: Record<string, any>;
    created_by?: string;
    updated_by?: string;
    created_at: string;
    updated_at: string;
}
