from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    UserAdminView,
    UserAdminView,
)
from .staff_views import (
    DepartmentListView,
    DoctorByDepartmentListView,
    DoctorScheduleListView,
    AppointmentCreateView,
    AppointmentListView,
    CheckInPatientView,
    CompleteAppointmentView,
    NotificationListView,
    NotificationMarkReadView,
    PatientRegistrationView
)

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User Management (Admin)
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserAdminView.as_view(), name='user_admin_detail'),
    
    # Receptionist Tasks
    path('receptionist/patients/register/', PatientRegistrationView.as_view(), name='receptionist_register_patient'),
    
    # Hospital structure (Receptionist)
    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:dept_id>/doctors/', DoctorByDepartmentListView.as_view(), name='doctor_list_by_dept'),
    
    # Schedules and Appointments (Receptionist/Doctor/Patient)
    path('doctors/<int:doctor_id>/schedule/', DoctorScheduleListView.as_view(), name='doctor_schedule'),
    path('appointments/', AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/create/', AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/<int:appointment_id>/check-in/', CheckInPatientView.as_view(), name='check_in_patient'),
    path('appointments/<int:appointment_id>/complete/', CompleteAppointmentView.as_view(), name='complete_appointment'),
    
    # Notifications (Primary for Doctors)
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:notification_id>/read/', NotificationMarkReadView.as_view(), name='notification_read'),
]