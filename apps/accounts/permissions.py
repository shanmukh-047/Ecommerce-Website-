from rest_framework.permissions import BasePermission

from .models import Role


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission allowing only the owner of the resource
    or administrative staff to view/modify it.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check user attribute
        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user


class IsApprovedWholesaleBuyer(BasePermission):
    """
    Allows access only to authenticated users with approved wholesale status.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_wholesale_buyer
        )


class IsStaffOrManager(BasePermission):
    """
    Allows access to staff, managers, and superadmins.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.role in [Role.STAFF, Role.MANAGER, Role.SUPERADMIN]
            or request.user.is_staff
            or request.user.is_superuser
        )


class IsManagerOrAdmin(BasePermission):
    """
    Allows access strictly to managers and superadministrators
    (e.g., for approving or rejecting wholesale KYC accounts).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [Role.MANAGER, Role.SUPERADMIN] or request.user.is_superuser
