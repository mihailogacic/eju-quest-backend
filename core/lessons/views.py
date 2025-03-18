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

            return Response(lesson, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SaveLessonContentView(APIView):
    """
    API view to save lesson content along with its sections and quiz data.

    Expects a JSON payload with the following structure:

    {
        "content": [
            {
                "heading": "Introduction to Crypto Trading",
                "text": "Crypto trading involves buying and selling..."
            },
            {
                "heading": "History of Cryptocurrencies",
                "text": "Cryptocurrencies began in 2009 with the creation of Bitcoin..."
            },
            ...
        ],
        "questions": [
            {
                "question": "Who is credited with creating Bitcoin?",
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

    The view will:
      - Create a Lesson instance (using the first section's heading as the lesson title if none is provided).
      - Create a Section for each item in the "content" list.
      - Create a Quiz for the Lesson.
      - For each question, create a QuizQuestions instance and create all QuizQuestionOptions.
        Due to the models’ design, the QuizQuestions.options field will be linked to the correct option.
    """

    def post(self, request, *args, **kwargs):
        data = request.data

        # Validate required keys
        if 'content' not in data or 'questions' not in data:
            return Response(
                {"detail": "Invalid data format. 'content' and 'questions' fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine lesson title (use provided title if available, or use the first section's heading)
        lesson_title = data.get("title")
        if not lesson_title:
            if data["content"]:
                lesson_title = data["content"][0].get(
                    "heading", "Untitled Lesson")
            else:
                lesson_title = "Untitled Lesson"

        # Create the Lesson instance
        # Here we use default values for age_level and lesson_length for simplicity.
        # You might want to extract these from data if available.
        lesson = Lesson.objects.create(
            creator=request.user,
            title=lesson_title,
            age_level=10,            # default value; adjust as needed
            lesson_length="medium",  # default value; adjust as needed
            status="pending"
        )

        # Create Sections from the content data
        for section in data["content"]:
            heading = section.get("heading", "")
            text = section.get("text", "")
            if heading and text:
                Sections.objects.create(
                    lesson=lesson,
                    heading=heading,
                    content=text
                )

        # Create a Quiz for the lesson
        quiz = Quiz.objects.create(lesson=lesson)

        # Process each question in the quiz data
        for question_data in data["questions"]:
            question_text = question_data.get("question", "")
            options_data = question_data.get("options", [])
            correct_answer = question_data.get("answer", "")

            created_options = []
            # Create QuizQuestionOptions for each provided option
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

            # From the created options, pick the correct one to link in the QuizQuestions instance.
            correct_option_instance = next(
                (opt for opt in created_options if opt.option == correct_answer), None)
            if not correct_option_instance:
                return Response(
                    {"detail": f"Correct option not found for question: {question_text}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create the quiz question and assign the correct option.
            QuizQuestions.objects.create(
                quiz=quiz,
                question_text=question_text,
                options=correct_option_instance
            )

        return Response({"detail": "Lesson, sections, and quiz created successfully."}, status=status.HTTP_201_CREATED)


class LessonApi(APIView):
    pass


class ApproveLesson(APIView):
    pass


class UnapproveLesson(APIView):
    pass


class QuizApi(APIView):
    pass
