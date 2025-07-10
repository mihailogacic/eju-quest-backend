"""
Serializers for user registration, authentication, and profile management.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.timezone import now
from retrying import retry
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer including user role."""

    @classmethod
    def get_token(cls, user):
        """Add custom claims to token."""
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def create(self, validated_data):
        """Not implemented, as JWT creation is handled by get_token."""
        raise NotImplementedError("create() method is not used for this serializer.")

    def update(self, instance, validated_data):
        """Not implemented, as JWT creation is handled by get_token."""
        raise NotImplementedError("update() method is not used for this serializer.")


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with validations and email confirmation."""

    confirm_password = serializers.CharField(write_only=True, min_length=8)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default="parent")

    class Meta:
        """Define serializer fields and validation rules."""
        model = User
        fields = [
            "id", "first_name", "last_name", "email", "password",
            "confirm_password", "role"
        ]

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_password(self, value):
        """Ensure password meets complexity requirements."""
        if (
            len(value) < 8
            or not any(char.isdigit() for char in value)
            or not any(char.isalpha() for char in value)
            or not any(char in "!@#$%^&*()-_=+[{]}|;:',<.>/?`~" for char in value)
        ):
            raise serializers.ValidationError(
                "Password must be at least 8 characters long, contain letters, numbers, "
                "and special characters."
            )
        return value

    def validate(self, attrs):
        """Validate that passwords match and enforce role restrictions."""
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        role = attrs.get("role", "parent")
        request_user = self.context.get("request").user
        if role == "child" and (not request_user or request_user.role != "parent"):
            raise serializers.ValidationError({"role": "Only parents can create child accounts."})
        return attrs

    def create(self, validated_data):
        """Create user and send confirmation email if needed."""
        validated_data.pop("confirm_password")
        role = validated_data.get("role", "parent")
        validated_data["is_active"] = role != "parent"
        validated_data["is_verified"] = False

        try:
            user = User.objects.create_user(**validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError("Failed to create user.") from exc

        if user.role == "parent":
            try:
                self.send_confirmation_email(user)
            except Exception as exc:
                print(exc)
                user.delete()
                raise serializers.ValidationError("Failed to send confirmation email.") from exc

            return {"detail": "Registration successful. Please confirm your email."}

        refresh = RefreshToken.for_user(user)
        return {
            "user": UserProfileSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def send_confirmation_email(self, user):
        """Send email with confirmation link."""
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}"
        send_mail(
            subject="Confirm Your Account",
            message=f"Click the link to confirm your account: {verification_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset link."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Ensure the email corresponds to an existing user."""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value

    def save(self):
        """Generate a reset token and send an email with a reset link."""
        email = self.validated_data["email"]
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # Construct reset link that includes both uid and token.
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
        send_mail(
            subject="Reset Your Password - EjuQuest",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset via token."""
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        """Validate that passwords match and that the token is valid."""
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError("Passwords do not match.")

        # Retrieve uidb64 and token from the serializer context
        uidb64 = self.context.get("uidb64")
        token = self.context.get("token")
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid uid.")

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Invalid or expired token.")

        attrs["user"] = user
        return attrs

    def save(self):
        """Set the new password for the user."""
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile retrieval and update."""

    class Meta:
        """Define serializer fields and read-only fields."""
        model = User
        fields = ["id", "first_name", "last_name", "email", "role"]
        read_only_fields = ["id", "email", "role"]
