from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware


from app.core.database.connection import engine, Base
from app.core.routers import auth, org


from app.config import settings

from app.modules.talent import router as talent_master_router
from app.modules.audit import router as audits_router
from app.modules.support import router as support_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nexus Enterprise AI",
    description="Unified, multi-tenant cloud automation engine with rigid data boundaries.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Infrastructure"])
def system_health_check():
    """Verifies API engine live states without exposing internal configurations."""
    return {
        "status": "healthy",
        "engine": "FastAPI",
        "tenancy_isolation": "active",
        "version": "1.0.0"
    }

app.include_router(auth.router)
app.include_router(org.router)
app.include_router(talent_master_router.router)
app.include_router(audits_router.router)
app.include_router(support_router.router)
