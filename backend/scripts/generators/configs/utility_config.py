"""Utility data generation configuration."""
UTILITY_CONFIG = {
    'target_bill_rows': 350,
    'target_interval_rows': 7200,  # 10 days * 24 hours * 30 meters
    'meters': 25,
    'billing_period_months': 18,  # 18 months of history
    'anomaly_target': 40,
    'estimated_bill_ratio': 0.1,  # 10% estimated bills
    'negative_consumption_ratio': 0.02,  # 2% negative (solar feed-in)
    'missing_meter_ratio': 0.03,
    'interval_gap_probability': 0.05,  # 5% chance of missing hour
}