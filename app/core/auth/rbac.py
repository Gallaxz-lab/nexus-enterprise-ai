from fastapi import HTTPException, Security, status
from app.core.auth.security import get_current_user_claims

class RoleChecker:
    """Restricts API execution routes based on minimum user permissions."""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Security(get_current_user_claims)):
        if current_user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation denied: You do not possess the required security clearance."
            )
        return current_user
