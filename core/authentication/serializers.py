from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
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
    """Serializer for user registration with email confirmation for parents."""
    
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'confirm_password', 'role', 'parent']
        extra_kwargs = {
            'parent': {'read_only': True}  # Only set automatically for child accounts
        }

    def validate(self, attrs):
        """Ensure role restrictions are followed."""
        role = attrs.get('role')
        request_user = self.context.get('request').user

        if role == 'child':
            # Ensure only parents can create child accounts.
            if not request_user or request_user.role != 'parent':
                raise serializers.ValidationError("Only a parent can create child accounts.")
        return attrs

    def create(self, validated_data):
        """Create a new user and send a confirmation email if it's a parent."""
        # Remove confirm_password from the validated data.
        validated_data.pop('confirm_password')
        role = validated_data.get('role', 'parent')
        request_user = self.context.get('request').user

        if role == 'child' and request_user:
            validated_data['parent'] = request_user
        # For parent accounts, mark inactive so they must confirm their email.
        if role == 'parent':
            validated_data['is_active'] = False
            validated_data['is_verified'] = False

        user = User.objects.create_user(**validated_data)

        if user.role == 'parent':
            self.send_confirmation_email(user)
            return {'message': 'Registration successful. Please confirm your email.'}
        else:
            refresh = RefreshToken.for_user(user)
            from .serializers import UserProfileSerializer  # Ensure this is imported without circular dependency
            return {
                'user': UserProfileSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }

    def send_confirmation_email(self, user):
        """Send an email containing the confirmation link."""
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
            raise serializers.ValidationError("No user found with this email address.")
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
        otp_instance = OTP.objects.filter(user=user, purpose='password_reset', otp_code=otp_code, is_used=False).last()
        if not otp_instance:
            raise serializers.ValidationError("Invalid OTP.")
        if otp_instance.is_expired():
            raise serializers.ValidationError("OTP has expired. Please request a new one.")
        if otp_instance.attempts >= 5:
            raise serializers.ValidationError("Too many failed attempts. Please request a new OTP.")
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
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'accepted_terms_date', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'accepted_terms_date', 'created_at']
