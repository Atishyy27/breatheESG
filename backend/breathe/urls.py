from django.contrib import admin
from django.urls import path
from ingestion.views import (
    upload_file_endpoint, 
    home_placeholder_view,
    review_queue_list,
    review_queue_detail,
    approve_activity,
    reject_activity
)

urlpatterns = [
    path('', home_placeholder_view, name='home-status'),
    path('admin/', admin.site.urls),
    path('api/upload/', upload_file_endpoint, name='file-upload'),
    path('api/review/', review_queue_list, name='review-list'),
    path('api/review/<int:pk>/', review_queue_detail, name='review-detail'),
    path('api/review/<int:pk>/approve/', approve_activity, name='review-approve'),
    path('api/review/<int:pk>/reject/', reject_activity, name='review-reject'),
]