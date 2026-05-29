from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import math
from django.db.models import Avg
from .models import RawRecord, NormalizedActivity, EmissionFactor, ValidationIssue


# ── Date parsing ──────────────────────────────────────────────────────────────

# def parse_date(date_str):
#     if not date_str:
#         return None
#     s=str(date_str).strip()


#     # Excel weirdness:
#     s=s.replace('"="','')
#     s=s.replace('"','')
#     s=s.strip("=")
#     formats=[
#         '%Y-%m-%d',
#         '%d.%m.%Y',
#         '%Y/%m/%d',
#         '%m/%d/%Y',
#         '%d/%m/%Y',
#         '%d%m%Y',
#         '%Y%m%d'
#     ]
#     for fmt in formats:
#         try:
#             return datetime.strptime(
#                 s,
#                 fmt
#             ).date()
#         except ValueError:
#             pass
#     return None

def parse_date(date_str):
    s = str(date_str).strip()
    # Remove Excel formula wrapping: ="01.01.2025" or ="01012025"
    s = s.lstrip('=').strip('"').strip()

    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d%m%Y', '%Y/%m/%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: '{date_str}'")

def parse_decimal(value, default=None):
    """Safely convert value to Decimal."""
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return default


# ── Haversine ────────────────────────────────────────────────────────────────

# Extended airport coordinate lookup
AIRPORT_COORDS = {
    'BOM': (19.0896, 72.8656), 'DEL': (28.5562, 77.1000),
    'BLR': (13.1979, 77.7063), 'HYD': (17.2313, 78.4298),
    'MAA': (12.9941, 80.1709), 'CCU': (22.6545, 88.4467),
    'LHR': (51.4700, -0.4543), 'CDG': (49.0097, 2.5479),
    'FRA': (50.0379, 8.5622),  'AMS': (52.3105, 4.7683),
    'JFK': (40.6413, -73.7781),'EWR': (40.6895, -74.1745),
    'SFO': (37.6213, -122.379),'LAX': (33.9425, -118.408),
    'ORD': (41.9742, -87.9073),'DFW': (32.8968, -97.0380),
    'DXB': (25.2532, 55.3657), 'SIN': (1.3644, 103.9915),
    'HKG': (22.3080, 113.9185),'NRT': (35.7720, 140.3929),
}


def calculate_haversine_distance(origin_code, dest_code):
    if origin_code not in AIRPORT_COORDS or dest_code not in AIRPORT_COORDS:
        return None
    lat1, lon1 = map(math.radians, AIRPORT_COORDS[origin_code])
    lat2, lon2 = map(math.radians, AIRPORT_COORDS[dest_code])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return Decimal(str(round(6371 * 2 * math.asin(math.sqrt(a)), 2)))


# ── Anomaly detection ────────────────────────────────────────────────────────

def detect_anomalies(activity):
    if not activity.quantity or not activity.facility_code:
        return
    avg = NormalizedActivity.objects.filter(
        facility_code=activity.facility_code,
        activity_type=activity.activity_type,
        review_status='APPROVED',
    ).aggregate(Avg('quantity'))['quantity__avg']

    if avg and activity.quantity > (Decimal(str(avg)) * Decimal('2.5')):
        activity.review_status = 'SUSPICIOUS'
        activity.anomaly_code = 'QUANTITY_SPIKE'
        activity.anomaly_details = (
            f"Spike detected: {float(activity.quantity / Decimal(str(avg))):.1f}x "
            f"above facility historical average ({float(avg):.2f} {activity.unit})."
        )
        activity.save(update_fields=['review_status', 'anomaly_code', 'anomaly_details'])


# ── SAP processor ────────────────────────────────────────────────────────────

