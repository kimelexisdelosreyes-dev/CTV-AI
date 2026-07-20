import jwt
from time import perf_counter

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    started = perf_counter()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        decode_started = perf_counter()
        email = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise credentials_exception from exc
    request.state.authentication_decode_duration_ms = (
        perf_counter() - decode_started
    ) * 1000

    query_started = perf_counter()
    result = await db.execute(select(User).where(User.email == email.lower()))
    request.state.authentication_query_duration_ms = (
        perf_counter() - query_started
    ) * 1000
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    request.state.authentication_duration_ms = (perf_counter() - started) * 1000
    return user
