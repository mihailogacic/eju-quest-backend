"""Models for user-generated summaries."""

from django.db import models
from django.conf import settings


class UserSummary(models.Model):
    """Model representing a summary created by a user."""

    description = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='summaries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a string representation of the summary."""
        # pylint: disable=no-member
        return f"Summary {self.id} by {self.user.email}"
