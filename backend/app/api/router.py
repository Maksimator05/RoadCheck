from fastapi import APIRouter

from app.api.endpoints import analyze, auth, health, history, profile

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(analyze.router)
router.include_router(history.router)
