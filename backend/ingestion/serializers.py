from rest_framework import serializers
from .models import RawUpload, RawRecord, NormalizedActivity, ValidationIssue


class ValidationIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationIssue
        fields = ['severity', 'issue_type', 'message']


class UploadSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RawUpload
        fields = [
            'id', 'filename', 'source_type', 'status',
            'total_rows', 'normalized_rows', 'error_rows',
            'warning_rows', 'suspicious_rows', 'uploaded_at',
            'uploaded_by_email', 'processing_error',
        ]


class QueueItemSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the review queue list view."""
    source_type = serializers.SerializerMethodField()
    anomaly_details = serializers.CharField(allow_null=True)
    inline_issues = serializers.SerializerMethodField()

    class Meta:
        model = NormalizedActivity
        fields = [
            'id', 'source_type', 'activity_type', 'activity_date',
            'reporting_period', 'facility_code', 'quantity', 'unit',
            'co2e_kg', 'review_status', 'anomaly_code', 'anomaly_details',
            'inline_issues', 'created_at',
        ]

    def get_source_type(self, obj):
        return obj.raw_record.upload.source_type

    def get_inline_issues(self, obj):
        errors = obj.raw_record.validation_issues.filter(severity='ERROR')
        return [e.message for e in errors]


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Full serializer for the forensic detail modal."""
    raw_record_data = serializers.SerializerMethodField()
    raw_line_number = serializers.SerializerMethodField()
    validation_issues = serializers.SerializerMethodField()
    source_type = serializers.SerializerMethodField()

    class Meta:
        model = NormalizedActivity
        fields = [
            'id', 'source_type', 'scope', 'scope_category',
            'activity_type', 'activity_date', 'reporting_period',
            'facility_code', 'country_code', 'quantity', 'unit',
            'factor_value_used', 'emission_factor_source', 'co2e_kg',
            'review_status', 'anomaly_code', 'anomaly_details',
            'validation_bypassed', 'review_notes', 'reviewed_at',
            'reviewed_by_email', 'source_metadata', 'created_at',
            'raw_record_data', 'raw_line_number', 'validation_issues',
        ]

    def get_raw_record_data(self, obj):
        return obj.raw_record.raw_data

    def get_raw_line_number(self, obj):
        return obj.raw_record.line_number

    def get_validation_issues(self, obj):
        return ValidationIssueSerializer(
            obj.raw_record.validation_issues.all(), many=True
        ).data

    def get_source_type(self, obj):
        return obj.raw_record.upload.source_type