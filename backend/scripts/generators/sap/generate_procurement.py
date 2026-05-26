"""Generate SAP procurement data (EKKO/EKPO style)."""
import random
from datetime import datetime, timedelta
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.temporal_patterns import TemporalPattern
from ..core.facility_profiles import get_plant_profile
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils
from ..configs.sap_config import SAP_CONFIG

fake.add_provider(EnterpriseProvider)

def generate_sap_procurement(anomaly_count=80, duplicate_count=15, output_path='outputs/'):
    """Generate main SAP procurement dataset."""
    print("Generating SAP procurement data...")
    rows = []
    plants = SAP_CONFIG['plants']
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 5, 31)
    
    # Pre-generate timestamps with temporal patterns
    timestamps = TemporalPattern.generate_timestamps(
        start_date, end_date, SAP_CONFIG['target_rows'], plant_type='manufacturing'
    )
    
    for i in range(SAP_CONFIG['target_rows']):
        plant = random.choice(plants)
        profile = get_plant_profile(plant)
        dt = timestamps[i] if i < len(timestamps) else fake.date_time_between(start_date, end_date)
        
        # Material selection based on plant profile
        materials = profile['materials']
        material_names = list(materials.keys())
        material_weights = [materials[m]['weight'] for m in material_names]
        material = random.choices(material_names, weights=material_weights)[0]
        mat_config = materials[material]
        
        quantity = 0
        if material == 'diesel':
            quantity = fake.diesel_quantity()
        elif material == 'steel':
            quantity = fake.steel_quantity()
        else:
            quantity = round(random.uniform(10, 500), 3)
        
        unit = mat_config['unit']
        vendor = random.choices(
            profile['primary_vendors'], 
            weights=profile['vendor_weights']
        )[0]
        
        # Movement type with distribution
        movement = random.choices(
            list(SAP_CONFIG['movement_type_weights'].keys()),
            weights=list(SAP_CONFIG['movement_type_weights'].values())
        )[0]
        
        # Amount
        amount = round(quantity * random.uniform(50, 500), 2)
        currency = fake.currency_code(plant)
        
        row = {
            'MBLNR': f"{random.randint(5000000000, 5999999999)}",
            'MJAHR': dt.year,
            'BLDAT': fake.sap_date(start_date, dt),
            'BUDAT': fake.sap_date(start_date, dt),
            'WERKS': fake.sap_plant(profile['country']),
            'MATNR': fake.sap_material_number(),
            'MENGE': quantity,
            'MEINS': unit,
            'ERFMG': quantity if random.random() > 0.1 else '',  # 10% missing
            'ERFME': unit if random.random() > 0.1 else '',
            'BWART': movement,
            'SHKZG': random.choice(['S', 'H']),  # Debit/Credit
            'NETWR': amount,
            'WAERS': currency,
            'LIFNR': vendor,
            'XBLNR': f"PO-{random.randint(2025001, 2026999)}" if random.random() > 0.3 else '',
        }
        rows.append(row)
    
    # Inject anomalies
    rows = AnomalyInjector.inject_anomalies(rows, anomaly_count)
    rows = AnomalyInjector.inject_duplicates(rows, duplicate_count)
    
    # Export
    ExportUtils.ensure_dir(output_path)
    ExportUtils.export_csv(
        f"{output_path}/sap_procurement.csv", 
        rows, 
        fieldnames=SAP_CONFIG['fields'],
        delimiter=SAP_CONFIG['delimiter']
    )
    return rows