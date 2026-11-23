"""Custom exceptions for Sarvam AI speech and LLM adapters."""

from typing import Optional

class SarvamAPIError(Exception):
    """Base exception for Sarvam API failures."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

class SarvamAuthenticationError(SarvamAPIError):
    """Raised on 401 Unauthorized or 403 Forbidden."""
    pass

class SarvamRateLimitError(SarvamAPIError):
    """Raised on 429 Too Many Requests."""
    pass

class SarvamServerError(SarvamAPIError):
    """Raised on 5xx upstream server errors."""
    pass

class SarvamTimeoutError(SarvamAPIError):
    """Raised when request times out."""
    pass

class InvalidToolCallError(SarvamAPIError):
    """Raised when LLM returns invalid or missing transfer proposals."""
    pass
