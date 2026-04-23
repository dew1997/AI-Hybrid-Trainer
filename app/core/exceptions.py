from fastapi import HTTPException, status


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} '{resource_id}' not found", status_code=404)


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class PipelineError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class AgentError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class AgentMaxTurnsError(AgentError):
    def __init__(self, max_turns: int):
        super().__init__(f"Agent exceeded maximum of {max_turns} turns without a final answer")
