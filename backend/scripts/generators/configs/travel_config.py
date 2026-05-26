"""Travel data generation configuration."""
TRAVEL_CONFIG = {
    'target_rows': 800,
    'multi_leg_ratio': 0.3,  # 30% of trips are multi-leg
    'cancelled_ratio': 0.05,
    'resubmission_ratio': 0.08,
    'missing_receipt_ratio': 0.1,
    'invalid_airport_ratio': 0.02,
    'anomaly_target': 60,
    'employees': 50,
    'date_range_months': 12,
}