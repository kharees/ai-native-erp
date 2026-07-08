export interface InventoryForecast {
    item_id: string;
    item_name: string;
    current_stock: number;
    projected_demand_30d: number;
    confidence_score: number;
    seasonality_trend: string;
}

export interface OptimizationRecommendation {
    item_id: string;
    item_name: string;
    recommendation_type: string;
    current_level: number;
    suggested_level: number;
    rationale: string;
    potential_savings: number;
}

export interface InventoryAlert {
    alert_type: string;
    severity: string;
    message: string;
    item_id?: string;
    batch_id?: string;
}

export interface InventoryInsightsDashboard {
    health_score: number;
    total_alerts: number;
    optimization_opportunities: number;
    forecasts: InventoryForecast[];
    recommendations: OptimizationRecommendation[];
    alerts: InventoryAlert[];
}
