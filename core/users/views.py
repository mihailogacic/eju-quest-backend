"""Views for user management, including child registration and searching."""

from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .serializers import (
    ChildRegistrationSerializer,
    UserProfileSerializer,
    SummarySerializer
)
from .models import Summary

User = get_user_model()


class IsParent(permissions.BasePermission):
    """Custom permission ensuring the logged-in user is a parent."""

    def has_permission(self, request, view):
        """Only allow if the user is authenticated and has role='parent'."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'parent'
        )


class ChildRegistrationView(generics.CreateAPIView):
    """View for registering child accounts under a parent."""

    serializer_class = ChildRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsParent]

    def post(self, request, *_args, **_kwargs):
        """Handle POST request to register a child account."""
        try:
            return super().post(request, *_args, **_kwargs)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Profile view for both parent and child (GET, PUT/PATCH)."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrieve the currently authenticated user."""
        return self.request.user

    def get(self, request, *_args, **_kwargs):
        """Handle GET request to retrieve user profile."""
        try:
            return super().get(request, *_args, **_kwargs)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *_args, **_kwargs):
        """Handle PUT request to update user profile."""
        try:
            return super().put(request, *_args, **_kwargs)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *_args, **_kwargs):
        """Handle PATCH request to partially update user profile."""
        try:
            return super().patch(request, *_args, **_kwargs)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ParentDashboardView(generics.GenericAPIView):
    """Parent dashboard: lists the parent, child users, and summaries."""

    permission_classes = [permissions.IsAuthenticated, IsParent]

    def get(self, request, *_args, **_kwargs):
        """Retrieve all related child accounts and their summaries."""
        try:
            # List the parent and all child users added by the parent.
            users = User.objects.filter(
                Q(id=request.user.id) | Q(parent=request.user),
                is_active=True
            )
            users_serializer = UserProfileSerializer(users, many=True)

            # pylint: disable=no-member
            summaries = Summary.objects.filter(
                creator__parent=request.user
            )
            summaries_serializer = SummarySerializer(summaries, many=True)

            data = {
                "users": users_serializer.data,
                "summaries": summaries_serializer.data,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class UserSearchView(generics.ListAPIView):
    """Allows searching for users by first name, last name, or email."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter users by search term if provided."""
        queryset = User.objects.all()
        search_term = self.request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
                | Q(email__icontains=search_term)
            )
        return queryset


class ChildDeactivateView(generics.DestroyAPIView):
    """Allows a parent to soft-delete (deactivate) a child account."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsParent]
    lookup_field = 'pk'

    def get_queryset(self):
        """Return only active child accounts for the requesting parent."""
        return User.objects.filter(
            parent=self.request.user,
            role='child',
            is_active=True
        )

    def delete(self, request, *_args, **_kwargs):
        """Deactivate the specified child account via soft delete."""
        try:
            instance = self.get_object()
            instance.delete_user()  # Use the soft delete method from the model.
            return Response(
                {"detail": "Child account deactivated successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
