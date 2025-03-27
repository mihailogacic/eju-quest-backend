"""URL patterns for the authentication app."""

from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserProfileView,
    DeleteAccountView,
    RemoveChildView,
    ChildListView
)

urlpatterns = [
    # Authentication routes
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/<str:uidb64>/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    # Updated pattern: token confirmation URL includes uidb64 and token.
    path('auth/password-reset/confirm/<str:uidb64>/<str:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # User profile and management routes
    path('user/profile/', UserProfileView.as_view(), name='user_profile'),
    path('user/profile/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('users/children/', ChildListView.as_view(), name='list_children'),
    path('users/children/<int:child_id>/delete/', RemoveChildView.as_view(), name='remove_child'),
]
