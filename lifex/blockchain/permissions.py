from rest_framework import permissions


class IsNurse(permissions.BasePermission):
    """Permission for Nurses only - can upload medical records"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'NURSE'
        )


class IsDoctor(permissions.BasePermission):
    """Permission for Doctors only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'DOCTOR'
        )


class IsReceptionist(permissions.BasePermission):
    """Permission for Medical Receptionist only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'RECEPTIONIST'
        )


class IsPatient(permissions.BasePermission):
    """Permission for PATIENT users only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PATIENT'
        )


class IsAdmin(permissions.BasePermission):
    """Permission for ADMIN only"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'ADMIN'
        )


class IsMedicalStaff(permissions.BasePermission):
    """Permission for any medical staff (receptionist, nurse, or doctor)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']
        )


class CanUploadRecords(permissions.BasePermission):
    """Permission for users who can upload medical records (nurses only)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'NURSE'
        )


class CanViewRecords(permissions.BasePermission):
    """Permission for users who can view medical records
    - Admin: full access
    - Receptionist: read-only (can view and print, cannot alter)
    - Nurse: can upload and view
    - Doctor: can view all
    - Patient: can view own records
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin can view all
        if request.user.role == 'ADMIN':
            return True
        
        # Medical staff can view records
        if request.user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return True
        
        # Patients can view their own
        if request.user.role == 'PATIENT':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.role == 'ADMIN':
            return True
        
        # Nurse and Doctor can access all records
        if request.user.role in ['NURSE', 'DOCTOR']:
            return True
        
        # Receptionist can only view (read-only)
        if request.user.role == 'RECEPTIONIST':
            return request.method in permissions.SAFE_METHODS
        
        # Patient can only view their own records
        if request.user.role == 'PATIENT':
            if hasattr(obj, 'patient'):
                return obj.patient == request.user
        
        return False


class CanRegisterPatients(permissions.BasePermission):
    """Permission for users who can register new patients (receptionists only)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['RECEPTIONIST', 'ADMIN']
        )
