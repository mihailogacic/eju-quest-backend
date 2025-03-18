"""
This module contains all APIs related to Lessons, Quiz including creation
and child interaction with both.
"""
import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import LessonSerializer
from .services import LessonServices

logger = logging.getLogger(__name__)


class GenerateNewLessonView(APIView):
    """
    This API is used to generate new lesson content
    by using OpenAI API, it doesn't save data in database
    however it returns JSON format to the frontend.
    """

    serializer_class = LessonSerializer

    def post(self, request):
        """
        Handles POST method for this API.
        """

        serializer = LessonSerializer(
            data=request.data, context={'request': request})

        # Check if the data is valid
        if serializer.is_valid():
            lesson = LessonServices.generate_new_content(
                serializer.validated_data)
            print(lesson)

            return Response(lesson, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class LessonsViewset(viewsets.ModelViewSet):
#     queryset = Lesson.objects.all()
#     filter_backends = [DjangoFilterBackend]
#     filterset_class = LessonFilter

#     def get_serializer_class(self):
#         """
#         Dynamically returns the serializer based on the action being performed.
#         """
#         if self.action == "generate_new_lesson":
#             return LessonSerializer

#         return LessonSerializer

#     def retrieve(self, request, *args, **kwargs):
#         pass

#     @action(detail=False, methods=['post'], url_path='add-questions/')
#     def add_questions_to_the_lesson(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='approve/')
#     def approve_lesson(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='unapprove/')
#     def unapprove_lesson(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='explore-approved/')
#     def explore_approved_lessons(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='quiz/')
#     def view_quiz(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='submit-quiz/')
#     def submit_quiz(self, request):
#         pass

#     @action(detail=False, methods=['post'], url_path='summary/')
#     def submit_summary(self, request):
#         pass
