"""Utility functions for authentication-related tasks."""

from django.utils.timezone import now
from django.db.models import Q

from .models import SecurityLog


def log_security_event(
    user,
    email,
    ip_address,
    event_type,
    event_description,
    failed_attempts=0
):
    """Log security-related events such as failed logins or password resets.

    Args:
        user (User): User object related to the event (can be None).
        email (str): Email associated with the event.
        ip_address (str): IP address involved in the event.
        event_type (str): Type of event.
        event_description (str): Description of the event.
        failed_attempts (int, optional): Number of failed attempts. Defaults to 0.
    """
    # pylint: disable=no-member
    SecurityLog.objects.create(
        user=user,
        email=email,
        ip_address=ip_address,
        event_type=event_type,
        event_description=event_description,
        failed_attempts=failed_attempts,
        event_time=now()
    )


def log_failed_login_attempt(user, email, ip_address):
    """Log a failed login attempt and increment failed_attempts cumulatively.

    Looks up the most recent failed_login event for this user/email and IP
    combination. If it exists, increments failed_attempts on that entry.
    Otherwise, creates a new SecurityLog with failed_attempts set to 1.
    """
    query = Q(ip_address=ip_address, event_type="failed_login")

    if user is not None:
        query &= Q(user=user)
    else:
        query &= Q(email=email)

    last_log = (
        SecurityLog.objects
        .filter(query)
        .order_by("-event_time")
        .first()
    )

    if last_log:
        last_log.increment_failed_attempts()
        return last_log

    return SecurityLog.objects.create(
        user=user,
        email=email,
        ip_address=ip_address,
        event_type="failed_login",
        event_description="Failed login attempt.",
        failed_attempts=1,
        event_time=now()
    )
