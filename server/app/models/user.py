"""User model for authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.internal.rbac import Role


class User(Base):
    """SQLAlchemy model for storing user credentials."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=Role.VIEWER.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class UserCreate(BaseModel):
    """Pydantic schema for user registration."""

    username: str = Field(..., description="Unique username")
    password: str = Field(..., description="Plain text password (hashed on storage)")


class UserResponse(BaseModel):
    """Pydantic schema for user responses."""

    id: str
    username: str
    role: Role = Role.VIEWER
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
