from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.database import models, schemas

class OrgService:
    @staticmethod
    def construct_isolated_tenant(org_in: schemas.OrganizationCreate, db: Session) -> models.Organization:
        if db.query(models.Organization).filter(models.Organization.name == org_in.name).first():
            raise HTTPException(status_code=400, detail="Corporate namespace already registered.")
        
        new_org = models.Organization(name=org_in.name)
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        return new_org

    @staticmethod
    def fetch_all_tenant_members(org_id, db: Session) -> list[models.User]:
        return db.query(models.User).filter(models.User.organization_id == org_id).all()
