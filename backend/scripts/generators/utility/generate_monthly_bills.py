"""Generate monthly utility bills with realistic patterns."""
import random
from datetime import datetime, timedelta
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.temporal_patterns import TemporalPattern
from ..core.facility_profiles import get_plant_profile
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils
from ..configs.utility_config import UTILITY_CONFIG

fake.add_provider(EnterpriseProvider)

def generate_monthly_bills(anomaly_count=40, output_path='outputs/'):
    """Generate utility monthly bill CSV with realistic enterprise patterns."""
    print("Generating utility monthly bills...")
    rows = []
    plants = list(get_plant_profile(p) for p in ['IN01', 'IN02', 'DE02', 'US03', 'LON02'])
    start_date = datetime(2025, 1, 1)
    
    for month_offset in range(UTILITY_CONFIG['billing_period_months']):
        bill_date = start_date + timedelta(days=30 * month_offset)
        for meter_idx in range(UTILITY_CONFIG['meters']):
            plant = random.choice(plants)
            profile = plant
            
            # Electricity consumption with seasonal variance
            base_consumption = random.uniform(
                profile['electricity_daily_kwh'][0], 
                profile['electricity_daily_kwh'][1]
            ) * 30  # Monthly
            
            # Summer spike (May-June)
            if bill_date.month in [5, 6]:
                base_consumption *= random.uniform(1.1, 1.3)
            # Winter reduction (Dec-Feb for IN, Nov-Mar for others)
            elif bill_date.month in [12, 1, 2] and profile['country'] == 'IN':
                base_consumption *= random.uniform(0.85, 0.95)
            
            consumption = round(base_consumption, 2)
            
            # Peak demand (kW) – separate from consumption
            peak_demand = round(consumption / 30 * random.uniform(0.3, 0.6), 2)
            
            # Read type: 10% estimated
            read_type = fake.read_type()
            
            row = {
                'account_number': fake.account_number(),
                'service_address': f"{profile['name']}, {random.choice(['Sector 12','Industrial Area','Plot 45'])}",
                'meter_id': fake.meter_id(),
                'billing_start': (bill_date - timedelta(days=30)).strftime('%Y-%m-%d'),
                'billing_end': bill_date.strftime('%Y-%m-%d'),
                'read_type': read_type,
                'consumption_kwh': consumption,
                'peak_demand_kw': peak_demand,
                'demand_charge': round(peak_demand * random.uniform(80, 150), 2),
                'energy_charge': round(consumption * random.uniform(5, 15), 2),
                'total_amount': 0,  # calculated
                'currency': fake.currency_code(profile['country']),
            }
            row['total_amount'] = round(row['demand_charge'] + row['energy_charge'], 2)
            rows.append(row)
    
    # Inject anomalies
    rows = AnomalyInjector.inject_anomalies(rows, anomaly_count)
    
    # Override some rows as ESTIMATED (already set in read_type)
    ExportUtils.export_csv(f"{output_path}/utility_bills.csv", rows)
    return rows