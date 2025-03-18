"""
This module contains all APIs related to Lessons, Quiz including creation
and child interaction with both.
"""
import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import LessonSerializer, LessonSummarySerializer
from .services import LessonServices
from .models import Lesson, Sections, Quiz, QuizQuestions, QuizQuestionOptions

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

            return Response({"lesson": lesson, "prompt_input": {
                "age_level": serializer.validated_data.get('age_level'),
                "title": serializer.validated_data.get('title'),
                "lesson_length": serializer.validated_data.get('lesson_length')
            }}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SaveLessonContentView(APIView):
    """
    API view to save lesson content along with its sections and quiz data.

    This view will:
      - Create a Lesson instance.
      - Create Sections from the "content" list.
      - Create a Quiz for the Lesson.
      - For each question:
        - Create multiple QuizQuestionOptions.
        - Link all options to the corresponding QuizQuestions instance.

    Expected JSON Format:
    {
        "content": [
            {"heading": "Introduction", "text": "Some text"},
            ...
        ],
        "questions": [
            {
                "question": "Who created Bitcoin?",
                "options": [
                    {"option": "A", "text": "Vitalik Buterin"},
                    {"option": "B", "text": "Satoshi Nakamoto"},
                    {"option": "C", "text": "Nick Szabo"},
                    {"option": "D", "text": "Hal Finney"}
                ],
                "answer": "B"
            },
            ...
        ]
    }
    """

    def post(self, request, *args, **kwargs):
        data = request.data

        # Validate required keys
        if 'content' not in data or 'questions' not in data:
            return Response(
                {"detail": "Invalid data format. 'content' and 'questions' fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine lesson title (use provided title or fallback to first section heading)
        lesson_title = data.get("title") or (data["content"][0].get(
            "heading") if data["content"] else "Untitled Lesson")

        # Create the Lesson instance
        lesson = Lesson.objects.create(
            creator=request.user,
            title=lesson_title,
            # Default value; can be adjusted
            age_level=data.get('age_level'),
            # Default value; can be adjusted
            lesson_length=data.get('lesson_length'),
            status="pending"
        )

        # Create Sections from content data
        for section in data["content"]:
            heading = section.get("heading", "")
            text = section.get("text", "")
            if heading and text:
                Sections.objects.create(
                    lesson=lesson, heading=heading, content=text)

        # Create a Quiz for the lesson
        quiz = Quiz.objects.create(lesson=lesson)

        # Process each question
        for question_data in data["questions"]:
            question_text = question_data.get("question", "")
            options_data = question_data.get("options", [])
            correct_answer = question_data.get("answer", "")

            created_options = []
            # Create all options and determine which is correct
            for option_data in options_data:
                option_letter = option_data.get("option")
                option_text = option_data.get("text")
                is_correct = (option_letter == correct_answer)

                quiz_option = QuizQuestionOptions.objects.create(
                    option=option_letter,
                    option_text=option_text,
                    correct=is_correct
                )
                created_options.append(quiz_option)

            # Create the quiz question and associate all options
            quiz_question = QuizQuestions.objects.create(
                quiz=quiz,
                question_text=question_text
            )
            quiz_question.options.set(created_options)  # Associate all options
            quiz_question.save()

        return Response({"detail": "Lesson, sections, and quiz created successfully."}, status=status.HTTP_201_CREATED)


class LessonSummaryView(APIView):

    def post(self, request):
        data = request.data
        print('wht')
        serializer = LessonSummarySerializer(
            data=data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response({'detail': "Lesson summary successfully saved!"}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonApi(APIView):
    pass


class ApproveLesson(APIView):
    pass


class UnapproveLesson(APIView):
    pass


class QuizApi(APIView):
    pass
