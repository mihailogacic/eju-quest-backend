"""Serializers for user registration, authentication, and profile management."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer including user role.

    Extends the TokenObtainPairSerializer to add the user's role to
    the generated JWT token.
    """

    @classmethod
    def get_token(cls, user):
        """Add custom claims to token."""
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def create(self, validated_data):  # pylint: disable=unused-argument
        """Not implemented, as JWT creation is handled by get_token."""
        raise NotImplementedError('create() method is not used for this serializer.')

    def update(self, instance, validated_data):  # pylint: disable=unused-argument
        """Not implemented, as JWT creation is handled by get_token."""
        raise NotImplementedError('update() method is not used for this serializer.')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with validations and email confirmation."""

    confirm_password = serializers.CharField(write_only=True, min_length=8)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        """Define serializer fields and validation rules."""
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'password', 'confirm_password',
            'role', 'accepted_terms_date'
        ]

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email is already registered.')
        return value

    def validate_password(self, value):
        """Ensure password meets complexity requirements."""
        if (
            len(value) < 8
            or not any(char.isdigit() for char in value)
            or not any(char.isalpha() for char in value)
            or not any(
                char in "!@#$%^&*()-_=+[{]}|;:',<.>/?`~" for char in value
            )
        ):
            raise serializers.ValidationError(
                'Password must be at least 8 characters long, '
                'contain letters, numbers, and special characters.'
            )
        return value

    def validate(self, attrs):
        """Validate passwords match and terms acceptance."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})

        if not attrs.get('accepted_terms_date'):
            raise serializers.ValidationError({'accepted_terms_date': 'Terms must be accepted.'})

        role = attrs.get('role', 'parent')
        request_user = self.context.get('request').user
        if role == 'child' and (not request_user or request_user.role != 'parent'):
            raise serializers.ValidationError({'role': 'Only parents can create child accounts.'})

        return attrs

    def create(self, validated_data):
        """Create user and send confirmation email if needed."""
        validated_data.pop('confirm_password')
        validated_data.pop('accepted_terms_date')

        role = validated_data.get('role', 'parent')
        validated_data['is_active'] = role != 'parent'
        validated_data['is_verified'] = False
        validated_data['accepted_terms_date'] = now()

        try:
            user = User.objects.create_user(**validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError('Failed to create user.') from exc

        if user.role == 'parent':
            try:
                self.send_confirmation_email(user)
            except Exception as exc:
                user.delete()
                raise serializers.ValidationError('Failed to send confirmation email.') from exc

            return {'detail': 'Registration successful. Please confirm your email.'}

        refresh = RefreshToken.for_user(user)
        return {
            'user': UserProfileSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }

    def send_confirmation_email(self, user):
        """Send email verification link."""
        confirmation_link = f"{settings.FRONTEND_URL}/verify-email/{user.email_confirmation_token}/"
        send_mail(
            subject='Verify Your Email - EjuQuest',
            message=f'Click the link to confirm your email:\n\n{confirmation_link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetOTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset OTP."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Ensure the email corresponds to an existing user."""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user found with this email address.')
        return value

    def create(self, validated_data):
        """Generate OTP and send via email."""
        # pylint: disable=no-member
        user = User.objects.get(email=validated_data['email'])
        otp_instance = OTP.objects.create(
            user=user,
            purpose='password_reset',
            expires_at=now() + timedelta(minutes=10)
        )
        send_mail(
            subject='Your Password Reset OTP - EjuQuest',
            message=(
                f'Your OTP is: {otp_instance.otp_code}. '\
                'It expires in 10 minutes.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return otp_instance

    def update(self, instance, validated_data):  # pylint: disable=unused-argument
        """Not implemented, as this serializer does not handle updates."""
        raise NotImplementedError('update() method is not used for this serializer.')


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset via OTP."""

    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        """Validate provided email and OTP code."""
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError('Invalid email or OTP.')

        # pylint: disable=no-member
        otp_instance = OTP.objects.filter(
            user=user,
            purpose='password_reset',
            otp_code=attrs['otp_code'],
            is_used=False
        ).last()
        if not otp_instance or otp_instance.is_expired() or otp_instance.attempts >= 5:
            raise serializers.ValidationError('Invalid or expired OTP.')

        self.context.update({'user': user, 'otp_instance': otp_instance})
        return attrs

    def create(self, validated_data):  # pylint: disable=unused-argument
        """Not implemented, as this serializer uses save() instead of create()."""
        raise NotImplementedError('create() method is not used for this serializer.')

    def update(self, instance, validated_data):  # pylint: disable=unused-argument
        """Not implemented, as this serializer uses save() instead of update()."""
        raise NotImplementedError('update() method is not used for this serializer.')

    def save(self, **kwargs):  # fix arguments-differ by using kwargs
        """Set new password and invalidate OTP."""
        user = self.context['user']
        otp_instance = self.context['otp_instance']
        user.set_password(self.validated_data['new_password'])
        user.save()
        otp_instance.is_used = True
        otp_instance.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile retrieval and update."""

    class Meta:
        """Define serializer fields and read-only fields."""
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'created_at']
