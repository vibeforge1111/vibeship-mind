"""User model routes for the HTTP API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mind.models import UserModel, UserModelUpdate
from mind.storage.sqlite import SQLiteStorage
from mind.api.deps import get_storage


router = APIRouter(prefix="/user", tags=["user"])


class UserUpdateRequest(BaseModel):
    """Request body for updating user model."""
    name: Optional[str] = None
    current_energy: Optional[str] = None
    current_focus: Optional[str] = None
    add_win: Optional[str] = None
    add_frustration: Optional[str] = None


@router.get("")
async def get_user(
    storage: SQLiteStorage = Depends(get_storage),
) -> UserModel:
    """Get the user model."""
    return await storage.get_or_create_user()


@router.patch("")
async def update_user(
    data: UserUpdateRequest,
    storage: SQLiteStorage = Depends(get_storage),
) -> UserModel:
    """Update the user model."""
    storage_update = UserModelUpdate(
        name=data.name,
        current_energy=data.current_energy,
        current_focus=data.current_focus,
        add_win=data.add_win,
        add_frustration=data.add_frustration,
    )
    return await storage.update_user(storage_update)
