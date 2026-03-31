from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from app.db.models import User
from app.repositories import token_repo, user_repo
from app.schemas import Token


async def register(db: AsyncSession, email: str, password: str) -> Token:
    if await user_repo.get_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await user_repo.create(db, email, hash_password(password))
    return await _issue_tokens(db, user)


async def login(db: AsyncSession, email: str, password: str) -> Token:
    user = await user_repo.get_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return await _issue_tokens(db, user)


async def refresh(db: AsyncSession, raw_token: str) -> Token:
    stored = await token_repo.get_by_hash(db, hash_refresh_token(raw_token))

    if not stored or stored.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    await token_repo.revoke(db, stored)

    user = await user_repo.get_by_id(db, stored.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return await _issue_tokens(db, user)


async def change_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )
    await user_repo.update_password(db, user, hash_password(new_password))


async def logout(db: AsyncSession, raw_token: str) -> None:
    stored = await token_repo.get_by_hash(db, hash_refresh_token(raw_token))
    if stored and not stored.revoked:
        await token_repo.revoke(db, stored)


async def _issue_tokens(db: AsyncSession, user: User) -> Token:
    access = create_access_token(str(user.id), user.email, user.role)
    raw_refresh, refresh_hash = generate_refresh_token()
    await token_repo.save(db, user.id, refresh_hash, refresh_token_expires_at())
    return Token(access_token=access, refresh_token=raw_refresh)
