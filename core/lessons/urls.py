"""
This module contains all API endpoints for lessons API
"""

from django.urls import path

from . import views


urlpatterns = [
    path('generate-new-lesson/', views.GenerateNewLessonView.as_view(),
         name='generate-new-lesson'),

    path('add-questions/', views.SaveLessonContentView.as_view(), name='save-lesson'),
    path('summary/', views.LessonSummaryView.as_view(),
         name='save-lesson-summary'),
    path('unapprove/', views.UnapproveLessonView.as_view(),
         name='unapprove-lesson'),
    path('approve/', views.ApproveLessonView.as_view(), name='approve-lesson')
]
