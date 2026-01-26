from django.urls import path
from .medical_views import (
    PatientRegistrationView,
    PatientListView,
    UploadMedicalRecordView,
    PatientRecordsView,
    MyMedicalRecordsView,
    MyMedicalRecordDetailView,
    VerifyMyRecordView,
    SystemStatsView,
    AuditLogView,
    DownloadMedicalRecordView,
)

app_name = 'blockchain'

urlpatterns = [
    # STAFF endpoints
    path('staff/register-patient/', PatientRegistrationView.as_view(), name='register_patient'),
    path('staff/patients/', PatientListView.as_view(), name='list_patients'),
    path('staff/upload-record/', UploadMedicalRecordView.as_view(), name='upload_record'),
    path('staff/patients/<int:patient_id>/records/', PatientRecordsView.as_view(), name='patient_records'),
    
    # SHARED endpoints (Staff, Admin, Patient - permissions handled in view)
    path('records/<int:record_id>/download/', DownloadMedicalRecordView.as_view(), name='download_record'),
    
    # PATIENT endpoints
    path('patient/my-records/', MyMedicalRecordsView.as_view(), name='my_records'),
    path('patient/my-records/<int:pk>/', MyMedicalRecordDetailView.as_view(), name='my_record_detail'),
    path('patient/my-records/<int:record_id>/verify/', VerifyMyRecordView.as_view(), name='verify_my_record'),
    
    # ADMIN endpoints
    path('admin/system-stats/', SystemStatsView.as_view(), name='system_stats'),
    path('admin/audit-logs/', AuditLogView.as_view(), name='audit_logs'),
]