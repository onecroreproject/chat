from django.db import models
from django.conf import settings
from teams.models import Channel


class ChatMessage(models.Model):
    """A chat message - can be 1:1 or in a channel."""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_messages'
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages'
    )
    message = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    delivered = models.BooleanField(default=True)

    def __str__(self):
        if self.is_deleted:
            return "Deleted message"
        if self.channel:
            return f"{self.sender.username} in {self.channel.name}: {self.message[:50]}"
        return f"{self.sender.username} to {self.receiver.username if self.receiver else 'N/A'}: {self.message[:50]}"

    def get_file_url(self):
        if self.file:
            return self.file.url
        return None

    def get_file_name(self):
        if self.file:
            return self.file.name.split('/')[-1]
        return None

    def is_image(self):
        if self.file:
            name = self.file.name.lower()
            return any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'])
        return False

    def is_video(self):
        if self.file:
            name = self.file.name.lower()
            return any(name.endswith(ext) for ext in ['.mp4', '.webm', '.ogg', '.mov', '.avi'])
        return False

    class Meta:
        ordering = ['timestamp']


class Notification(models.Model):
    """User notifications for messages, team invites, etc."""
    NOTIF_TYPES = [
        ('message', 'New Message'),
        ('team_invite', 'Team Invite'),
        ('mention', 'Mention'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    link = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        ordering = ['-created_at']
