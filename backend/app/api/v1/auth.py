"""Auth router — see docs/api/v1.md Auth section."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.token import AuthSuccess, RefreshRequest, TokenPair
from app.schemas.user import UserLogin, UserRead, UserSignup
from app.services import auth as auth_svc

router = APIRouter()


def _err(exc: auth_svc.AuthError, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


@router.post("/signup", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, db: DbSession) -> AuthSuccess:
    try:
        user, access, refresh, exp = await auth_svc.signup(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except auth_svc.EmailAlreadyRegistered as e:
        raise _err(e, status.HTTP_409_CONFLICT) from e

    return AuthSuccess(
        tokens=TokenPair(access_token=access, refresh_token=refresh, expires_at=exp),
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=AuthSuccess)
async def login(payload: UserLogin, db: DbSession) -> AuthSuccess:
    try:
        user, access, refresh, exp = await auth_svc.login(
            db, email=payload.email, password=payload.password
        )
    except (auth_svc.InvalidCredentials, auth_svc.InactiveUser) as e:
        # We collapse "invalid creds" and "inactive" to 401 with the same message
        # so attackers can't enumerate which emails exist.
        raise _err(auth_svc.InvalidCredentials(), status.HTTP_401_UNAUTHORIZED) from e

    return AuthSuccess(
        tokens=TokenPair(access_token=access, refresh_token=refresh, expires_at=exp),
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        _, access, refresh_token, exp = await auth_svc.refresh(
            db, refresh_token=payload.refresh_token
        )
    except auth_svc.InvalidToken as e:
        raise _err(e, status.HTTP_401_UNAUTHORIZED) from e
    return TokenPair(access_token=access, refresh_token=refresh_token, expires_at=exp)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DbSession) -> None:
    await auth_svc.logout_family(db, refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
