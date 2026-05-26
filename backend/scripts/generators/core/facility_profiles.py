"""Facility behavior profiles for realistic data generation."""
import random

PLANT_PROFILES = {
    'IN01': {
        'name': 'Pune Manufacturing Plant',
        'type': 'manufacturing_24x7',
        'country': 'IN',
        'electricity_daily_kwh': (18000, 35000),
        'electricity_weekend_factor': 0.9,
        'diesel_monthly_liters': (8000, 15000),
        'primary_vendors': ['000009981', '000004611', '000008821'],
        'vendor_weights': [0.6, 0.3, 0.1],
        'materials': {
            'diesel': {'weight': 0.5, 'unit': 'L', 'scope': 'SCOPE_1'},
            'steel': {'weight': 0.3, 'unit': 'MT', 'scope': 'SCOPE_3'},
            'lubricants': {'weight': 0.15, 'unit': 'L', 'scope': 'SCOPE_1'},
            'spares': {'weight': 0.05, 'unit': 'EA', 'scope': 'SCOPE_3'},
        }
    },
    'IN02': {
        'name': 'Mumbai Corporate Office',
        'type': 'office',
        'country': 'IN',
        'electricity_daily_kwh': (2500, 5500),
        'electricity_weekend_factor': 0.15,
        'diesel_monthly_liters': (500, 1200),  # Generator backup
        'primary_vendors': ['000009981'],
        'vendor_weights': [1.0],
        'materials': {
            'diesel': {'weight': 0.8, 'unit': 'L', 'scope': 'SCOPE_1'},
            'stationery': {'weight': 0.2, 'unit': 'BOX', 'scope': 'SCOPE_3'},
        }
    },
    'DE02': {
        'name': 'Frankfurt Logistics Hub',
        'type': 'warehouse',
        'country': 'DE',
        'electricity_daily_kwh': (8000, 15000),
        'electricity_weekend_factor': 0.5,
        'diesel_monthly_liters': (4000, 9000),
        'primary_vendors': ['000000112', '000000223'],
        'vendor_weights': [0.7, 0.3],
        'materials': {
            'diesel': {'weight': 0.4, 'unit': 'L', 'scope': 'SCOPE_1'},
            'pallet': {'weight': 0.3, 'unit': 'EA', 'scope': 'SCOPE_3'},
            'packaging': {'weight': 0.3, 'unit': 'KG', 'scope': 'SCOPE_3'},
        }
    },
    'US03': {
        'name': 'Chicago Distribution Center',
        'type': 'warehouse',
        'country': 'US',
        'electricity_daily_kwh': (12000, 22000),
        'electricity_weekend_factor': 0.6,
        'diesel_monthly_liters': (6000, 12000),
        'primary_vendors': ['000002211', '000002212'],
        'vendor_weights': [0.8, 0.2],
        'materials': {
            'diesel': {'weight': 0.6, 'unit': 'L', 'scope': 'SCOPE_1'},
            'forklift_battery': {'weight': 0.2, 'unit': 'EA', 'scope': 'SCOPE_3'},
            'maintenance': {'weight': 0.2, 'unit': 'HR', 'scope': 'SCOPE_3'},
        }
    },
    'LON02': {
        'name': 'London Sales Office',
        'type': 'office',
        'country': 'GB',
        'electricity_daily_kwh': (1800, 3500),
        'electricity_weekend_factor': 0.1,
        'diesel_monthly_liters': (200, 600),
        'primary_vendors': ['000005551'],
        'vendor_weights': [1.0],
        'materials': {
            'diesel': {'weight': 0.7, 'unit': 'L', 'scope': 'SCOPE_1'},
            'office_supplies': {'weight': 0.3, 'unit': 'BOX', 'scope': 'SCOPE_3'},
        }
    }
}

def get_plant_profile(plant_code):
    """Return profile for plant, with fallback."""
    return PLANT_PROFILES.get(plant_code.strip(), PLANT_PROFILES['IN01'])