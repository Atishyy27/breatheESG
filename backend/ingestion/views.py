import hashlib
import csv
import json
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import RawUpload, RawRecord, NormalizedActivity
from .processors import execute_ingestion_pipeline

@api_view(['POST'])
def upload_file_endpoint(request):
    """Accepts data uploads, extracts raw structures, and executes the processing pipeline."""
    uploaded_file = request.FILES.get('file')
    source_type = request.data.get('source_type')

    if not uploaded_file or not source_type:
        return Response(
            {"error": "Missing file payload or source type specification."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    file_bytes = uploaded_file.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    existing_upload = RawUpload.objects.filter(file_hash=file_hash).first()
    if existing_upload:
        if existing_upload.status == 'FAILED':
            existing_upload.delete()
        else:
            return Response({
                "error": "This file batch has already been uploaded.",
                "upload_id": existing_upload.id,
                "status": existing_upload.status
            }, status=status.HTTP_400_BAD_REQUEST)

    try:
        file_content = file_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        return Response(
            {"error": "Invalid encoding format. Please upload files saved in standard UTF-8."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    upload_ledger = RawUpload.objects.create(
        filename=uploaded_file.name,
        source_type=source_type,
        file_hash=file_hash,
        status='PROCESSING'
    )

    records_to_create = []
    row_count = 0

    try:
        if source_type in ['SAP', 'UTILITY_BILL', 'UTILITY_METER']:
            reader = csv.DictReader(file_content.splitlines())
            for idx, row in enumerate(reader, start=1):
                row_count += 1
                records_to_create.append(RawRecord(
                    upload=upload_ledger, line_number=idx, raw_data=dict(row)
                ))
                
        elif source_type == 'TRAVEL':
            json_array = json.loads(file_content)
            if not isinstance(json_array, list):
                raise ValueError("JSON payload formatting must contain an outer array structure.")
            for idx, item in enumerate(json_array, start=1):
                row_count += 1
                records_to_create.append(RawRecord(
                    upload=upload_ledger, line_number=idx, raw_data=item
                ))

        if row_count == 0:
            raise ValueError("The provided data asset contains no readable records.")

        RawRecord.objects.bulk_create(records_to_create)
        upload_ledger.total_rows = row_count
        
        # Run calculation engine and validation constraints
        execute_ingestion_pipeline(upload_ledger)

        return Response({
            "message": "Data stream successfully parsed and normalized.",
            "upload_details": {
                "id": upload_ledger.id,
                "total_records": upload_ledger.total_rows,
                "successfully_normalized": upload_ledger.normalized_rows,
                "validation_errors_found": upload_ledger.error_rows,
                "anomalies_flagged": upload_ledger.suspicious_rows
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        upload_ledger.status = 'FAILED'
        upload_ledger.processing_error = str(e)
        upload_ledger.save()
        return Response(
            {"error": f"Pipeline execution halted: {str(e)}"}, 
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

@api_view(['GET'])
def review_queue_list(request):
    """Lists all active records requiring analyst verification (PENDING or SUSPICIOUS) with inline validation context."""
    activities = NormalizedActivity.objects.filter(
        review_status__in=['PENDING', 'SUSPICIOUS']
    ).select_related('raw_record__upload').prefetch_related('raw_record__validation_issues').order_by('-created_at')
    
    data = []
    for act in activities:
        # Grab inline validation issues to display directly on the dashboard
        inline_issues = [issue.message for issue in act.raw_record.validation_issues.all()[:2]]
        
        data.append({
            "id": act.id,
            "source_type": act.raw_record.upload.source_type,
            "activity_type": act.activity_type,
            "activity_date": str(act.activity_date),
            "reporting_period": act.reporting_period,
            "facility_code": act.facility_code,
            "quantity": float(act.quantity) if act.quantity else None,
            "unit": act.unit,
            "co2e_kg": float(act.co2e_kg),
            "review_status": act.review_status,
            "anomaly_code": act.anomaly_code,
            "inline_issues": inline_issues  # Added for Task 5
        })
    
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
def review_queue_detail(request, pk):
    """Surfaces a side-by-side view matching a normalized row directly to its unparsed origin line."""
    act = get_object_or_404(NormalizedActivity.objects.select_related('raw_record'), id=pk)
    issues = act.raw_record.validation_issues.all()
    
    data = {
        "id": act.id,
        "scope": act.scope,
        "scope_category": act.scope_category,
        "activity_type": act.activity_type,
        "activity_date": str(act.activity_date),
        "reporting_period": act.reporting_period,
        "facility_code": act.facility_code,
        "quantity": float(act.quantity) if act.quantity else None,
        "unit": act.unit,
        "factor_value_used": float(act.factor_value_used),
        "emission_factor_source": act.emission_factor_source,
        "co2e_kg": float(act.co2e_kg),
        "review_status": act.review_status,
        "anomaly_code": act.anomaly_code,
        "anomaly_details": act.anomaly_details,
        "source_metadata": act.source_metadata,
        "raw_line_number": act.raw_record.line_number,
        "raw_record_data": act.raw_record.raw_data,
        "validation_issues": [{
            "severity": issue.severity,
            "issue_type": issue.issue_type,
            "message": issue.message
        } for issue in issues]
    }
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
def approve_activity(request, pk):
    """Approves a record. Enforces an informative review note if validation errors are active."""
    act = get_object_or_404(NormalizedActivity, id=pk)
    
    if act.review_status == 'APPROVED':
        return Response({"error": "This transaction sequence is already approved."}, status=status.HTTP_400_BAD_REQUEST)
        
    bypass_validation = request.data.get('bypass_validation', False)
    review_notes = request.data.get('review_notes', '').strip()
    
    has_errors = act.raw_record.validation_issues.filter(severity='ERROR').exists()
    
    if has_errors and not bypass_validation:
        return Response({
            "error": "Cannot approve row containing active validation errors without enabling override bypass check."
        }, status=status.HTTP_400_BAD_REQUEST)
        
    if has_errors and bypass_validation and not review_notes:
        return Response({
            "error": "Auditor Compliance Rule: Review notes must explain the reason for bypassing validation errors."
        }, status=status.HTTP_400_BAD_REQUEST)

    act.review_status = 'APPROVED'
    act.validation_bypassed = bypass_validation
    act.review_notes = review_notes
    act.reviewed_at = timezone.now()
    act.reviewed_by_email = request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')
    act.save()
    
    return Response({"message": "Transaction verified and approved successfully."}, status=status.HTTP_200_OK)

@api_view(['POST'])
def reject_activity(request, pk):
    """Removes a row from the active analyst review queue by updating its status to REJECTED."""
    act = get_object_or_404(NormalizedActivity, id=pk)
    
    if act.review_status == 'APPROVED':
        return Response({"error": "Approved records are sealed and cannot be rejected."}, status=status.HTTP_400_BAD_REQUEST)
        
    act.review_status = 'REJECTED'
    act.reviewed_at = timezone.now()
    act.save(update_fields=['review_status', 'reviewed_at'])
    
    return Response({"message": "Transaction successfully archived from active queue view."}, status=status.HTTP_200_OK)

@api_view(['GET'])
def upload_list(request):
    """Feeds the main upload dashboard with processing histories."""
    uploads = RawUpload.objects.all().order_by('-uploaded_at')
    data = [{
        "id": u.id,
        "filename": u.filename,
        "source_type": u.source_type,
        "status": u.status,
        "total_rows": u.total_rows,
        "normalized_rows": u.normalized_rows,
        "error_rows": u.error_rows,
        "suspicious_rows": u.suspicious_rows,
        "uploaded_at": u.uploaded_at.strftime('%b %d, %H:%M'),
        "uploaded_by": u.uploaded_by_email
    } for u in uploads]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
def batch_approve_activity(request):
    """Approves multiple clean rows instantly for operational velocity."""
    activity_ids = request.data.get('activity_ids', [])
    if not activity_ids:
        return Response({"error": "No activities selected for batch approval."}, status=status.HTTP_400_BAD_REQUEST)
        
    activities = NormalizedActivity.objects.filter(id__in=activity_ids, review_status__in=['PENDING', 'SUSPICIOUS'])
    
    # Block batch approval if any selected rows have active errors
    for act in activities:
        if act.raw_record.validation_issues.filter(severity='ERROR').exists():
            return Response({
                "error": f"Batch halted. Row ID {act.id} contains active validation errors. Please review individually with a bypass note."
            }, status=status.HTTP_400_BAD_REQUEST)
            
    activities.update(
        review_status='APPROVED',
        reviewed_at=timezone.now(),
        reviewed_by_email=request.META.get('HTTP_X_ANALYST_EMAIL', 'analyst@breatheesg.com')
    )
    
    return Response({"message": f"{len(activity_ids)} transactions successfully approved."}, status=status.HTTP_200_OK)

@api_view(['GET'])
def export_approved_activities_csv(request):
    """Generates a downloadable clean CSV ledger of all approved activities for compliance auditors."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="approved_emissions_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Reporting Period', 'Activity Type', 'Scope', 'Quantity', 'Unit', 'CO2e (kg)', 'Verified By', 'Notes'])
    
    approved_records = NormalizedActivity.objects.filter(review_status='APPROVED').order_by('-activity_date')
    for act in approved_records:
        writer.writerow([
            act.reporting_period,
            act.activity_type,
            act.scope,
            act.quantity,
            act.unit,
            act.co2e_kg,
            act.reviewed_by_email,
            act.review_notes or ''
        ])
    return response

    