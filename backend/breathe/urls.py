from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from ingestion.views import (
    upload_file_endpoint,
    upload_list,
    review_queue_list,
    review_queue_detail,
    approve_activity,
    reject_activity,
    batch_approve_activity,
    export_approved_activities_csv,
    dashboard_stats,
    health_check,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Upload pipeline
    path('api/upload/', upload_file_endpoint, name='file-upload'),
    path('api/uploads/', upload_list, name='upload-list'),

    # Review queue — batch-approve MUST come before <int:pk>/ to avoid routing collision
    path('api/review/batch-approve/', batch_approve_activity, name='batch-approve'),
    path('api/review/export/', export_approved_activities_csv, name='review-export'),
    path('api/review/', review_queue_list, name='review-list'),
    path('api/review/<int:pk>/', review_queue_detail, name='review-detail'),
    path('api/review/<int:pk>/approve/', approve_activity, name='review-approve'),
    path('api/review/<int:pk>/reject/', reject_activity, name='review-reject'),

    # Dashboard + health
    path('api/dashboard/', dashboard_stats, name='dashboard-stats'),
    path('api/health/', health_check, name='health-check'),

    # React SPA catch-all — must be last
    path('', TemplateView.as_view(template_name='index.html'), name='spa'),
]