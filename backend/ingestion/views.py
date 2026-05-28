import csv
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
from .processors import process_upload


# ─── Health Check ───────────────────────────────────────────

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})


# ─── Upload Pipeline ────────────────────────────────────────

@api_view(['POST'])
def upload_file(request):
    file = request.FILES.get('file')
    source_type = request.data.get('source_type')

    if not file or not source_type:
        return Response(
            {'error': 'file and source_type are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Duplicate detection via MD5
    file_content = file.read()
    file_hash = hashlib.md5(file_content).hexdigest()
    file.seek(0)

    if RawUpload.objects.filter(file_hash=file_hash).exists():
        return Response(
            {'error': 'Duplicate upload detected. This file has already been ingested.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    upload = RawUpload.objects.create(
        source_type=source_type,
        filename=file.name,
        file_hash=file_hash,
        uploaded_by_email=request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com'),
        status='PROCESSING',
    )

    try:
        result = process_upload(upload, file_content)
        upload.status = 'COMPLETED'
        upload.save()

        return Response({
            'upload_id': upload.id,
            'status': 'completed',
            'upload_details': {
                'total_records': result.get('total', 0),
                'successfully_normalized': result.get('normalized', 0),
                'validation_errors_found': result.get('errors', 0),
                'suspicious_flagged': result.get('suspicious', 0),
            },
        })
    except Exception as e:
        upload.status = 'FAILED'
        upload.processing_error = str(e)[:500]
        upload.save()
        return Response(
            {'error': f'Pipeline failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def list_uploads(request):
    uploads = RawUpload.objects.order_by('-uploaded_at')[:50]
    return Response(UploadSummarySerializer(uploads, many=True).data)


# ─── Review Queue ────────────────────────────────────────────

@api_view(['GET'])
def review_queue(request):
    activities = NormalizedActivity.objects.filter(
        review_status__in=['PENDING', 'SUSPICIOUS']
    ).select_related('raw_record__upload').order_by('-created_at')

    return Response(QueueItemSerializer(activities, many=True).data)


@api_view(['GET'])
def activity_detail(request, pk):
    try:
        activity = NormalizedActivity.objects.select_related(
            'raw_record__upload'
        ).prefetch_related(
            'raw_record__validation_issues'
        ).get(pk=pk)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(ActivityDetailSerializer(activity).data)


@api_view(['POST'])
def approve_activity(request, pk):
    try:
        activity = NormalizedActivity.objects.get(pk=pk)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if activity.review_status == 'APPROVED':
        return Response(
            {'error': 'Record is already approved and locked'},
            status=status.HTTP_409_CONFLICT,
        )

    bypass = request.data.get('bypass_validation', False)
    notes = request.data.get('review_notes', '').strip()

    # If errors exist and bypass requested, notes are mandatory
    has_errors = activity.raw_record.validation_issues.filter(severity='ERROR').exists()
    if has_errors and bypass and not notes:
        return Response(
            {'error': 'Review notes are required when bypassing validation errors'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if has_errors and not bypass:
        return Response(
            {'error': 'Record has unresolved validation errors. Check bypass to override.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    activity.review_status = 'APPROVED'
    activity.validation_bypassed = bypass
    activity.review_notes = notes
    activity.reviewed_at = timezone.now()
    activity.reviewed_by_email = request.META.get(
        'HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com'
    )
    activity.save()

    return Response({'status': 'approved', 'id': activity.id})


@api_view(['POST'])
def reject_activity(request, pk):
    try:
        activity = NormalizedActivity.objects.get(pk=pk)
    except NormalizedActivity.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if activity.review_status == 'APPROVED':
        return Response(
            {'error': 'Approved records cannot be rejected'},
            status=status.HTTP_409_CONFLICT,
        )

    activity.review_status = 'REJECTED'
    activity.reviewed_at = timezone.now()
    activity.reviewed_by_email = request.META.get(
        'HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com'
    )
    activity.save()

    return Response({'status': 'rejected', 'id': activity.id})


@api_view(['POST'])
def batch_approve(request):
    ids = request.data.get('activity_ids', [])
    if not ids:
        return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

    activities = NormalizedActivity.objects.filter(
        id__in=ids,
        review_status__in=['PENDING', 'SUSPICIOUS'],
    ).select_related('raw_record')

    # Block entire batch if any have unresolved hard errors without bypass
    blocked = []
    for a in activities:
        has_errors = a.raw_record.validation_issues.filter(severity='ERROR').exists()
        if has_errors:
            blocked.append(a.id)

    if blocked:
        return Response(
            {'error': f'Records {blocked} have unresolved errors. Review individually to bypass.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    reviewer = request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')

    count = activities.update(
        review_status='APPROVED',
        reviewed_at=now,
        reviewed_by_email=reviewer,
    )

    return Response({'message': f'{count} records approved successfully', 'approved': count})


# ─── Export ─────────────────────────────────────────────────

@api_view(['GET'])
def export_approved(request):
    activities = NormalizedActivity.objects.filter(
        review_status='APPROVED'
    ).select_related('raw_record__upload').order_by('reporting_period')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="approved_emissions_{timezone.now().date()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Reporting Period', 'Scope', 'Activity Type', 'Facility Code',
        'Quantity', 'Unit', 'CO2e (kg)', 'Emission Factor', 'Factor Source',
        'Reviewed By', 'Reviewed At', 'Source File',
    ])

    for a in activities:
        writer.writerow([
            a.reporting_period,
            a.scope,
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
        ])

    return response


# ─── Dashboard ──────────────────────────────────────────────

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
    success_rate = (
        uploads.filter(status='COMPLETED').count() / total_uploads * 100
        if total_uploads > 0
        else 0
    )

    FACILITY_NAMES = {
        'IN01': 'Mumbai Manufacturing Plant',
        'DE02': 'Frankfurt Distribution Center',
        'US03': 'Austin Operations Hub',
        'CN04': 'Shanghai Assembly Facility',
        'BR05': 'São Paulo Warehouse',
        'IN02': 'Bangalore Tech Center',
    }

    top_facilities = list(
        approved.values('facility_code')
        .annotate(total=Sum('co2e_kg'))
        .order_by('-total')[:5]
    )

    pipeline = {
        'uploaded': RawUpload.objects.count(),
        'parsed': RawRecord.objects.count(),
        'normalized': NormalizedActivity.objects.count(),
        'pending': pending,
        'approved': approved.count(),
    }

    return Response({
        'total_co2e': total_co2e,
        'scope_1': scope_1,
        'scope_2': scope_2,
        'scope_3': scope_3,
        'pending_count': pending,
        'suspicious_count': suspicious,
        'success_rate': round(success_rate, 1),
        'total_uploads': total_uploads,
        'pipeline': pipeline,
        'scopes': {
            'scope_1': scope_1,
            'scope_2': scope_2,
            'scope_3': scope_3,
        },
        'top_facilities': [
            {
                'code': f['facility_code'] or 'UNMAPPED',
                'name': FACILITY_NAMES.get(f['facility_code'], 'Unknown Facility'),
                'co2e': float(f['total']),
                'percent': round(f['total'] / total_co2e * 100, 1) if total_co2e else 0,
            }
            for f in top_facilities
        ],
    })
# import hashlib
# import csv
# import json
# from django.http import HttpResponse
# from django.utils import timezone
# from django.shortcuts import get_object_or_404
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework import status

# from .models import RawUpload, RawRecord, NormalizedActivity
# from .processors import execute_ingestion_pipeline

# @api_view(['POST'])
# def upload_file_endpoint(request):
#     """Accepts data uploads, extracts raw structures, and executes the processing pipeline."""
#     uploaded_file = request.FILES.get('file')
#     source_type = request.data.get('source_type')

#     if not uploaded_file or not source_type:
#         return Response(
#             {"error": "Missing file payload or source type specification."}, 
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     file_bytes = uploaded_file.read()
#     file_hash = hashlib.md5(file_bytes).hexdigest()

#     existing_upload = RawUpload.objects.filter(file_hash=file_hash).first()
#     if existing_upload:
#         if existing_upload.status == 'FAILED':
#             existing_upload.delete()
#         else:
#             return Response({
#                 "error": "This file batch has already been uploaded.",
#                 "upload_id": existing_upload.id,
#                 "status": existing_upload.status
#             }, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         file_content = file_bytes.decode('utf-8-sig')
#     except UnicodeDecodeError:
#         return Response(
#             {"error": "Invalid encoding format. Please upload files saved in standard UTF-8."}, 
#             status=status.HTTP_400_BAD_REQUEST
#         )
        
#     upload_ledger = RawUpload.objects.create(
#         filename=uploaded_file.name,
#         source_type=source_type,
#         file_hash=file_hash,
#         status='PROCESSING'
#     )

#     records_to_create = []
#     row_count = 0

#     try:
#         if source_type in ['SAP', 'UTILITY_BILL', 'UTILITY_METER']:
#             reader = csv.DictReader(file_content.splitlines())
#             for idx, row in enumerate(reader, start=1):
#                 row_count += 1
#                 records_to_create.append(RawRecord(
#                     upload=upload_ledger, line_number=idx, raw_data=dict(row)
#                 ))
                
#         elif source_type == 'TRAVEL':
#             json_array = json.loads(file_content)
#             if not isinstance(json_array, list):
#                 raise ValueError("JSON payload formatting must contain an outer array structure.")
#             for idx, item in enumerate(json_array, start=1):
#                 row_count += 1
#                 records_to_create.append(RawRecord(
#                     upload=upload_ledger, line_number=idx, raw_data=item
#                 ))

#         if row_count == 0:
#             raise ValueError("The provided data asset contains no readable records.")

#         RawRecord.objects.bulk_create(records_to_create)
#         upload_ledger.total_rows = row_count
        
#         # Run calculation engine and validation constraints
#         execute_ingestion_pipeline(upload_ledger)

#         return Response({
#             "message": "Data stream successfully parsed and normalized.",
#             "upload_details": {
#                 "id": upload_ledger.id,
#                 "total_records": upload_ledger.total_rows,
#                 "successfully_normalized": upload_ledger.normalized_rows,
#                 "validation_errors_found": upload_ledger.error_rows,
#                 "anomalies_flagged": upload_ledger.suspicious_rows
#             }
#         }, status=status.HTTP_201_CREATED)

#     except Exception as e:
#         upload_ledger.status = 'FAILED'
#         upload_ledger.processing_error = str(e)
#         upload_ledger.save()
#         return Response(
#             {"error": f"Pipeline execution halted: {str(e)}"}, 
#             status=status.HTTP_422_UNPROCESSABLE_ENTITY
#         )

# @api_view(['GET'])
# def review_queue_list(request):
#     """Lists all active records requiring analyst verification (PENDING or SUSPICIOUS) with inline validation context."""
#     activities = NormalizedActivity.objects.filter(
#         review_status__in=['PENDING', 'SUSPICIOUS']
#     ).select_related('raw_record__upload').prefetch_related('raw_record__validation_issues').order_by('-created_at')
    
#     data = []
#     for act in activities:
#         # Grab inline validation issues to display directly on the dashboard
#         inline_issues = [issue.message for issue in act.raw_record.validation_issues.all()[:2]]
        
#         data.append({
#             "id": act.id,
#             "source_type": act.raw_record.upload.source_type,
#             "activity_type": act.activity_type,
#             "activity_date": str(act.activity_date),
#             "reporting_period": act.reporting_period,
#             "facility_code": act.facility_code,
#             "quantity": float(act.quantity) if act.quantity else None,
#             "unit": act.unit,
#             "co2e_kg": float(act.co2e_kg),
#             "review_status": act.review_status,
#             "anomaly_code": act.anomaly_code,
#             "inline_issues": inline_issues  # Added for Task 5
#         })
    
#     return Response(data, status=status.HTTP_200_OK)

# @api_view(['GET'])
# def review_queue_detail(request, pk):
#     """Surfaces a side-by-side view matching a normalized row directly to its unparsed origin line."""
#     act = get_object_or_404(NormalizedActivity.objects.select_related('raw_record'), id=pk)
#     issues = act.raw_record.validation_issues.all()
    
#     data = {
#         "id": act.id,
#         "scope": act.scope,
#         "scope_category": act.scope_category,
#         "activity_type": act.activity_type,
#         "activity_date": str(act.activity_date),
#         "reporting_period": act.reporting_period,
#         "facility_code": act.facility_code,
#         "quantity": float(act.quantity) if act.quantity else None,
#         "unit": act.unit,
#         "factor_value_used": float(act.factor_value_used),
#         "emission_factor_source": act.emission_factor_source,
#         "co2e_kg": float(act.co2e_kg),
#         "review_status": act.review_status,
#         "anomaly_code": act.anomaly_code,
#         "anomaly_details": act.anomaly_details,
#         "source_metadata": act.source_metadata,
#         "raw_line_number": act.raw_record.line_number,
#         "raw_record_data": act.raw_record.raw_data,
#         "validation_issues": [{
#             "severity": issue.severity,
#             "issue_type": issue.issue_type,
#             "message": issue.message
#         } for issue in issues]
#     }
#     return Response(data, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def approve_activity(request, pk):
#     """Approves a record. Enforces an informative review note if validation errors are active."""
#     act = get_object_or_404(NormalizedActivity, id=pk)
    
#     if act.review_status == 'APPROVED':
#         return Response({"error": "This transaction sequence is already approved."}, status=status.HTTP_400_BAD_REQUEST)
        
#     bypass_validation = request.data.get('bypass_validation', False)
#     review_notes = request.data.get('review_notes', '').strip()
    
#     has_errors = act.raw_record.validation_issues.filter(severity='ERROR').exists()
    
#     if has_errors and not bypass_validation:
#         return Response({
#             "error": "Cannot approve row containing active validation errors without enabling override bypass check."
#         }, status=status.HTTP_400_BAD_REQUEST)
        
#     if has_errors and bypass_validation and not review_notes:
#         return Response({
#             "error": "Auditor Compliance Rule: Review notes must explain the reason for bypassing validation errors."
#         }, status=status.HTTP_400_BAD_REQUEST)

#     act.review_status = 'APPROVED'
#     act.validation_bypassed = bypass_validation
#     act.review_notes = review_notes
#     act.reviewed_at = timezone.now()
#     act.reviewed_by_email = request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')
#     act.save()
    
#     return Response({"message": "Transaction verified and approved successfully."}, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def reject_activity(request, pk):
#     """Removes a row from the active analyst review queue by updating its status to REJECTED."""
#     act = get_object_or_404(NormalizedActivity, id=pk)
    
#     if act.review_status == 'APPROVED':
#         return Response({"error": "Approved records are sealed and cannot be rejected."}, status=status.HTTP_400_BAD_REQUEST)
        
#     act.review_status = 'REJECTED'
#     act.reviewed_at = timezone.now()
#     act.save(update_fields=['review_status', 'reviewed_at'])
    
#     return Response({"message": "Transaction successfully archived from active queue view."}, status=status.HTTP_200_OK)

# @api_view(['GET'])
# def upload_list(request):
#     """Feeds the main upload dashboard with processing histories."""
#     uploads = RawUpload.objects.all().order_by('-uploaded_at')
#     data = [{
#         "id": u.id,
#         "filename": u.filename,
#         "source_type": u.source_type,
#         "status": u.status,
#         "total_rows": u.total_rows,
#         "normalized_rows": u.normalized_rows,
#         "error_rows": u.error_rows,
#         "suspicious_rows": u.suspicious_rows,
#         "uploaded_at": u.uploaded_at.strftime('%b %d, %H:%M'),
#         "uploaded_by": u.uploaded_by_email
#     } for u in uploads]
#     return Response(data, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def batch_approve_activity(request):
#     """Approves multiple clean rows instantly for operational velocity."""
#     activity_ids = request.data.get('activity_ids', [])
#     if not activity_ids:
#         return Response({"error": "No activities selected for batch approval."}, status=status.HTTP_400_BAD_REQUEST)
        
#     activities = NormalizedActivity.objects.filter(id__in=activity_ids, review_status__in=['PENDING', 'SUSPICIOUS'])
    
#     # Block batch approval if any selected rows have active errors
#     for act in activities:
#         if act.raw_record.validation_issues.filter(severity='ERROR').exists():
#             return Response({
#                 "error": f"Batch halted. Row ID {act.id} contains active validation errors. Please review individually with a bypass note."
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#     activities.update(
#         review_status='APPROVED',
#         reviewed_at=timezone.now(),
#         reviewed_by_email=request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')
#     )
    
#     return Response({"message": f"{len(activity_ids)} transactions successfully approved."}, status=status.HTTP_200_OK)

# @api_view(['GET'])
# def export_approved_activities_csv(request):
#     """Generates a downloadable clean CSV ledger of all approved activities for compliance auditors."""
#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="approved_emissions_report.csv"'
    
#     writer = csv.writer(response)
#     writer.writerow(['Reporting Period', 'Activity Type', 'Scope', 'Quantity', 'Unit', 'CO2e (kg)', 'Verified By', 'Notes'])
    
#     approved_records = NormalizedActivity.objects.filter(review_status='APPROVED').order_by('-activity_date')
#     for act in approved_records:
#         writer.writerow([
#             act.reporting_period,
#             act.activity_type,
#             act.scope,
#             act.quantity,
#             act.unit,
#             act.co2e_kg,
#             act.reviewed_by_email,
#             act.review_notes or ''
#         ])
#     return response

    