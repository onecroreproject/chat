from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('room/<int:user_id>/', views.chat_room_view, name='chat_room'),
    path('start/<int:user_id>/', views.start_chat_view, name='start_chat'),
    # API endpoints
    path('api/messages/<int:user_id>/', views.get_messages_api, name='api_messages'),
    path('api/messages/<int:message_id>/edit/', views.edit_message_api, name='api_edit_message'),
    path('api/messages/<int:message_id>/delete/', views.delete_message_api, name='api_delete_message'),
    path('api/mark-seen/<int:user_id>/', views.mark_seen_api, name='api_mark_seen'),
    path('api/search/', views.search_messages_api, name='api_search'),
    path('api/notifications/', views.get_notifications_api, name='api_notifications'),
    path('api/notifications/<int:notif_id>/read/', views.mark_notification_read_api, name='api_notification_read'),
    path('activity/', views.activity_view, name='activity'),
    path('calendar/', views.calendar_view, name='calendar'),
]
