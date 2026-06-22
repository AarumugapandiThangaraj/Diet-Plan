import contextvars
import logging
import uuid
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from exceptions.base import (
    NutriException,
    ValidationException,
    ResourceNotFoundException,
    ConfigurationException,
    AuthenticationException,
    AuthorizationException
)
from exceptions.repository import RepositoryException
from exceptions.service import (
    ServiceException,
    DatabaseException,
    AIServiceException,
    ExternalDependencyException
)
from exceptions.domain import (
    NutritionCalculationException,
    SwapEngineException,
    PlanGenerationException
)

logger = logging.getLogger("app.errors")
request_id_ctx_var = contextvars.ContextVar("request_id", default=None)

def get_request_id() -> str:
    req_id = request_id_ctx_var.get()
    if not req_id:
        req_id = str(uuid.uuid4())
        request_id_ctx_var.set(req_id)
    return req_id

def make_error_response(code: str, message: str, status_code: int = 500, details: any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details
            }
        }
    )

def register_global_handlers(app):
    
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        req_id = get_request_id()
        logger.warning(
            f"ValidationException: {exc}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "ValidationException"}
        )
        return make_error_response("VALIDATION_ERROR", str(exc), 400)

    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
        req_id = get_request_id()
        logger.warning(
            f"ResourceNotFoundException: {exc}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "ResourceNotFoundException"}
        )
        return make_error_response("RESOURCE_NOT_FOUND", str(exc), 404)

    @app.exception_handler(ConfigurationException)
    async def configuration_exception_handler(request: Request, exc: ConfigurationException):
        req_id = get_request_id()
        logger.error(
            f"ConfigurationException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "ConfigurationException"}
        )
        return make_error_response("CONFIGURATION_ERROR", "Server configuration error", 500)

    @app.exception_handler(AuthenticationException)
    async def authentication_exception_handler(request: Request, exc: AuthenticationException):
        req_id = get_request_id()
        logger.warning(
            f"AuthenticationException: {exc}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "AuthenticationException"}
        )
        return make_error_response("AUTHENTICATION_ERROR", str(exc), 401)

    @app.exception_handler(AuthorizationException)
    async def authorization_exception_handler(request: Request, exc: AuthorizationException):
        req_id = get_request_id()
        logger.warning(
            f"AuthorizationException: {exc}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "AuthorizationException"}
        )
        return make_error_response("AUTHORIZATION_ERROR", str(exc), 403)

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(request: Request, exc: DatabaseException):
        req_id = get_request_id()
        logger.error(
            f"DatabaseException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "DatabaseException"}
        )
        # Sanitized error message to protect database details
        return make_error_response("DATABASE_ERROR", "A database operational error occurred.", 500)

    @app.exception_handler(AIServiceException)
    async def ai_service_exception_handler(request: Request, exc: AIServiceException):
        req_id = get_request_id()
        logger.error(
            f"AIServiceException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "AIServiceException"}
        )
        return make_error_response("AI_SERVICE_ERROR", "Failed to process AI companion request.", 500)

    @app.exception_handler(ExternalDependencyException)
    async def external_dependency_exception_handler(request: Request, exc: ExternalDependencyException):
        req_id = get_request_id()
        logger.error(
            f"ExternalDependencyException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "ExternalDependencyException"}
        )
        return make_error_response("EXTERNAL_DEPENDENCY_ERROR", "A connection dependency failure occurred.", 502)

    @app.exception_handler(NutritionCalculationException)
    async def nutrition_calculation_handler(request: Request, exc: NutritionCalculationException):
        req_id = get_request_id()
        logger.error(
            f"NutritionCalculationException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "NutritionCalculationException"}
        )
        return make_error_response("NUTRITION_CALCULATION_ERROR", str(exc), 400)

    @app.exception_handler(SwapEngineException)
    async def swap_engine_handler(request: Request, exc: SwapEngineException):
        req_id = get_request_id()
        logger.error(
            f"SwapEngineException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "SwapEngineException"}
        )
        return make_error_response("SWAP_ENGINE_ERROR", str(exc), 400)

    @app.exception_handler(PlanGenerationException)
    async def plan_generation_handler(request: Request, exc: PlanGenerationException):
        req_id = get_request_id()
        logger.error(
            f"PlanGenerationException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "PlanGenerationException"}
        )
        return make_error_response("PLAN_GENERATION_ERROR", str(exc), 400)

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        req_id = get_request_id()
        logger.error(
            f"ServiceException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "ServiceException"}
        )
        return make_error_response("SERVICE_ERROR", str(exc), 400)

    @app.exception_handler(RepositoryException)
    async def repository_exception_handler(request: Request, exc: RepositoryException):
        req_id = get_request_id()
        logger.error(
            f"RepositoryException: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "RepositoryException"}
        )
        return make_error_response("REPOSITORY_ERROR", "A storage repository error occurred.", 500)

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(request: Request, exc: RequestValidationError):
        req_id = get_request_id()
        logger.warning(
            f"Pydantic Validation Error: {exc.errors()}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "RequestValidationError"}
        )
        return make_error_response("VALIDATION_ERROR", "Invalid request parameters.", 422, exc.errors())

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = get_request_id()
        logger.info(
            f"HTTPException: status={exc.status_code} detail={exc.detail}",
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "HTTPException"}
        )
        return make_error_response(f"HTTP_{exc.status_code}", str(exc.detail), exc.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def raw_sqlalchemy_handler(request: Request, exc: SQLAlchemyError):
        req_id = get_request_id()
        logger.critical(
            f"Unhandled SQLAlchemyError: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "SQLAlchemyError"}
        )
        # Protect internal SQL queries and credentials
        return make_error_response("DATABASE_ERROR", "A database persistence error occurred.", 500)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id()
        logger.critical(
            f"Unhandled exception on {request.url.path}: {exc}",
            exc_info=True,
            extra={"request_id": req_id, "endpoint": request.url.path, "exception_type": "UnhandledException"}
        )
        return make_error_response("INTERNAL_SERVER_ERROR", "An unexpected error occurred. Please try again later.", 500)
