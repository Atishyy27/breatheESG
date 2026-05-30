import csv
import io
import json
import hashlib
import subprocess
from datetime import timedelta
from functools import wraps
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import RawUpload, RawRecord, NormalizedActivity, ValidationIssue
from .serializers import (
    UploadSummarySerializer,
    QueueItemSerializer,
    ActivityDetailSerializer,
)
from .processors import execute_ingestion_pipeline


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_analyst_email(request):
    return request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')

def role_required(*allowed_roles):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(request, *args, **kwargs):
            role = request.META.get('HTTP_X_USER_ROLE', 'ANALYST').upper()
            if role not in allowed_roles:
                return Response(
                    {'error': f'Access Denied: Role {role} cannot access this process mapping.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_fn(request, *args, **kwargs)
        return wrapped
    return decorator

def _parse_file_to_rows(file_content: bytes, source_type: str) -> list:
    """
    Converts raw file bytes to a list of row dicts with dynamic delimiter
    sniffing and Excel formula cleanup for auditing fidelity.
    """
    if source_type == 'TRAVEL':
        decoded = file_content.decode('utf-8')
        data = json.loads(decoded)
        return data if isinstance(data, list) else [data]

    # CSV sources — auto-detect delimiter between pipe and comma
    text = file_content.decode('utf-8-sig')
    sample = text[:1000]
    delimiter = '|' if sample.count('|') > sample.count(',') else ','

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for row in reader:
        cleaned = {}
        for k, v in row.items():
            if not k:
                continue
            key = k.strip()
            # Strip Excel formula artifacts if present: ="value" -> value
            val = str(v).strip().lstrip('=').strip('"').strip() if v else ''
            cleaned[key] = val
        rows.append(cleaned)
    return rows

# ── Health check ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'service': 'BreatheESG Ingestion API'})


# ── Upload pipeline ───────────────────────────────────────────────────────────

@api_view(['POST'])
@role_required('ANALYST', 'MANAGER')
def upload_file_endpoint(request):
    file = request.FILES.get('file')
    source_type = request.data.get('source_type', '').strip()

    if not file:
        return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

    valid_sources = {'SAP', 'UTILITY_BILL', 'UTILITY_METER', 'TRAVEL'}
    if source_type not in valid_sources:
        return Response(
            {'error': f'Invalid source_type. Must be one of: {", ".join(valid_sources)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Read bytes once
    file_content = file.read()

    # Duplicate detection via MD5
    file_hash = hashlib.md5(file_content).hexdigest()
    if RawUpload.objects.filter(file_hash=file_hash).exists():
        return Response(
            {'error': 'Duplicate upload detected. This exact file has already been ingested.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse file into rows
    try:
        rows = _parse_file_to_rows(file_content, source_type)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return Response(
            {'error': f'File parse error: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not rows:
        return Response({'error': 'File is empty or has no parseable rows.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create upload record
    upload = RawUpload.objects.create(
        source_type=source_type,
        filename=file.name,
        file_hash=file_hash,
        uploaded_by_email=_get_analyst_email(request),
        status='PROCESSING',
        total_rows=len(rows),
    )

    # Persist each row as an immutable RawRecord
    raw_records = []
    for line_number, row_dict in enumerate(rows, start=1):
        raw_records.append(RawRecord(
            upload=upload,
            line_number=line_number,
            raw_data=row_dict,
        ))
    RawRecord.objects.bulk_create(raw_records)

    # Run ingestion pipeline
    try:
        execute_ingestion_pipeline(upload)
    except Exception as e:
        upload.status = 'FAILED'
        upload.processing_error = str(e)[:500]
        upload.save(update_fields=['status', 'processing_error'])
        return Response(
            {'error': f'Pipeline execution failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Refresh from DB after pipeline updates stats
    upload.refresh_from_db()

    return Response({
        'upload_id': upload.id,
        'status': 'completed',
        'upload_details': {
            'total_records': upload.total_rows,
            'successfully_normalized': upload.normalized_rows,
            'validation_errors_found': upload.error_rows,
            'suspicious_flagged': upload.suspicious_rows,
        },
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def upload_list(request):
    uploads = RawUpload.objects.order_by('-uploaded_at')[:100]
    return Response(UploadSummarySerializer(uploads, many=True).data)

@api_view(['GET'])
def audit_ledger(request):
    """Returns approved+locked records for the Audit page."""
    activities = (
        NormalizedActivity.objects
        .filter(review_status='APPROVED')
        .select_related('raw_record__upload')
        .prefetch_related('raw_record__validation_issues')
        .order_by('-reviewed_at')
    )
    return Response(QueueItemSerializer(activities, many=True).data)


# ── Review queue ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def review_queue_list(request):
    activities = (
        NormalizedActivity.objects
        .filter(review_status__in=['PENDING', 'SUSPICIOUS'])
        .select_related('raw_record__upload')
        .prefetch_related('raw_record__validation_issues')
        .order_by(
            Case(
                When(review_status='SUSPICIOUS', then=0),
                When(review_status='PENDING', then=1),
                default=2,
                output_field=IntegerField()
            ),
            '-created_at'
        )
    )
    return Response(QueueItemSerializer(activities, many=True).data)

@api_view(['GET'])
def review_queue_detail(request, pk):
    try:
        activity = (
            NormalizedActivity.objects
            .select_related('raw_record__upload')
            .prefetch_related('raw_record__validation_issues')
            .get(pk=pk)
        )
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(ActivityDetailSerializer(activity).data)


@api_view(['POST'])
def approve_activity(request, pk):
    try:
        activity = NormalizedActivity.objects.select_related('raw_record').get(pk=pk)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found.'}, status=status.HTTP_404_NOT_FOUND)

    if activity.review_status == 'APPROVED':
        return Response(
            {'error': 'Record is already approved and locked for audit.'},
            status=status.HTTP_409_CONFLICT,
        )

    bypass = request.data.get('bypass_validation', False)
    notes = (request.data.get('review_notes') or '').strip()

    has_errors = activity.raw_record.validation_issues.filter(severity='ERROR').exists()

    if has_errors and not bypass:
        return Response(
            {'error': 'Record has unresolved validation errors. Enable bypass to override with justification.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if has_errors and bypass and not notes:
        return Response(
            {'error': 'Review notes are mandatory when bypassing validation errors.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    activity.review_status = 'APPROVED'
    activity.validation_bypassed = bypass
    activity.review_notes = notes
    activity.reviewed_at = timezone.now()
    activity.reviewed_by_email = _get_analyst_email(request)
    activity.save(update_fields=[
        'review_status', 'validation_bypassed', 'review_notes',
        'reviewed_at', 'reviewed_by_email',
    ])

    return Response({'status': 'approved', 'id': activity.id})


@api_view(['POST'])
@role_required('ANALYST', 'MANAGER')
def reject_activity(request, pk):
    try:
        activity = NormalizedActivity.objects.get(pk=pk)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Activity not found.'}, status=status.HTTP_404_NOT_FOUND)

    if activity.review_status == 'APPROVED':
        return Response(
            {'error': 'Approved records are immutable and cannot be rejected.'},
            status=status.HTTP_409_CONFLICT,
        )

    notes = (request.data.get('review_notes') or 'Rejected by analyst').strip()
    activity.review_notes = notes
    activity.review_status = 'REJECTED'
    activity.reviewed_at = timezone.now()
    activity.reviewed_by_email = _get_analyst_email(request)
    activity.save(update_fields=['review_notes', 'reviewed_at', 'reviewed_by_email', 'review_status'])

    return Response({'status': 'rejected', 'id': activity.id})

@api_view(['POST'])
@role_required('MANAGER','ANALYST')
def batch_approve_activity(request):
    ids = request.data.get('activity_ids', [])
    if not ids:
        return Response({'error': 'activity_ids list is required.'}, status=status.HTTP_400_BAD_REQUEST)

    activities = NormalizedActivity.objects.filter(
        id__in=ids,
        review_status__in=['PENDING', 'SUSPICIOUS'],
    ).select_related('raw_record')

    # Block batch if any record has unresolved hard errors
    blocked = [
        a.id for a in activities
        if a.raw_record.validation_issues.filter(severity='ERROR').exists()
    ]
    if blocked:
        return Response(
            {'error': f'Records {blocked} have unresolved validation errors. Review individually to bypass.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    reviewer = _get_analyst_email(request)
    count = activities.update(
        review_status='APPROVED',
        reviewed_at=now,
        reviewed_by_email=reviewer,
    )

    return Response({'message': f'{count} records approved and locked for audit.', 'approved': count})


# ── Export ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
def export_approved_activities_csv(request):
    activities = (
        NormalizedActivity.objects
        .filter(review_status='APPROVED')
        .select_related('raw_record__upload')
        .order_by('reporting_period', 'facility_code')
    )

    response = HttpResponse(content_type='text/csv')
    filename = f'breatheesg_approved_emissions_{timezone.now().date()}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Reporting Period', 'Activity Date', 'Scope', 'Scope Category',
        'Activity Type', 'Facility Code', 'Quantity', 'Unit',
        'CO2e (kg)', 'Emission Factor', 'Factor Source',
        'Reviewed By', 'Reviewed At', 'Source File', 'Validation Bypassed',
    ])

    for a in activities:
        writer.writerow([
            a.reporting_period,
            a.activity_date,
            a.scope,
            a.scope_category,
            a.activity_type,
            a.facility_code or 'UNMAPPED',
            a.quantity,
            a.unit,
            a.co2e_kg,
            a.factor_value_used,
            a.emission_factor_source,
            a.reviewed_by_email,
            a.reviewed_at.strftime('%Y-%m-%d %H:%M') if a.reviewed_at else '',
            a.raw_record.upload.filename,
            'YES' if a.validation_bypassed else 'NO',
        ])

    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────



@api_view(['GET'])
def dashboard_trends(request):
    """
    Returns time-series, FY comparison, and distribution data
    for dashboard charts. Uses existing NormalizedActivity data.
    """
    # ── Monthly breakdown by scope ────────────────────────────────
    # Include ALL records (not just approved) for richer trend signal
    scope_rows = (
        NormalizedActivity.objects
        .values('reporting_period', 'scope')
        .annotate(total=Sum('co2e_kg'))
        .order_by('reporting_period')
    )

    months_map: dict = {}
    for row in scope_rows:
        p = row['reporting_period']
        if not p or len(p) != 7:
            continue
        if p not in months_map:
            months_map[p] = {
                'period': p,
                'SCOPE_1': 0.0,
                'SCOPE_2': 0.0,
                'SCOPE_3': 0.0,
                'total': 0.0,
            }
        months_map[p][row['scope']] = round(float(row['total'] or 0), 2)
        months_map[p]['total'] = round(
            months_map[p]['SCOPE_1'] + months_map[p]['SCOPE_2'] + months_map[p]['SCOPE_3'], 2
        )

    sorted_months = sorted(months_map.values(), key=lambda x: x['period'])
    recent_months = sorted_months[-13:]  # Last 13 months max

    # ── Real MoM change (replaces hardcoded 8.2%) ────────────────
    mom_change = None
    if len(sorted_months) >= 2:
        curr = sorted_months[-1]['total']
        prev = sorted_months[-2]['total']
        if prev > 0:
            mom_change = round((curr - prev) / prev * 100, 1)

    # ── FY comparison (calendar year grouping) ───────────────────
    fy_rows = (
        NormalizedActivity.objects
        .values('reporting_period', 'scope')
        .annotate(total=Sum('co2e_kg'))
    )
    fy_map: dict = {}
    for row in fy_rows:
        p = row['reporting_period']
        if not p or len(p) != 7:
            continue
        fy = f"FY{p[:4]}"
        if fy not in fy_map:
            fy_map[fy] = {'fy': fy, 'SCOPE_1': 0.0, 'SCOPE_2': 0.0, 'SCOPE_3': 0.0, 'total': 0.0}
        fy_map[fy][row['scope']] = round(fy_map[fy].get(row['scope'], 0.0) + float(row['total'] or 0), 2)
        fy_map[fy]['total'] = round(
            fy_map[fy]['SCOPE_1'] + fy_map[fy]['SCOPE_2'] + fy_map[fy]['SCOPE_3'], 2
        )
    fy_list = sorted(fy_map.values(), key=lambda x: x['fy'])

    # ── Activity type breakdown ────────────────────────────────────
    act_rows = list(
        NormalizedActivity.objects
        .values('activity_type')
        .annotate(total=Sum('co2e_kg'), count=Count('id'))
        .order_by('-total')[:8]
    )
    for r in act_rows:
        r['total'] = round(float(r['total'] or 0), 2)

    # ── Anomaly distribution ────────────────────────────────────
    anomaly_rows = list(
        NormalizedActivity.objects
        .filter(anomaly_code__isnull=False)
        .exclude(anomaly_code='')
        .values('anomaly_code')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ── Facility monthly trend (top 3 facilities over time) ───────
    top_facility_codes = [
        r['facility_code'] for r in
        NormalizedActivity.objects
        .exclude(facility_code__isnull=True)
        .exclude(facility_code='')
        .values('facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('-total')[:3]
    ]

    facility_monthly = {}
    fac_rows = (
        NormalizedActivity.objects
        .filter(facility_code__in=top_facility_codes)
        .values('reporting_period', 'facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('reporting_period')
    )
    for row in fac_rows:
        p = row['reporting_period']
        if p not in facility_monthly:
            facility_monthly[p] = {'period': p}
        facility_monthly[p][row['facility_code']] = round(float(row['total'] or 0), 2)

    facility_monthly_list = sorted(facility_monthly.values(), key=lambda x: x['period'])

    return Response({
        'monthly': recent_months,
        'fy_comparison': fy_list,
        'mom_change': mom_change,
        'activity_breakdown': act_rows,
        'anomaly_distribution': anomaly_rows,
        'facility_monthly': facility_monthly_list[-12:],
        'top_facility_codes': top_facility_codes,
    })
@api_view(['GET'])
def dashboard_stats(request):
    thirty_days_ago = timezone.now() - timedelta(days=30)

    approved = NormalizedActivity.objects.filter(review_status='APPROVED')
    total_co2e = float(approved.aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0)

    scope_1 = float(
        approved.filter(scope='SCOPE_1').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
    )
    scope_2 = float(
        approved.filter(scope='SCOPE_2').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
    )
    scope_3 = float(
        approved.filter(scope='SCOPE_3').aggregate(Sum('co2e_kg'))['co2e_kg__sum'] or 0
    )

    pending = NormalizedActivity.objects.filter(review_status='PENDING').count()
    suspicious = NormalizedActivity.objects.filter(review_status='SUSPICIOUS').count()

    uploads = RawUpload.objects.filter(uploaded_at__gte=thirty_days_ago)
    total_uploads = uploads.count()
    completed = uploads.filter(status='COMPLETED').count()
    success_rate = round(completed / total_uploads * 100, 1) if total_uploads else 0

    FACILITY_NAMES = {
        'IN01': 'Mumbai Manufacturing Plant',
        'DE02': 'Frankfurt Distribution Center',
        'US03': 'Austin Operations Hub',
        'CN04': 'Shanghai Assembly Facility',
        'BR05': 'São Paulo Warehouse',
        'IN02': 'Bangalore Tech Center',
        'METER_PROTOTYPE_01': 'Smart Meter Prototype Site',
    }

    top_facilities_qs = (
        approved.values('facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('-total')[:5]
    )

    return Response({
        'total_co2e': total_co2e,
        'scope_1': scope_1,
        'scope_2': scope_2,
        'scope_3': scope_3,
        'pending_count': pending,
        'suspicious_count': suspicious,
        'success_rate': success_rate,
        'total_uploads': total_uploads,
        'scopes': {'scope_1': scope_1, 'scope_2': scope_2, 'scope_3': scope_3},
        'top_facilities': [
            {
                'code': f['facility_code'] or 'UNMAPPED',
                'name': FACILITY_NAMES.get(f['facility_code'], 'Unknown Facility'),
                'co2e': float(f['total']),
                'percent': round(float(f['total']) / total_co2e * 100, 1) if total_co2e else 0,
            }
            for f in top_facilities_qs
        ],
        'pipeline': {
            'uploaded': RawUpload.objects.count(),
            'parsed': RawRecord.objects.count(),
            'normalized': NormalizedActivity.objects.count(),
            'pending': pending,
            'approved': approved.count(),
        },
    })

@api_view(['GET'])
def dashboard_trends(request):
    """
    Returns time-series, FY comparison, and distribution data
    for dashboard charts. Uses existing NormalizedActivity data.
    """
    # ── Monthly breakdown by scope ────────────────────────────────
    # Include ALL records (not just approved) for richer trend signal
    scope_rows = (
        NormalizedActivity.objects
        .values('reporting_period', 'scope')
        .annotate(total=Sum('co2e_kg'))
        .order_by('reporting_period')
    )

    months_map: dict = {}
    for row in scope_rows:
        p = row['reporting_period']
        if not p or len(p) != 7:
            continue
        if p not in months_map:
            months_map[p] = {
                'period': p,
                'SCOPE_1': 0.0,
                'SCOPE_2': 0.0,
                'SCOPE_3': 0.0,
                'total': 0.0,
            }
        months_map[p][row['scope']] = round(float(row['total'] or 0), 2)
        months_map[p]['total'] = round(
            months_map[p]['SCOPE_1'] + months_map[p]['SCOPE_2'] + months_map[p]['SCOPE_3'], 2
        )

    sorted_months = sorted(months_map.values(), key=lambda x: x['period'])
    recent_months = sorted_months[-13:]  # Last 13 months max

    # ── Real MoM change (replaces hardcoded 8.2%) ────────────────
    mom_change = None
    if len(sorted_months) >= 2:
        curr = sorted_months[-1]['total']
        prev = sorted_months[-2]['total']
        if prev > 0:
            mom_change = round((curr - prev) / prev * 100, 1)

    # ── FY comparison (calendar year grouping) ───────────────────
    fy_rows = (
        NormalizedActivity.objects
        .values('reporting_period', 'scope')
        .annotate(total=Sum('co2e_kg'))
    )
    fy_map: dict = {}
    for row in fy_rows:
        p = row['reporting_period']
        if not p or len(p) != 7:
            continue
        fy = f"FY{p[:4]}"
        if fy not in fy_map:
            fy_map[fy] = {'fy': fy, 'SCOPE_1': 0.0, 'SCOPE_2': 0.0, 'SCOPE_3': 0.0, 'total': 0.0}
        fy_map[fy][row['scope']] = round(fy_map[fy].get(row['scope'], 0.0) + float(row['total'] or 0), 2)
        fy_map[fy]['total'] = round(
            fy_map[fy]['SCOPE_1'] + fy_map[fy]['SCOPE_2'] + fy_map[fy]['SCOPE_3'], 2
        )
    fy_list = sorted(fy_map.values(), key=lambda x: x['fy'])

    # ── Activity type breakdown ────────────────────────────────────
    act_rows = list(
        NormalizedActivity.objects
        .values('activity_type')
        .annotate(total=Sum('co2e_kg'), count=Count('id'))
        .order_by('-total')[:8]
    )
    for r in act_rows:
        r['total'] = round(float(r['total'] or 0), 2)

    # ── Anomaly distribution ────────────────────────────────────
    anomaly_rows = list(
        NormalizedActivity.objects
        .filter(anomaly_code__isnull=False)
        .exclude(anomaly_code='')
        .values('anomaly_code')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ── Facility monthly trend (top 3 facilities over time) ───────
    top_facility_codes = [
        r['facility_code'] for r in
        NormalizedActivity.objects
        .exclude(facility_code__isnull=True)
        .exclude(facility_code='')
        .values('facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('-total')[:3]
    ]

    facility_monthly = {}
    fac_rows = (
        NormalizedActivity.objects
        .filter(facility_code__in=top_facility_codes)
        .values('reporting_period', 'facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('reporting_period')
    )
    for row in fac_rows:
        p = row['reporting_period']
        if p not in facility_monthly:
            facility_monthly[p] = {'period': p}
        facility_monthly[p][row['facility_code']] = round(float(row['total'] or 0), 2)

    facility_monthly_list = sorted(facility_monthly.values(), key=lambda x: x['period'])

    return Response({
        'monthly': recent_months,
        'fy_comparison': fy_list,
        'mom_change': mom_change,
        'activity_breakdown': act_rows,
        'anomaly_distribution': anomaly_rows,
        'facility_monthly': facility_monthly_list[-12:],
        'top_facility_codes': top_facility_codes,
    })

@api_view(['POST'])
def generate_dataset(request):
    """
    Wraps existing generator scripts to produce downloadable datasets.
    Parameters: source_type, row_count, anomaly_rate, facilities
    """
    source_type = request.data.get('source_type', 'SAP')
    row_count = min(int(request.data.get('row_count', 100)), 2000)  # Cap at 2k
    anomaly_rate = max(0, min(float(request.data.get('anomaly_rate', 0.05)), 0.5))
    preset = request.data.get('preset', 'custom')

    # Map source type to generator script path
    GENERATOR_MAP = {
        'SAP': 'scripts/generators/sap/generate_procurement.py',
        'SAP_FUEL': 'scripts/generators/sap/generate_fuel_procurement.py',
        'UTILITY_BILL': 'scripts/generators/utility/generate_monthly_bills.py',
        'UTILITY_METER': 'scripts/generators/utility/generate_smart_meter.py',
        'TRAVEL': 'scripts/generators/travel/generate_concur_exports.py',
    }

    script_path = GENERATOR_MAP.get(source_type)
    if not script_path:
        return Response({'error': f'Unknown source type: {source_type}'}, status=400)

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_script = os.path.join(backend_root, script_path)

    if not os.path.exists(full_script):
        # Graceful fallback: return sample data
        return Response({'error': f'Generator script not found: {script_path}'}, status=404)

    # Run generator with parameters (scripts need to accept CLI args)
    try:
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name

        result = subprocess.run(
            ['python', full_script, '--rows', str(row_count), '--anomaly-rate', str(anomaly_rate), '--output', tmp_path],
            capture_output=True, text=True, timeout=30,
            cwd=backend_root,
        )

        if result.returncode != 0:
            return Response({'error': result.stderr[:500]}, status=500)

        if os.path.exists(tmp_path):
            response = FileResponse(
                open(tmp_path, 'rb'),
                content_type='text/csv',
                as_attachment=True,
                filename=f'{source_type.lower()}_{row_count}rows_{int(anomaly_rate * 100)}pct_anomalies.csv',
            )
            return response
        return Response({'error': 'Generator produced no output'}, status=500)

    except subprocess.TimeoutExpired:
        return Response({'error': 'Generation timed out'}, status=500)
    except Exception as e:
        return Response({'error': str(e)[:500]}, status=500)
