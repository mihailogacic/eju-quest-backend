"""Models for custom user authentication and related activities."""

import random
import uuid
from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils.timezone import now


class UserManager(BaseUserManager):
    """Custom user manager handling user creation."""

    def _create_user(self, email, password=None, role='parent', **extra_fields):
        """Create and save a user with given email and password."""
        if not email:
            raise ValueError('Email is required.')

        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, role='parent', **extra_fields):
        """Create and return a regular user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('created_at', now())
        if role == 'parent':
            extra_fields.setdefault('is_active', False)
            extra_fields.setdefault('is_verified', False)
        return self._create_user(email, password, role, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        return self._create_user(email, password, role='parent', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model supporting Parent and Child roles."""

    ROLE_CHOICES = [
        ('parent', 'Parent'),
        ('child', 'Child'),
    ]

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='parent')
    accepted_terms_date = models.DateTimeField(null=True, blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='children'
    )
    is_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    email_confirmation_token = models.UUIDField(
        default=uuid.uuid4, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        """Return a string representation of the user."""
        return f"{self.email} ({self.role})"

    def has_children(self):
        """Check if a user has child accounts."""
        # pylint: disable=no-member
        return self.children.exists()

    def delete_user(self):
        """Soft delete a user by marking inactive and setting deletion time."""
        self.deleted_at = now()
        self.is_active = False
        self.save()


class OTP(models.Model):
    """Model for OTP codes for authentication and password resets."""

    OTP_PURPOSES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=OTP_PURPOSES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        """Generate OTP and set expiry if not already set."""
        if not self.otp_code:
            self.otp_code = str(random.randint(100000, 999999))
        if not self.expires_at:
            self.expires_at = now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if the OTP has expired."""
        return now() > self.expires_at

    def __str__(self):
        """Return a string representation of the OTP instance."""
        # pylint: disable=no-member
        return f"OTP ({self.purpose}) for {self.user.email}"


class UserActivityLog(models.Model):
    """Model logging user activity events like login/logout."""

    EVENT_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    ip_address = models.GenericIPAddressField()
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    event_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return string representation of user activity log entry."""
        # pylint: disable=no-member
        return f"{self.user.email} - {self.event_type} at {self.event_time}"


class SecurityLog(models.Model):
    """Model storing logs related to security incidents."""

    EVENT_TYPES = [
        ('failed_login', 'Failed Login'),
        ('otp_abuse', 'Multiple OTP Failures'),
        ('password_reset_fail', 'Failed Password Reset Attempt'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_description = models.TextField()
    event_time = models.DateTimeField(auto_now_add=True)
    failed_attempts = models.PositiveIntegerField(default=0)

    def increment_failed_attempts(self):
        """Increment the count of failed attempts."""
        self.failed_attempts += 1
        self.save()

    def reset_failed_attempts(self):
        """Reset the count of failed attempts to zero."""
        self.failed_attempts = 0
        self.save()

    def __str__(self):
        """Return string representation of a security log entry."""
        return f"{self.event_type} at {self.event_time}"
