"""
This module contains connection to URLs accross all applications
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('authentication.urls')),
    path('api/v1/', include('lessons.urls')),
    path('api/v1/', include('quiz.urls')),
]
