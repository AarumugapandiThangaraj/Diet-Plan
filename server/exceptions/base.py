class NutriException(Exception):
    """Base exception for all Nutri-related domain and application exceptions."""
    pass


class AppException(NutriException):
    """Generic application exception with HTTP status code."""
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ValidationException(NutriException):
    """Raised when request validation checks fail outside FastAPI built-ins."""
    pass

class ResourceNotFoundException(NutriException):
    """Raised when requested data (such as meal, food, or cuisine) is not found."""
    pass

class ConfigurationException(NutriException):
    """Raised when application configurations or environment parameters are invalid."""
    pass

class AuthenticationException(NutriException):
    """Raised when request authentication fails."""
    pass

class AuthorizationException(NutriException):
    """Raised when authorization checks fail."""
    pass
