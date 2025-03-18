from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from django_filters.rest_framework import DjangoFilterBackend

from .serializers import LessonSerializer
from .models import Lesson
from .filters import LessonFilter


class LessonsViewset(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LessonFilter

    def retrieve(self, request, *args, **kwargs):
        pass

    @action(detail=False, methods=['post'])
    def generate_new_lesson(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='add-questions/')
    def add_questions_to_the_lesson(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='approve/')
    def approve_lesson(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='unapprove/')
    def unapprove_lesson(self, request):
        pass

    @action(detail=False, methods=['post'], url_path='explore-approved/')
    def explore_approved_lessons(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='quiz/')
    def view_quiz(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='submit-quiz/')
    def submit_quiz(self, request):
        pass

    @action(detail=True, methods=['post'], url_path='summary/')
    def submit_summary(self, request):
        pass
