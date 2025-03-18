from django.urls import path
from .views import RegisterView, VerifyEmailView, LoginView, PasswordResetOTPRequestView, PasswordResetConfirmView, UserProfileView, DeleteAccountView, ChildListView, RemoveChildView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/<uuid:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/request/', PasswordResetOTPRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('children/', ChildListView.as_view(), name='list_children'),
    path('children/<int:child_id>/delete/', RemoveChildView.as_view(), name='remove_child'),
]
