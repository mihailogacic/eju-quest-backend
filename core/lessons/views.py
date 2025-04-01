"""
This module contains all APIs related to Lessons, Quiz including creation
and child interaction with both.
"""
import logging, json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404


from .serializers import LessonSerializer, LessonDetailSerializer, QuizSerializer, LessonSummarySerializer
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
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        data = request.data
        image = request.FILES.get("image")

        # Parse content and questions from JSON string
        try:
            content = json.loads(data.get("content", "[]"))
            questions = json.loads(data.get("questions", "[]"))
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON format in content or questions."}, status=400)

        # Validate required fields
        if not content or not questions:
            return Response(
                {"detail": "'content' and 'questions' fields are required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine lesson title
        lesson_title = data.get("title") or (content[0].get("heading") if content else "Untitled Lesson")

        # Create the Lesson instance
        lesson = Lesson.objects.create(
            creator=request.user,
            title=lesson_title,
            age_level=data.get('age_level'),
            lesson_length=data.get('lesson_length'),
            image=image,
            status="pending"
        )

        # Create Sections
        for section in content:
            heading = section.get("heading", "")
            text = section.get("text", "")
            if heading and text:
                Sections.objects.create(lesson=lesson, heading=heading, content=text)

        # Create Quiz and Questions
        quiz = Quiz.objects.create(lesson=lesson)
        for question_data in questions:
            question_text = question_data.get("question", "")
            options_data = question_data.get("options", [])
            correct_answer = question_data.get("answer", "")

            created_options = []
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

            quiz_question = QuizQuestions.objects.create(
                quiz=quiz,
                question_text=question_text
            )
            quiz_question.options.set(created_options)

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


class LessonAPI(APIView):
    """
    API view to retrieve lessons with optional filtering by status.

    If a query parameter "status" is provided, only lessons with that status
    (case-insensitive) will be returned.
    """

    def get(self, request, format=None):
        """
        Retrieve all lessons or filter by lesson status if provided.

        Query Parameters:
            status (str, optional): The lesson status to filter by (e.g., "pending").

        Returns:
            Response: A response object containing serialized lesson data.
        """
        status_filter = request.query_params.get('status')
        lessons = Lesson.objects.filter(creator=request.user)

        if status_filter:
            lessons = lessons.filter(status__iexact=status_filter)

        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LessonReviewView(RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonDetailSerializer
    lookup_field = 'pk'

class ApproveLessonView(APIView):
    def post(self, request):
        data = request.data
        lesson_id = data.get('lesson_id')
        lesson = get_object_or_404(Lesson, id=lesson_id)
        lesson.status = 'approved'
        lesson.save()
        return Response({'detail':  "Lesson has been successfully approved."}, status=status.HTTP_200_OK)

class UnapproveLessonView(APIView):
    def post(self, request):
        data = request.data
        lesson_id = data.get('lesson_id')
        lesson = get_object_or_404(Lesson, id=lesson_id)
        lesson.delete()
        return Response({'detail':  "Lesson has been successfully unapproved."}, status=status.HTTP_204_NO_CONTENT)

class ExploreApprovedLessonsView(APIView):
    """
    Returns all approved lessons created by the parent of the logged-in child user.

    Response includes:
        - recommended_courses: list of lessons
        - recent_activity: empty for now
    """
    def get(self, request):
        """
        GET method to fetch approved lessons for the child's parent.
        """
        user = request.user
        parent = user.parent

        if not parent:
            return Response({"error": "Only child users can explore approved lessons."},
                            status=status.HTTP_403_FORBIDDEN)

        approved_lessons = Lesson.objects.filter(creator=parent, status="approved")
        serializer = LessonSerializer(approved_lessons, many=True)

        return Response({
            "recommended_courses": serializer.data,
            "recent_activity": []
        }, status=status.HTTP_200_OK)

class QuizAPI(APIView):
    """
    API view to handle quiz submission and retrieval.

    This view provides endpoints to submit a new quiz and retrieve an existing quiz.
    It adheres to the principles of simplicity and readability as stated in PEP 8, PEP 257,
    and PEP 20.
    """

    def get(self, request, lesson, format=None):
        """
        Retrieve an existing quiz by its ID.

        Args:
            request (HttpRequest): The HTTP request instance.
            quiz_id (int): The primary key of the quiz to retrieve.
            format (str, optional): Format suffix for content negotiation.

        Returns:
            Response: A response object containing the quiz data if found,
                        otherwise an error message with status 404.
        """
        quiz = get_object_or_404(Quiz, lesson=lesson)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        """
        Submit a new quiz.

        This method creates a new quiz instance along with its related quiz questions and options
        (if provided). It restricts users from creating more than one quiz per lesson.

        Args:
            request (HttpRequest): The HTTP request containing quiz data.
            format (str, optional): Format suffix for content negotiation.

        Returns:
            Response: A response object containing the created quiz data with status 201 if successful,
                    or validation errors with status 400.
        """
        # Extract lesson ID from input data.
        lesson_id = request.data.get("lesson")
        if not lesson_id:
            return Response(
                {"lesson": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a quiz already exists for the given lesson.
        if Quiz.objects.filter(lesson_id=lesson_id).exists():
            return Response(
                {"detail": "Quiz already exists for this lesson."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process quiz creation.
        serializer = QuizSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            quiz = serializer.save()
            return Response(
                QuizSerializer(quiz, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
