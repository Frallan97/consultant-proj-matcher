"""
Custom exception classes for consistent error handling.
"""
from typing import Optional


class ServiceUnavailableError(Exception):
    """Raised when a required service is unavailable (503)."""
    def __init__(self, message: str, service: Optional[str] = None):
        self.message = message
        self.service = service
        super().__init__(self.message)


class ValidationError(Exception):
    """Raised when validation fails (422)."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class NotFoundError(Exception):
    """Raised when a resource is not found (404)."""
    def __init__(self, message: str, resource: Optional[str] = None):
        self.message = message
        self.resource = resource
        super().__init__(self.message)


class FileUploadError(Exception):
    """Raised when file upload fails (400/413)."""
    def __init__(self, message: str, reason: Optional[str] = None):
        self.message = message
        self.reason = reason
        super().__init__(self.message)