def process_sap_line(record):
    data = record.raw_data
    act_date=parse_date(
    data.get('BUDAT')
    )

    if not act_date:

        ValidationIssue.objects.create(

            raw_record=record,

            severity='ERROR',

            issue_type='INVALID_DATE',

            message=f"Could not parse date {data.get('BUDAT')}"

        )

        record.has_error=True

        record.save(
            update_fields=['has_error']
        )

        return
    mat_type = str(data.get('MATNR', '')).upper()

    qty_raw = data.get('MENGE', '').strip()
    qty = parse_decimal(qty_raw)
    if qty is None:
        ValidationIssue.objects.create(
            raw_record=record, severity='ERROR',
            issue_type='INVALID_QUANTITY',
            message=f"Could not parse MENGE value: '{qty_raw}'",
        )
        record.has_error = True
        record.save(update_fields=['has_error'])
        return

    # Route by material type
    fuel_keywords = ('DIESEL', 'FUEL', 'PETROL', 'GAS', 'HFO', 'NATGAS', 'NATURAL_GAS')
    if any(kw in mat_type for kw in fuel_keywords):
        scope, cat, act_type = 'SCOPE_1', 'Stationary Combustion', 'fuel_diesel'
        default_unit = 'L'
    else:
        scope, cat, act_type = 'SCOPE_3', 'Category 1: Purchased Goods & Services', 'material_procurement'
        default_unit = 'MT'

    raw_unit = str(data.get('MEINS', default_unit)).strip()

    # Unit normalisation
    if raw_unit == 'GAL':
        qty = qty * Decimal('3.78541')
        raw_unit = 'L'
    elif raw_unit == 'KG':
        qty = qty / Decimal('1000')
        raw_unit = 'MT'

    ef = EmissionFactor.objects.filter(activity_type=act_type, unit=raw_unit).first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.0')
    ef_src = ef.source if ef else 'Factor Database Missing'

    activity = NormalizedActivity.objects.create(
        raw_record=record,
        scope=scope,
        scope_category=cat,
        activity_type=act_type,
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        facility_code=data.get('WERKS') or None,
        quantity=qty,
        unit=raw_unit,
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=qty * factor_val,
        source_metadata={
            'material': data.get('MATNR'), 'vendor': data.get('LIFNR'),
            'net_value': data.get('NETWR'), 'currency': data.get('WAERS'),
        },
    )
    detect_anomalies(activity)


# ── Utility bill processor ───────────────────────────────────────────────────

def process_utility_bill_line(record):
    data = record.raw_data
    start_date = parse_date(data['billing_start'])
    end_date = parse_date(data['billing_end'])

    # Accept either combined field OR split peak/offpeak (matches generated data)
    if 'consumption_kwh' in data and data['consumption_kwh'].strip():
        total_kwh = parse_decimal(data['consumption_kwh'])
    else:
        peak = parse_decimal(data.get('peak_consumption_kwh', 0)) or Decimal('0')
        offpeak = parse_decimal(data.get('offpeak_consumption_kwh', 0)) or Decimal('0')
        total_kwh = peak + offpeak

    if total_kwh is None or total_kwh < 0:
        ValidationIssue.objects.create(
            raw_record=record, severity='ERROR',
            issue_type='INVALID_CONSUMPTION',
            message='Utility consumption value is invalid or negative.',
        )
        record.has_error = True
        record.save(update_fields=['has_error'])
        return

    total_days = max((end_date - start_date).days + 1, 1)
    kwh_per_day = total_kwh / Decimal(total_days)

    ef = EmissionFactor.objects.filter(activity_type='electricity_grid', region='IN').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.71')
    ef_src = ef.source if ef else 'IEA Default Grid Index'

    # Split billing period across calendar months
    month_splits = {}
    current = start_date
    while current <= end_date:
        key = current.strftime('%Y-%m')
        month_splits[key] = month_splits.get(key, 0) + 1
        current += timedelta(days=1)

    peak_demand_kw = data.get('max_demand_kw') or data.get('peak_demand_kw')

    for period, days in month_splits.items():
        allocated_qty = kwh_per_day * Decimal(days)
        mid_date = datetime.strptime(f'{period}-15', '%Y-%m-%d').date()

        activity = NormalizedActivity.objects.create(
            raw_record=record,
            scope='SCOPE_2',
            scope_category='Scope 2: Purchased Utilities',
            activity_type='electricity_grid',
            activity_date=mid_date,
            reporting_period=period,
            facility_code=data.get('plant_ref') or None,
            quantity=allocated_qty,
            unit='kWh',
            factor_value_used=factor_val,
            emission_factor_source=ef_src,
            co2e_kg=allocated_qty * factor_val,
            source_metadata={
                'meter_id': data.get('meter_id'),
                'peak_demand_kw': peak_demand_kw,
                'billing_start': str(start_date),
                'billing_end': str(end_date),
                'total_days_in_period': total_days,
                'days_allocated_to_period': days,
            },
        )
        detect_anomalies(activity)


