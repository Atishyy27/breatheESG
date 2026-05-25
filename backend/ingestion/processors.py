from decimal import Decimal
from datetime import datetime, timedelta
import json
from .models import NormalizedActivity, RawRecord, EmissionFactor, ValidationIssue

def parse_date(date_str, formats=('%Y-%m-%d', '%d.%m.%Y')):
    """Gracefully extracts datetimes across German and ISO enterprise outputs."""
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Temporal string format mismatch: {date_str}")

def normalize_utility_monthly_bill(raw_record_id):
    """
    Ingests monthly electricity logs and handles billing cycles that cross month boundaries.
    If a bill runs from Apr 12 to May 11 (30 days), it creates two prorated records.
    """
    raw_record = RawRecord.objects.get(id=raw_record_id)
    data = json.loads(raw_record.raw_data)
    
    start_date = parse_date(data['billing_start'])
    end_date = parse_date(data['billing_end'])
    total_kwh = Decimal(str(data['consumption_kwh']))
    facility = data.get('plant_ref')
    
    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        raise ValueError("Billing engine failure: End bounds precede inception parameters.")
        
    kwh_per_day = total_kwh / Decimal(total_days)
    
    # Calculate day distribution weights per calendar month bucket
    current_date = start_date
    calendar_buckets = {}
    
    while current_date <= end_date:
        period_key = current_date.strftime('%Y-%m')
        calendar_buckets[period_key] = calendar_buckets.get(period_key, 0) + 1
        current_date += timedelta(days=1)
        
    # Resolve global emission coefficients (Default Grid Coefficient fallback)
    try:
        ef_ref = EmissionFactor.objects.get(activity_type='electricity_grid', unit='kWh', region='IN', year=2025)
    except EmissionFactor.DoesNotExist:
        ef_ref = EmissionFactor.objects.filter(activity_type='electricity_grid', unit='kWh').first()
        
    # Emit tracking footprints into the analytical ledger matrix
    for period, day_count in calendar_buckets.items():
        prorated_qty = kwh_per_day * Decimal(day_count)
        calculated_co2e = prorated_qty * ef_ref.factor_kg_co2e
        
        # Calculate a placeholder tracking point anchored to the middle of the month
        representative_date = datetime.strptime(f"{period}-15", "%Y-%m-%d").date()
        
        NormalizedActivity.objects.create(
            raw_record=raw_record,
            tenant_id=raw_record.upload.tenant_id,
            scope='SCOPE_2',
            scope_category='Scope 2: Purchased Electricity',
            activity_type='electricity_grid',
            activity_date=representative_date,
            reporting_period=period,
            facility_code=facility,
            country_code='IND',
            quantity=prorated_qty,
            unit='kWh',
            factor_value_used=ef_ref.factor_kg_co2e,
            emission_factor_source=ef_ref.source,
            co2e_kg=calculated_co2e,
            review_status='PENDING'
        )

def process_smart_meter_hourly_batch(raw_upload, file_rows):
    """
    Aggregates high-frequency hourly telemetry directly into single daily entries.
    Prevents large dataset parsing timeouts during analyst verification sweeps.
    """
    daily_matrix = {}
    
    for row in file_rows:
        timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
        day_key = timestamp.date()
        
        if day_key not in daily_matrix:
            daily_matrix[day_key] = {'kwh': Decimal('0.0'), 'max_kw': Decimal('0.0')}
            
        daily_matrix[day_key]['kwh'] += Decimal(str(row['kwh_interval']))
        daily_matrix[day_key]['max_kw'] = max(daily_matrix[day_key]['max_kw'], Decimal(str(row['peak_demand_kw'])))
        
    try:
        ef_ref = EmissionFactor.objects.get(activity_type='electricity_grid', unit='kWh', region='IN', year=2025)
    except EmissionFactor.DoesNotExist:
        ef_ref = EmissionFactor.objects.filter(activity_type='electricity_grid', unit='kWh').first()

    for target_day, aggregated_metrics in daily_matrix.items():
        # Commit raw trace elements to map structural verification paths
        raw_record = RawRecord.objects.create(
            upload=raw_upload,
            line_number=0,  # Denotes consolidated tracking sequence 
            raw_data=json.dumps({
                "note": "Aggregated IoT interval vector block",
                "target_date": str(target_day),
                "total_kwh": float(aggregated_metrics['kwh']),
                "max_peak_kw": float(aggregated_metrics['max_kw'])
            })
        )
        
        NormalizedActivity.objects.create(
            raw_record=raw_record,
            tenant_id=raw_upload.tenant_id,
            scope='SCOPE_2',
            scope_category='Scope 2: High-Frequency Interval Telemetry',
            activity_type='electricity_grid',
            activity_date=target_day,
            reporting_period=target_day.strftime('%Y-%m'),
            facility_code="METER_PROTOTYPE_01",
            quantity=aggregated_metrics['kwh'],
            unit='kWh',
            factor_value_used=ef_ref.factor_kg_co2e,
            emission_factor_source=ef_ref.source,
            co2e_kg=aggregated_metrics['kwh'] * ef_ref.factor_kg_co2e,
            review_status='PENDING',
            source_metadata={"max_demand_peak_kw": float(aggregated_metrics['max_kw'])}
        )