"""
This module is used to register database models to Django admin section
"""

from django.contrib import admin
from .models import Lesson, Sections, QuizQuestionOptions, Quiz, QuizQuestions, LessonSummary

admin.site.register([Lesson, Sections, QuizQuestionOptions,
                    Quiz, QuizQuestions, LessonSummary])
