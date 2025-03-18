from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now

from .models import OTP

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Customize JWT to include user role in the token payload"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role  # Add user role to the token
        return token


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with proper validations and email confirmation."""

    confirm_password = serializers.CharField(write_only=True, min_length=8)
    terms_accepted = serializers.BooleanField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'password', 'confirm_password',
            'role',  'terms_accepted'
        ]

    def validate_email(self, value):
        """Check if email is already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_password(self, value):
        """Check password strength."""
        if len(value) < 8 or not any(char.isdigit() for char in value) or not any(char.isalpha() for char in value) or not any(char in "!@#$%^&*()-_=+[{]}|;:',<.>/?`~" for char in value):
            raise serializers.ValidationError(
                "Password must be at least 8 characters long, contain a letter, a number, and a special character.")
        return value

    def validate(self, attrs):
        """Additional validations for passwords, terms, and roles."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {"password": "Passwords do not match."})

        if not attrs.get('terms_accepted', False):
            raise serializers.ValidationError(
                {"terms_accepted": "Terms must be accepted to register."})

        # Restrict children creation
        role = attrs.get('role', 'parent')
        request_user = self.context.get('request').user
        if role == 'child' and (not request_user or request_user.role != 'parent'):
            raise serializers.ValidationError(
                {"role": "Only a parent can create child accounts."})

        return attrs

    def create(self, validated_data):
        """Create user and handle email confirmation."""
        validated_data.pop('confirm_password')
        validated_data.pop('terms_accepted')
        role = validated_data.get('role', 'parent')

        validated_data['is_active'] = False if role == 'parent' else True
        validated_data['is_verified'] = False
        validated_data['accepted_terms_date'] = now()

        try:
            user = User.objects.create_user(**validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                {"detail": "Failed to create user. Please check the input data."})

        if user.role == 'parent':
            try:
                self.send_confirmation_email(user)
            except Exception:
                user.delete()  # Clean up if email fails
                raise serializers.ValidationError(
                    {"detail": "Failed to send confirmation email. Please try again later."})

            return {'detail': 'Registration successful. Please confirm your email.'}
        else:
            refresh = RefreshToken.for_user(user)
            return {
                'user': UserProfileSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }

    def send_confirmation_email(self, user):
        """Send a confirmation email."""
        confirmation_link = f"{settings.FRONTEND_URL}/verify-email/{user.email_confirmation_token}/"
        send_mail(
            subject="Verify Your Email - EjuQuest",
            message=f"Please click the link below to confirm your email address:\n\n{confirmation_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = User.objects.filter(email=value).first()
        if not user:
            raise serializers.ValidationError(
                "No user found with this email address.")
        return value

    def create(self, validated_data):
        user = User.objects.get(email=validated_data['email'])
        # Create a new OTP for password reset with a 10-minute expiry.
        otp_instance = OTP.objects.create(
            user=user,
            purpose='password_reset',
            expires_at=now() + timedelta(minutes=10)
        )
        # Send the OTP via email.
        send_mail(
            subject="Your Password Reset OTP - EjuQuest",
            message=f"Your OTP is: {otp_instance.otp_code}. It expires in 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return otp_instance


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        otp_code = attrs.get("otp_code")
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError("Invalid email or OTP.")
        # Find a matching, unused OTP for password reset.
        otp_instance = OTP.objects.filter(
            user=user, purpose='password_reset', otp_code=otp_code, is_used=False).last()
        if not otp_instance:
            raise serializers.ValidationError("Invalid OTP.")
        if otp_instance.is_expired():
            raise serializers.ValidationError(
                "OTP has expired. Please request a new one.")
        if otp_instance.attempts >= 5:
            raise serializers.ValidationError(
                "Too many failed attempts. Please request a new OTP.")
        # Save the OTP instance for use in save() method.
        self.context['otp_instance'] = otp_instance
        self.context['user'] = user
        return attrs

    def save(self):
        user = self.context['user']
        otp_instance = self.context['otp_instance']
        new_password = self.validated_data.get("new_password")
        # Reset the user's password.
        user.set_password(new_password)
        user.save()
        # Mark the OTP as used.
        otp_instance.is_used = True
        otp_instance.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and updating the user profile."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name',
                  'email', 'role', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'created_at']
