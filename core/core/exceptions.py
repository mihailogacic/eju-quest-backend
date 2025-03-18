from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from django.utils.timezone import now

def custom_exception_handler(exc, context):
    """
    Custom error handler to return consistent error format.
    """
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get('detail', None)
        if isinstance(exc, ValidationError):
            # Flatten error dict for fields
            errors = {k: v[0] if isinstance(v, list) else v for k, v in response.data.items()}
            response.data = {"detail": errors}
        elif detail:
            response.data = {"detail": str(detail)}
        else:
            response.data = {"detail": "An error occurred. Please try again later."}
    return response
