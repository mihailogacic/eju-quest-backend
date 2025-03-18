"""Utility functions for authentication-related tasks."""

from django.utils.timezone import now

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
        event_type (str): Type of event ('failed_login', 'otp_abuse', 'password_reset_fail').
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
