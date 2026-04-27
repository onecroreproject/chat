from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    """Extended user model with profile image and email verification."""
    email = models.EmailField(unique=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    bio = models.CharField(max_length=255, blank=True, default='')
    last_seen = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def get_profile_image_url(self):
        if self.profile_image:
            return self.profile_image.url
        return '/static/images/default-avatar.svg'

    def get_display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class OTPVerification(models.Model):
    """OTP codes for email verification and password reset."""
    OTP_TYPE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES, default='registration')
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.email} - {self.otp_code}"

    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))

    def is_valid(self):
        """Check if OTP is still valid (10 minutes window)."""
        if self.is_used:
            return False
        expiry_time = self.created_at + timedelta(minutes=10)
        return timezone.now() < expiry_time

    class Meta:
        ordering = ['-created_at']
