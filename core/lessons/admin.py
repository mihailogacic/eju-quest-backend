"""
This module is used to register database models to Django admin section
"""

from django.contrib import admin
from .models import Lesson, Section, QuizQuestionOption, Quiz, QuizQuestion, LessonSummary

admin.site.register(
    [Lesson, Section, QuizQuestionOption, Quiz, QuizQuestion, LessonSummary]
)