# ── Travel processor ─────────────────────────────────────────────────────────

def process_travel_line(record):
    data = record.raw_data
    expense_type = str(data.get('expense_type', 'Air Travel')).strip()

    # Skip non-emission expense types
    if expense_type.lower() in ('meals', 'meal', 'entertainment', 'other'):
        return

    act_date = parse_date(data['transaction_date'])

    if expense_type in ('Air Travel', 'Flight'):
        _process_flight(record, data, act_date)
    elif expense_type in ('Hotel Stay', 'Hotel', 'Accommodation'):
        _process_hotel(record, data, act_date)
    elif expense_type in ('Ground Transport', 'Taxi', 'Train', 'Rail', 'Car Rental'):
        _process_ground_transport(record, data, act_date)
    else:
        # Default: treat as flight if origin/destination present
        if data.get('origin') and data.get('destination'):
            _process_flight(record, data, act_date)


def _process_flight(record, data, act_date):
    origin = str(data.get('origin', '')).strip().upper()
    destination = str(data.get('destination', '')).strip().upper()

    distance = calculate_haversine_distance(origin, destination)

    ef = EmissionFactor.objects.filter(activity_type='travel_flight').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.133')
    ef_src = ef.source if ef else 'DEFRA Aviation Factors'

    co2e = (distance * factor_val) if distance else Decimal('0.0')

    # Business class multiplier (2.5x per DEFRA floor-space methodology)
    booking_class = str(data.get('booking_class', 'Economy')).strip().lower()
    if booking_class in ('business', 'first', 'business class', 'first class'):
        co2e = co2e * Decimal('2.5')

    activity = NormalizedActivity.objects.create(
        raw_record=record,
        scope='SCOPE_3',
        scope_category='Category 6: Business Travel',
        activity_type='travel_flight',
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        facility_code=None,
        quantity=distance if distance else Decimal('0.0'),
        unit='pkm',
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=co2e,
        source_metadata={
            'origin': origin, 'destination': destination,
            'booking_class': data.get('booking_class'),
            'vendor': data.get('vendor'),
            'employee_id': data.get('employee_id'),
        },
    )

    if not distance:
        activity.review_status = 'SUSPICIOUS'
        activity.anomaly_code = 'MISSING_FACILITY'
        activity.anomaly_details = (
            f"Cannot resolve distance: airport code '{origin}' or '{destination}' "
            f"not found in coordinate database."
        )
        activity.save(update_fields=['review_status', 'anomaly_code', 'anomaly_details'])


def _process_hotel(record, data, act_date):
    nights = parse_decimal(data.get('nights', 1)) or Decimal('1')

    ef = EmissionFactor.objects.filter(activity_type='travel_hotel').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('15.5')
    ef_src = ef.source if ef else 'DEFRA Hotel Accommodation Factors'

    NormalizedActivity.objects.create(
        raw_record=record,
        scope='SCOPE_3',
        scope_category='Category 6: Business Travel',
        activity_type='travel_hotel',
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        quantity=nights,
        unit='room_nights',
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=nights * factor_val,
        source_metadata={
            'city': data.get('city'), 'vendor': data.get('vendor'),
            'employee_id': data.get('employee_id'),
        },
    )


def _process_ground_transport(record, data, act_date):
    distance_km = parse_decimal(data.get('distance_km', 0)) or Decimal('0')

    ef = EmissionFactor.objects.filter(activity_type='travel_ground').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.14')
    ef_src = ef.source if ef else 'DEFRA Ground Transport Factors'

    NormalizedActivity.objects.create(
        raw_record=record,
        scope='SCOPE_3',
        scope_category='Category 6: Business Travel',
        activity_type='travel_ground',
        activity_date=act_date,
        reporting_period=act_date.strftime('%Y-%m'),
        quantity=distance_km,
        unit='km',
        factor_value_used=factor_val,
        emission_factor_source=ef_src,
        co2e_kg=distance_km * factor_val,
        source_metadata={
            'mode': data.get('mode'), 'employee_id': data.get('employee_id'),
        },
    )


