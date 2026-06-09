"""Auth router — see docs/api/v1.md Auth section."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.ratelimit import rate_limit
from app.schemas.token import AuthSuccess, RefreshRequest, TokenPair
from app.schemas.user import ChangePasswordRequest, UserLogin, UserRead, UserSignup
from app.services import auth as auth_svc
from app.services import profile as profile_svc

router = APIRouter()


def _err(exc: auth_svc.AuthError, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"error": {"code": exc.code, "message": exc.message}},
    )


@router.post(
    "/signup",
    response_model=AuthSuccess,
    status_code=status.HTTP_201_CREATED,
    # Brute-force / mass-registration defence — see app/core/ratelimit.py.
    dependencies=[rate_limit("signup", limit=5, window_seconds=60)],
)
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

    # Spin up the primary profile right away so /v1/me/profiles is never empty.
    # The picker UI expects at least one row to land on after signup.
    await profile_svc.ensure_primary_profile(db, user.id, default_name=payload.full_name)
    await db.commit()

    return AuthSuccess(
        tokens=TokenPair(access_token=access, refresh_token=refresh, expires_at=exp),
        user=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthSuccess,
    # Password-guessing defence — 10 attempts/min per client IP.
    dependencies=[rate_limit("login", limit=10, window_seconds=60)],
)
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


@router.post("/change-password", response_model=TokenPair)
async def change_password(
    payload: ChangePasswordRequest, db: DbSession, user: CurrentUser
) -> TokenPair:
    """Change password. Revokes every other session (all refresh families +
    session_version bump) and returns a fresh TokenPair so THIS session
    stays logged in — the frontend swaps its stored tokens for these."""
    try:
        access, refresh_token, exp = await auth_svc.change_password(
            db,
            user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except auth_svc.InvalidCredentials as e:
        raise _err(e, status.HTTP_401_UNAUTHORIZED) from e
    return TokenPair(access_token=access, refresh_token=refresh_token, expires_at=exp)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
