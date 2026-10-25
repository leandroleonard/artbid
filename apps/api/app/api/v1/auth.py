from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, SessionDep, rate_limit
from app.schemas.models import (
    AuthEnvelope,
    LoginRequest,
    LogoutEnvelope,
    ProfileUpdateRequest,
    RegisterRequest,
    UserEnvelope,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", "rate_limit_register_per_hour", 3600))],
    summary="Registar licitante ou leiloeiro",
)
def register(payload: RegisterRequest, session: SessionDep) -> dict:
    user, raw_token, record = auth_service.register(
        session,
        display_name=payload.displayName,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    session.commit()
    return {"data": auth_service.auth_payload(user, raw_token, record)}


@router.post(
    "/login",
    response_model=AuthEnvelope,
    dependencies=[Depends(rate_limit("login", "rate_limit_login_per_minute", 60))],
    summary="Iniciar sessão",
)
def login(payload: LoginRequest, session: SessionDep) -> dict:
    user, raw_token, record = auth_service.login(
        session, email=payload.email, password=payload.password
    )
    session.commit()
    return {"data": auth_service.auth_payload(user, raw_token, record)}


@router.post("/logout", response_model=LogoutEnvelope, summary="Terminar sessão e revogar token")
def logout(auth: CurrentUser, session: SessionDep) -> dict:
    _, record = auth
    revoked = auth_service.logout(session, record)
    session.commit()
    return {"data": {"revoked": revoked}}


@router.get("/me", response_model=UserEnvelope, summary="Perfil autoritativo do utilizador")
def read_me(auth: CurrentUser) -> dict:
    user, _ = auth
    return {"data": auth_service.user_payload(user)}


@router.patch("/me", response_model=UserEnvelope, summary="Actualizar displayName")
def update_me(auth: CurrentUser, payload: ProfileUpdateRequest, session: SessionDep) -> dict:
    user, _ = auth
    auth_service.update_profile(session, user, payload.displayName)
    session.commit()
    return {"data": auth_service.user_payload(user)}
