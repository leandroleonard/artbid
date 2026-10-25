from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, lots

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(lots.router)

__all__ = ["api_router"]



