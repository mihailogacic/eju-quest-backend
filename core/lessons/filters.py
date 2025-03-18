
"""
lesson_filter.py

This module defines filtering functionality for the Lesson model using Django Filters.

The `LessonFilter` class allows filtering lessons based on their status, making it
easier to retrieve specific lesson records from the database.
"""
from django_filters import rest_framework as filters

from .models import Lesson


class LessonFilter(filters.FilterSet):
    """
    A filter set for filtering Lesson instances based on status.

    Filters:
        - status (CharFilter): Allows case-insensitive filtering by lesson status.
    """

    status = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Lesson
        fields = ['status']
