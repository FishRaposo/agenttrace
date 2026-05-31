"""Authentication API — endpoints for user authentication."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db import get_session
from app.models.user import User as UserDB

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


class User(BaseModel):
    """User model for authentication."""

    username: str


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User creation model."""

    username: str
    password: str


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get the current user from the JWT token.

    Args:
        token: The JWT access token.
        session: Async database session.

    Returns:
        The current user.

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist.
    """
    from app.auth import decode_access_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await session.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return User(username=user.username)


async def get_optional_user(
    token: str | None = Depends(optional_oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Get the current user from an optional JWT token.

    Returns None if no valid auth header is present.

    Args:
        token: The optional JWT access token.
        session: Async database session.

    Returns:
        The current user or None if not authenticated.
    """
    if token is None:
        return None
    try:
        return await get_current_user(token=token, session=session)
    except HTTPException:
        return None


@router.post("/auth/register", response_model=User, status_code=201)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Register a new user.

    Args:
        user_data: The user registration data.
        session: Async database session.

    Returns:
        The created user.

    Raises:
        HTTPException: If the username already exists.
    """
    existing = await session.execute(
        select(UserDB).where(UserDB.username == user_data.username)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    user = UserDB(username=user_data.username, hashed_password=hashed_password)
    session.add(user)
    await session.flush()

    return User(username=user.username)


@router.post("/auth/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Token:
    """Login and get an access token.

    Args:
        form_data: The OAuth2 password form data.
        session: Async database session.

    Returns:
        The access token.

    Raises:
        HTTPException: If the username or password is incorrect.
    """
    result = await session.execute(
        select(UserDB).where(UserDB.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """Get the current authenticated user.

    Args:
        current_user: The current authenticated user.

    Returns:
        The current user.
    """
    return current_user
