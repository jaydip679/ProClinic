"""
Role-based DRF permission classes for ProClinic.
"""

from rest_framework.permissions import BasePermission


STAFF_ROLES = {'ADMIN', 'DOCTOR', 'RECEPTIONIST', 'PHARMACIST', 'ACCOUNTANT'}


class IsPatient(BasePermission):
    """Allow access only to users with the PATIENT role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'PATIENT'
        )


class IsDoctor(BasePermission):
    """Allow access only to users with the DOCTOR role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'DOCTOR'
        )


class IsAdminRole(BasePermission):
    """Allow access only to users with the ADMIN role."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'ADMIN'
        )


class IsStaff(BasePermission):
    """Allow access to any staff role (non-patient)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) in STAFF_ROLES
        )
