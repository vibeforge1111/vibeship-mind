"""Error handling for the HTTP API."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    """Standard error response shape."""
    error: str
    code: str
    detail: Optional[dict] = None


class MindAPIError(HTTPException):
    """Custom API error with consistent response format."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        detail: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.error_detail = detail
        super().__init__(
            status_code=status_code,
            detail={
                "error": message,
                "code": code,
                "detail": detail,
            },
        )


# Convenience constructors
def not_found(resource: str, id: str) -> MindAPIError:
    """404 Not Found error."""
    return MindAPIError(
        code="NOT_FOUND",
        message=f"{resource} not found: {id}",
        status_code=404,
    )


def validation_error(message: str, detail: dict) -> MindAPIError:
    """400 Validation Error."""
    return MindAPIError(
        code="VALIDATION_ERROR",
        message=message,
        status_code=400,
        detail=detail,
    )


def conflict(message: str) -> MindAPIError:
    """409 Conflict error."""
    return MindAPIError(
        code="CONFLICT",
        message=message,
        status_code=409,
    )


def internal_error(message: str = "Internal server error") -> MindAPIError:
    """500 Internal Error."""
    return MindAPIError(
        code="INTERNAL_ERROR",
        message=message,
        status_code=500,
    )


async def mind_exception_handler(request: Request, exc: MindAPIError) -> JSONResponse:
    """Handler for MindAPIError exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
            "detail": exc.error_detail,
        },
    )
