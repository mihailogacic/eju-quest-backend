"""
This module contains all API endpoints for lessons API
"""

from django.urls import path

from . import views


urlpatterns = [
     # lesson
     path('generate-new-lesson/', views.GenerateNewLessonView.as_view(),
          name='generate-new-lesson'),
     path('list/', views.LessonAPI.as_view(), name='pending-lessons'),
     path('<int:pk>/', views.LessonReviewView.as_view(), name='lesson-review'),

     # quiz
     path('add-questions/', views.SaveLessonContentView.as_view(), name='save-lesson'),
     path('submit-quiz/', views.QuizAPI.as_view(), name='quiz-submit'),
     path('quiz/<int:lesson>/', views.QuizAPI.as_view(), name='quiz-detail'),


     path('summary/', views.LessonSummaryView.as_view(),
          name='save-lesson-summary'),
     path('unapprove/', views.UnapproveLessonView.as_view(),
          name='unapprove-lesson'),
     path('approve/', views.ApproveLessonView.as_view(), name='approve-lesson')
]
