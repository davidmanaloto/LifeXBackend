from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import (
    Department, DoctorSchedule, ScheduleException, 
    Appointment, Notification, StaffInvitation
)

User = get_user_model()






class StaffProvisioningSerializer(serializers.ModelSerializer):
    """Serializer for Admins to provision new staff accounts"""
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'role', 
            'department', 'employee_id', 'license_number', 'specialization',
            'phone_number'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'role': {'required': True},
        }

    def validate(self, attrs):
        role = attrs.get('role')
        if role == 'PATIENT':
            raise serializers.ValidationError("This endpoint is for staff provisioning only.")
        
        # Professional validation
        if role in ['DOCTOR', 'NURSE']:
            if not attrs.get('license_number'):
                raise serializers.ValidationError({"license_number": f"License number is required for {role} accounts."})
        
        if role != 'ADMIN' and not attrs.get('department'):
             raise serializers.ValidationError({"department": "Staff members must be assigned to a department."})
        
        return attrs

    def create(self, validated_data):
        # Generate random password (discarded soon)
        temp_password = User.objects.make_random_password()
        
        # Set staff flags - staff accounts start INACTIVE until invitation claimed
        validated_data['is_staff'] = True
        validated_data['is_active'] = False
        
        if validated_data.get('role') == 'ADMIN':
            validated_data['is_superuser'] = True
            
        user = User.objects.create_user(
            password=temp_password,
            **validated_data
        )
        
        # Create invitation record
        StaffInvitation.objects.create(user=user)
        
        return user


class PatientRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for receptionists to register patients"""
    password = serializers.CharField(
        write_only=True, 
        required=False, 
        style={'input_type': 'password'},
        allow_blank=True
    )
    
    class Meta:
        model = User
        fields = (
            'email', 'password', 'first_name', 'last_name', 
            'role', 'phone_number', 'date_of_birth', 'gender',
            'civil_status', 'nationality', 'religion',
            'address_line1', 'address_line2', 'city', 'state_province', 'postal_code', 'country',
            'government_id_type', 'government_id_number',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'
        )
        
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        validated_data['role'] = 'PATIENT'
        
        if not password:
            password = User.objects.make_random_password()
            
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, max_length=20)
    password = serializers.CharField(
        required=True, 
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        
        if not email and not phone_number:
            raise serializers.ValidationError("Must include either 'email' or 'phone_number'.")
            
        return attrs





class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active',
            'civil_status', 'nationality', 'religion', 'government_id_type', 'government_id_number',
            'department', 'employee_id', 'license_number', 'specialization',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'date_joined', 'last_login'
        )
        read_only_fields = (
            'id', 'role', 'is_active', 'date_joined', 'last_login'
        )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.age


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'date_of_birth', 'gender', 
            'civil_status', 'nationality', 'religion', 
            'government_id_type', 'government_id_number',
            'phone_number', 'address_line1', 'address_line2', 
            'city', 'state_province', 'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship'
        )
    
    def update(self, instance, validated_data):
        """Update user instance"""
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate that new passwords match"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "New password fields didn't match."}
            )
        return attrs
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin user management - includes sensitive fields"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_active', 'is_staff', 'is_superuser',
            'date_of_birth', 'age', 'gender', 'phone_number',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_age(self, obj):
        return obj.age





class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Hospital Departments"""
    staff_count = serializers.IntegerField(source='staff_members.count', read_only=True)
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'code', 'description', 'is_active', 'staff_count')


class DoctorScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Doctor Schedules"""
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorSchedule
        fields = (
            'id', 'doctor', 'doctor_name', 'day_of_week', 'day_name',
            'start_time', 'end_time', 'slot_duration_minutes',
            'max_patients_per_slot', 'is_active'
        )


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointments"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = (
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'booked_by', 'booked_by_name',
            'appointment_date', 'appointment_time',
            'appointment_type', 'status', 'status_display',
            'reason', 'created_at', 'checked_in_at', 'completed_at'
        )
        read_only_fields = ('booked_by', 'created_at', 'checked_in_at', 'completed_at')


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notifications"""
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'notification_type', 'type_display',
            'priority', 'title', 'message', 'related_appointment',
            'is_read', 'created_at'
        )
        read_only_fields = ('recipient', 'created_at')
