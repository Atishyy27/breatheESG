from django.db import models

class RawUpload(models.Model):
    """Tracks metadata and summary metrics for an uploaded data file."""
    SOURCE_CHOICES = [
        ('SAP', 'SAP Procurement & Fuel'),
        ('UTILITY_BILL', 'Utility Portal Monthly CSV'),
        ('UTILITY_METER', 'Smart Meter Hourly CSV'),
        ('TRAVEL', 'Concur Corporate Travel JSON')
    ]
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, unique=True)  # MD5 checksum
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_email = models.CharField(max_length=100, default='analyst@breatheesg.com')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPLOADED')
    processing_error = models.TextField(blank=True, null=True)

    # Ingestion Summary Statistics
    total_rows = models.IntegerField(default=0)
    normalized_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    warning_rows = models.IntegerField(default=0)
    suspicious_rows = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.source_type}) - {self.status}"

class RawRecord(models.Model):
    """Stores the original unparsed row data for lineage tracking."""
    upload = models.ForeignKey(RawUpload, on_delete=models.CASCADE, related_name='records')
    line_number = models.IntegerField()
    raw_data = models.JSONField()  # Direct JSON storage of the parsed source line
    has_error = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['upload', 'line_number']]

class NormalizedActivity(models.Model):
    """Unified schema for emissions activity data across all source types."""
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1: Direct Combustion'),
        ('SCOPE_2', 'Scope 2: Purchased Utilities'),
        ('SCOPE_3', 'Scope 3: Value Chain')
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('SUSPICIOUS', 'Flagged Anomaly'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    ANOMALY_CHOICES = [
        ('QUANTITY_SPIKE', 'Consumption spike >2.5x baseline'),
        ('NEGATIVE_VALUE', 'Negative data value'),
        ('MISSING_FACILITY', 'Missing facility identifier'),
        ('FUTURE_DATE', 'Activity date falls in the future')
    ]

    raw_record = models.ForeignKey(RawRecord, on_delete=models.PROTECT, related_name='normalized_activities')
    
    # Classification & Scope
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    scope_category = models.CharField(max_length=150)  # e.g., "Category 6: Business Travel"
    activity_type = models.CharField(max_length=50)    # fuel_diesel, electricity_grid, travel_flight

    # Temporal & Spatial Parameters
    activity_date = models.DateField()
    reporting_period = models.CharField(max_length=7)  # YYYY-MM
    facility_code = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=3, default='IND')

    # Normalized Quantities
    quantity = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=20)  # Standardized targets: L, kWh, pkm, room_nights

    # Emission Factor Snapshot (Frozen at calculation time)
    factor_value_used = models.DecimalField(max_digits=12, decimal_places=6)
    emission_factor_source = models.CharField(max_length=150)  # e.g., "EPA 2025 Hub"
    co2e_kg = models.DecimalField(max_digits=15, decimal_places=4)

    # Workflow Columns
    review_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    anomaly_code = models.CharField(max_length=30, choices=ANOMALY_CHOICES, blank=True, null=True)
    anomaly_details = models.TextField(blank=True, null=True)
    validation_bypassed = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_email = models.CharField(max_length=100, default='analyst@breatheesg.com')
    
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['review_status', '-created_at']),
        ]

class ValidationIssue(models.Model):
    """Tracks semantic issues or errors found on specific input rows."""
    raw_record = models.ForeignKey(RawRecord, on_delete=models.CASCADE, related_name='validation_issues')
    severity = models.CharField(max_length=10, choices=[('ERROR', 'Error'), ('WARNING', 'Warning')])
    issue_type = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class EmissionFactor(models.Model):
    """Reference table for greenhouse gas emission factors."""
    activity_type = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    factor_kg_co2e = models.DecimalField(max_digits=12, decimal_places=6)
    scope = models.CharField(max_length=10)
    source = models.CharField(max_length=150)
    year = models.IntegerField()
    region = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = [['activity_type', 'unit', 'region', 'year']]