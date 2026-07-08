export interface StockValuationSummary {
    total_quantity: number;
    total_value: number;
    warehouse_count: number;
    item_count: number;
}

export interface ABCAnalysisItem {
    item_id: string;
    item_code: string;
    item_name: string;
    total_value_consumed: number;
    cumulative_percentage: number;
    classification: string;
}

export interface AgingReportItem {
    item_id: string;
    warehouse_id: string;
    quantity_on_hand: number;
    days_since_last_movement: number;
    aging_bucket: string;
}
