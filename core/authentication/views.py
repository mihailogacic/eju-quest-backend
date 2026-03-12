"""Views for user authentication and account management."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer
)
from .utils import log_security_event

User = get_user_model()


class VerifyEmailView(generics.GenericAPIView):
    """
    Verify a user's email using a confirmation link.
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            # Decode the uidb64 to get the user id
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # Check the token validity and update the user accordingly
        if user is not None and default_token_generator.check_token(user, token):
            if user.is_verified:
                return Response(
                    {'message': 'Email already verified.'},
                    status=status.HTTP_200_OK
                )
            user.is_verified = True
            user.is_active = True
            user.save()
            return Response(
                {'message': 'Email verified successfully.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

class RegisterView(generics.GenericAPIView):
    """Register new users with role-specific permissions."""

    serializer_class = RegisterSerializer

    def get_permissions(self):
        """Define permissions based on user role."""
        role = self.request.data.get('role', 'parent')
        if self.request.method == 'POST' and role == 'child':
            return [IsAuthenticated()]
        return [AllowAny()]

    def post(self, request, *_args, **_kwargs):
        """Handle user registration requests."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user_data = serializer.save()
        return Response(user_data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """Authenticate users and log security events on failure."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # The serializer returns tokens with keys "refresh" and "access"
            token_data = serializer.validated_data
            user = serializer.user
            custom_response = {
                "access_token": token_data.get("access"),
                "refresh_token": token_data.get("refresh"),
                "user": UserProfileSerializer(user).data,
            }
            return Response(custom_response, status=status.HTTP_200_OK)
        except Exception as exc:
            ip_address = request.META.get("REMOTE_ADDR")
            email = request.data.get("email", "")
            user = User.objects.filter(email=email).first()
            log_security_event(
                user=user,
                email=email,
                ip_address=ip_address,
                event_type="failed_login",
                event_description="Failed login attempt.",
                failed_attempts=1
            )
            raise exc


class PasswordResetRequestView(generics.GenericAPIView):
    """Request a password reset link."""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Generate and email the password reset link."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        ip_address = request.META.get("REMOTE_ADDR")
        log_security_event(
            user=user,
            email=email,
            ip_address=ip_address,
            event_type="password_reset_request",
            event_description="Password reset link requested.",
            failed_attempts=0
        )
        return Response(
            {"message": "Password reset link has been sent to your email."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm token and reset user's password."""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token, *args, **kwargs):
        """
        Validate token from the URL and update the user's password.
        Expects JSON payload with new_password and confirm_new_password.
        """
        serializer = self.get_serializer(data=request.data, context={"uidb64": uidb64, "token": token})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        ip_address = request.META.get("REMOTE_ADDR")
        log_security_event(
            user=user,
            email=user.email,
            ip_address=ip_address,
            event_type="password_reset_success",
            event_description="Password reset successful.",
            failed_attempts=0
        )
        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )
