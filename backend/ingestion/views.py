import csv
import io
import json
import hashlib
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
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


def _parse_file_to_rows(file_content: bytes, source_type: str) -> list:
    """
    Converts raw file bytes to a list of row dicts.
    CSV sources: SAP, UTILITY_BILL, UTILITY_METER
    JSON source: TRAVEL
    """
    if source_type == 'TRAVEL':
        decoded = file_content.decode('utf-8')
        data = json.loads(decoded)
        return data if isinstance(data, list) else [data]

    # CSV sources — handle BOM from Excel exports
    decoded = file_content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    rows = []
    for row in reader:
        # Strip whitespace from all keys and values
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})
    return rows


# ── Health check ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'service': 'BreatheESG Ingestion API'})


# ── Upload pipeline ───────────────────────────────────────────────────────────

@api_view(['POST'])
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


# ── Review queue ─────────────────────────────────────────────────────────────

@api_view(['GET'])
def review_queue_list(request):
    activities = (
        NormalizedActivity.objects
        .filter(review_status__in=['PENDING', 'SUSPICIOUS'])
        .select_related('raw_record__upload')
        .prefetch_related('raw_record__validation_issues')
        .order_by('-created_at')
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

    # Store as PENDING with a rejection note rather than a new status
    # (model doesn't have REJECTED choice — keeping data clean)
    notes = (request.data.get('review_notes') or 'Rejected by analyst').strip()
    activity.review_notes = f'[REJECTED] {notes}'
    activity.reviewed_at = timezone.now()
    activity.reviewed_by_email = _get_analyst_email(request)
    # Remove from active queue without altering status enum
    activity.review_status = 'PENDING'
    activity.save(update_fields=['review_notes', 'reviewed_at', 'reviewed_by_email', 'review_status'])

    # Hide from queue by marking raw_record
    activity.raw_record.has_error = True
    activity.raw_record.save(update_fields=['has_error'])

    return Response({'status': 'rejected', 'id': activity.id})


@api_view(['POST'])
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