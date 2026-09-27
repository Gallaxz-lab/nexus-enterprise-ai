from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import uuid

from app.core.database.connection import get_db
from app.core.database import models, schemas
from app.core.services.org_service import OrgService
from app.core.dependencies import auth_deps

router = APIRouter(tags=["Multi-Tenant Layer"])


@router.post("/organizations", response_model=schemas.OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(org_in: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    return OrgService.construct_isolated_tenant(org_in, db)


@router.get("/admin/dashboard")
def administrative_only_gateway(
    current_admin: models.User = Depends(auth_deps.RoleGuard([models.UserRole.ADMIN]))
):
    return {"clearance_granted": True, "operator_id": str(current_admin.id)}

@router.get("/organizations/my-data")
def get_isolated_tenant_data(
    current_user: models.User = Depends(auth_deps.get_current_user), 
    db: Session = Depends(get_db)
):
    tenant_records = OrgService.fetch_all_tenant_members(current_user.organization_id, db)
    return {
        "access_granted_for_tenant_id": str(current_user.organization_id),
        "visible_organization_records": [
            {"username": u.username, "role": u.role, "email": u.email} for u in tenant_records
        ]
    }
