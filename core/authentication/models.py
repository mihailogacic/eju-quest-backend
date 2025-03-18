"""
users/models.py

Contains tables related to AppUsers:
    AppUser: Table that defines user
    Ticket: Table that defines customer support ticket submitted by user
"""

import uuid
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


class AppUserManager(BaseUserManager):
    """
    AppUserManager handles user creation and superuser creation
    """

    def create_user(self, email, password, username, **extra_fields):
        """
        create_user method:
            - overrieds django-builtin create_user method
            - handles regular user creation by custom fields
        """

        if not email:
            raise ValueError('An email is required.')

        if not password:
            raise ValueError('A password is required.')

        if not username:
            raise ValueError('A username is required.')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, username):
        """
        create_superuser method:
          - overrides django-builtin create_superuser
          -  method and creates superuser by custom fields

        returns:
          user object
        """

        if not email:
            raise ValueError('An email is required.')

        if not password:
            raise ValueError('A password is required.')

        user = self.create_user(email, password, username,)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user


class AppUser(AbstractBaseUser, PermissionsMixin):
    """
    AppUser database table
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)  # user id
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75)
    role = models.CharField(default="parent")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = AppUserManager()
    is_staff = True

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.role}"
