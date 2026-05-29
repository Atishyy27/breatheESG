from django.contrib import admin
from django.urls import path

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
    dashboard_trends,
    health_check,
    generate_dataset,
)

urlpatterns = [

    path('admin/', admin.site.urls),

    # Upload pipeline
    path('api/upload/', upload_file_endpoint, name='file-upload'),
    path('api/uploads/', upload_list, name='upload-list'),

    # Review queue
    path('api/review/batch-approve/', batch_approve_activity),
    path('api/review/export/', export_approved_activities_csv),

    path('api/review/', review_queue_list),
    path('api/review/<int:pk>/', review_queue_detail),
    path('api/review/<int:pk>/approve/', approve_activity),
    path('api/review/<int:pk>/reject/', reject_activity),

    # Dashboard
    path('api/dashboard/', dashboard_stats),
    path('api/dashboard/trends/', dashboard_trends, name='dashboard-trends'),

    # Dataset
    path('api/generate/', generate_dataset, name='generate-dataset'),

    # Health
    path('', health_check),
    path('api/health/', health_check),

]