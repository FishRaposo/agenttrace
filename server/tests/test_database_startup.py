"""Startup preserves all existing accounts and seeds only an empty local database."""

import pytest
from app import db
from app.auth import verify_password
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_repeated_startup_preserves_admin_and_multiple_users(
    tmp_path, monkeypatch
):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'startup.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "async_session_factory", factory)
    try:
        await db.init_db()
        async with factory() as session:
            admin = (await session.execute(select(User))).scalar_one()
            assert admin.username == "admin" and admin.role == "admin"
            assert verify_password("admin123", admin.hashed_password)
            before = (admin.id, admin.hashed_password, admin.role)
            session.add_all(
                [
                    User(
                        username="one", hashed_password="unchanged-one", role="viewer"
                    ),
                    User(
                        username="two", hashed_password="unchanged-two", role="ingestor"
                    ),
                ]
            )
            await session.commit()
        await db.init_db()
        await db.init_db()
        async with factory() as session:
            users = {
                user.username: user
                for user in (await session.execute(select(User))).scalars()
            }
            assert len(users) == 3
            assert (
                users["admin"].id,
                users["admin"].hashed_password,
                users["admin"].role,
            ) == before
            assert (
                users["one"].role == "viewer"
                and users["one"].hashed_password == "unchanged-one"
            )
            assert (
                users["two"].role == "ingestor"
                and users["two"].hashed_password == "unchanged-two"
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_regular_user_is_not_promoted_or_replaced(tmp_path, monkeypatch):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'existing.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "async_session_factory", factory)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(db.Base.metadata.create_all)
        async with factory() as session:
            session.add(
                User(username="existing", hashed_password="unchanged", role="viewer")
            )
            await session.commit()
        await db.init_db()
        async with factory() as session:
            user = (await session.execute(select(User))).scalar_one()
            assert (user.username, user.hashed_password, user.role) == (
                "existing",
                "unchanged",
                "viewer",
            )
    finally:
        await engine.dispose()