# ── Smart meter processor ────────────────────────────────────────────────────

def process_smart_meter_hourly_batch(upload, file_rows):
    """
    Aggregates hourly interval rows into daily totals.
    Handles timezone-offset timestamps and both kwh_interval / interval_kwh field names.
    """
    daily_matrix = {}

    for row in file_rows:
        try:
            raw_ts = str(row.get('timestamp', '')).strip()
            # Strip timezone offset (+05:30, +01:00, Z, etc.)
            for sep in ('+', ' UTC', 'Z'):
                if sep in raw_ts:
                    raw_ts = raw_ts.split(sep)[0].strip()

            timestamp = datetime.strptime(raw_ts, '%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError):
            continue  # Skip unparseable timestamps

        # Accept both field names from different generator versions
        kwh_raw = row.get('kwh_interval') or row.get('interval_kwh', 0)
        kwh = parse_decimal(kwh_raw) or Decimal('0')

        # Skip suspect/bad quality readings
        quality = str(row.get('quality', 'GOOD')).upper()
        if quality == 'SUSPECT':
            continue

        day_key = timestamp.date()
        if day_key not in daily_matrix:
            daily_matrix[day_key] = {'kwh': Decimal('0'), 'count': 0}
        daily_matrix[day_key]['kwh'] += kwh
        daily_matrix[day_key]['count'] += 1

    ef = EmissionFactor.objects.filter(activity_type='electricity_grid', region='IN').first()
    factor_val = ef.factor_kg_co2e if ef else Decimal('0.71')
    ef_src = ef.source if ef else 'IEA Default Grid Index'

    # Use offset line numbers to avoid unique_together conflict with original rows
    BASE_OFFSET = 100000

    for idx, (target_day, metrics) in enumerate(sorted(daily_matrix.items())):
        raw_record = RawRecord.objects.create(
            upload=upload,
            line_number=BASE_OFFSET + idx,
            raw_data={
                'aggregated_date': str(target_day),
                'total_kwh': float(metrics['kwh']),
                'interval_count': metrics['count'],
                'source': 'smart_meter_hourly_aggregation',
            },
        )
        NormalizedActivity.objects.create(
            raw_record=raw_record,
            scope='SCOPE_2',
            scope_category='Scope 2: Smart Meter Telemetry',
            activity_type='electricity_grid',
            activity_date=target_day,
            reporting_period=target_day.strftime('%Y-%m'),
            facility_code='METER_PROTOTYPE_01',
            quantity=metrics['kwh'],
            unit='kWh',
            factor_value_used=factor_val,
            emission_factor_source=ef_src,
            co2e_kg=metrics['kwh'] * factor_val,
            source_metadata={
                'interval_count': metrics['count'],
                'aggregation_method': 'hourly_sum',
            },
        )


# ── Pipeline orchestrator ────────────────────────────────────────────────────

def execute_ingestion_pipeline(upload):
    records = list(upload.records.filter(line_number__lt=100000))  # Original rows only

    if upload.source_type == 'UTILITY_METER':
        rows_list = [r.raw_data for r in records]
        process_smart_meter_hourly_batch(upload, rows_list)
        normalized = NormalizedActivity.objects.filter(raw_record__upload=upload).count()
        upload.normalized_rows = normalized
        upload.status = 'COMPLETED'
        upload.save(update_fields=['normalized_rows', 'status'])
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
            ValidationIssue.objects.create(
                raw_record=record,
                severity='ERROR',
                issue_type='PROCESSING_CRASH',
                message=f'Runtime error: {str(e)}'
            )
            record.has_error = True
            record.save(update_fields=['has_error'])

    # Update upload summary statistics
    upload.normalized_rows = NormalizedActivity.objects.filter(
        raw_record__upload=upload
    ).count()
    upload.error_rows = RawRecord.objects.filter(
        upload=upload, has_error=True, line_number__lt=100000
    ).count()
    upload.suspicious_rows = NormalizedActivity.objects.filter(
        raw_record__upload=upload, review_status='SUSPICIOUS'
    ).count()
    upload.status = 'COMPLETED'
    upload.save(update_fields=['normalized_rows', 'error_rows', 'suspicious_rows', 'status'])