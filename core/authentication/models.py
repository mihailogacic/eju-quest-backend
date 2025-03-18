from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now
from django.conf import settings
import uuid
import random
from datetime import timedelta

class UserManager(BaseUserManager):
    """Custom user manager for handling user creation."""

    def _create_user(self, email, password=None, role='parent', **extra_fields):
        """Helper method to create a user with validated fields."""
        if not email:
            raise ValueError("Email is required")

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
    """Custom user model with Parent & Child roles."""
    
    ROLE_CHOICES = [
        ('parent', 'Parent'),
        ('child', 'Child'),
    ]

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='parent')
    zip_code = models.CharField(max_length=10, null=True, blank=True)
    subscription_plan = models.CharField(max_length=10, choices=[
        ('trial', 'Trial'),
        ('core', 'Core'),
        ('advanced', 'Advanced')
    ], default='trial')
    accepted_terms_date = models.DateTimeField(null=True, blank=True)
    
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    
    is_verified = models.BooleanField(default=False)  # Will be set to True after email confirmation
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    
    # New field for email confirmation token:
    email_confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Note: For parent accounts, is_active will be False until the email is confirmed.
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['']

    def __str__(self):
        return f"{self.email} ({self.role})"

    def has_children(self):
        """Check if a parent has registered child accounts."""
        return self.children.exists()

    def delete_user(self):
        """Soft delete the user account."""
        self.deleted_at = now()
        self.is_active = False
        self.save()

class OTP(models.Model):
    """Model for storing OTP codes for authentication and password reset."""

    OTP_PURPOSES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=OTP_PURPOSES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        """Auto-set expiry time and generate OTP."""
        if not self.otp_code:
            self.otp_code = f"{random.randint(100000, 999999)}"
        if not self.expires_at:
            self.expires_at = now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        return now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"



class UserActivityLog(models.Model):
    """Logs user login attempts and activity."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_logs")
    ip_address = models.GenericIPAddressField()
    event_type = models.CharField(max_length=50, choices=[('login', 'Login'), ('logout', 'Logout')])
    event_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.event_type} at {self.event_time}"


class SecurityLog(models.Model):
    """Stores security-related logs for failed logins and password resets."""

    EVENT_TYPES = [
        ("failed_login", "Failed Login"),
        ("otp_abuse", "Multiple OTP Failures"),
        ("password_reset_fail", "Failed Password Reset Attempt"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_description = models.TextField()
    event_time = models.DateTimeField(auto_now_add=True)
    failed_attempts = models.PositiveIntegerField(default=0)

    def increment_failed_attempts(self):
        """Increments failed login attempts."""
        self.failed_attempts += 1
        self.save()

    def reset_failed_attempts(self):
        """Resets failed login attempts counter."""
        self.failed_attempts = 0
        self.save()

    def __str__(self):
        return f"Security Event: {self.event_type} - {self.event_time}"
