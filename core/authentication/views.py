"""Views for user authentication and account management."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetOTPRequestSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer
)
from .utils import log_security_event

User = get_user_model()


class VerifyEmailView(generics.GenericAPIView):
    """Verify a user's email via a confirmation token."""

    permission_classes = [AllowAny]

    def get(self, _request, token):  # rename request to _request since it's unused
        """Verify email confirmation token."""
        user = get_object_or_404(User, email_confirmation_token=token)
        if user.is_verified:
            return Response(
                {'message': 'Email already verified.'},
                status=status.HTTP_200_OK
            )

        user.is_verified = True
        user.is_active = True
        user.email_confirmation_token = None
        user.save()

        return Response(
            {'message': 'Email verified successfully.'},
            status=status.HTTP_200_OK
        )


class RegisterView(generics.GenericAPIView):
    """Register new users with role-specific permissions."""

    serializer_class = RegisterSerializer

    def get_permissions(self):
        """Define permissions based on user role."""
        role = self.request.data.get('role')
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

    def post(self, request, *_args, **_kwargs):
        """Handle user login and log failed attempts."""
        try:
            return super().post(request, *_args, **_kwargs)
        except Exception as exc:
            ip_address = request.META.get('REMOTE_ADDR')
            email = request.data.get('email', '')
            user = User.objects.filter(email=email).first()
            log_security_event(
                user=user,
                email=email,
                ip_address=ip_address,
                event_type='failed_login',
                event_description='Failed login attempt.',
                failed_attempts=1
            )
            raise exc


class PasswordResetOTPRequestView(generics.GenericAPIView):
    """Request OTP for password reset."""

    serializer_class = PasswordResetOTPRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *_args, **_kwargs):
        """Generate and email password reset OTP."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_instance = serializer.save()
        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=otp_instance.user,
            email=otp_instance.user.email,
            ip_address=ip_address,
            event_type='password_reset_request',
            event_description='Password reset OTP requested.',
            failed_attempts=0
        )
        return Response(
            {'message': 'OTP has been sent to your email.'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm OTP and reset user's password."""

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *_args, **_kwargs):
        """Validate OTP and update password."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=user,
            email=user.email,
            ip_address=ip_address,
            event_type='password_reset_success',
            event_description='Password reset successful.',
            failed_attempts=0
        )
        return Response(
            {'message': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update user profile information."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return current authenticated user."""
        return self.request.user


class DeleteAccountView(APIView):
    """Disable (soft delete) the user's account."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, *_args, **_kwargs):
        """Soft delete the current user's account."""
        user = request.user
        user.deleted_at = now()
        user.is_active = False
        user.save()
        return Response(
            {'message': 'Your account has been disabled.'},
            status=status.HTTP_200_OK
        )


class ChildListView(generics.ListAPIView):
    """List child accounts for authenticated parent user."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return queryset of children for the current user."""
        return self.request.user.children.all()


class RemoveChildView(APIView):
    """Disable a child account."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, child_id, *_args, **_kwargs):
        """Soft delete a specified child account."""
        try:
            child = request.user.children.get(id=child_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Child account not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        child.deleted_at = now()
        child.is_active = False
        child.save()
        return Response(
            {'message': 'Child account has been disabled.'},
            status=status.HTTP_200_OK
        )
