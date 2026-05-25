from django.contrib import admin
from .models import RawUpload, RawRecord, NormalizedActivity, ValidationIssue, EmissionFactor

@admin.register(RawUpload)
class RawUploadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'source_type', 'status', 'total_rows', 'uploaded_at')
    list_filter = ('source_type', 'status')
    search_fields = ('filename', 'file_hash')

@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'upload', 'line_number', 'has_error', 'created_at')
    list_filter = ('has_error', 'upload__source_type')

@admin.register(NormalizedActivity)
class NormalizedActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'scope', 'activity_type', 'reporting_period', 'quantity', 'unit', 'co2e_kg', 'review_status')
    list_filter = ('scope', 'review_status', 'reporting_period')
    search_fields = ('facility_code', 'activity_type')

@admin.register(ValidationIssue)
class ValidationIssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'raw_record', 'severity', 'issue_type', 'message')
    list_filter = ('severity', 'issue_type')

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('activity_type', 'unit', 'factor_kg_co2e', 'scope', 'source', 'year', 'region')
    list_filter = ('scope', 'year', 'region')