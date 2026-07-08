export interface UniversalBatchMaster {
    id: string;
    tenant_id: string;
    item_id: string;
    batch_number: string;
    mfg_date?: string;
    expiry_date?: string;
    shelf_life_days?: number;
    status: string;
    cost_multiplier: number;
    created_at: string;
    updated_at: string;
}

export interface UniversalSerialMaster {
    id: string;
    tenant_id: string;
    item_id: string;
    batch_id?: string;
    serial_number: string;
    status: string;
    warehouse_id?: string;
    bin_id?: string;
    warranty_expiry?: string;
    created_at: string;
    updated_at: string;
}
