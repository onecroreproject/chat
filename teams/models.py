from django.db import models
from django.conf import settings


class Team(models.Model):
    """A team is a group of users who collaborate together."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='team_avatars/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None

    def get_member_count(self):
        return self.memberships.count()

    class Meta:
        ordering = ['-created_at']


class Channel(models.Model):
    """A channel is a topic-based conversation within a team."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='channels')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.name} ({self.team.name})"

    class Meta:
        ordering = ['name']
        unique_together = ['team', 'name']


class Membership(models.Model):
    """Represents a user's membership in a team."""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.role})"

    class Meta:
        unique_together = ['user', 'team']
