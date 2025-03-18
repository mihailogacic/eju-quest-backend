"""Admin view for User and SecurityLog models."""

from django.contrib import admin
from .models import User, SecurityLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin view for User model."""

    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_verified')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('role', 'is_active', 'is_verified')


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    """Admin view for SecurityLog model."""

    list_display = ('email', 'event_type', 'ip_address', 'event_time', 'failed_attempts')
    search_fields = ('email', 'ip_address', 'event_type')
    list_filter = ('event_type', 'event_time')
