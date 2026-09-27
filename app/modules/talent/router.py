# Save this code inside app/modules/talent/router.py
from fastapi import APIRouter
from app.modules.talent.candidates import router as candidates_sub_router
from app.modules.talent.jobs import router as jobs_sub_router

# The master router that combines both pipelines
router = APIRouter()

# Mount both sub-modules cleanly
router.include_router(candidates_sub_router.router)
router.include_router(jobs_sub_router.router)