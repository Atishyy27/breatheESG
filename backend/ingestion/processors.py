from decimal import Decimal
from datetime import datetime, timedelta
import math
from django.db.models import Avg
from .models import RawRecord, NormalizedActivity, EmissionFactor

def parse_date(date_str):
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date formatting: '{date_str}'")

def calculate_haversine_distance(origin_code, dest_code):
    coordinates = {
        'BOM': (19.0896, 72.8656),
        'DEL': (28.5562, 77.1000),
        'LHR': (51.4700, -0.4543),
        'JFK': (40.6413, -73.7781)
    }
    
    if origin_code not in coordinates or dest_code not in coordinates:
        return None
        
    lat1, lon1 = map(math.radians, coordinates[origin_code])
    lat2, lon2 = map(math.radians, coordinates[dest_code])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return Decimal(str(round(6371 * c, 2)))

def detect_anomalies(activity):
    if activity.quantity and activity.facility_code:
        historical_avg = NormalizedActivity.objects.filter(
            facility_code=activity.facility_code,
            activity_type=activity.activity_type,
            review_status='APPROVED'
        ).aggregate(Avg('quantity'))['quantity__avg']
        
        if historical_avg and activity.quantity > (Decimal(str(historical_avg)) * Decimal('2.5')):
            activity.review_status = 'SUSPICIOUS'
            activity.anomaly_code = 'QUANTITY_SPIKE'
            activity.anomaly_details = f"Spike detected: {activity.quantity / Decimal(str(historical_avg)):.1f}x higher than historical average ({historical_avg:.2f})."
            activity.save(update_fields=['review_status', 'anomaly_code', 'anomaly_details'])

def process_sap_line(record):
    data = record.raw_data
    act_date = parse_date(data['BUDAT'])
    mat_type = str(data['MATNR']).upper()
    qty = Decimal(str(data['MENGE']))
    
    if "DIESEL" in mat_type or "FUEL" in mat_type:
        scope, cat, act_type, default_unit = 'SCOPE_1', 'Stationary Combustion', 'fuel_diesel', 'L'
    else:
        scope, cat, act_type, default_unit = 'SCOPE_3', 'Category 1: Purchased Goods', 'material_procurement', 'MT'
        
    raw_unit = data.get('MEINS', default_unit)
    if raw_unit == 'GAL':
        qty = qty * Decimal('3.78541')
        raw_unit = 'L'
        
    ef = EmissionFactor.objects.filter(activity_type=act_type, unit=raw_unit).first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.0')
    ef_src = ef.source if ef else "Factor Database Missing"
    
    activity = NormalizedActivity.objects.create(
        raw_record=record,
        scope=scope,
        scope_category=cat,
        activity_type=act_type,
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        facility_code=data.get('WERKS'),
        quantity=qty,
        unit=raw_unit,
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=qty * factor_val
    )
    detect_anomalies(activity)

def process_utility_bill_line(record):
    data = record.raw_data
    start_date = parse_date(data['billing_start'])
    end_date = parse_date(data['billing_end'])
    total_kwh = Decimal(str(data['consumption_kwh']))
    
    total_days = (end_date - start_date).days + 1
    kwh_per_day = total_kwh / Decimal(total_days)
    
    ef = EmissionFactor.objects.filter(activity_type='electricity_grid', region='IN').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.71')
    ef_src = ef.source if ef else "IEA Default Grid Index"
    
    current_date = start_date
    month_splits = {}
    while current_date <= end_date:
        m_key = current_date.strftime('%Y-%m')
        month_splits[m_key] = month_splits.get(m_key, 0) + 1
        current_date += timedelta(days=1)
        
    for period, days in month_splits.items():
        allocated_qty = kwh_per_day * Decimal(days)
        mid_date = datetime.strptime(f"{period}-15", "%Y-%m-%d").date()
        
        activity = NormalizedActivity.objects.create(
            raw_record=record,
            scope='SCOPE_2',
            scope_category='Scope 2: Purchased Utilities',
            activity_type='electricity_grid',
            activity_date=mid_date,
            reporting_period=period,
            facility_code=data.get('plant_ref'),
            quantity=allocated_qty,
            unit='kWh',
            factor_value_used=factor_val,
            emission_factor_source=ef_src,
            co2e_kg=allocated_qty * factor_val,
            source_metadata={"peak_demand_kw": data.get('peak_demand_kw')}
        )
        detect_anomalies(activity)

