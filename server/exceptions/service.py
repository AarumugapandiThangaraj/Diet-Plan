from exceptions.base import NutriException

class ServiceException(NutriException):
    """Base exception for all service layer business logic failures."""
    pass

class DatabaseException(NutriException):
    """Raised for database query failures, connection losses, or transaction rollbacks."""
    pass

class AIServiceException(NutriException):
    """Raised when the AI integration/LLM errors out, times out, or returns invalid structure."""
    pass

class ExternalDependencyException(NutriException):
    """Raised when third-party endpoints or downstream system interfaces error out."""
    pass
