"""
This module is responsible for validation and serialization
of data that comes to the backend from frontend.
"""

from rest_framework import serializers
from core.exceptions import CustomValidationException
from .models import Lesson, Sections, Quiz, QuizQuestions, QuizQuestionOptions, LessonSummary, QuizResult


class LessonSerializer(serializers.ModelSerializer):
    """
    Serializer for Lesson model.
    """
    creator = serializers.SerializerMethodField()
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'image',
                    'age_level', 'lesson_length', 'description', 'status', 'creator']
        read_only_fields = ['creator']

    def get_creator(self, obj):
        return obj.creator.first_name

    def validate_age_level(self, value):
        """
        Checks for age provided, it must be between 4 and 18

        Args:
            value (number): age

        Raises:
            CustomValidationException

        Returns:
            number: age
        """

        if not 4 <= value <= 18:
            raise CustomValidationException(
                "Age level must be between 4 and 18.")
        return value

    def validate_lesson_length(self, value):
        """Can have only three lesson lengths

        Args:
            value (string): lesson length

        Raises:
            CustomValidationException

        Returns:
            string: lesson length
        """
        valid_lengths = ['short', 'medium', 'long']
        if value.lower() not in valid_lengths:
            raise CustomValidationException(
                "Lesson length must be either short, medium, or long.")
        return value

    def validate_image(self, value):
        """Validates if file is image

        Args:
            value (file): image of topic

        Raises:
            CustomValidationException: 

        Returns:
            file: image of topic
        """
        if not hasattr(value, 'content_type'):
            raise CustomValidationException(
                "Invalid file. The file must be an image.")
        if not value.content_type.startswith('image/'):
            raise CustomValidationException(
                "Invalid file. The file must be an image.")
        return value

    def create(self, validated_data):
        """
        Overwrites default create method and 
        provides authenticated user
        """
        request = self.context.get('request')
        if request and hasattr(request, "user"):
            validated_data['creator'] = request.user
        return super().create(validated_data)

class SectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Sections model.
    """
    class Meta:
        model = Sections
        fields = ['heading', 'content']

class LessonDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Lesson model with related sections.
    """
    sections = SectionSerializer(many=True, source='sections_set')

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'image', 'age_level', 'lesson_length', 'status', 'sections']

class QuizQuestionOptionSerializer(serializers.ModelSerializer):
    """
    Serializer for QuizQuestionOptions model.
    """

    class Meta:
        model = QuizQuestionOptions
        fields = ['id', 'option', 'option_text', 'correct']


class QuizQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for QuizQuestions model.
    """
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())
    options = QuizQuestionOptionSerializer(many=True)

    class Meta:
        model = QuizQuestions
        fields = ['id', 'quiz', 'question_text', 'options']


class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer for Quiz model.
    Accepts a lesson ID for creation and returns lesson details.
    """
    lesson = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.all(), write_only=True
    )
    lesson_detail = LessonSerializer(source='lesson', read_only=True)
    questions = QuizQuestionSerializer(many=True, read_only=True, source='quizquestions_set')

    class Meta:
        model = Quiz
        fields = ['id', 'lesson', 'lesson_detail', 'questions']

class QuizResultSerializer(serializers.ModelSerializer):
    child_username = serializers.SerializerMethodField()

    class Meta:
        model = QuizResult
        fields = (
            'id', 'child_username', 'score',
            'correct_answers', 'total_questions', 'passed', 'answers', 'created_at'
        )
    
    def get_child_username(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}"

class LessonSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for LessonSummary model.
    """

    class Meta:
        model = LessonSummary
        fields = ['id', 'lesson', 'description', 'remaining_time', 'created_at']
        read_only_fields = ['creator']

    def create(self, validated_data):
        request = self.context.get('request')
        lesson_id = request.data.get('lesson_id')
        raw_time  = request.data.get('remaining_time')
        from .services import LessonServices
        remaining = LessonServices.parse_remaining_time(raw_time)
        if remaining is None:
            raise serializers.ValidationError({
                "remaining_time": "Invalid format, must be seconds|mm:ss|ms"
            })
        validated_data['remaining_time'] = remaining

        lesson = Lesson.objects.get(id=lesson_id)
        validated_data['creator'] = request.user
        validated_data['lesson'] = lesson
        return super().create(validated_data)

class CompletedLessonSerializer(serializers.ModelSerializer):
    child_username = serializers.SerializerMethodField()
    child_id = serializers.IntegerField(source="user.id")
    id = serializers.IntegerField(source="lesson.id")
    title = serializers.CharField(source="lesson.title")
    lesson_image = serializers.SerializerMethodField()
    completed_at = serializers.DateTimeField(source="created_at")

    class Meta:
        model  = QuizResult
        fields = (
            "child_username", "child_id",
            "id", "title", "passed",
            "completed_at", "lesson_image",
        )

    def get_child_username(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}"

    def get_lesson_image(self, obj):
        request = self.context.get("request")
        img = obj.lesson.image
        if img and hasattr(img, "url"):
            return request.build_absolute_uri(img.url)
        return None

class SingleQuizResultSerializer(serializers.ModelSerializer):
    child_username = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    lesson_image = serializers.SerializerMethodField()

    class Meta:
        model  = QuizResult
        exclude = ("lesson", "user", "updated_at")

    def get_answers(self, obj):
        """
        Za svaki zapis u obj.answers (JSONField sa question_id, selected_option, correct),
        dohvatimo QuizQuestions instancu, serijalizujemo je postojećim QuizQuestionSerializer-om,
        i iz njega kreiramo dict koji API očekuje.
        """
        detail = []
        for entry in obj.answers:
            q_id = entry["question_id"]
            selected = entry["selected_option"]
            correct_flag = entry["correct"]

            question = QuizQuestions.objects.get(pk=q_id)
            q_data = QuizQuestionSerializer(question).data

            opts_dict = {opt["option"]: opt["option_text"] for opt in q_data["options"]}

            correct_opt = next((opt["option"] for opt in q_data["options"] if opt["correct"]), None)

            detail.append({
                "question_text":    q_data["question_text"],
                "options":          opts_dict,
                "correct_option":   correct_opt,
                "selected_option":  selected,
                "correct":          correct_flag,
            })

        return detail

    def get_child_username(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}"

    def get_lesson_image(self, obj):
        request = self.context.get("request")
        img = obj.lesson.image
        if img and hasattr(img, "url"):
            return request.build_absolute_uri(img.url)
        return None