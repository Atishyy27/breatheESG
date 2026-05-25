from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class RawUpload(models.Model):
    """Immutable asset ledger tracking raw file ingestion metadata to block duplicates."""
    SOURCE_CHOICES = [
        ('SAP', 'SAP Procurement & Fuel Flat File'),
        ('UTILITY_BILL', 'Utility Portal Monthly CSV'),
        ('UTILITY_METER', 'Smart Meter Hourly Interval Stream'),
        ('TRAVEL', 'Concur Corporate Travel Expense JSON')
    ]
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, unique=True)  # MD5 Hex digest
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_email = models.CharField(max_length=100, default='analyst@breatheesg.com')
    row_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADED')
    processing_error = models.TextField(blank=True, null=True)
    tenant_id = models.CharField(max_length=50, default="client_enterprise_alpha")  # Entity tracking code

    def __str__(self):
        return f"{self.filename} ({self.source_type}) - {self.status}"

class RawRecord(models.Model):
    """Immutable sequence tracking the literal text line input to guarantee data lineage."""
    upload = models.ForeignKey(RawUpload, on_delete=models.CASCADE, related_name='records')
    line_number = models.IntegerField()
    raw_data = models.TextField()  # Exact JSON string of raw data row
    has_error = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['upload', 'line_number']]

class NormalizedActivity(models.Model):
    """The unified golden carbon schema where all distinct input vectors converge."""
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1: Direct Combustion'),
        ('SCOPE_2', 'Scope 2: Purchased Utilities'),
        ('SCOPE_3', 'Scope 3: Broader Value Chain')
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('SUSPICIOUS', 'Flagged Anomaly'),
        ('APPROVED', 'Approved & Sealed'),
        ('REJECTED', 'Archived From Active Queue')
    ]
    ANOMALY_CHOICES = [
        ('QUANTITY_SPIKE', 'Consumption spike >2.5x facility baseline'),
        ('NEGATIVE_VALUE', 'Impossible negative ledger quantity'),
        ('MISSING_FACILITY', 'Opaque or missing facility location identity'),
        ('FUTURE_DATE', 'Activity registration date falls into future space')
    ]

    # Lineage & Multitenancy Context
    raw_record = models.ForeignKey(RawRecord, on_delete=models.PROTECT, related_name='normalized_activities')
    tenant_id = models.CharField(max_length=50, default="client_enterprise_alpha")

    # Classification
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    scope_category = models.CharField(max_length=150)  # e.g., "Category 6: Business Travel"
    activity_type = models.CharField(max_length=50)    # fuel_diesel, electricity_grid, travel_flight

    # Temporal Scope
    activity_date = models.DateField()
    reporting_period = models.CharField(max_length=7)   # YYYY-MM Format

    # Spatial Context
    facility_code = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=3, default='IND')

    # Normalized Target Quantities
    quantity = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=20)  # Unified standards: L, kWh, pkm, room_nights

    # Provenance Tracking (Snapshot values frozen at calculation time)
    factor_value_used = models.DecimalField(max_digits=12, decimal_places=6)
    emission_factor_source = models.CharField(max_length=150)  # e.g., "EPA 2025 Hub", "DEFRA 2025"
    co2e_kg = models.DecimalField(max_digits=15, decimal_places=4)

    # Operational Review State Machine
    review_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    anomaly_code = models.CharField(max_length=30, choices=ANOMALY_CHOICES, blank=True, null=True)
    anomaly_details = models.TextField(blank=True, null=True)
    validation_bypassed = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_email = models.CharField(max_length=100, default='analyst@breatheesg.com')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['review_status', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        """Immutable state engine seal: Blocks database tampering once approved."""
        if self.pk:
            original = NormalizedActivity.objects.get(pk=self.pk)
            if original.review_status == 'APPROVED' and self.review_status == 'APPROVED':
                raise ValidationError("Audit Lock Breach: Records verified as APPROVED are sealed permanently.")
        super().save(*args, **kwargs)

class ValidationIssue(models.Model):
    """Captures non-blocking syntax and semantic errors tied to specific line items."""
    raw_record = models.ForeignKey(RawRecord, on_delete=models.CASCADE, related_name='validation_issues')
    severity = models.CharField(max_length=10, choices=[('ERROR', 'Error'), ('WARNING', 'Warning')])
    issue_type = models.CharField(max_length=50)  # e.g., "MISSING_QUANTITY", "UNKNOWN_AIRPORT"
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class EmissionFactor(models.Model):
    """Master reference index storing localized greenhouse gas conversion coefficients."""
    activity_type = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    factor_kg_co2e = models.DecimalField(max_digits=12, decimal_places=6)
    scope = models.CharField(max_length=10)
    source = models.CharField(max_length=150)
    year = models.IntegerField()
    region = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = [['activity_type', 'unit', 'region', 'year']]