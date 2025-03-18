"""URLs for the users app."""
from django.urls import path
from .views import (
    ChildRegistrationView,
    ProfileView,
    ParentDashboardView,
    UserSearchView,
    ChildDeactivateView
)

urlpatterns = [
    path('add_child/', ChildRegistrationView.as_view(), name='add-child'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('dashboard/', ParentDashboardView.as_view(), name='dashboard'),
    path('', UserSearchView.as_view(), name='user-search'),
    path('deactivate_child/<int:pk>/', ChildDeactivateView.as_view(), name='deactivate-child'),
]
