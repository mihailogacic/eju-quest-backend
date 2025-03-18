from rest_framework import permissions

class IsParent(permissions.BasePermission):
    """Custom permission ensuring the logged-in user is a parent."""

    def has_permission(self, request, view):
        """Only allow if the user is authenticated and has role='parent'."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'parent'
        )
