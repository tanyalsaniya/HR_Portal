from rest_framework.permissions import BasePermission
from rules import ROLE_ADMIN, ROLE_HR, ROLE_MANAGEMENT

class IsAdminUserRole(BasePermission):
    """
    Allows access only to Admin users (and superusers).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            ((request.user.role and request.user.role.code == ROLE_ADMIN) or request.user.is_superuser)
        )

class IsHRUserRole(BasePermission):
    """
    Allows access to Admin, HR, and Management users.
    Note: Certain write actions (like approve salary increments or delete employee)
    are protected separately at the endpoint or method level.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role and request.user.role.code in (ROLE_ADMIN, ROLE_HR, ROLE_MANAGEMENT)
        )

class IsManagementUserRole(BasePermission):
    """
    Allows access to Admin and Management users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role and request.user.role.code in (ROLE_ADMIN, ROLE_MANAGEMENT)
        )