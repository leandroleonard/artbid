from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter()

__all__ = ["api_router"]



