from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from ingestion.views import (
    upload_file_endpoint, 
    review_queue_list,
    review_queue_detail,
    approve_activity,
    reject_activity,
    upload_list,
    batch_approve_activity,
    export_approved_activities_csv
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/review/batch-approve/', batch_approve_activity, name='batch-approve'),

    # Upload pipeline
    path('api/upload/', upload_file_endpoint, name='file-upload'),
    path('api/uploads/', upload_list, name='upload-list'),
    
    # Review queue
    path('api/review/', review_queue_list, name='review-list'),
    path('api/review/<int:pk>/', review_queue_detail, name='review-detail'),
    path('api/review/<int:pk>/approve/', approve_activity, name='review-approve'),
    path('api/review/<int:pk>/reject/', reject_activity, name='review-reject'),
    path('api/review/export/', export_approved_activities_csv, name='review-export'),
    
     # Dashboard
    path('api/dashboard/', views.dashboard_stats, name='dashboard_stats'),

    # Health check
    path('api/health/', views.health_check, name='health_check'),

    # Serve index.html directly for single-app deployment simplicity
    path('', TemplateView.as_view(template_name='index.html'), name='dashboard'),
]