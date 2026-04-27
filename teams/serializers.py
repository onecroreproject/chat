from rest_framework import serializers
from .models import Team, Channel, Membership
from accounts.serializers import UserMiniSerializer


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'description', 'is_default', 'created_at']


class TeamSerializer(serializers.ModelSerializer):
    channels = ChannelSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'created_by', 'created_by_name',
                  'created_at', 'channels', 'member_count']

    def get_member_count(self, obj):
        return obj.get_member_count()

    def get_created_by_name(self, obj):
        return obj.created_by.get_display_name()


class MembershipSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'user', 'role', 'joined_at']
