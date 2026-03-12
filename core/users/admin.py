"""Admin view for UserSummary model."""

from django.contrib import admin
from .models import UserSummary


@admin.register(UserSummary)
class UserSummaryAdmin(admin.ModelAdmin):
    """Admin view for UserSummary model."""

    list_display = ('description', 'user', 'created_at')
    search_fields = ('description', 'user__email')
    list_filter = ('created_at',)
