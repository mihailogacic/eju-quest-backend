"""
This module contains all API endpoints for lessons API
"""

from django.urls import path

from . import views


urlpatterns = [
     # lesson
     path('generate-new-lesson/', views.GenerateNewLessonView.as_view(),
          name='generate-new-lesson'),
     path('tasks/<str:task_id>/status/', views.CheckTaskStatusView.as_view(), name='task_status'),
     path('list/', views.LessonAPI.as_view(), name='pending-lessons'),
     path('<int:pk>/', views.LessonReviewView.as_view(), name='lesson-review'),
     path('<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson-delete'),
     path('explore-approved/', views.ExploreApprovedLessonsView.as_view(), name='explore-approved-lessons'),
     path('add-questions/', views.SaveLessonContentView.as_view(), name='save-lesson'),

     # quiz
     path('quiz/<int:lesson>/', views.QuizAPI.as_view(), name='quiz-detail'),
     path('submit-quiz/', views.QuizAPI.as_view(), name='quiz-submit'),

     #results
     path('completed-lessons/', views.CompletedLessonsView.as_view(), name='completed-lessons'),
     path('<int:lesson_id>/results/', views.LessonResultsView.as_view(), name='lesson-results'),

     path('summary/', views.LessonSummaryView.as_view(),
          name='save-lesson-summary'),
     path('unapprove/', views.UnapproveLessonView.as_view(),
          name='unapprove-lesson'),
     path('approve/', views.ApproveLessonView.as_view(), name='approve-lesson')
]
