"""Generate Concur-style travel expense exports."""
import random
from datetime import datetime, timedelta
from ..core.faker_extensions import fake, EnterpriseProvider
from ..core.anomaly_injector import AnomalyInjector
from ..core.export_utils import ExportUtils
from ..configs.travel_config import TRAVEL_CONFIG

fake.add_provider(EnterpriseProvider)

def generate_concur_exports(anomaly_count=60, output_path='outputs/'):
    """Generate travel expense JSON with realistic patterns."""
    print("Generating travel expense data...")
    rows = []
    employees = [f"EMP_{random.randint(1, 999):03d}" for _ in range(TRAVEL_CONFIG['employees'])]
    start_date = datetime(2025, 6, 1)
    end_date = datetime(2026, 5, 31)
    
    for i in range(TRAVEL_CONFIG['target_rows']):
        employee = random.choice(employees)
        expense_type = random.choices(
            ['Air Travel', 'Hotel Stay', 'Ground Transport', 'Meal'],
            weights=[0.5, 0.25, 0.15, 0.1]
        )[0]
        
        dt = fake.date_time_between(start_date=start_date, end_date=end_date)
        report_id = f"EXP-{dt.year}-{random.randint(1000,9999)}"
        
        # Version / resubmission handling
        version = 1
        if random.random() < TRAVEL_CONFIG['resubmission_ratio']:
            version = random.randint(2, 3)
        
        base_row = {
            'report_id': report_id,
            'report_version': version,
            'employee_id': employee,
            'expense_type': expense_type,
            'transaction_date': dt.strftime('%Y-%m-%d'),
            'has_receipt': random.random() > TRAVEL_CONFIG['missing_receipt_ratio'],
        }
        
        if expense_type == 'Air Travel':
            base_row.update({
                'booking_class': fake.booking_class(),
                'origin': fake.iata_code(valid=(random.random() > TRAVEL_CONFIG['invalid_airport_ratio'])),
                'destination': fake.iata_code(valid=(random.random() > TRAVEL_CONFIG['invalid_airport_ratio'])),
                'airline': fake.airline_name(),
                'transaction_amount': round(random.uniform(5000, 200000), 2),
                'currency': random.choice(['INR', 'USD', 'GBP', 'EUR']),
            })
            # Multi-leg? Will be handled in separate generator
        elif expense_type == 'Hotel Stay':
            base_row.update({
                'city': random.choice(['Mumbai', 'Delhi', 'London', 'New York', 'Frankfurt']),
                'nights': random.randint(1, 5),
                'vendor': random.choice(['Hilton', 'Marriott', 'Accor', 'Local Hotel']),
                'transaction_amount': round(random.uniform(5000, 30000), 2),
                'currency': 'INR',
            })
        else:  # Ground transport or meal
            base_row.update({
                'vendor': random.choice(['Uber', 'Lyft', 'Local Taxi', 'Ola']),
                'transaction_amount': round(random.uniform(200, 5000), 2),
                'currency': 'INR',
            })
        
        # Cancellation
        if random.random() < TRAVEL_CONFIG['cancelled_ratio']:
            base_row['reimbursement_status'] = 'CANCELLED'
            base_row['cancellation_reason'] = random.choice(['Flight changed', 'Meeting cancelled', 'Duplicate booking'])
        else:
            base_row['reimbursement_status'] = random.choices(['PENDING', 'APPROVED', 'PAID'], weights=[0.2, 0.6, 0.2])[0]
        
        rows.append(base_row)
    
    rows = AnomalyInjector.inject_anomalies(rows, anomaly_count)
    ExportUtils.export_json(f"{output_path}/travel_expenses.json", rows)
    return rows