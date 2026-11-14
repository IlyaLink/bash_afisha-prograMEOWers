"""Корневой роутер REST API v1."""

from fastapi import APIRouter
from src.api.events import router as events_router
from src.api.references import router as references_router
from src.api.subscriptions import router as subscriptions_router
from src.api.feedback import router as feedback_router
from src.api.admin_api import router as admin_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(events_router)
api_v1_router.include_router(references_router)
api_v1_router.include_router(subscriptions_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(admin_router)
