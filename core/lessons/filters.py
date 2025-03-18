from django_filters import rest_framework as filters

from .models import Lesson


class LessonFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Lesson
        fields = ['status']
