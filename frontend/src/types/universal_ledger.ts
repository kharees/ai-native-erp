export interface UniversalInventoryLedger {
    id: string;
    tenant_id: string;
    item_id: string;
    warehouse_id: string;
    bin_id?: string;
    transaction_id?: string;
    
    quantity_before: number;
    movement_quantity: number;
    quantity_after: number;
    
    unit_cost: number;
    total_cost: number;
    
    reference_type: string;
    reference_id?: string;
    user_id?: string;
    created_at: string;
}
