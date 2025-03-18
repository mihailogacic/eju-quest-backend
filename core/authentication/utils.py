# authentication/utils.py
from .models import SecurityLog
from django.utils.timezone import now

def log_security_event(user, email, ip_address, event_type, event_description, failed_attempts=0):
    """
    Log a security-related event.
    event_type should be one of: 'failed_login', 'otp_abuse', 'password_reset_fail'.
    """
    SecurityLog.objects.create(
        user=user,
        email=email,
        ip_address=ip_address,
        event_type=event_type,
        event_description=event_description,
        event_time=now(),
        failed_attempts=failed_attempts
    )
