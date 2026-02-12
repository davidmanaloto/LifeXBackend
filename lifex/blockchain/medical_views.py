from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from .models import MedicalRecord, BlockchainTransaction, AuditLog
from .medical_serializers import (
    PatientListSerializer,
    MedicalRecordUploadSerializer,
    MedicalRecordSerializer,
    AuditLogSerializer
)
from users.serializers import PatientRegistrationSerializer
from .permissions import (
    IsNurse, 
    IsPatient, 
    IsAdmin, 
    IsReceptionist, 
    IsMedicalStaff,
    CanViewRecords, 
    CanRegisterPatients,
    CanUploadRecords
)
from .blockchain_service import BlockchainService
from .utils import generate_document_id, hash_file


def log_action(user, action, resource_type='', resource_id='', details='', request=None, is_encrypted=False):
    """Helper to create audit log"""
    ip_address = '0.0.0.0'
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
        ip_address=ip_address,
        is_encrypted=is_encrypted
    )


User = get_user_model()


# ==================== STAFF VIEWS ====================

class PatientRegistrationView(generics.CreateAPIView):
    """Staff can register new patients"""
    permission_classes = [CanRegisterPatients]
    serializer_class = PatientRegistrationSerializer
    
    def perform_create(self, serializer):
        user = serializer.save()
        log_action(
            user=self.request.user, 
            action='REGISTER_PATIENT', 
            resource_type='USER', 
            resource_id=user.id, 
            details=f"Registered patient {user.email}",
            request=self.request
        )


