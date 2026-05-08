from typing import Optional

class KrishiBondhuException(Exception):
    """Base exception for all domain errors in Krishi-Bondhu."""
    def __init__(self, message: str, detail: Optional[str] = None, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.detail = detail
        self.code = code
        super().__init__(self.message)

class KrishiBondhuClientException(KrishiBondhuException):
    """Base for 400-range errors."""
    pass

class ResourceNotFoundException(KrishiBondhuClientException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            detail=f"Could not find {resource} with identifier {identifier}",
            code="RESOURCE_NOT_FOUND"
        )

class InvalidInputException(KrishiBondhuClientException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message=message, detail=detail, code="INVALID_INPUT")

class UnauthorizedException(KrishiBondhuClientException):
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message=message, code="UNAUTHORIZED")

class KrishiBondhuServerException(KrishiBondhuException):
    """Base for 500-range errors."""
    pass

class AgentTimeoutException(KrishiBondhuServerException):
    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent {agent_name} timed out",
            detail="The AI agent took too long to respond. Please try again.",
            code="AGENT_TIMEOUT"
        )

class DatabaseError(KrishiBondhuServerException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message=message, code="DATABASE_ERROR")

class ExternalServiceException(KrishiBondhuServerException):
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {service}",
            detail=message,
            code="EXTERNAL_SERVICE_ERROR"
        )
