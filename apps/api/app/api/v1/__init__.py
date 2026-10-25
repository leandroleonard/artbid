from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auctioneer, audit, auth, bidder, lots

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(lots.router)
api_router.include_router(auctioneer.router)
api_router.include_router(bidder.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]



