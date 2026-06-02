"""Admin routes — film CRUD + user list. Requires role=admin."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import AdminUser, DbSession
from app.schemas.film import FilmCreate, FilmDetail, FilmUpdate
from app.schemas.user import UserRead
from app.services import admin as admin_svc

router = APIRouter()


class UserListResponse(BaseModel):
    items: list[UserRead]
    page: int
    page_size: int
    total: int


@router.post("/films", response_model=FilmDetail, status_code=status.HTTP_201_CREATED)
async def create_film(payload: FilmCreate, db: DbSession, _: AdminUser) -> FilmDetail:
    try:
        film = await admin_svc.create_film(db, payload.model_dump())
    except admin_svc.SlugInUse as e:
        raise HTTPException(409, detail={"error": {"code": e.code, "message": e.message}}) from e
    return FilmDetail.model_validate(film)


@router.patch("/films/{film_id}", response_model=FilmDetail)
async def update_film(
    film_id: int, payload: FilmUpdate, db: DbSession, _: AdminUser
) -> FilmDetail:
    try:
        film = await admin_svc.update_film(
            db, film_id, payload.model_dump(exclude_unset=True)
        )
    except admin_svc.FilmNotFound as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e
    return FilmDetail.model_validate(film)


@router.delete("/films/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_film(film_id: int, db: DbSession, _: AdminUser) -> None:
    try:
        await admin_svc.soft_delete_film(db, film_id)
    except admin_svc.FilmNotFound as e:
        raise HTTPException(404, detail={"error": {"code": e.code, "message": e.message}}) from e


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> UserListResponse:
    items, total = await admin_svc.list_users(db, page=page, page_size=page_size)
    return UserListResponse(
        items=[UserRead.model_validate(u) for u in items],
        page=page,
        page_size=page_size,
        total=total,
    )
