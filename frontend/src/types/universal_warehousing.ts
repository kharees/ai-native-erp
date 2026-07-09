export interface UniversalWarehouse {
    id: string;
    tenant_id: string;
    branch_id?: string;
    code: string;
    name: string;
    type: string;
    status: string;
    manager_id?: string;
    capacity: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface UniversalWarehouseZone {
    id: string;
    tenant_id: string;
    warehouse_id: string;
    code: string;
    name: string;
    type?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface UniversalWarehouseBin {
    id: string;
    tenant_id: string;
    warehouse_id: string;
    zone_id?: string;
    code: string;
    name: string;
    aisle?: string;
    rack?: string;
    shelf?: string;
    max_weight: number;
    max_volume: number;
    metadata: Record<string, unknown>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface StockMovementRequest {
    item_id: string;
    warehouse_id: string;
    bin_id?: string;
    transaction_type: string;
    reference_type: string;
    reference_id?: string;
    quantity: number;
    metadata: Record<string, unknown>;
}

export interface StockTransactionResponse {
    id: string;
    item_id: string;
    warehouse_id: string;
    bin_id?: string;
    transaction_type: string;
    reference_type: string;
    reference_id?: string;
    quantity: number;
    metadata: Record<string, unknown>;
    created_at: string;
}
