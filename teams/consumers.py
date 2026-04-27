import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class TeamChannelConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for team channel messaging."""

    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'team_channel_{self.channel_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Check membership
        is_member = await self.check_membership()
        if not is_member:
            await self.close()
            return

        # Join the channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')

        if message_type == 'chat_message':
            message = data.get('message', '').strip()
            file_url = data.get('file_url', '')
            file_name = data.get('file_name', '')

            if not message and not file_url:
                return

            # Save message to database
            msg_data = await self.save_message(message, file_url)

            # Broadcast to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': await self.get_display_name(),
                    'sender_avatar': await self.get_avatar_url(),
                    'timestamp': msg_data['timestamp'],
                    'message_id': msg_data['id'],
                    'file_url': file_url,
                    'file_name': file_name,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
            'file_url': event.get('file_url', ''),
            'file_name': event.get('file_name', ''),
        }))

    @database_sync_to_async
    def check_membership(self):
        from teams.models import Channel, Membership
        try:
            channel = Channel.objects.get(id=self.channel_id)
            return Membership.objects.filter(user=self.user, team=channel.team).exists()
        except Channel.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message, file_url=''):
        from chat.models import ChatMessage
        from teams.models import Channel
        channel = Channel.objects.get(id=self.channel_id)
        msg = ChatMessage.objects.create(
            sender=self.user,
            channel=channel,
            message=message,
            file=file_url if file_url else '',
        )
        return {'id': msg.id, 'timestamp': msg.timestamp.isoformat()}

    @database_sync_to_async
    def get_display_name(self):
        return self.user.get_display_name()

    @database_sync_to_async
    def get_avatar_url(self):
        return self.user.get_profile_image_url()
