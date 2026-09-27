from fastapi import Depends, HTTPException, status
from app.core.auth import security
from app.core.database import models

# Re-use our existing modern JWT resolver logic
get_current_user = security.get_current_user

class RoleGuard:
    """Enforces minimum Role-Based Access Control requirements across targeted routes."""
    def __init__(self, required_roles: list[models.UserRole]):
        self.required_roles = required_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in self.required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Clearance Denied: Administrative authority required."
            )
        return current_user
