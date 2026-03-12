"""
This module defines the database models for the lesson management system.

It includes models for lessons, sections, quizzes, quiz questions, quiz options, 
and lesson summaries. Each model represents a key component of the learning 
platform and is linked via ForeignKey relationships.
"""
from django.db import models
from django.utils.timezone import now

from authentication.models import User


class Lesson(models.Model):
    """
    Represents a lesson created by a user. 

    Attributes:
        creator (User): The user who created the lesson.
        title (str): The title of the lesson.
        image (ImageField): The image associated with the lesson.
        age_level (int): The target age level for the lesson.
        lesson_length (str): The estimated duration of the lesson.
        lesson_status (str): The status of the lesson (e.g., "draft", "published").
    """

    class LessonLength(models.TextChoices):
        SHORT = "short", "Short"
        MEDIUM = "medium", "Medium"
        LONG = "long", "Long"

    class LessonStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"

    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to='lesson_images/', blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)
    age_level = models.IntegerField()
    lesson_length = models.CharField(
        max_length=10,
        choices=LessonLength.choices,
    )
    status = models.CharField(
        max_length=10,
        choices=LessonStatus.choices,
        default=LessonStatus.PENDING,
    )
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.creator.first_name} {self.creator.first_name} - {self.title}'

class LessonVisit(models.Model):
    """
    Tracks when a user views a specific lesson.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visited_at']

class Section(models.Model):
    """
    Represents a section within a lesson. 

    Attributes:
        lesson (Lesson): The lesson this section belongs to.
        heading (str): The heading of the section.
        content (str): The detailed content of the section.
    """

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    heading = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return f'{self.lesson.title}: {self.heading}'


class QuizQuestionOption(models.Model):
    """
    Represents an option for a quiz question.

    Attributes:
        option (str): The choice identifier (A, B, C, or D).
        option_text (str): The text for the answer choice.
        correct (bool): Indicates if the option is the correct answer.
    """

    OPTION_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]

    question = models.ForeignKey(
        'QuizQuestion',
        on_delete=models.CASCADE,
        related_name='options',
    )
    option = models.CharField(
        max_length=10,
        choices=OPTION_CHOICES,
    )
    option_text = models.CharField(max_length=255)
    correct = models.BooleanField(default=False)

    def __str__(self):
        return (
            f'Option {self.option}: {self.option_text} '
            f'({"Correct" if self.correct else "Incorrect"})'
        )

class Quiz(models.Model):
    """
    Represents a quiz associated with a lesson.

    Attributes:
        lesson (Lesson): The lesson this quiz belongs to.
    """

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)

    def __str__(self):
        return f'Quiz for Lesson: {self.lesson.title}'


class QuizQuestion(models.Model):
    """
    Represents a question in a quiz.

    Attributes:
        quiz (Quiz): The quiz this question belongs to.
        question_text (str): The text of the quiz question.
        options (QuizQuestionOption): The possible answer options (1:N via FK).
    """

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=255)

    def __str__(self):
        return f'Question: {self.question_text}'

class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()
    correct_answers = models.PositiveSmallIntegerField()
    total_questions = models.PositiveSmallIntegerField()
    remaining_time = models.PositiveIntegerField()
    passed = models.BooleanField()
    answers = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'quiz')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} – {self.quiz.lesson.title} ({self.score}%)'

class LessonSummary(models.Model):
    """
    Represents a summary of a lesson, created by a user.

    Attributes:
        creator (User): The user who created the summary.
        description (str): The content of the lesson summary.
    """

    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    description = models.TextField()
    remaining_time = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Lesson Summary by {self.creator.first_name} {self.creator.last_name}'
