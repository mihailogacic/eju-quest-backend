from rest_framework import generics, status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, PasswordResetOTPRequestSerializer, PasswordResetConfirmSerializer, UserProfileSerializer
from .utils import log_security_event
from django.utils.timezone import now

User = get_user_model()

class VerifyEmailView(generics.GenericAPIView):
    """API endpoint for verifying a user's email using the confirmation token."""

    permission_classes = [AllowAny]
    
    def get(self, request, token):
        user = get_object_or_404(User, email_confirmation_token=token)
        if user.is_verified:
            return Response({"message": "Email already verified."}, status=status.HTTP_200_OK)
        
        # Mark the user as verified and activate their account.
        user.is_verified = True
        user.is_active = True
        user.email_confirmation_token = None  # Invalidate the token after use.
        user.save()
        
        return Response({"message": "Email verified successfully. You can now log in."}, status=status.HTTP_200_OK)

class RegisterView(generics.GenericAPIView):
    """API endpoint for user registration."""
    
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        """Set permissions based on user role."""
        if self.request.method == "POST" and self.request.data.get('role') == 'child':
            return [IsAuthenticated()]  # Parents must be logged in to add child accounts.
        return [AllowAny()]

    def post(self, request, *args, **kwargs):
        """Handle user registration."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user_data = serializer.save()
            return Response(user_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(TokenObtainPairView):
    """API endpoint for user login."""
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return response
        except Exception as e:
            ip_address = request.META.get('REMOTE_ADDR')
            email = request.data.get('email', '')
            user = User.objects.filter(email=email).first()
            log_security_event(
                user=user,
                email=email,
                ip_address=ip_address,
                event_type="failed_login",
                event_description="Failed login attempt.",
                failed_attempts=1
            )
            raise e

class PasswordResetOTPRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetOTPRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Request a password reset OTP.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_instance = serializer.save()
        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=otp_instance.user,
            email=otp_instance.user.email,
            ip_address=ip_address,
            event_type="password_reset_request",
            event_description="Password reset OTP requested.",
            failed_attempts=0
        )
        return Response({"message": "OTP has been sent to your email."}, status=status.HTTP_200_OK)
    
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Confirm OTP and reset the user's password.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        ip_address = request.META.get('REMOTE_ADDR')
        log_security_event(
            user=user,
            email=user.email,
            ip_address=ip_address,
            event_type="password_reset_success",
            event_description="Password reset successfully.",
            failed_attempts=0
        )
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
    
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to retrieve and update the authenticated user's profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class DeleteAccountView(APIView):
    """
    API endpoint for soft deleting (disabling) the user account.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        user.deleted_at = now()
        user.is_active = False
        user.save()
        return Response({"message": "Your account has been disabled."}, status=status.HTTP_200_OK)
    
class ChildListView(generics.ListAPIView):
    """
    API endpoint to list all child accounts for the authenticated parent.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return only children of the authenticated parent
        return self.request.user.children.all()

class RemoveChildView(APIView):
    """
    API endpoint for a parent to soft delete a child account.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, child_id, *args, **kwargs):
        parent = request.user
        try:
            child = parent.children.get(id=child_id)
        except User.DoesNotExist:
            return Response({"error": "Child account not found."}, status=status.HTTP_404_NOT_FOUND)
        child.deleted_at = now()
        child.is_active = False
        child.save()
        return Response({"message": "Child account has been disabled."}, status=status.HTTP_200_OK)