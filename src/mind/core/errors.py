"""Error types for Mind v5.

All expected failures use Result[T], never raise.
Only unexpected failures (bugs) should raise exceptions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


class ErrorCode(Enum):
    """Standardized error codes for Mind operations."""

    # Memory errors (1xxx)
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    MEMORY_INVALID_LEVEL = "MEMORY_INVALID_LEVEL"
    MEMORY_DUPLICATE = "MEMORY_DUPLICATE"

    # Decision errors (2xxx)
    DECISION_NOT_FOUND = "DECISION_NOT_FOUND"
    DECISION_ALREADY_OBSERVED = "DECISION_ALREADY_OBSERVED"
    DECISION_INVALID_OUTCOME = "DECISION_INVALID_OUTCOME"

    # Event errors (3xxx)
    EVENT_INVALID_TYPE = "EVENT_INVALID_TYPE"
    EVENT_PUBLISH_FAILED = "EVENT_PUBLISH_FAILED"
    EVENT_REPLAY_FAILED = "EVENT_REPLAY_FAILED"

    # Infrastructure errors (4xxx)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    NATS_CONNECTION_FAILED = "NATS_CONNECTION_FAILED"
    VECTOR_SEARCH_FAILED = "VECTOR_SEARCH_FAILED"

    # Validation errors (5xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"

    # Privacy errors (6xxx)
    PRIVACY_VIOLATION = "PRIVACY_VIOLATION"
    PII_DETECTED = "PII_DETECTED"


@dataclass(frozen=True)
class MindError(Exception):
    """Base error for all Mind operations.

    Use for expected failures that should be handled gracefully.
    Never log PII in context.
    """

    code: ErrorCode
    message: str
    context: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "context": self.context,
            }
        }


@dataclass(frozen=True)
class Result(Generic[T]):
    """Explicit success/failure wrapper.

    Use instead of exceptions for expected failures.
    Forces callers to handle both cases explicitly.
    """

    _value: T | None = None
    _error: MindError | None = None

    @property
    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self._error is None

    @property
    def is_err(self) -> bool:
        """Check if result is an error."""
        return self._error is not None

    @property
    def value(self) -> T:
        """Get the success value. Raises if error."""
        if self._error is not None:
            raise ValueError(f"Cannot get value from error result: {self._error}")
        return self._value  # type: ignore

    @property
    def error(self) -> MindError:
        """Get the error. Raises if success."""
        if self._error is None:
            raise ValueError("Cannot get error from success result")
        return self._error

    def unwrap_or(self, default: T) -> T:
        """Get value or return default if error."""
        if self._error is not None:
            return default
        return self._value  # type: ignore

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        """Create a success result."""
        return cls(_value=value)

    @classmethod
    def err(cls, error: MindError) -> "Result[T]":
        """Create an error result."""
        return cls(_error=error)
