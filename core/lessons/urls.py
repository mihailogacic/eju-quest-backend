"""
This module contains all API endpoints for lessons API
"""

from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import LessonsViewset

router = DefaultRouter()
router.register(r'', LessonsViewset, basename='lessons')

urlpatterns = [
    path('', include(router.urls)),
]
