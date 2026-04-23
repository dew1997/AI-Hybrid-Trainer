from fastapi import APIRouter

from app.api.v1 import auth, workouts, analytics, agent, plans

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(agent.router, prefix="/agent", tags=["agent"])
router.include_router(plans.router, prefix="/agent/plans", tags=["plans"])
