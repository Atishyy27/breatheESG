"""Generate multi-leg travel itineraries."""
import random
from datetime import datetime, timedelta
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils

fake.add_provider(EnterpriseProvider)

def generate_itineraries(anomaly_count=20, output_path='outputs/'):
    """Generate detailed multi-leg itineraries."""
    print("Generating travel itineraries...")
    itineraries = []
    
    routes = [
        (['BOM', 'DEL', 'LHR'], 2),
        (['DEL', 'DXB', 'JFK'], 2),
        (['BOM', 'SIN', 'SYD'], 2),
        (['LHR', 'CDG', 'FRA'], 2),
        (['JFK', 'LHR', 'BOM'], 2),
    ]
    
    for i in range(300):
        route, stops = random.choice(routes)
        start_date = fake.date_time_between(start_date='-180d', end_date='+30d')
        legs = []
        prev_airport = None
        for idx, airport in enumerate(route):
            leg_dt = start_date + timedelta(hours=idx * 3)
            leg = {
                'leg_sequence': idx + 1,
                'origin': prev_airport if prev_airport else airport,
                'destination': airport if idx > 0 else route[1],
                'departure_datetime': leg_dt.isoformat(),
                'arrival_datetime': (leg_dt + timedelta(hours=2)).isoformat(),
                'flight_number': f"{random.choice(['AI','UA','BA','LH'])}{random.randint(100,999)}",
                'booking_class': fake.booking_class(),
            }
            legs.append(leg)
            prev_airport = airport
        
        # Physical impossibility: same employee, overlapping flights
        if random.random() < 0.03:
            legs[0]['departure_datetime'] = legs[1]['arrival_datetime']  # Impossible connection
        
        itinerary = {
            'itinerary_id': f"ITIN-{random.randint(10000,99999)}",
            'employee_id': f"EMP_{random.randint(1,999):03d}",
            'legs': legs,
            'total_amount': round(random.uniform(50000, 300000), 2),
            'currency': 'INR',
        }
        itineraries.append(itinerary)
    
    rows = AnomalyInjector.inject_anomalies(itineraries, anomaly_count)
    ExportUtils.export_json(f"{output_path}/travel_itineraries.json", rows)
    return itineraries