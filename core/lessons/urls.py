"""
This module contains all API endpoints for lessons API
"""

from django.urls import path

from . import views


urlpatterns = [
    path('generate-new-lesson/', views.GenerateNewLessonView.as_view(),
         name='generate-new-lesson'),
]
