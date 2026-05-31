"""Authentication API — endpoints for user authentication."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


class User(BaseModel):
    """User model for authentication."""

    username: str


class UserInDB(User):
    """User model with hashed password."""

    hashed_password: str


# In production, this should be stored in a database
# For now, we'll use a simple in-memory store
fake_users_db: dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        hashed_password=get_password_hash("admin123"),
    ),
}


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """User creation model."""

    username: str
    password: str


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current user from the JWT token.

    Args:
        token: The JWT access token.

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

    user = fake_users_db.get(username)
    if user is None:
        raise credentials_exception

    return user


async def get_optional_user(token: str | None = Depends(optional_oauth2_scheme)) -> User | None:
    """Get the current user from an optional JWT token.

    Returns None if no valid auth header is present.

    Args:
        token: The optional JWT access token.

    Returns:
        The current user or None if not authenticated.
    """
    if token is None:
        return None
    try:
        return await get_current_user(token=token)
    except HTTPException:
        return None


@router.post("/auth/register", response_model=User, status_code=201)
async def register(user_data: UserCreate) -> User:
    """Register a new user.

    Args:
        user_data: The user registration data.

    Returns:
        The created user.

    Raises:
        HTTPException: If the username already exists.
    """
    if user_data.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    user = UserInDB(username=user_data.username, hashed_password=hashed_password)
    fake_users_db[user_data.username] = user

    return User(username=user.username)


@router.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Login and get an access token.

    Args:
        form_data: The OAuth2 password form data.

    Returns:
        The access token.

    Raises:
        HTTPException: If the username or password is incorrect.
    """
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
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
