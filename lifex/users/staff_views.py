from rest_framework import status, generics, filters, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Department, DoctorSchedule, Appointment, Notification, DoctorNurseAssignment
from .serializers import (
    DepartmentSerializer, 
    DoctorScheduleSerializer, 
    AppointmentSerializer, 
    NotificationSerializer,
    UserSerializer
)
from .permissions import IsReceptionist, IsDoctor, IsNurse, CanViewDoctorSchedule, CanManageAppointments

User = get_user_model()

class DepartmentListView(generics.ListAPIView):
    """List all hospital departments"""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class DoctorByDepartmentListView(generics.ListAPIView):
    """List all doctors in a specific department (For Receptionists)"""
    serializer_class = UserSerializer
    permission_classes = [IsReceptionist]
    
    def get_queryset(self):
        dept_id = self.kwargs.get('dept_id')
        return User.objects.filter(role='DOCTOR', department_id=dept_id, is_active=True)

class DoctorScheduleListView(generics.ListAPIView):
    """View schedule for a specific doctor"""
    serializer_class = DoctorScheduleSerializer
    permission_classes = [CanViewDoctorSchedule]
    
    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_id')
        return DoctorSchedule.objects.filter(doctor_id=doctor_id, is_active=True)

class AppointmentCreateView(generics.CreateAPIView):
    """Create a new appointment (Receptionists only)"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsReceptionist]
    
    def perform_create(self, serializer):
        appointment = serializer.save(booked_by=self.request.user)
        
        # Notify the doctor
        Notification.objects.create(
            recipient=appointment.doctor,
            notification_type='NEW_APPOINTMENT',
            priority='NORMAL',
            title='New Appointment Scheduled',
            message=f'New appointment scheduled for {appointment.patient.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}.',
            related_appointment=appointment
        )

class AppointmentListView(generics.ListAPIView):
    """List appointments
    - Receptionists see all
    - Doctors see their own
    - Patients see their own
    """
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageAppointments]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['patient__email', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['appointment_date', 'appointment_time']
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['RECEPTIONIST', 'ADMIN', 'NURSE']:
            return Appointment.objects.all()
        elif user.role == 'DOCTOR':
            return Appointment.objects.filter(doctor=user)
        elif user.role == 'PATIENT':
            return Appointment.objects.filter(patient=user)
        return Appointment.objects.none()

class CheckInPatientView(APIView):
    """Check in a patient for their appointment and notify the doctor"""
    permission_classes = [IsReceptionist]
    
    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'CHECKED_IN'
            appointment.checked_in_at = timezone.now()
            appointment.save()
            
            # Notify the doctor with URGENT priority
            Notification.objects.create(
                recipient=appointment.doctor,
                notification_type='PATIENT_CHECK_IN',
                priority='HIGH',
                title='Patient Arrived',
                message=f'Patient {appointment.patient.get_full_name()} has checked in and is waiting for their appointment.',
                related_appointment=appointment
            )
            
            return Response({'message': 'Patient checked in successfully. Doctor has been notified.'}, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

class CompleteAppointmentView(APIView):
    """Doctors can complete an appointment"""
    permission_classes = [IsDoctor]
    
    def post(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id, doctor=request.user)
            appointment.status = 'COMPLETED'
            appointment.completed_at = timezone.now()
            appointment.save()
            return Response({'message': 'Appointment marked as completed.'}, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

class NotificationListView(generics.ListAPIView):
    """List notifications for the logged in user (Primarily for Doctors)"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

class NotificationMarkReadView(APIView):
    """Mark a notification as read"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification.mark_as_read()
            return Response({'message': 'Notification marked as read'}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class PatientRegistrationView(generics.CreateAPIView):
    """
    Register a new patient (Receptionist access)
    """
    from .serializers import PatientRegistrationSerializer
    queryset = User.objects.all()
    serializer_class = PatientRegistrationSerializer
    permission_classes = [IsReceptionist]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Determine what password was used to show to receptionist
        password_used = request.data.get('password') or 'Password123!'
        
        return Response({
            'message': 'Patient registered successfully',
            'user': UserSerializer(user).data,
            'temporary_password': password_used
        }, status=status.HTTP_201_CREATED)
