"""Generate hourly interval data (smart meter)."""
import random
from datetime import datetime, timedelta
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.temporal_patterns import TemporalPattern
from ..core.facility_profiles import get_plant_profile
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils
from ..configs.utility_config import UTILITY_CONFIG

fake.add_provider(EnterpriseProvider)

def generate_interval_data(anomaly_count=30, output_path='outputs/'):
    """Generate smart meter hourly interval data with realistic patterns."""
    print("Generating utility interval data (smart meter)...")
    rows = []
    meters = [fake.meter_id() for _ in range(UTILITY_CONFIG['meters'])]
    end_date = datetime(2026, 5, 31)
    start_date = end_date - timedelta(days=10)  # 10 days of interval data
    
    current_date = start_date
    while current_date <= end_date:
        for meter in meters:
            # Plant type for hour probability
            plant_type = random.choice(['manufacturing_24x7', 'office', 'warehouse'])
            for hour in range(24):
                dt = current_date.replace(hour=hour, minute=0)
                
                # Skip if gap injection
                if random.random() < UTILITY_CONFIG['interval_gap_probability']:
                    continue
                
                # Hourly consumption based on temporal pattern
                hour_prob = TemporalPattern.hour_probability(hour, plant_type)
                base_kwh = random.uniform(50, 500) * hour_prob
                
                # Weekend/holiday reduction
                date_only = dt.date()
                if dt.weekday() >= 5:
                    base_kwh *= 0.4
                if dt.month in [5, 6]:  # Summer
                    base_kwh *= 1.2
                
                kwh = round(base_kwh, 3)
                
                # Quality flag
                quality = 'ACTUAL'
                if random.random() < 0.02:
                    quality = random.choice(['ESTIMATED', 'POWER_OUTAGE', 'MANUAL_ENTRY'])
                
                row = {
                    'meter_id': meter,
                    'timestamp': dt.isoformat(),
                    'kwh_interval': kwh,
                    'quality_flag': quality,
                }
                rows.append(row)
        current_date += timedelta(days=1)
    
    rows = AnomalyInjector.inject_anomalies(rows, anomaly_count)
    ExportUtils.export_csv(f"{output_path}/utility_intervals.csv", rows)
    return rows