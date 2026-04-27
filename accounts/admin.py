from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OTPVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_verified', 'is_online']
    list_filter = ['is_verified', 'is_online', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['email']

    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('profile_image', 'bio', 'is_verified', 'is_online', 'last_seen')}),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_code', 'otp_type', 'created_at', 'is_used']
    list_filter = ['otp_type', 'is_used']
    search_fields = ['user__email']
