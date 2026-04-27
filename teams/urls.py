from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    path('', views.teams_home_view, name='teams_home'),
    path('create/', views.create_team_view, name='create_team'),
    path('<int:team_id>/', views.team_detail_view, name='team_detail'),
    path('<int:team_id>/channel/<int:channel_id>/', views.channel_view, name='channel'),
    path('<int:team_id>/create-channel/', views.create_channel_view, name='create_channel'),
    path('<int:team_id>/add-member/', views.add_member_view, name='add_member'),
    path('<int:team_id>/remove-member/', views.remove_member_view, name='remove_member'),
    path('<int:team_id>/delete-channel/<int:channel_id>/', views.delete_channel_view, name='delete_channel'),
    # API endpoints
    path('api/<int:team_id>/channels/', views.get_team_channels_api, name='api_channels'),
    path('api/<int:team_id>/members/', views.get_team_members_api, name='api_members'),
]
