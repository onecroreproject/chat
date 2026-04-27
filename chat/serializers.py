from rest_framework import serializers
from .models import ChatMessage, Notification
from accounts.serializers import UserMiniSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'message', 'file_url', 'file_name',
                  'is_image', 'timestamp', 'seen', 'delivered']

    def get_file_url(self, obj):
        return obj.get_file_url()

    def get_file_name(self, obj):
        return obj.get_file_name()

    def get_is_image(self, obj):
        return obj.is_image()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notif_type', 'title', 'body', 'link', 'is_read', 'created_at']
