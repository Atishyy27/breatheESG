"""Generate fuel-specific SAP data with realistic diesel/gas patterns."""
import random
from datetime import datetime
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.facility_profiles import get_plant_profile
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils

fake.add_provider(EnterpriseProvider)

def generate_fuel_procurement(anomaly_count=40, output_path='outputs/'):
    """Generate SAP fuel procurement data (diesel, natural gas, heavy fuel)."""
    print("Generating SAP fuel procurement data...")
    rows = []
    fuel_types = [
        {'name': 'DIESEL', 'unit': 'L', 'factor': 1.0},
        {'name': 'HEAVY_FUEL_OIL', 'unit': 'MT', 'factor': 1.0},
        {'name': 'NATURAL_GAS', 'unit': 'M3', 'factor': 1.0},
        {'name': 'PETROL', 'unit': 'L', 'factor': 1.0},
    ]
    
    plants = ['IN01', 'IN02', 'DE02', 'US03', 'LON02']
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 5, 31)
    
    for i in range(600):  # Fuel-specific subset
        plant = random.choice(plants)
        profile = get_plant_profile(plant)
        fuel = random.choice(fuel_types)
        dt = fake.date_time_between(start_date=start_date, end_date=end_date)
        
        qty = 0
        if fuel['unit'] == 'L':
            qty = round(random.uniform(500, 5000), 3)
        elif fuel['unit'] == 'MT':
            qty = round(random.uniform(5, 100), 3)
        else:
            qty = round(random.uniform(200, 2000), 3)
        
        amount = round(qty * random.uniform(50, 150), 2)
        currency = fake.currency_code(plant)
        
        row = {
            'MBLNR': f"{random.randint(5000000000, 5999999999)}",
            'MJAHR': dt.year,
            'BLDAT': fake.sap_date(start_date, dt),
            'BUDAT': fake.sap_date(start_date, dt),
            'WERKS': fake.sap_plant(profile['country']),
            'MATNR': f"FUEL_{fuel['name']}_{random.randint(100,999)}",
            'MENGE': qty,
            'MEINS': fuel['unit'],
            'BWART': '101',  # Goods receipt for fuel
            'NETWR': amount,
            'WAERS': currency,
            'LIFNR': fake.sap_vendor(),
        }
        rows.append(row)
    
    rows = AnomalyInjector.inject_anomalies(rows, anomaly_count)
    ExportUtils.export_csv(f"{output_path}/sap_fuel_procurement.csv", rows, delimiter='|')
    return rows