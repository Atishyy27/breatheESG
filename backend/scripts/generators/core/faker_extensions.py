"""Custom Faker providers for realistic enterprise data."""
from faker import Faker
from faker.providers import BaseProvider
import random
import string

fake = Faker()

class EnterpriseProvider(BaseProvider):
    """Enterprise-specific fake data generators."""
    
    def sap_material_number(self):
        """Generate realistic SAP material master number."""
        # 18-character zero-padded or cryptic codes
        patterns = [
            lambda: f"{random.randint(1, 999999999999999999):018d}",
            lambda: f"RMF-{random.choice(['DIE','IND','LUB','CHE'])}-{random.randint(100,999)}{random.choice(['L','KG','MT'])}",
            lambda: f"Z-{random.choice(['FUEL','STEEL','LUBE','CHEM'])}-{random.randint(1000,9999)}",
            lambda: f"MAT_{random.randint(100000,999999)}_{random.choice(['REV1','REV2','A','B'])}",
        ]
        return random.choice(patterns)()
    
    def sap_vendor(self):
        """Generate realistic vendor number (leading zeros)."""
        return f"{random.randint(1, 99999999):08d}"
    
    def sap_plant(self, country=None):
        """Plant codes with trailing spaces."""
        plants = {
            'IN': ['IN01  ', 'IN02  ', 'MUM01 ', 'DEL05 '],
            'DE': ['DE01  ', 'DE02  ', 'FRA01 '],
            'US': ['US01  ', 'US02  ', 'CHI03 '],
            'GB': ['UK01  ', 'LON02 '],
        }
        if country:
            return random.choice(plants.get(country, plants['IN']))
        return random.choice([p for sub in plants.values() for p in sub])
    
    def sap_movement_type(self):
        """Realistic movement types with distribution."""
        # 101 = goods receipt, 102 = reversal, 122 = return, etc.
        return random.choices(
            ['101', '102', '122', '201', '261', '321', '501', '541'],
            weights=[0.7, 0.05, 0.05, 0.05, 0.05, 0.03, 0.03, 0.04]
        )[0]
    
    def sap_date(self, start_date=None, end_date=None):
        """Generate SAP-formatted dates with deliberate corruption."""
        from datetime import datetime, timedelta
        if not start_date:
            start_date = datetime(2025, 1, 1)
        if not end_date:
            end_date = datetime(2026, 12, 31)
        date = fake.date_between(start_date=start_date, end_date=end_date)
        
        # 85% clean DDMMYYYY, 10% DD.MM.YYYY, 5% corrupted Excel
        r = random.random()
        if r < 0.85:
            return date.strftime('%d%m%Y')
        elif r < 0.95:
            return date.strftime('%d.%m.%Y')
        else:
            # Excel mangling: MM/DD/YYYY or formula
            return random.choice([
                date.strftime('%m/%d/%Y'),
                f'="{date.strftime("%d.%m.%Y")}"',
                date.strftime('%d-%b-%Y'),
            ])
    
    def diesel_quantity(self):
        """Generate realistic diesel quantities in liters."""
        # 60% between 500-2000, 30% between 2000-10000, 10% very large
        r = random.random()
        if r < 0.6:
            qty = random.uniform(500, 2000)
        elif r < 0.9:
            qty = random.uniform(2000, 10000)
        else:
            qty = random.uniform(10000, 50000)
        return round(qty, 3)
    
    def steel_quantity(self):
        """Steel in metric tons."""
        return round(random.uniform(5, 500), 3)
    
    def currency_code(self, plant):
        """Currency based on plant country."""
        plant_country = {
            'IN01': 'INR', 'IN02': 'INR', 'MUM01': 'INR', 'DEL05': 'INR',
            'DE01': 'EUR', 'DE02': 'EUR', 'FRA01': 'EUR',
            'US01': 'USD', 'US02': 'USD', 'CHI03': 'USD',
            'UK01': 'GBP', 'LON02': 'GBP',
        }
        return plant_country.get(plant.strip(), 'USD')
    
    def meter_id(self):
        """Realistic meter ID format."""
        return f"MTR-{random.choice(['IND','GER','USA','UK'])}-{random.randint(1,999):03d}"
    
    def account_number(self):
        """Utility account number."""
        return f"{random.randint(100000000, 999999999)}"
    
    def read_type(self):
        """Actual vs estimated reading."""
        return random.choices(['ACTUAL', 'ESTIMATED'], weights=[0.9, 0.1])[0]
    
    def iata_code(self, valid=True):
        """Real IATA codes or invalid ones."""
        valid_codes = ['BOM', 'DEL', 'LHR', 'JFK', 'CDG', 'FRA', 'DXB', 'SIN', 'HKG', 'SYD']
        if valid or random.random() > 0.05:
            return random.choice(valid_codes)
        else:
            return random.choice(['XXX', 'YYY', 'ZZZ', 'INV', 'NUL', ''])
    
    def airline_name(self):
        """Airline names with occasional typos."""
        airlines = [
            'Air India', 'United Airlines', 'British Airways', 'Lufthansa',
            'Emirates', 'Singapore Airlines', 'Delta', 'American Airlines',
            'Air Indi', 'Unietd', 'Brittish Airways', 'Lufthansa Airlines'
        ]
        return random.choice(airlines)
    
    def booking_class(self):
        """Cabin class with distribution."""
        return random.choices(['Economy', 'Business', 'First'], weights=[0.7, 0.25, 0.05])[0]