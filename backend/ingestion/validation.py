from decimal import Decimal, InvalidOperation
from .models import ValidationIssue

def validate_raw_record(raw_record):
    """
    Validates structural and semantic rules per source type.
    Returns True if row contains no blocking errors, False otherwise.
    """
    source_type = raw_record.upload.source_type
    data = raw_record.raw_data
    issues = []

    # Helper to check missing fields
    def check_required(field_name):
        if field_name not in data or str(data[field_name]).strip() == "":
            issues.append(ValidationIssue(
                raw_record=raw_record,
                severity='ERROR',
                issue_type='MISSING_FIELD',
                message=f"Required field '{field_name}' is missing or empty."
            ))
            return False
        return True

    if source_type == 'SAP':
        if check_required('MENGE') and check_required('MATNR') and check_required('BUDAT'):
            try:
                qty = Decimal(str(data['MENGE']))
                if qty < 0:
                    issues.append(ValidationIssue(
                        raw_record=raw_record,
                        severity='ERROR',
                        issue_type='NEGATIVE_VALUE',
                        message="SAP transaction quantity cannot be negative."
                    ))
            except (ValueError, InvalidOperation):
                issues.append(ValidationIssue(
                    raw_record=raw_record,
                    severity='ERROR',
                    issue_type='INVALID_NUMBER',
                    message=f"Could not parse quantity '{data['MENGE']}' as a valid number."
                ))

    elif source_type == 'UTILITY_BILL':
        required_fields = ['billing_start', 'billing_end', 'consumption_kwh']
        valid = True
        for f in required_fields:
            if not check_required(f):
                valid = False
        
        if valid:
            try:
                cons = Decimal(str(data['consumption_kwh']))
                if cons < 0:
                    issues.append(ValidationIssue(
                        raw_record=raw_record,
                        severity='ERROR',
                        issue_type='NEGATIVE_CONSUMPTION',
                        message="Utility bill consumption cannot be negative."
                    ))
            except (ValueError, InvalidOperation):
                issues.append(ValidationIssue(
                    raw_record=raw_record,
                    severity='ERROR',
                    issue_type='INVALID_NUMBER',
                    message=f"Could not parse consumption '{data['consumption_kwh']}' as a number."
                ))

            if not data.get('plant_ref') or str(data['plant_ref']).strip() == "":
                issues.append(ValidationIssue(
                    raw_record=raw_record,
                    severity='WARNING',
                    issue_type='MISSING_FACILITY',
                    message="Utility bill missing facility reference ('plant_ref')."
                ))

    elif source_type == 'TRAVEL':
        required_fields = ['origin', 'destination', 'booking_class', 'transaction_date']
        for f in required_fields:
            check_required(f)

    # Save all discovered issues to DB
    if issues:
        ValidationIssue.objects.bulk_create(issues)
        
    # Check if any created issue is a blocking ERROR
    has_blocking_error = any(issue.severity == 'ERROR' for issue in issues)
    if has_blocking_error:
        raw_record.has_error = True
        raw_record.save(update_fields=['has_error'])
        
    return not has_blocking_error