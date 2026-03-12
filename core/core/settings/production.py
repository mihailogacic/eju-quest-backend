"""
Production settings.

Extends base settings with production database, Google Cloud Storage and Celery configuration.
"""

import os
import base64
import json
import logging

import dj_database_url
from ssl import CERT_NONE
from google.oauth2 import service_account

from .base import *  # noqa


# Database configuration for production (single DATABASE_URL / dj-database-url)

DATABASES = {
    "default": dj_database_url.config(),
}


# Google Cloud Storage configuration for media and static files

google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
google_credentials_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")

try:
    if google_credentials_path and os.path.exists(google_credentials_path):
        with open(google_credentials_path, "r", encoding="utf-8") as f:
            google_credentials_info = json.load(f)
    elif google_credentials_base64:
        google_credentials_info = json.loads(
            base64.b64decode(google_credentials_base64).decode("utf-8")
        )
    else:
        raise ValueError("Google Cloud credentials not provided.")

    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
        google_credentials_info
    )

except Exception as e:
    logging.error("Error loading Google Cloud credentials: %s", e)
    raise ValueError("Error while loading Google Cloud Credentials!")


STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "project_id": os.getenv("G_CLOUD_PROJECT_ID"),
            "bucket_name": os.getenv("G_CLOUD_BUCKET_NAME_MEDIA"),
            "credentials": GS_CREDENTIALS,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "project_id": os.getenv("G_CLOUD_PROJECT_ID"),
            "bucket_name": os.getenv("G_CLOUD_BUCKET_NAME_STATIC"),
            "credentials": GS_CREDENTIALS,
        },
    },
}


# Celery / Redis configuration for production

CELERY_BROKER_URL = os.getenv("REDIS_URL")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BROKER_USE_SSL = {
    "ssl_cert_reqs": CERT_NONE,
}

CELERY_REDIS_BACKEND_USE_SSL = {
    "ssl_cert_reqs": CERT_NONE,
}

