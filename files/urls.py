from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('', views.files_home_view, name='files_home'),
    path('upload/', views.upload_file_view, name='upload'),
    path('delete/<int:file_id>/', views.delete_file_view, name='delete'),
]
