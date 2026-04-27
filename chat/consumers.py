import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for 1:1 chat messaging."""

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Notify online status
        await self.set_online(True)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.set_online(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'chat_message')

        if msg_type == 'chat_message':
            message = data.get('message', '').strip()
            receiver_id = data.get('receiver_id')
            file_url = data.get('file_url', '')
            file_name = data.get('file_name', '')

            if not message and not file_url:
                return

            # Save to database
            msg_data = await self.save_message(message, receiver_id, file_url)

            # Send notification to receiver
            await self.send_notification(receiver_id, message)

            # Broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': await self.get_display_name(),
                    'sender_avatar': await self.get_avatar_url(),
                    'receiver_id': receiver_id,
                    'timestamp': msg_data['timestamp'],
                    'message_id': msg_data['id'],
                    'file_url': file_url,
                    'file_name': file_name,
                    'seen': False,
                    'delivered': True,
                }
            )

        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'sender_id': self.user.id,
                    'sender_name': await self.get_display_name(),
                    'is_typing': data.get('is_typing', False),
                }
            )

        elif msg_type == 'mark_seen':
            msg_id = data.get('message_id')
            if msg_id:
                await self.mark_message_seen(msg_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_seen',
                        'message_id': msg_id,
                        'seen_by': self.user.id,
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'receiver_id': event['receiver_id'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
            'file_url': event.get('file_url', ''),
            'file_name': event.get('file_name', ''),
            'seen': event.get('seen', False),
            'delivered': event.get('delivered', True),
        }))

    async def typing_indicator(self, event):
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender_id': event['sender_id'],
                'sender_name': event['sender_name'],
                'is_typing': event['is_typing'],
            }))

    async def message_seen(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_seen',
            'message_id': event['message_id'],
            'seen_by': event['seen_by'],
        }))

    @database_sync_to_async
    def save_message(self, message, receiver_id, file_url=''):
        from .models import ChatMessage
        from accounts.models import CustomUser
        receiver = CustomUser.objects.get(id=receiver_id)
        msg = ChatMessage.objects.create(
            sender=self.user,
            receiver=receiver,
            message=message,
            file=file_url if file_url else '',
        )
        return {'id': msg.id, 'timestamp': msg.timestamp.isoformat()}

    @database_sync_to_async
    def mark_message_seen(self, message_id):
        from .models import ChatMessage
        try:
            msg = ChatMessage.objects.get(id=message_id, receiver=self.user)
            msg.seen = True
            msg.save(update_fields=['seen'])
        except ChatMessage.DoesNotExist:
            pass

    @database_sync_to_async
    def set_online(self, is_online):
        self.user.is_online = is_online
        if not is_online:
            self.user.last_seen = timezone.now()
        self.user.save(update_fields=['is_online', 'last_seen'] if not is_online else ['is_online'])

    @database_sync_to_async
    def get_display_name(self):
        return self.user.get_display_name()

    @database_sync_to_async
    def get_avatar_url(self):
        return self.user.get_profile_image_url()

    @database_sync_to_async
    def send_notification(self, receiver_id, message):
        from .models import Notification
        from accounts.models import CustomUser
        try:
            receiver = CustomUser.objects.get(id=receiver_id)
            Notification.objects.create(
                user=receiver,
                notif_type='message',
                title=f'New message from {self.user.get_display_name()}',
                body=message[:100],
                link=f'/chat/room/{self.user.id}/',
            )
        except CustomUser.DoesNotExist:
            pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications."""

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # Send unread count on connect
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def new_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
        }))

    async def unread_count_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count'],
        }))

    @database_sync_to_async
    def get_unread_count(self):
        from .models import Notification
        return Notification.objects.filter(user=self.user, is_read=False).count()
