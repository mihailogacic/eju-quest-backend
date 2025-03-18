"""This module contains the URL patterns for the authentication app."""

from django.urls import path

from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    PasswordResetOTPRequestView,
    PasswordResetConfirmView,
    UserProfileView,
    DeleteAccountView,
    RemoveChildView,
    ChildListView
)

urlpatterns = [
    # Authentication routes
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/<uuid:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path(
        'auth/password-reset/request/',
        PasswordResetOTPRequestView.as_view(),
        name='password_reset_request'
    ),
    path(
        'auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),

    # User profile and management routes
    path('user/profile/', UserProfileView.as_view(), name='user_profile'),
    path('user/profile/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('users/children/', ChildListView.as_view(), name='list_children'),
    path('users/children/<int:child_id>/delete/', RemoveChildView.as_view(), name='remove_child'),
]
