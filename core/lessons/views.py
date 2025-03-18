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


class SubmitLesson(APIView):
    pass


class Lesson(APIView):
    pass


class ApproveLesson(APIView):
    pass


class UnapproveLesson(APIView):
    pass


class Quiz(APIView):
    pass
