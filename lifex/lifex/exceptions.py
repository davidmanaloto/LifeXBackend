from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler to provide a uniform error response format.
    Format:
    {
        "status": "error",
        "message": "Human readable message",
        "code": "internal_error_code",
        "details": {} # Original validation errors if any
    }
    """
    # Call standard exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # standard DRF exception
        custom_data = {
            "status": "error",
            "message": str(exc),
            "code": exc.__class__.__name__.lower().replace('exception', ''),
            "details": response.data
        }
        
        # Improve message for common errors
        if response.status_code == 401:
            custom_data["message"] = "Authentication credentials were not provided or are invalid."
        elif response.status_code == 403:
            custom_data["message"] = "You do not have permission to perform this action."
        elif response.status_code == 404:
            custom_data["message"] = "The requested resource was not found."
        elif response.status_code == 400:
            custom_data["message"] = "Invalid request parameters."

        response.data = custom_data
    else:
        # Handled unhandled exceptions (500)
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        
        # Mask exception details in production-like environments
        # (Assuming DEBUG settings are handled at entry point)
        response = Response({
            "status": "error",
            "message": "An unexpected server error occurred. Please contact support.",
            "code": "internal_server_error",
            "details": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
