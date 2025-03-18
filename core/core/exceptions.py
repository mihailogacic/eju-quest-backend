from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, CustomValidationException):
        response.data = {"detail": str(exc.detail)}
    return response


class CustomValidationException(APIException):
    status_code = 400
    default_detail = "Invalid input."
    default_code = "invalid"

    def __init__(self, detail):
        super().__init__(detail=detail)
