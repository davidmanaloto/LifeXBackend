from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from .serializers import (
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    StaffProvisioningSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin
from .utils import send_staff_invitation_email
from .models import StaffInvitation

User = get_user_model()

class UserAdminView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin can view, update or delete any user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'pk'


class StaffProvisioningView(generics.CreateAPIView):
    """
    Provision a new staff member (Admin access)
    """
    queryset = User.objects.all()
    serializer_class = StaffProvisioningSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Invitation and Email (Access user.invitation which was created in serializer)
        invitation = user.invitation
        email_sent = send_staff_invitation_email(invitation, request)
        
        return Response({
            'message': f'Staff account for {user.get_full_name()} provisioned successfully',
            'user': UserSerializer(user).data,
            'invitation_token': str(invitation.token),
            'email_status': 'Sent' if email_sent else 'Failed to send'
        }, status=status.HTTP_201_CREATED)


class StaffActivationView(APIView):
    """
    Handle staff account activation/claiming
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            invite = StaffInvitation.objects.get(token=token, is_claimed=False)
            if invite.is_expired:
                return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'email': invite.user.email,
                'name': invite.user.get_full_name(),
                'role': invite.user.role
            })
        except StaffInvitation.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, token):
        try:
            invite = StaffInvitation.objects.get(token=token, is_claimed=False)
            if invite.is_expired:
                return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            password = request.data.get('password')
            if not password:
                return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                validate_password(password, invite.user)
            except Exception as e:
                return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

            # Activate user
            user = invite.user
            user.set_password(password)
            user.is_active = True
            user.save()
            
            # Claim invite
            invite.is_claimed = True
            invite.save()
            
            return Response({'message': 'Account activated successfully. You can now log in.'})
            
        except StaffInvitation.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_404_NOT_FOUND)






from drf_spectacular.utils import extend_schema, OpenApiResponse

class UserLoginView(APIView):
    """
    Login user and return JWT tokens
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer
    
    @extend_schema(
        summary="User Authentication",
        description="Authenticate user with email/phone and password to receive JWT tokens.",
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid credentials"),
            403: OpenApiResponse(description="Account locked or disabled")
        }
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone_number = serializer.validated_data.get('phone_number')
        password = serializer.validated_data['password'].strip()
        
        user = None
        
        # Check if user is locked out before attempting auth
        temp_user = None
        if email:
            temp_user = User.objects.filter(email=email.lower().strip()).first()
        elif phone_number:
            temp_user = User.objects.filter(phone_number=phone_number).first()
            
        if temp_user and temp_user.failed_login_attempts >= 5:
            # Check if 15 minutes have passed since last failure
            if temp_user.last_failed_login and (timezone.now() - temp_user.last_failed_login).total_seconds() < 900:
                remaining = int(15 - (timezone.now() - temp_user.last_failed_login).total_seconds() / 60)
                return Response(
                    {'error': f'Account locked due to too many failed attempts. Try again in {remaining} minutes.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                # Reset attempts if timeout passed
                temp_user.failed_login_attempts = 0
                temp_user.save()

        if email:
            email = email.lower().strip()
            # Try email auth
            user = authenticate(email=email, password=password)
            if user is None:
                user = authenticate(username=email, password=password)
        elif phone_number:
            # Try finding user by phone number first
            try:
                # Try direct lookup first (for unencrypted records)
                user_obj = User.objects.filter(phone_number=phone_number).first()
                if not user_obj:
                    # Try hash lookup (for encrypted records)
                    import hashlib
                    pn_hash = hashlib.sha256(phone_number.strip().encode()).hexdigest()
                    user_obj = User.objects.filter(phone_number_hash=pn_hash).first()
                
                if user_obj:
                    user = authenticate(email=user_obj.email, password=password)
                    if user is None:
                         user = authenticate(username=user_obj.email, password=password)
            except Exception:
                pass
        
        if user is None:
            # Record failed attempt if user exists
            error_message = 'Invalid credentials'
            if temp_user:
                temp_user.failed_login_attempts += 1
                temp_user.last_failed_login = timezone.now()
                temp_user.save()
                
                # Log lockout if it just happened
                if temp_user.failed_login_attempts == 5:
                    from blockchain.models import AuditLog
                    ip_address = '0.0.0.0'
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip_address = x_forwarded_for.split(',')[0]
                    else:
                        ip_address = request.META.get('REMOTE_ADDR')
                        
                    AuditLog.objects.create(
                        user=None, # User is not logged in
                        action='ACCOUNT_LOCKOUT',
                        resource_type='USER',
                        resource_id=str(temp_user.id),
                        details=f"Account locked for {temp_user.email} after 5 failed attempts.",
                        ip_address=ip_address
                    )
                
                # Warn if close to lockout
                if temp_user.failed_login_attempts >= 3:
                    remaining_attempts = 5 - temp_user.failed_login_attempts
                    if remaining_attempts > 0:
                        error_message = f'Invalid credentials. Warning: {remaining_attempts} attempts remaining before account lockout.'
            
            return Response(
                {'error': error_message},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Success - reset attempts
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Invalid token or token already blacklisted'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Save old password to history
        from .models import PasswordHistory
        PasswordHistory.objects.create(
            user=request.user,
            password_hash=request.user.password
        )
        
        # Set new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )


class UserListView(generics.ListAPIView):
    """
    List all users (Admin and Staff only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admins can see all users
        if user.role == 'ADMIN':
            return User.objects.all()
        
        # Medical Staff (Receptionist, Nurse, Doctor) can see Patients
        if user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return User.objects.filter(role='PATIENT')
        
        # Patients can only see themselves
        return User.objects.filter(id=user.id)