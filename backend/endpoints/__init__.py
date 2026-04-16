from fastapi import APIRouter

from .flow import router as flow_router
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(flow_router)