def process_travel_line(record):
    data = record.raw_data
    act_date = parse_date(data['transaction_date'])
    
    distance = calculate_haversine_distance(data['origin'], data['destination'])
    ef = EmissionFactor.objects.filter(activity_type='travel_flight').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.133')
    ef_src = ef.source if ef else "DEFRA Aviation Factors"
    
    activity = NormalizedActivity.objects.create(
        raw_record=record,
        scope='SCOPE_3',
        scope_category='Category 6: Business Travel',
        activity_type='travel_flight',
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        quantity=distance if distance else Decimal('0.0'),
        unit='pkm',
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=(distance * factor_val) if distance else Decimal('0.0')
    )
    
    if not distance:
        activity.review_status = 'SUSPICIOUS'
        activity.anomaly_code = 'MISSING_FACILITY'
        activity.anomaly_details = f"Location resolution error: Airport codes '{data['origin']}' or '{data['destination']}' not found in master database lookup."
        activity.save(update_fields=['review_status', 'anomaly_code', 'anomaly_details'])
        
    if str(data.get('booking_class')).strip().lower() == 'business' and distance:
        activity.co2e_kg = activity.co2e_kg * Decimal('2.5')
        activity.save(update_fields=['co2e_kg'])

def process_smart_meter_hourly_batch(upload, file_rows):
    """Processes interval smart meter metrics by aggregating rows by day."""
    daily_matrix = {}
    
    for row in file_rows:
        # Expects: timestamp, kwh_interval, peak_demand_kw
        timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
        day_key = timestamp.date()
        
        if day_key not in daily_matrix:
            daily_matrix[day_key] = {'kwh': Decimal('0.0'), 'max_kw': Decimal('0.0')}
            
        daily_matrix[day_key]['kwh'] += Decimal(str(row['kwh_interval']))
        daily_matrix[day_key]['max_kw'] = max(daily_matrix[day_key]['max_kw'], Decimal(str(row['peak_demand_kw'])))
        
    ef = EmissionFactor.objects.filter(activity_type='electricity_grid', region='IN').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.71')
    ef_src = ef.source if ef else "IEA Default Grid Index"

    for target_day, metrics in daily_matrix.items():
        raw_record = RawRecord.objects.create(
            upload=upload,
            line_number=0,  # Combined track reference code
            raw_data={
                "target_date": str(target_day),
                "total_kwh": float(metrics['kwh']),
                "max_peak_kw": float(metrics['max_kw'])
            }
        )
        
        NormalizedActivity.objects.create(
            raw_record=raw_record,
            scope='SCOPE_2',
            scope_category='Scope 2: Smart Meter Data',
            activity_type='electricity_grid',
            activity_date=target_day,
            reporting_period=target_day.strftime('%Y-%m'),
            facility_code="METER_PROTOTYPE_01",
            quantity=metrics['kwh'],
            unit='kWh',
            factor_value_used=factor_val,
            emission_factor_source=ef_src,
            co2e_kg=metrics['kwh'] * factor_val,
            review_status='PENDING',
            source_metadata={"max_demand_peak_kw": float(metrics['max_kw'])}
        )

def execute_ingestion_pipeline(upload):
    records = upload.records.all()
    
    if upload.source_type == 'UTILITY_METER':
        rows_list = [r.raw_data for r in records]
        process_smart_meter_hourly_batch(upload, rows_list)
        upload.status = 'COMPLETED'
        upload.normalized_rows = upload.total_rows
        upload.save()
        return

    from .validation import validate_raw_record
    
    for record in records:
        is_valid = validate_raw_record(record)
        if not is_valid:
            continue
            
        try:
            if upload.source_type == 'SAP':
                process_sap_line(record)
            elif upload.source_type == 'UTILITY_BILL':
                process_utility_bill_line(record)
            elif upload.source_type == 'TRAVEL':
                process_travel_line(record)
        except Exception as e:
            from .models import ValidationIssue
            ValidationIssue.objects.create(
                raw_record=record,
                severity='ERROR',
                issue_type='PROCESSING_CRASH',
                message=f"Runtime error context: {str(e)}"
            )
            record.has_error = True
            record.save(update_fields=['has_error'])

    # Aggregate upload metrics
    upload.normalized_rows = NormalizedActivity.objects.filter(raw_record__upload=upload).count()
    upload.error_rows = RawRecord.objects.filter(upload=upload, has_error=True).count()
    upload.suspicious_rows = NormalizedActivity.objects.filter(raw_record__upload=upload, review_status='SUSPICIOUS').count()
    upload.status = 'COMPLETED'
    upload.save()