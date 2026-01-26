from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import (
    Department, 
    DoctorSchedule, 
    ScheduleException, 
    Appointment, 
    Notification,
    DoctorNurseAssignment
)

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model"""
    
    list_display = ('email', 'first_name', 'last_name', 'role', 'department', 'is_active', 'date_joined')
    list_filter = ('role', 'department', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name', 'employee_id')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'date_of_birth', 'gender', 'phone_number')}),
        ('Professional Info', {'fields': ('role', 'department', 'employee_id', 'license_number', 'specialization')}),
        ('Address', {'fields': (
            'address_line1', 'address_line2', 'city', 'state_province', 'postal_code', 'country'
        )}),
        ('Emergency Contact', {'fields': (
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'
        )}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'department', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(DoctorNurseAssignment)
class DoctorNurseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'nurse', 'is_primary', 'created_at')
    list_filter = ('is_primary',)
    search_fields = ('doctor__email', 'nurse__email')

@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active')
    search_fields = ('doctor__email', 'doctor__first_name', 'doctor__last_name')

@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'exception_type', 'date', 'start_time', 'end_time')
    list_filter = ('exception_type', 'date')
    search_fields = ('doctor__email',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('status', 'appointment_date', 'appointment_type')
    search_fields = ('patient__email', 'doctor__email', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'checked_in_at', 'completed_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'priority', 'is_read', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'title', 'message')
    readonly_fields = ('created_at',)