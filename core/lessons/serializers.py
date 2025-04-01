"""
This module is responsible for validation and serialization
of data that comes to the backend from frontend.
"""

from rest_framework import serializers
from core.exceptions import CustomValidationException
from .models import Lesson, Sections, Quiz, QuizQuestions, QuizQuestionOptions, LessonSummary


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
    # options = QuizQuestionOptionSerializer(many=True)

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


class LessonSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for LessonSummary model.
    """

    class Meta:
        model = LessonSummary
        fields = ['id', 'lesson', 'description']
        read_only_fields = ['creator']

    def create(self, validated_data):
        """
        Overwrites default create method and 
        provides authenticated user
        """
        request = self.context.get('request')
        lesson_id = request.data.get('lesson_id')
        print(lesson_id)
        lesson = Lesson.objects.get(id=lesson_id)
        if request and hasattr(request, "user"):
            validated_data['creator'] = request.user
            validated_data['lesson'] = lesson
        return super().create(validated_data)
