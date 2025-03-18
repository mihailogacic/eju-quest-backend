"""Admin view for Summary model."""

from django.contrib import admin
from .models import Summary

@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    """Admin view for Summary model."""
    list_display = ('description', 'creator', 'created_at')
    search_fields = ('description', 'creator__email')
    list_filter = ('created_at',)
