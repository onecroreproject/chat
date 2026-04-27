from django.contrib import admin
from .models import ChatMessage, Notification


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'channel', 'message_preview', 'timestamp', 'seen']
    list_filter = ['seen', 'timestamp']
    search_fields = ['message', 'sender__username', 'receiver__username']

    def message_preview(self, obj):
        return obj.message[:50] if obj.message else '(file)'
    message_preview.short_description = 'Message'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notif_type', 'title', 'is_read', 'created_at']
    list_filter = ['notif_type', 'is_read']
    search_fields = ['user__username', 'title']
