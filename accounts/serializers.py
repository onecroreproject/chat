from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'display_name', 'profile_image_url', 'bio', 'is_online', 'last_seen']

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_profile_image_url(self, obj):
        return obj.get_profile_image_url()


class UserMiniSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'display_name', 'profile_image_url', 'is_online']

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_profile_image_url(self, obj):
        return obj.get_profile_image_url()
