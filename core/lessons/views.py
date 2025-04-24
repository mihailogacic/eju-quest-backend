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
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from celery.result import AsyncResult

from authentication.models import User

from .services import LessonServices
from .serializers import LessonSerializer, LessonDetailSerializer, QuizSerializer, LessonSummarySerializer, SingleQuizResultSerializer, CompletedLessonSerializer
from .models import Lesson, Sections, Quiz, QuizQuestions, QuizQuestionOptions, LessonVisit, QuizResult, LessonSummary
from .tasks import generate_lesson_task

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

        serializer = LessonSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            task = generate_lesson_task.delay(serializer.validated_data)

            return Response({
                "task_id": task.id,
                "status": "processing",
                "prompt_input": {
                    "age_level": serializer.validated_data.get('age_level'),
                    "title": serializer.validated_data.get('title'),
                    "lesson_length": serializer.validated_data.get('lesson_length')
                }
            }, status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckTaskStatusView(APIView):

    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.ready():
            return Response({"status": "completed", "result": result.result}, status=status.HTTP_200_OK)

        return Response({"status": "processing"}, status=status.HTTP_202_ACCEPTED)

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
    """
    Retrieve a single lesson and track the visit by the user.
    Keeps max 2 recent lessons per child user.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonDetailSerializer
    lookup_field = 'pk'

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)

        if request.user.is_authenticated and request.user.parent_id:
            lesson = self.get_object()

            LessonVisit.objects.filter(user=request.user, lesson=lesson).delete()

            visits = LessonVisit.objects.filter(user=request.user).order_by('-visited_at')
            if visits.count() >= 2:
                visits.last().delete()

            LessonVisit.objects.create(user=request.user, lesson=lesson)

        return response

class LessonDeleteView(APIView):
    """
    DELETE /api/v1/lessons/<pk>/delete/

    Briše lekciju i sve zavisne entitete + sliku sa cloud-a.
    Dozvoljeno je samo kreatoru (ili staff-u/superuser-u).
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=pk)

        if lesson.creator != request.user:
            raise PermissionDenied("You do not have permission to delete this lesson.")

        with transaction.atomic():
            if lesson.image:
                lesson.image.delete(save=False)

            QuizQuestionOptions.objects.filter(
                quizquestions__quiz__lesson=lesson
            ).delete()

            lesson.delete()

        return Response(
            {"detail": "Lesson and all related data were deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )

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
        - recent_activity: last 2 visited lessons
    """
    def get(self, request):
        user = request.user
        parent = user.parent

        if not parent:
            return Response({"error": "Only child users can explore approved lessons."},
                            status=status.HTTP_403_FORBIDDEN)

        # Recommended courses
        approved_lessons = Lesson.objects.filter(creator=parent, status="approved")
        recommended_serializer = LessonSerializer(approved_lessons, many=True)

        # Recent activity (last 2 visited lessons)
        recent_visits = LessonVisit.objects.filter(user=user).select_related('lesson')[:2]
        recent_lessons = [visit.lesson for visit in recent_visits]
        recent_serializer = LessonSerializer(recent_lessons, many=True)

        return Response({
            "recommended_courses": recommended_serializer.data,
            "recent_activity": recent_serializer.data
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
        Submit quiz answers and return the result.
        Expected input:
        {
            "lesson_id": 1,
            "answers": [
                {"question_id": 101, "selected_option": "A"},
                ...
            ]
        }
        """
        lesson_id = request.data.get("lesson_id")
        answers = request.data.get("answers", [])
        raw_time = request.data.get("remaining_time")
        remaining_time = LessonServices.parse_remaining_time(raw_time)

        if remaining_time is None:
            return Response({"detail": "'remaining_time' format is not valid."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not lesson_id or not answers:
            return Response(
                {"detail": "'lesson_id' and 'answers' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        quiz = get_object_or_404(Quiz, lesson_id=lesson_id)

        correct_count = 0
        results = []

        for answer in answers:
            q_id = answer.get("question_id")
            selected_option = answer.get("selected_option")

            try:
                question = QuizQuestions.objects.get(id=q_id, quiz=quiz)
            except QuizQuestions.DoesNotExist:
                continue

            correct_option = question.options.filter(correct=True).first()
            is_correct = (selected_option == correct_option.option) if correct_option else False
            
            if is_correct:
                correct_count += 1

            results.append({
                "question_id": q_id,
                "selected_option": selected_option,
                "correct": "true" if is_correct else "false"
            })

        total_questions = len(answers)
        score = round((correct_count / total_questions) * 100) if total_questions > 0 else 0
        passed = score >= 50 and remaining_time > 0

        QuizResult.objects.update_or_create(
            user=request.user,
            lesson_id=lesson_id,
            defaults={
                "score": score,
                "correct_answers": correct_count,
                "total_questions": total_questions,
                "passed": passed,
                "answers": results,
                "remaining_time": remaining_time,
            },
        )

        return Response({
            "detail": "Quiz completed successfully.",
            "score": score,
            "correct_answers": correct_count,
            "total_questions": total_questions,
            "answers": results,
            "passed": passed,
        }, status=status.HTTP_200_OK)

class CompletedLessonsView(APIView):
    """
    GET /api/v1/lessons/completed-lessons/
    Vrati SVE results zapise za SVU roditeljevu decu.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        children = User.objects.filter(parent=request.user)
        results = (QuizResult.objects
                    .filter(user__in=children)
                    .select_related("lesson", "user")
                    .order_by("-created_at"))

        serializer = CompletedLessonSerializer(
            results,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

class LessonResultsView(APIView):
    """
    GET /api/v1/lessons/<lesson_id>/results/?child_id=17
    Vrati detaljan rezultat za to dete + njegov summary (ako postoji).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        child_id = request.query_params.get("child_id")
        if not child_id:
            return Response({"detail": "child_id is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        lesson = get_object_or_404(Lesson, id=lesson_id)
        child  = get_object_or_404(User, id=child_id)

        if lesson.creator != request.user or child.parent_id != request.user.id:
            return Response({"detail": "Forbidden."},
                            status=status.HTTP_403_FORBIDDEN)

        result = get_object_or_404(QuizResult, lesson=lesson, user=child)

        res_ser = SingleQuizResultSerializer(
            result,
            context={"request": request}
        )

        summary_obj = (LessonSummary.objects
                        .filter(lesson=lesson, creator=child)
                        .order_by("-created_at")
                        .first())
        summary_data = (LessonSummarySerializer(summary_obj).data
                        if summary_obj else None)

        return Response({
            "lesson_title": lesson.title,
            "child_username": child.first_name,
            "quiz_results": res_ser.data,
            "summary": summary_data,
        }, status=status.HTTP_200_OK)