"""Standard response shapes for the HTTP API."""

from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    """Standard list response with count and pagination hint.

    Attributes:
        items: The list of items
        count: Number of items in this response
        has_more: Whether more items exist beyond the limit
    """
    items: List[T]
    count: int
    has_more: bool

    @classmethod
    def from_items(
        cls,
        items: list,
        limit: int = 100,
    ) -> "ListResponse":
        """Create a ListResponse from a list of items.

        If len(items) > limit, truncates and sets has_more=True.
        Call with limit+1 items to detect has_more.
        """
        has_more = len(items) > limit
        truncated = items[:limit]
        return cls(
            items=truncated,
            count=len(truncated),
            has_more=has_more,
        )


# Default limit for list endpoints
DEFAULT_LIMIT = 100
