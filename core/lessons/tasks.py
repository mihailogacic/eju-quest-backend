# tasks.py
from celery import shared_task
from .services import LessonServices

@shared_task
def generate_lesson_task(data):
    return LessonServices.generate_new_content(data)