class PatientListView(generics.ListAPIView):
    """Staff view all patients"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['first_name', 'last_name', 'date_joined']
    
    def get_queryset(self):
        # Only medical staff/admin can see patients
        if self.request.user.role not in ['ADMIN', 'RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return User.objects.none()
            
        return User.objects.filter(role='PATIENT').order_by('-date_joined')


# ==================== NURSE VIEWS ====================

class UploadMedicalRecordView(APIView):
    """Nurses upload medical records for patients"""
    permission_classes = [CanUploadRecords]
    
    def post(self, request):
        serializer = MedicalRecordUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get patient
        patient_email = serializer.validated_data.pop('patient_email')
        patient = User.objects.get(email=patient_email, role='PATIENT')
        
        # Get uploaded file
        document_file = serializer.validated_data['document_file']
        
        try:
            # Generate document ID
            document_id = generate_document_id()
            
            # Hash the document
            document_hash = hash_file(document_file)
            
            # Register on blockchain
            blockchain_service = BlockchainService()
            tx_result = blockchain_service.register_document(
                user_id=patient.id,
                document_id=document_id,
                document_hash=document_hash,
                document_type=serializer.validated_data['record_type']
            )
            
            # Get blockchain address
            blockchain_address = blockchain_service.get_account_for_user(patient.id)
            
            # Create medical record - save via serializer to ensure encryption logic runs
            medical_record = serializer.save(
                patient=patient,
                uploaded_by=request.user,
                document_id=document_id,
                document_hash=document_hash,
                blockchain_address=blockchain_address,
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                status='CONFIRMED',
                is_verified=True,
                is_encrypted=True,
                registered_on_blockchain_at=timezone.now()
            )
            
            # Log blockchain transaction
            BlockchainTransaction.objects.create(
                user=patient,
                transaction_type='REGISTER',
                transaction_hash=tx_result['transaction_hash'],
                block_number=tx_result['block_number'],
                gas_used=tx_result['gas_used'],
                status='SUCCESS'
            )
            
            # Log the upload action
            log_action(
                user=request.user,
                action='UPLOAD_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=medical_record.id,
                details=f"Uploaded {medical_record.record_type} for patient {patient.email}. Status: ENCRYPTED",
                request=request,
                is_encrypted=True
            )
            
            return Response({
                'message': 'Medical record uploaded and registered on blockchain successfully',
                'record': MedicalRecordSerializer(medical_record, context={'request': request}).data,
                'blockchain_data': {
                    'transaction_hash': tx_result['transaction_hash'],
                    'block_number': tx_result['block_number'],
                    'gas_used': tx_result['gas_used']
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': f'Failed to upload medical record: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientRecordsView(generics.ListAPIView):
    """View all records for a specific patient
    - Receptionist: read-only access
    - Nurse/Doctor: full access
    - Patient: own records only
    """
    permission_classes = [CanViewRecords]
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        user = self.request.user
        
        # Patients can only view their own records
        if user.role == 'PATIENT':
            return MedicalRecord.objects.filter(patient=user)
        
        # Medical staff can view any patient's records
        return MedicalRecord.objects.filter(patient_id=patient_id)


# ==================== PATIENT VIEWS ====================

class MyMedicalRecordsView(generics.ListAPIView):
    """Patients can view their own medical records"""
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'record_type']
    ordering_fields = ['date_of_service', 'created_at']
    ordering = ['-date_of_service']
    
    def get_queryset(self):
        # Log the view action
        log_action(
            user=self.request.user,
            action='VIEW_RECORDS',
            resource_type='MEDICAL_RECORD',
            details='Viewed medical records (on-the-fly decryption)',
            request=self.request,
            is_encrypted=True
        )
        return MedicalRecord.objects.filter(patient=self.request.user)


class MyMedicalRecordDetailView(generics.RetrieveAPIView):
    """Patients can view a specific medical record"""
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordSerializer
    
    def get_queryset(self):
        return MedicalRecord.objects.filter(patient=self.request.user)


class VerifyMyRecordView(APIView):
    """Patients can verify their medical records on blockchain"""
    permission_classes = [IsPatient]
    
    def post(self, request, record_id):
        try:
            # Get the record
            record = MedicalRecord.objects.get(id=record_id, patient=request.user)
            
            # Open and hash the file
            document_hash = hash_file(record.document_file)
            
            # Verify on blockchain
            blockchain_service = BlockchainService()
            verification_result = blockchain_service.verify_document(
                document_id=record.document_id,
                document_hash=document_hash
            )
            
            # Update record verification status
            record.is_verified = verification_result['is_valid']
            record.save()
            
            # Log verification transaction
            BlockchainTransaction.objects.create(
                user=request.user,
                transaction_type='VERIFY',
                transaction_hash=verification_result['transaction_hash'],
                block_number=verification_result['block_number'],
                gas_used=verification_result['gas_used'],
                status='SUCCESS' if verification_result['is_valid'] else 'FAILED'
            )
            
            # Log the verification action
            log_action(
                user=request.user,
                action='VERIFY_RECORD',
                resource_type='MEDICAL_RECORD',
                resource_id=record.id,
                details=f"Verified record {record.document_id}. Result: {record.is_verified}",
                request=request
            )
            
            return Response({
                'is_valid': verification_result['is_valid'],
                'blockchain_data': verification_result
            }, status=status.HTTP_200_OK)
            
        except MedicalRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Verification failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADMIN VIEWS ====================
from users.models import Appointment

class SystemStatsView(APIView):
    """Admin can view system statistics"""
    permission_classes = [IsAdmin | IsMedicalStaff]
    
    def get(self, request):
        today = timezone.now().date()
        
        # Base stats for everyone
        stats = {
            'patients': {
                'total': User.objects.filter(role='PATIENT').count(),
            },
            'staff': {
                'receptionists': User.objects.filter(role='RECEPTIONIST').count(),
                'nurses': User.objects.filter(role='NURSE').count(),
                'doctors': User.objects.filter(role='DOCTOR').count(),
            },
            'medical_records': {
                'total': MedicalRecord.objects.count(),
                'confirmed': MedicalRecord.objects.filter(status='CONFIRMED').count(),
                'encrypted': MedicalRecord.objects.filter(is_encrypted=True).count(),
            },
            'blockchain_transactions': {
                'total': BlockchainTransaction.objects.count(),
            }
        }

        # Personalized stats for doctors
        if request.user.role == 'DOCTOR':
            stats['personal'] = {
                'today_appointments': Appointment.objects.filter(
                    doctor=request.user, 
                    appointment_date=today
                ).count(),
                'pending_checkins': Appointment.objects.filter(
                    doctor=request.user,
                    appointment_date=today,
                    status='CHECKED_IN'
                ).count()
            }
        
        return Response(stats, status=status.HTTP_200_OK)
            
            
class AuditLogView(generics.ListAPIView):
    """Admin can view audit logs"""
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AuditLog.objects.all()


from django.http import FileResponse
from django.shortcuts import get_object_or_404


class DownloadMedicalRecordView(APIView):
    """
    Securely download medical record file and log the action.
    Accessible by: 
    - Patient (own records only)
    - Receptionist (read-only, can print)
    - Nurse/Doctor (full access)
    - Admin (full access)
    """
    permission_classes = [CanViewRecords]
    
    def get(self, request, record_id):
        record = get_object_or_404(MedicalRecord, id=record_id)
        
        # Check permissions based on role
        user = request.user
        
        # Patients can only download their own records
        if user.role == 'PATIENT' and record.patient != user:
            return Response({
                'error': 'You can only access your own medical records'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Log the download
        log_action(
            user=request.user,
            action='DOWNLOAD_RECORD',
            resource_type='MEDICAL_RECORD',
            resource_id=record.id,
            details=f"Downloaded file: {record.document_file.name}",
            request=request,
            is_encrypted=True
        )
        
        # Serve file
        if record.document_file:
            response = FileResponse(record.document_file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{record.document_file.name.split("/")[-1]}"'
            return response
        else:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)